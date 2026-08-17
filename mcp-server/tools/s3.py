from fastmcp import FastMCP

mcp = FastMCP("s3")


@mcp.tool
def list_files(prefix: str = "") -> list:
    pass


@mcp.tool
def get_file(key: str) -> dict:
    pass
