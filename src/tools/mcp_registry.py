from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
	from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:  # pragma: no cover - optional dependency
	TfidfVectorizer = None

try:
	import tiktoken
except ImportError:  # pragma: no cover - optional dependency
	tiktoken = None

from mcp.client import Client
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

from src.mcp_server.config import MCPServerConfig, load_server_configs
from src.tools.tool_schemas import MEMORY_TOOLS

logger = logging.getLogger(__name__)

_ALWAYS_KEEP_TOOL_NAMES = {"add_memory", "search_memory"}


@dataclass
class _ConnectedServer:
	config: MCPServerConfig
	client: Client
	session: ClientSession


class MCPClientRegistry:
	def __init__(self, configs: list[MCPServerConfig] | None = None, config_path: str | Path | None = None) -> None:
		self._config_path = config_path
		self._configs = configs or load_server_configs(config_path)
		self._clients: dict[str, Client] = {}

	async def connect_all(self) -> dict[str, ClientSession]:
		tasks = [self._connect_one(config) for config in self._configs]
		results = await asyncio.gather(*tasks, return_exceptions=True)

		sessions: dict[str, ClientSession] = {}
		for result in results:
			if isinstance(result, Exception):
				continue
			server_name, session = result
			sessions[server_name] = session
		return sessions

	async def list_available_tools(self, sessions: Mapping[str, ClientSession]) -> list[dict[str, Any]]:
		tools: list[dict[str, Any]] = []
		for server_name, session in sessions.items():
			try:
				result = await session.list_tools()
			except Exception as error:
				logger.warning("Failed to list tools for server %s: %s", server_name, error)
				continue

			for tool in result.tools:
				tools.append(self._tool_to_openai_schema(server_name, tool))
		return tools

	async def call_mcp_tool(
		self,
		sessions: Mapping[str, ClientSession],
		server_name: str,
		tool_name: str,
		arguments: dict[str, Any],
	) -> Any:
		session = sessions.get(server_name)
		if session is None:
			return {"error": f"No connected MCP session found for server '{server_name}'."}

		try:
			return await session.call_tool(tool_name, arguments)
		except Exception as error:
			return {"error": str(error)}

	async def aclose(self) -> None:
		await asyncio.gather(*(client.__aexit__(None, None, None) for client in self._clients.values()), return_exceptions=True)
		self._clients.clear()

	async def _connect_one(self, config: MCPServerConfig) -> tuple[str, ClientSession]:
		try:
			client = Client(self._build_target(config))
			await client.__aenter__()
			session = client.session
			if session is None:
				raise RuntimeError(f"Client session for server '{config.name}' was not initialized.")
			self._clients[config.name] = client
			return config.name, session
		except Exception as error:
			logger.warning("Skipping unreachable MCP server %s: %s", config.name, error)
			raise

	def _build_target(self, config: MCPServerConfig) -> Any:
		if config.transport == "stdio":
			if not config.command:
				raise ValueError(f"stdio server '{config.name}' is missing command")
			parameters = StdioServerParameters(command=config.command, args=config.args)
			return stdio_client(parameters)

		if config.transport in {"http", "streamable_http", "sse"}:
			if not config.url:
				raise ValueError(f"HTTP server '{config.name}' is missing url")
			return config.url

		raise ValueError(f"Unsupported transport '{config.transport}' for server '{config.name}'")

	def _tool_to_openai_schema(self, server_name: str, tool: Any) -> dict[str, Any]:
		return {
			"type": "function",
			"function": {
				"name": tool.name,
				"description": getattr(tool, "description", None) or f"Tool exposed by {server_name}",
				"parameters": self._normalize_input_schema(tool),
			},
			"x_mcp_server_name": server_name,
			"x_risk_level": getattr(tool, "meta", {}).get("x_risk_level", "low") if getattr(tool, "meta", None) else "low",
		}

	def _normalize_input_schema(self, tool: Any) -> dict[str, Any]:
		input_schema = getattr(tool, "input_schema", None)
		if input_schema is None:
			input_schema = getattr(tool, "inputSchema", None)
		if input_schema is None:
			return {"type": "object", "properties": {}}
		if isinstance(input_schema, Mapping):
			return dict(input_schema)
		if hasattr(input_schema, "model_dump"):
			return input_schema.model_dump(mode="json", by_alias=True)
		return json.loads(json.dumps(input_schema))


def select_tools(user_message: str, all_tools: list[dict[str, Any]], max_tools: int = 6) -> list[dict[str, Any]]:
	if max_tools <= 0 or not all_tools:
		return []

	candidates = _merge_missing_memory_tools(all_tools)
	seen_names: set[str] = set()
	selected: list[dict[str, Any]] = []

	for tool in candidates:
		tool_name = _tool_name(tool)
		if not tool_name or tool_name in seen_names:
			continue
		if tool_name in _ALWAYS_KEEP_TOOL_NAMES:
			selected.append(tool)
			seen_names.add(tool_name)

	if len(selected) >= max_tools:
		return selected[:max_tools]

	ranked_candidates = [tool for tool in candidates if _tool_name(tool) not in seen_names]
	ranked_candidates = _rank_tools_by_description(user_message, ranked_candidates)

	for tool in ranked_candidates:
		tool_name = _tool_name(tool)
		if not tool_name or tool_name in seen_names:
			continue
		selected.append(tool)
		seen_names.add(tool_name)
		if len(selected) >= max_tools:
			break

	if len(selected) < max_tools:
		for tool in candidates:
			tool_name = _tool_name(tool)
			if not tool_name or tool_name in seen_names:
				continue
			selected.append(tool)
			seen_names.add(tool_name)
			if len(selected) >= max_tools:
				break

	count_tokens_saved(candidates, selected)
	return selected[:max_tools]


def count_tokens_saved(all_tools: list[dict[str, Any]], selected_tools: list[dict[str, Any]]) -> int:
	all_tokens = _estimate_tokens(all_tools)
	selected_tokens = _estimate_tokens(selected_tools)
	saved_tokens = max(0, all_tokens - selected_tokens)
	logger.info("tool routing saved ~%s tokens this turn", saved_tokens)
	return saved_tokens


def _merge_missing_memory_tools(all_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
	existing_names = {_tool_name(tool) for tool in all_tools}
	merged = list(all_tools)
	for memory_tool in MEMORY_TOOLS:
		if _tool_name(memory_tool) not in existing_names:
			merged.append(memory_tool)
	return merged


def _rank_tools_by_description(user_message: str, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
	if not tools:
		return []

	if TfidfVectorizer is None:
		return sorted(tools, key=lambda tool: _keyword_overlap_score(user_message, _tool_description(tool)), reverse=True)

	corpus = [user_message] + [_tool_description(tool) for tool in tools]
	vectorizer = TfidfVectorizer(stop_words="english")
	matrix = vectorizer.fit_transform(corpus)
	user_vector = matrix[0]
	tool_vectors = matrix[1:]
	scores = (tool_vectors @ user_vector.T).toarray().ravel()
	ranked = sorted(zip(tools, scores), key=lambda item: item[1], reverse=True)
	return [tool for tool, _score in ranked]


def _keyword_overlap_score(user_message: str, description: str) -> int:
	user_terms = set(re.findall(r"[a-z0-9]+", user_message.lower()))
	desc_terms = set(re.findall(r"[a-z0-9]+", description.lower()))
	return len(user_terms & desc_terms)


def _tool_name(tool: Mapping[str, Any]) -> str:
	function = tool.get("function") if isinstance(tool, Mapping) else None
	if isinstance(function, Mapping):
		name = function.get("name")
		if name:
			return str(name)
	name = tool.get("name") if isinstance(tool, Mapping) else None
	return str(name) if name else ""


def _tool_description(tool: Mapping[str, Any]) -> str:
	function = tool.get("function") if isinstance(tool, Mapping) else None
	if isinstance(function, Mapping):
		description = function.get("description")
		if description:
			return str(description)
	description = tool.get("description") if isinstance(tool, Mapping) else None
	return str(description) if description else ""


def _estimate_tokens(payload: list[dict[str, Any]]) -> int:
	text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
	if tiktoken is not None:
		try:
			encoding = tiktoken.get_encoding("o200k_base")
		except Exception:
			encoding = tiktoken.get_encoding("cl100k_base")
		return len(encoding.encode(text))
	return max(1, len(text) // 4)


_DEFAULT_REGISTRY = MCPClientRegistry()


async def connect_all() -> dict[str, ClientSession]:
	return await _DEFAULT_REGISTRY.connect_all()


async def list_available_tools(sessions: Mapping[str, ClientSession]) -> list[dict[str, Any]]:
	return await _DEFAULT_REGISTRY.list_available_tools(sessions)


async def call_mcp_tool(
	sessions: Mapping[str, ClientSession],
	server_name: str,
	tool_name: str,
	arguments: dict[str, Any],
) -> Any:
	return await _DEFAULT_REGISTRY.call_mcp_tool(sessions, server_name, tool_name, arguments)
