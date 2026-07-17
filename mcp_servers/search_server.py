from mcp.server.fastmcp import FastMCP
from ddgs import DDGS

# Create an MCP server for web search.
mcp = FastMCP("Search Server")


@mcp.tool()
def search_tool(query: str) -> list[dict]:
    """
    Search the internet for current events, news or real-time info.
    """
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))

    return results


if __name__ == "__main__":
    mcp.run()
