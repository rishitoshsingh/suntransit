from fastmcp import FastMCP

from tools.postgres import mcp as postgres_mcp
from tools.s3 import mcp as s3_mcp
from tools.gtfs import mcp as gtfs_mcp, CITIES

mcp = FastMCP("suntransit")

mcp.mount(postgres_mcp)
# mcp.mount(s3_mcp)
mcp.mount(gtfs_mcp)


@mcp.resource("gtfs://cities")
def list_cities() -> dict:
    """List of supported cities and their transit agencies."""
    return {
        key: {
            "city": meta["city"],
            "agency": meta["agency"],
        }
        for key, meta in CITIES.items()
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8083)
