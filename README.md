# ouigo-es

Unofficial, not affiliated with Ouigo. A small CLI and MCP server for Ouigo España fares.

## How it works
A real headless Chrome opens Ouigo's public search page and reads the JSON that Ouigo's own page receives. There is no login, no stored credentials, no token or header handling, and no bot-check evasion. If Ouigo shows a challenge or answers 403, the tool stops and says `blocked`.

## Install
Needs Python 3.12+, [uv](https://docs.astral.sh/uv/) and Google Chrome installed (no browser download).

    uv sync

## CLI (all output is JSON)
    uv run ouigo search Madrid Valencia -d 2026-12-05 --after 08:00 --limit 3
    uv run ouigo search Madrid Valencia -d 2026-12-05 --sort price   # cheapest first
    uv run ouigo calendar Madrid Valencia --from 2026-12-01 --to 2026-12-31
    uv run ouigo open Madrid Valencia -d 2026-12-05   # Ouigo's own page, route and date filled in; you pick and pay there
    uv run ouigo stations valen
    uv run ouigo stations --refresh      # re-reads the list from Ouigo's page
    uv run ouigo --debug search ...      # visible browser; logs response URLs only

**Same layout as [luisgonzaleznf/renfe-cli](https://github.com/luisgonzaleznf/renfe-cli)**, so the two outputs can be merged as they are. `search` has the same top-level keys (`date`, `origin`, `destination`, `passengers`, `fares_included`, `notice`, `count`, `trains`, `shop`, `delays_included`, `retries`). Each train has the same keys (`service`, `type` = `"OUIGO"`, `departure`/`arrival` as full local timestamps, `duration_minutes`, `changes`, `available`, `fares` cheapest first as `{name, price, currency}`). Ouigo has no live delays, so `delay_minutes` and `live_train` are always `null`. The extras `source`, `fetched_at`, each train's `origin_station`/`destination_station` and each fare's `family` ride along. Trains are in departure order, as in renfe-cli; `--sort price` puts the cheapest first. A date with no trains is not an error: `count` is 0 and `notice` says why.

Errors go to stderr as `{"error": {"code": ...}}` with renfe-cli's exit codes: `2` usage (`unknown_station` with suggestions, `bad_dates`, `bad_input`), `5` blocked or upstream (`blocked`, `timeout`), `7` site changed (`api_changed`), `1` internal (only the exception type is shown; also `browser_unavailable`).

`calendar` is ours alone (renfe-cli has no equivalent): `{"days": [{"date", "price", "is_promo", "is_best_price"}], "cheapest": {"date", "price"}, ...}`, prices in EUR for the cheapest fare that day.

## MCP (Claude Desktop / Claude Code)
    {"mcpServers": {"ouigo": {"command": "uv",
      "args": ["--directory", "/path/to/tren-cli", "run", "ouigo-mcp"]}}}

Tools: `search_trains(origin, destination, date)`, `cheapest_days(origin, destination, start, end)`, `find_station(query)`, `shop_link(origin, destination, date)` (returns Ouigo's own page for the trip; the traveller picks and pays there).

## Limits
Slow (about 5-10 s per search). Breaks when Ouigo changes its site. May conflict with Ouigo's terms of use; use gently, for personal use. At least 2 s between page loads, one retry on a plain timeout.

Tests: `uv run pytest` (add `-m live` for one real search).

## Credit and licence
JSON shape follows luisgonzaleznf/renfe-cli. MIT licence, copyright Jade Zheng 2026.
