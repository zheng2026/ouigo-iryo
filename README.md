# ouigo-es

Unofficial, not affiliated with Ouigo. A small CLI and MCP server for Ouigo España fares.

## How it works
A real headless Chrome opens Ouigo's public search page and reads the JSON that Ouigo's own page receives. There is no login, no stored credentials, no token or header handling, and no bot-check evasion. If Ouigo shows a challenge or answers 403, the tool stops and says `blocked`.

## Install
Needs Python 3.12+, [uv](https://docs.astral.sh/uv/) and Google Chrome installed (no browser download).

    uv sync

## CLI (all output is JSON)
    uv run ouigo search Madrid Valencia -d 2026-12-05 --after 08:00 --limit 3
    uv run ouigo calendar Madrid Valencia --from 2026-12-01 --to 2026-12-31
    uv run ouigo stations valen
    uv run ouigo stations --refresh      # re-reads the list from Ouigo's page
    uv run ouigo --debug search ...      # visible browser; logs response URLs only

Errors go to stderr as JSON with exit code 2: `blocked`, `no_trains`, `unknown_station` (with suggestions), `timeout`.
`price` is the cheapest fare (OUIGO Esencial); `fares` lists all fare levels.

## MCP (Claude Desktop / Claude Code)
    {"mcpServers": {"ouigo": {"command": "uv",
      "args": ["--directory", "/path/to/tren-cli", "run", "ouigo-mcp"]}}}

Tools: `search_trains(origin, destination, date)`, `cheapest_days(origin, destination, start, end)`, `find_station(query)`.

## Limits
Slow (about 5-10 s per search). Breaks when Ouigo changes its site. May conflict with Ouigo's terms of use; use gently, for personal use. At least 2 s between page loads, one retry on a plain timeout.

Tests: `uv run pytest` (add `-m live` for one real search).

## Credit and licence
JSON shape follows luisgonzaleznf/renfe-cli. MIT licence, copyright Jade Zheng 2026.
