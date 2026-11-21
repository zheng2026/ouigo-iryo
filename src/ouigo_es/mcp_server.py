import asyncio

from mcp.server.fastmcp import FastMCP

from . import core, iryo, stations
from .errors import OuigoError

INSTRUCTIONS = ("When you show Ouigo trains or the cheapest day, always also give the user the Iryo link from the "
                "result's `iryo` field for the same route and day, labelled as Iryo, and say Iryo's prices appear "
                "when they open the link. Present both companies together so the user can compare before deciding.")
mcp = FastMCP("ouigo-es", instructions=INSTRUCTIONS)


def _safe(fn, *a):
    try:
        return fn(*a)
    except OuigoError as e:
        return e.payload()
    except ValueError as e:
        return {"error": {"code": "bad_input", "detail": str(e)}}


# core uses Playwright's sync API, which refuses to run inside the MCP server's
# asyncio loop; run it in a worker thread instead (fixed 2026-11-20).
@mcp.tool()
async def search_trains(origin: str, destination: str, date: str) -> dict:
    """Ouigo trains and prices for one day (YYYY-MM-DD), cheapest first. Slow (~5-10 s).
    The result has an `iryo` field (link for the same route and day, no prices): give it to the user too."""
    return await asyncio.to_thread(_safe, core.search, origin, destination, date)


@mcp.tool()
def shop_link(origin: str, destination: str, date: str) -> dict:
    """Ouigo's own search page for this trip (route and date filled in). The traveller picks and pays there."""
    return _safe(core.open_link, origin, destination, date)


@mcp.tool()
def iryo_link(origin: str, destination: str, date: str) -> dict:
    """Iryo's own booking page for this trip (YYYY-MM-DD), as a link. Iryo gives no fares through this tool:
    hand the link to the user, who opens it and picks and pays there. Does not open a browser.
    "Madrid" means all Madrid stations; a `warning` field flags pairs Iryo is known not to run."""
    return _safe(iryo.iryo_link, origin, destination, date)


@mcp.tool()
async def cheapest_days(origin: str, destination: str, start: str, end: str) -> dict:
    """Cheapest Ouigo price per day between start and end (YYYY-MM-DD).
    The result has an `iryo` field (link for the cheapest day, no prices): give it to the user too."""
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
