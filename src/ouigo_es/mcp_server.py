import asyncio

from mcp.server.fastmcp import FastMCP

from . import core, stations
from .errors import OuigoError

mcp = FastMCP("ouigo-es")


def _safe(fn, *a):
    try:
        return fn(*a)
    except OuigoError as e:
        return e.payload()
    except ValueError as e:
        return {"error": "bad_input", "detail": str(e)}


# core uses Playwright's sync API, which refuses to run inside the MCP server's
# asyncio loop; run it in a worker thread instead (fixed 2026-11-20).
@mcp.tool()
async def search_trains(origin: str, destination: str, date: str) -> dict:
    """Ouigo trains and prices for one day (YYYY-MM-DD), cheapest first. Slow (~5-10 s)."""
    return await asyncio.to_thread(_safe, core.search, origin, destination, date)


@mcp.tool()
async def cheapest_days(origin: str, destination: str, start: str, end: str) -> dict:
    """Cheapest Ouigo price per day between start and end (YYYY-MM-DD)."""
    return await asyncio.to_thread(_safe, core.calendar, origin, destination, start, end)


@mcp.tool()
def find_station(query: str) -> dict:
    """Find Ouigo stations by name or code (accents/case ignored)."""
    found = stations.search_stations(query)
    return {"count": len(found), "stations": found} if found else _safe(stations.resolve, query)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
