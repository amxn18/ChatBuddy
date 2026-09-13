from fastmcp import FastMCP
from langchain_community.tools import DuckDuckGoSearchRun

mcp = FastMCP(name="Search Server")

searchTool = DuckDuckGoSearchRun(region="us-en")

@mcp.tool()
def web_search(query: str) -> str:
    """
    Search the web for information using DuckDuckGo.

    Args:
        query: The search query.
    """

    try:
        result = searchTool.invoke(query)
        return result

    except Exception as e:
        return f"Error while searching: {str(e)}"


if __name__ == "__main__":
    mcp.run()