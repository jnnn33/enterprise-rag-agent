from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.repositories.sqlite_agent_runs import SQLiteAgentRunRepository
from app.services.agent_runtime import AgentRuntime
from app.services.agent_skills import MCPToolSkill, SkillRegistry
from app.services.agent_tools import ToolRegistry
from app.services.mcp_client import (
    MCPClientService,
    MCPConfigurationError,
    MCPServerConfig,
    MCPToolDefinition,
)


class FakeMCPGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def list_tools(self, server: MCPServerConfig) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                server_name=server.name,
                name="lookup_employee",
                description="Look up an employee.",
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
            )
        ]

    def call_tool(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append((server.name, tool_name, arguments))
        return {
            "server": server.name,
            "tool": tool_name,
            "employee": arguments["name"],
        }


def test_mcp_tools_are_discovered_and_execute_through_agent_runtime(tmp_path) -> None:
    gateway = FakeMCPGateway()
    service = MCPClientService.from_json(
        '[{"name":"directory","transport":"stdio","command":"python"}]',
        gateway=gateway,
    )
    mcp_tools = service.discover_tools()
    skill = MCPToolSkill({tool.name for tool in mcp_tools})
    runtime = AgentRuntime(
        repository=SQLiteAgentRunRepository(str(tmp_path / "mcp.db")),
        skills=SkillRegistry([skill]),
        tools=ToolRegistry(mcp_tools),
    )

    preview = runtime.preview(
        objective="Look up Lin Chen in the employee directory.",
        skill_name="mcp_tool",
        inputs={
            "tool_name": "mcp.directory.lookup_employee",
            "arguments": {"name": "Lin Chen"},
        },
    )

    assert preview.status.value == "awaiting_confirmation"
    assert preview.actions[0].risk_level.value == "external"
    runtime.confirm(preview.id, "Approved for directory lookup.")
    completed = runtime.execute(preview.id)

    assert completed.status.value == "completed"
    assert completed.actions[0].result["employee"] == "Lin Chen"
    assert gateway.calls == [
        ("directory", "lookup_employee", {"name": "Lin Chen"})
    ]
    assert any(event.event_type == "tool_completed" for event in completed.events)


def test_mcp_configuration_rejects_invalid_transport() -> None:
    with pytest.raises(MCPConfigurationError, match="transport"):
        MCPClientService.from_json(
            '[{"name":"bad","transport":"websocket","url":"ws://test"}]'
        )


def test_mcp_api_reports_empty_default_configuration(client: TestClient) -> None:
    assert client.get("/api/v1/mcp/servers").json() == []
    assert client.get("/api/v1/mcp/tools").json() == []