import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Create an MCP server for stock lookup.
mcp = FastMCP("Stock Server")

@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') using Alpha Vantage.
    """
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        return {"error": "Missing ALPHAVANTAGE_API_KEY in environment."}

    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
    )

    r = requests.get(url)
    return r.json()


if __name__ == "__main__":
    mcp.run()
