import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
import json
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = MultiServerMCPClient(
        {
            "calculator": {
                "command": "python",
                "args": ["mcp_servers/calculator_server.py"],
                "transport": "stdio",
            },
            "stock": {
                "command": "python",
                "args": ["mcp_servers/stock_server.py"],
                "transport": "stdio",
            },
            "search": {
                "command": "python",
                "args": ["mcp_servers/search_server.py"],
                "transport": "stdio",
            },
        }
    )

    tools = await client.get_tools()

    print("\nAvailable tools:")
    for t in tools:
        print("-", t.name)

    # pick calculator tool
    calculator_tool = next(t for t in tools if t.name == "calculator")

    result = await calculator_tool.ainvoke({
        "first_num": 10,
        "second_num": 5,
        "operation": "mul"
    })

    print("\nTool result:")
    print(result)

    print("\nTool result (clean):")

    text = result[0]["text"]
    data = json.loads(text)

    print(data)

    # stock price
    stock_tool = next(t for t in tools if t.name == "get_stock_price")

    result = await stock_tool.ainvoke({
    "symbol": "AAPL"})

    print(result)
    text = result[0]["text"]
    data = json.loads(text)
    print(json.dumps(data, indent=2))

    # search tool
    search_tool = next(t for t in tools if t.name == "search_tool")

    result = await search_tool.ainvoke({
    "query": "Latest FIFA news"})

    print(result)
    text = result[0]["text"]
    data = json.loads(text)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    asyncio.run(main())