import os

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP


load_dotenv()

STOCK_PRICE_API = os.getenv("STOCK_PRICE_API")


mcp = FastMCP(name="Stock Server")


@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """
    Fetch the latest stock price for a given stock symbol
    using Alpha Vantage.

    Args:
        symbol: Stock symbol such as AAPL, TSLA, MSFT.
    """

    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE"
        f"&symbol={symbol.upper()}"
        f"&apikey={STOCK_PRICE_API}"
    )

    try:

        response = requests.get(
            url,
            timeout=10,
        )

        if response.status_code != 200:
            return {
                "error": f"HTTP Error {response.status_code}"
            }

        return response.json()

    except Exception as e:
        return {
            "error": str(e)
        }


if __name__ == "__main__":
    mcp.run()