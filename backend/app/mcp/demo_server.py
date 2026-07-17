from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Enterprise RAG Agent Demo")


@mcp.tool()
def lookup_employee_directory(employee_name: str) -> dict[str, str]:
    """Return deterministic demo directory data for an employee."""
    return {
        "employee_name": employee_name,
        "department": "Platform Engineering",
        "location": "Shanghai",
        "email": f"{employee_name.lower().replace(' ', '.')}@example.com",
    }


@mcp.tool()
def create_support_ticket(title: str, priority: str = "normal") -> dict[str, str]:
    """Create a simulated support ticket for MCP integration demonstrations."""
    return {
        "ticket_id": "DEMO-1001",
        "title": title,
        "priority": priority,
        "status": "simulated",
    }


if __name__ == "__main__":
    mcp.run()