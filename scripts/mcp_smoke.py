"""Smoke test: start the MCP server over stdio, list tools, run two live calls."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    p = StdioServerParameters(command="uv", args=["run", "ouigo-mcp"])
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            res = await s.call_tool("cheapest_days", {"origin": "Valencia", "destination": "Madrid", "start": "2026-12-04", "end": "2026-12-07"})
            print("cheapest_days:", res.content[0].text[:300])
            res = await s.call_tool("search_trains", {"origin": "Valencia", "destination": "Madrid", "date": "2026-12-06"})
            print("search_trains:", res.content[0].text[:300])

asyncio.run(main())
