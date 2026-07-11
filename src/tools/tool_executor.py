from __future__ import annotations

import asyncio
import json
import inspect
from typing import Any, Awaitable, Callable, Mapping

from src.telemetry import track_call


class ToolExecutor:
	def __init__(
		self,
		tool_registry: dict[str, Callable[..., Any]],
		tool_schemas: list[dict[str, Any]] | None = None,
		confirm_high_risk: Callable[[str, dict[str, Any]], bool | Awaitable[bool]] | None = None,
	) -> None:
		self.tool_registry = tool_registry
		self.confirm_high_risk = confirm_high_risk or self._default_confirm_high_risk
		self._risk_levels = self._build_risk_levels(tool_schemas or [])

	@track_call("tool_executor.execute")
	async def execute(self, tool_call: Any) -> dict[str, Any]:
		tool_name = self._get_tool_name(tool_call)
		tool_call_id = getattr(tool_call, "id", None)

		try:
			args = json.loads(self._get_tool_arguments(tool_call))
		except json.JSONDecodeError as error:
			return self._tool_response(
				tool_call_id,
				{
					"ok": False,
					"tool": tool_name,
					"error": {
						"type": "invalid_json_arguments",
						"message": f"Tool arguments for '{tool_name}' were not valid JSON.",
						"details": str(error),
					},
				},
			)

		if not isinstance(args, dict):
			return self._tool_response(
				tool_call_id,
				{
					"ok": False,
					"tool": tool_name,
					"error": {
						"type": "invalid_arguments_shape",
						"message": f"Tool arguments for '{tool_name}' must decode to a JSON object.",
					},
				},
			)

		tool = self.tool_registry.get(tool_name)
		if tool is None:
			return self._tool_response(
				tool_call_id,
				{
					"ok": False,
					"tool": tool_name,
					"error": {
						"type": "unknown_tool",
						"message": f"No registered tool named '{tool_name}' was found.",
					},
				},
			)

		if self._risk_levels.get(tool_name) == "high":
			try:
				allowed = await self._maybe_await(self.confirm_high_risk(tool_name, args))
			except Exception as error:
				return self._tool_response(
					tool_call_id,
					{
						"ok": False,
						"tool": tool_name,
						"error": {
							"type": "high_risk_confirmation_error",
							"message": f"High-risk confirmation for '{tool_name}' failed.",
							"details": str(error),
						},
					},
				)
			if not allowed:
				return self._tool_response(
					tool_call_id,
					{
						"ok": False,
						"tool": tool_name,
						"error": {
							"type": "high_risk_rejected",
							"message": f"Execution of high-risk tool '{tool_name}' was not approved.",
						},
					},
				)

		try:
			if asyncio.iscoroutinefunction(tool):
				result = await tool(**args)
			else:
				result = await asyncio.to_thread(tool, **args)
		except Exception as error:
			return self._tool_response(
				tool_call_id,
				{
					"ok": False,
					"tool": tool_name,
					"error": {
						"type": "tool_execution_error",
						"message": f"Tool '{tool_name}' failed during execution.",
						"details": str(error),
					},
				},
			)

		return self._tool_response(tool_call_id, result)

	async def execute_all(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
		return await asyncio.gather(*(self.execute(tool_call) for tool_call in tool_calls))

	def _build_risk_levels(self, tool_schemas: list[dict[str, Any]]) -> dict[str, str]:
		risk_levels: dict[str, str] = {}
		for schema in tool_schemas:
			function_schema = schema.get("function") if isinstance(schema, Mapping) else None
			if not isinstance(function_schema, Mapping):
				continue
			tool_name = function_schema.get("name")
			if not tool_name:
				continue
			risk_level = schema.get("x_risk_level", "low")
			risk_levels[str(tool_name)] = str(risk_level)
		return risk_levels

	def _get_tool_name(self, tool_call: Any) -> str:
		function = getattr(tool_call, "function", None)
		tool_name = getattr(function, "name", None)
		if not tool_name:
			raise ValueError("Tool call is missing function.name.")
		return str(tool_name)

	def _get_tool_arguments(self, tool_call: Any) -> str:
		function = getattr(tool_call, "function", None)
		arguments = getattr(function, "arguments", None)
		if arguments is None:
			raise ValueError("Tool call is missing function.arguments.")
		return str(arguments)

	async def _maybe_await(self, value: bool | Awaitable[bool]) -> bool:
		if inspect.isawaitable(value):
			return bool(await value)
		return bool(value)

	def _default_confirm_high_risk(self, tool_name: str, args: dict[str, Any]) -> bool:
		return True

	def _tool_response(self, tool_call_id: Any, result: Any) -> dict[str, Any]:
		return {
			"role": "tool",
			"tool_call_id": tool_call_id,
			"content": json.dumps(result, ensure_ascii=False),
		}
