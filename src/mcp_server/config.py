from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    transport: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    env: dict[str, str] | None = None
    cwd: str | None = None


def default_mcp_server_configs() -> list[MCPServerConfig]:
    repo_root = Path(__file__).resolve().parents[2]
    memory_server_module = "src.mcp_server.memory_server"
    return [
        MCPServerConfig(
            name="memory-server",
            transport="stdio",
            command=sys.executable,
            args=["-m", memory_server_module],
            cwd=str(repo_root),
        ),
    ]


def load_server_configs(config_path: str | Path | None = None) -> list[MCPServerConfig]:
    path = Path(config_path) if config_path is not None else Path(__file__).resolve().parents[2] / "mcp_servers.json"
    if path.exists():
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("mcp_servers.json must contain a list of server configurations.")

        configs: list[MCPServerConfig] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("Each MCP server configuration must be a JSON object.")
            configs.append(
                MCPServerConfig(
                    name=item["name"],
                    transport=item.get("transport", "stdio"),
                    command=item.get("command"),
                    args=list(item.get("args", [])),
                    url=item.get("url"),
                    env=item.get("env"),
                    cwd=item.get("cwd"),
                )
            )
        return configs

    return default_mcp_server_configs()
