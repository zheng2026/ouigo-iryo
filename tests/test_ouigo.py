import json
import subprocess
import sys
from pathlib import Path

import pytest

from ouigo_es import cli, core, stations
from ouigo_es.errors import OuigoError

FX = Path(__file__).parent / "fixtures"


def fx(name):
    return (FX / name).read_text(encoding="utf-8")


def test_fixtures_have_no_secrets():
    for f in FX.glob("*.json"):
        t = f.read_text(encoding="utf-8").lower()
        for bad in ("bearer", "token", "password", "authorization"):
            assert bad not in t, (f.name, bad)


def test_parse_search():
    tr = core.parse_search(fx("search.json"), "2026-12-04")
    assert len(tr) == 5
    assert [t["price"] for t in tr] == sorted(t["price"] for t in tr)
    t = tr[0]
    assert t["service"] == "06472" and t["departure"] == "07:15" and t["arrival"] == "09:09"
    assert t["duration_min"] == 114 and t["currency"] == "EUR" and t["price"] == 17.0
    assert t["origin_station"].startswith("Madrid") and t["destination_station"].startswith("Valencia")
    assert [f["family"] for f in t["fares"]] == ["OUIGO_ESSENTIAL", "OUIGO_PLUS", "OUIGO_FULL"]
    assert t["fares"][0]["price"] == t["price"]


def test_parse_calendar():
    days = core.parse_calendar(fx("calendar_month.json"))
    assert len(days) == 31 and days[0]["date"] == "2026-12-01"
    assert set(days[0]) == {"date", "price", "is_promo", "is_best_price"}


def test_station_list_parse_matches_bundle():
    raw = json.loads(fx("stations.json"))
    assert stations.parse_stations(raw) == stations.load_stations()


@pytest.mark.parametrize("q,code", [("Madrid", "MT1"), ("madrid", "MT1"), ("VALÈNCIA", "7103216"),
                                    ("valencia", "7103216"), ("7103216", "7103216"), ("Malaga", "7154413"),
                                    ("Barcelona Sants", "7171801"), ("cordoba", "7150500"), ("VAL", "7103216")])
def test_resolve(q, code):
    assert stations.resolve(q)["code"] == code


def test_resolve_typo_suggests():
    with pytest.raises(OuigoError) as e:
        stations.resolve("Valensia")
    p = e.value.payload()
    assert p["error"] == "unknown_station" and "Valencia - Joaquín Sorolla" in p["suggestions"]


def test_cli_search_shape(monkeypatch, capsys):
    monkeypatch.setattr(core, "_capture", lambda *a, **k: fx("search.json"))
    cli.main(["search", "Madrid", "Valencia", "-d", "2026-12-04", "--after", "12:00", "--limit", "2"])
    out = json.loads(capsys.readouterr().out)
    assert out["source"] == "ouigo" and out["count"] == 2 and out["passengers"] == {"adults": 1}
    assert out["origin"]["code"] == "MT1" and out["destination"]["code"] == "7103216"
    assert all(t["departure"] >= "12:00" for t in out["trains"])
    assert {"service", "departure", "arrival", "duration_min", "origin_station",
            "destination_station", "price", "currency", "fares"} <= set(out["trains"][0])
    assert "fetched_at" in out


def test_cli_calendar_shape(monkeypatch, capsys):
    monkeypatch.setattr(core, "_capture", lambda *a, **k: fx("calendar_month.json"))
    cli.main(["calendar", "Madrid", "Valencia", "--from", "2026-12-05", "--to", "2026-12-20"])
    out = json.loads(capsys.readouterr().out)
    assert len(out["days"]) == 16 and out["days"][0]["date"] == "2026-12-05"
    assert out["cheapest"]["price"] == min(d["price"] for d in out["days"])


def test_cli_errors_go_to_stderr(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["search", "Madrid", "Narnia", "-d", "2026-12-04"])
    assert e.value.code != 0
    cap = capsys.readouterr()
    assert cap.out == "" and json.loads(cap.err)["error"] == "unknown_station"


def test_no_trains(monkeypatch):
    monkeypatch.setattr(core, "_capture", lambda *a, **k: '{"outbound":[],"error":null}')
    with pytest.raises(OuigoError) as e:
        core.search("Madrid", "Valencia", "2026-12-04")
    assert e.value.code == "no_trains"


def test_cli_stations_query(capsys):
    cli.main(["stations", "valen"])
    out = json.loads(capsys.readouterr().out)
    assert {s["code"] for s in out["stations"]} == {"7103216"}


def test_mcp_tools_registered():
    import asyncio
    from ouigo_es.mcp_server import mcp
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"search_trains", "cheapest_days", "find_station"}


@pytest.mark.live
def test_live_search():
    from datetime import date, timedelta
    r = core.search("Madrid", "Valencia", (date.today() + timedelta(days=14)).isoformat())
    assert r["count"] > 0
