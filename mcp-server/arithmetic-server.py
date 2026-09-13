from fastmcp import FastMCP

mcp = FastMCP(name="Arithmetic Server")


def _as_number(x):
    # Accept ints/floats or numeric strings; raise clean errors otherwise
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        return float(x.strip())
    raise TypeError("Expected a number (int/float or numeric string)")

@mcp.tool()
async def add(a: float, b: float) -> float:
    """Add two numbers."""
    return _as_number(a) + _as_number(b)

@mcp.tool()
async def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return _as_number(a) - _as_number(b)

@mcp.tool()
async def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return _as_number(a) * _as_number(b)

@mcp.tool()
async def divide(a: float, b: float) -> float:
    """Divide a by b."""
    b = _as_number(b)

    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return _as_number(a) / b

if __name__ == "__main__":
    mcp.run()