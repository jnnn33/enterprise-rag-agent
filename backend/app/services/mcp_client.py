import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import json
from typing import Any, AsyncIterator, Protocol

from app.domain.agent import ToolRisk


class MCPConfigurationError(ValueError):
    pass


class MCPClientError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    name: str
    transport: str
    command: str = ""
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MCPToolDefinition:
    server_name: str
    name: str
    description: str
    input_schema: dict[str, Any]


class MCPGateway(Protocol):
    def list_tools(self, server: MCPServerConfig) -> list[MCPToolDefinition]: ...

    def call_tool(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]: ...


class OfficialMCPGateway:
    def list_tools(self, server: MCPServerConfig) -> list[MCPToolDefinition]:
        return asyncio.run(self._list_tools(server))

    def call_tool(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        return asyncio.run(self._call_tool(server, tool_name, arguments))

    async def _list_tools(
        self,
        server: MCPServerConfig,
    ) -> list[MCPToolDefinition]:
        async with self._session(server) as session:
            response = await session.list_tools()
            return [
                MCPToolDefinition(
                    server_name=server.name,
                    name=tool.name,
                    description=tool.description or "MCP tool",
                    input_schema=dict(tool.inputSchema or {}),
                )
                for tool in response.tools
            ]

    async def _call_tool(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        async with self._session(server) as session:
            result = await session.call_tool(tool_name, arguments=arguments)
        content: list[Any] = []
        for block in result.content:
            if hasattr(block, "model_dump"):
                content.append(block.model_dump(mode="json"))
            else:
                content.append(str(block))
        structured = getattr(result, "structuredContent", None)
        return {
            "server": server.name,
            "tool": tool_name,
            "content": content,
            "structured_content": structured,
            "is_error": bool(getattr(result, "isError", False)),
        }

    @asynccontextmanager
    async def _session(self, server: MCPServerConfig) -> AsyncIterator[Any]:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            from mcp.client.streamable_http import streamable_http_client
        except ImportError as exc:
            raise MCPClientError(
                "MCP support requires the 'mcp' optional dependency"
            ) from exc

        if server.transport == "stdio":
            parameters = StdioServerParameters(
                command=server.command,
                args=list(server.args),
                env=server.env or None,
            )
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
            return
        if server.transport == "streamable_http":
            async with streamable_http_client(
                server.url,
                headers=server.headers or None,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
            return
        raise MCPConfigurationError(
            f"unsupported MCP transport: {server.transport}"
        )


class MCPClientService:
    def __init__(
        self,
        servers: list[MCPServerConfig],
        gateway: MCPGateway | None = None,
    ) -> None:
        names = [server.name for server in servers]
        if len(names) != len(set(names)):
            raise MCPConfigurationError("MCP server names must be unique")
        self._servers = {server.name: server for server in servers}
        self._gateway = gateway or OfficialMCPGateway()

    @classmethod
    def from_json(
        cls,
        raw: str,
        gateway: MCPGateway | None = None,
    ) -> "MCPClientService":
        try:
            items = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise MCPConfigurationError("MCP_SERVERS_JSON must be valid JSON") from exc
        if not isinstance(items, list):
            raise MCPConfigurationError("MCP_SERVERS_JSON must be a JSON array")
        servers = [cls._parse_server(item) for item in items]
        return cls(servers=servers, gateway=gateway)

    def list_servers(self) -> list[dict[str, str]]:
        return [
            {"name": server.name, "transport": server.transport}
            for server in self._servers.values()
        ]

    def discover_tools(self) -> list["MCPToolAdapter"]:
        tools: list[MCPToolAdapter] = []
        for server in self._servers.values():
            for definition in self._gateway.list_tools(server):
                if definition.server_name != server.name:
                    raise MCPClientError(
                        "MCP gateway returned a tool for the wrong server"
                    )
                tools.append(MCPToolAdapter(self, definition))
        names = [tool.name for tool in tools]
        if len(names) != len(set(names)):
            raise MCPClientError("discovered MCP tool names must be unique")
        return tools

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            server = self._servers[server_name]
        except KeyError as exc:
            raise MCPClientError(f"unknown MCP server: {server_name}") from exc
        return self._gateway.call_tool(server, tool_name, arguments)

    @staticmethod
    def _parse_server(item: Any) -> MCPServerConfig:
        if not isinstance(item, dict):
            raise MCPConfigurationError("each MCP server must be an object")
        name = str(item.get("name") or "").strip()
        transport = str(item.get("transport") or "stdio").strip().lower()
        if not name:
            raise MCPConfigurationError("MCP server name is required")
        if transport not in {"stdio", "streamable_http"}:
            raise MCPConfigurationError(
                "MCP transport must be 'stdio' or 'streamable_http'"
            )
        command = str(item.get("command") or "").strip()
        url = str(item.get("url") or "").strip()
        if transport == "stdio" and not command:
            raise MCPConfigurationError("stdio MCP server command is required")
        if transport == "streamable_http" and not url:
            raise MCPConfigurationError("HTTP MCP server url is required")
        args = item.get("args") or []
        env = item.get("env") or {}
        headers = item.get("headers") or {}
        if not isinstance(args, list) or not all(
            isinstance(value, str) for value in args
        ):
            raise MCPConfigurationError("MCP server args must be a string array")
        if not isinstance(env, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in env.items()
        ):
            raise MCPConfigurationError("MCP server env must contain strings")
        if not isinstance(headers, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in headers.items()
        ):
            raise MCPConfigurationError("MCP server headers must contain strings")
        return MCPServerConfig(
            name=name,
            transport=transport,
            command=command,
            args=tuple(args),
            env=env,
            url=url,
            headers=headers,
        )


class MCPToolAdapter:
    risk_level = ToolRisk.EXTERNAL

    def __init__(
        self,
        client: MCPClientService,
        definition: MCPToolDefinition,
    ) -> None:
        self._client = client
        self._definition = definition
        self.name = f"mcp.{definition.server_name}.{definition.name}"
        self.description = definition.description
        self.input_schema = definition.input_schema

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._client.call_tool(
            server_name=self._definition.server_name,
            tool_name=self._definition.name,
            arguments=arguments,
        )