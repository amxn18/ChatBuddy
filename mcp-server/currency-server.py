import os

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP


load_dotenv()

CONVERSION_API_KEY = os.getenv("CONVERSION_API_KEY")


mcp = FastMCP(name="Currency Server")


@mcp.tool()
def currency_converter(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict:
    """
    Convert an amount from one currency to another.

    Args:
        amount: Amount to convert.
        from_currency: Source currency code, for example USD, INR, EUR.
        to_currency: Target currency code, for example INR, USD, GBP.
    """

    url = (
        "https://api.exchangerate.host/convert"
        f"?access_key={CONVERSION_API_KEY}"
        f"&from={from_currency.upper()}"
        f"&to={to_currency.upper()}"
        f"&amount={amount}"
    )

    try:

        response = requests.get(
            url,
            timeout=10,
        )

        data = response.json()

        if response.status_code != 200:
            return {
                "error": f"HTTP Error {response.status_code}"
            }

        if not data.get("success", False):
            return {
                "error": data
            }

        return {
            "amount": amount,
            "from": from_currency.upper(),
            "to": to_currency.upper(),
            "converted_amount": data["result"],
            "exchange_rate": data["info"]["quote"],
        }

    except Exception as e:

        return {
            "error": str(e)
        }


if __name__ == "__main__":
    mcp.run()