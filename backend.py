from langgraph.graph import StateGraph, START, END
from typing import List, TypedDict, Annotated

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import sqlite3
import requests
import os
from dotenv import load_dotenv

load_dotenv()
STOCK_PRICE_API = os.getenv("STOCK_PRICE_API")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
CONVERSION_API_KEY = os.getenv("CONVERSION_API_KEY")

# Model
llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen3-4B-Instruct-2507",
    task="text-generation",
)

model = ChatHuggingFace(llm=llm)

# Tools
searchTool = DuckDuckGoSearchRun(region="us-en")


# Custom Calculator Tool
@tool
def calculator(a: float, b: float, operation: str) -> dict:
    """
    Perform basic arithmetic operations on two numbers.
    Supported operations: add, sub, mul, div.
    """
    try:
        if operation == "add":
            result = a + b
        elif operation == "sub":
            result = a - b
        elif operation == "mul":
            result = a * b
        elif operation == "div":
            if b == 0:
                return {"error": "Division by zero is not allowed"}
            result = a / b
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {"result": result}

    except Exception as e:
        return {"error": str(e)}


@tool
def getStockPrice(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol
    (e.g. 'AAPL', 'TSLA') using Alpha Vantage.
    """
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE"
        f"&symbol={symbol}"
        f"&apikey={STOCK_PRICE_API}"
    )

    response = requests.get(url)
    return response.json()


@tool
def getWhetherDetials(city: str) -> dict:
    """
    Get the current weather for a city.

    Args:
        city: Name of the city (e.g., Delhi, Mumbai, London)
    """
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}"
        "&units=metric"
        f"&appid={WEATHER_API_KEY}"
    )

    response = requests.get(url)

    if response.status_code != 200:
        return {"error": "City not found"}

    data = response.json()

    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "weather": data["weather"][0]["main"],
        "description": data["weather"][0]["description"],
        "wind_speed": data["wind"]["speed"],
    }

@tool
def currencyConverter(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict:
    """
    Convert an amount from one currency to another.

    Args:
        amount: Amount to convert.
        from_currency: Source currency code (USD, INR, EUR...)
        to_currency: Target currency code (INR, USD, GBP...)
    """

    url = (
        "https://api.exchangerate.host/convert"
        f"?access_key={CONVERSION_API_KEY}"
        f"&from={from_currency.upper()}"
        f"&to={to_currency.upper()}"
        f"&amount={amount}"
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        print("Status Code:", response.status_code)
        print("Response:", data)

        if response.status_code != 200:
            return {"error": f"HTTP Error {response.status_code}"}

        if not data.get("success", False):
            return {"error": data}

        return {
            "amount": amount,
            "from": from_currency.upper(),
            "to": to_currency.upper(),
            "converted_amount": data["result"],
            "exchange_rate": data["info"]["quote"],
        }

    except Exception as e:
        return {"error": str(e)}


tools = [
    searchTool,
    calculator,
    getStockPrice,
    getWhetherDetials,
    currencyConverter,
]

LLMWithTools = model.bind_tools(tools)


# State
class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


# Nodes
def chatNode(state: ChatState):
    """
    LLM node that may chat with the user or request a tool call.
    """
    messages = state["messages"]
    response = LLMWithTools.invoke(messages)
    return {"messages": [response]}


toolNode = ToolNode(tools)


# Checkpointer
conn = sqlite3.connect(
    database="chatbot.db",
    check_same_thread=False,
)

checkPointer = SqliteSaver(conn=conn)


# Graph
graph = StateGraph(ChatState)

graph.add_node("chatNode", chatNode)
graph.add_node("tools", toolNode)

graph.add_edge(START, "chatNode")
graph.add_conditional_edges("chatNode", tools_condition)
graph.add_edge("tools", "chatNode")

chatBot = graph.compile(checkpointer=checkPointer)


# Helper Function to retrieve threads
def retrieveAllThreads():
    allThreads = set()

    for checkPoint in checkPointer.list(None):
        allThreads.add(
            checkPoint.config["configurable"]["thread_id"]
        )

    return list(allThreads)