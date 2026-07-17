from mcp.server.fastmcp import FastMCP

# Create an MCP server using FastMCP
mcp = FastMCP("Calculator Server")

@mcp.tool()
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform basic arithmetic operations.
    Supported operations:
    add, sub, mul, div
    """

    if operation == "add":
        result = first_num + second_num

    elif operation == "sub":
        result = first_num - second_num

    elif operation == "mul":
        result = first_num * second_num

    elif operation == "div":
        if second_num == 0:
            return {"error": "Division by zero"}

        result = first_num / second_num

    else:
        return {"error": "Unsupported operation"}

    return {
        "first_num": first_num,
        "second_num": second_num,
        "operation": operation,
        "result": result,
    }
if __name__ == "__main__":
    mcp.run()