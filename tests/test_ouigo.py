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


RENFE_TRAIN_KEYS = {"service", "type", "type_code", "departure", "arrival", "duration_minutes", "changes",
                    "available", "fares", "intermediate_stops", "delay_minutes", "live_train"}
RENFE_TOP_KEYS = {"date", "origin", "destination", "passengers", "fares_included", "notice", "count",
                  "trains", "shop", "delays_included", "retries"}


def test_parse_search():
    tr = core.parse_search(fx("search.json"), "2026-12-04")
    assert len(tr) == 5
    assert [t["departure"] for t in tr] == sorted(t["departure"] for t in tr)
    t = tr[0]
    assert t["service"] == "06472" and t["departure"] == "2026-12-04T07:15:00+01:00"
    assert t["arrival"].startswith("2026-12-04T09:09") and t["duration_minutes"] == 114
    assert t["type"] == "OUIGO" and t["changes"] == 0 and t["available"] is True
    assert t["origin_station"].startswith("Madrid") and t["destination_station"].startswith("Valencia")
    assert [f["family"] for f in t["fares"]] == ["OUIGO_ESSENTIAL", "OUIGO_PLUS", "OUIGO_FULL"]
    assert t["fares"][0] == {"name": t["fares"][0]["name"], "price": 17.0, "currency": "EUR", "family": "OUIGO_ESSENTIAL"}
    assert RENFE_TRAIN_KEYS <= set(t)


def test_parse_search_api_changed():
    with pytest.raises(OuigoError) as e:
        core.parse_search('{"outbound":[{"segments":[{}]}]}', "2026-12-04")
    assert e.value.code == "api_changed" and e.value.exit_code == 7


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
    p = e.value.payload()["error"]
    assert p["code"] == "unknown_station" and "Valencia - Joaquín Sorolla" in p["suggestions"]


def test_cli_search_shape(monkeypatch, capsys):
    monkeypatch.setattr(core, "_capture", lambda *a, **k: fx("search.json"))
    cli.main(["search", "Madrid", "Valencia", "-d", "2026-12-04", "--after", "12:00", "--limit", "2"])
    out = json.loads(capsys.readouterr().out)
    assert RENFE_TOP_KEYS <= set(out) and out["source"] == "ouigo"
    assert out["count"] == 2 and out["passengers"] == {"adults": 1} and out["notice"] is None
    assert out["origin"] == {"code": "MT1", "name": "Madrid - Todas las estaciones", "group": True}
    assert out["destination"]["code"] == "7103216" and out["destination"]["group"] is False
    assert all(t["departure"][11:16] >= "12:00" for t in out["trains"])
    assert RENFE_TRAIN_KEYS <= set(out["trains"][0])
    assert "outboundDate=2026-12-04" in out["shop"]["url"] and "fetched_at" in out


def test_cli_search_sort_price(monkeypatch, capsys):
    monkeypatch.setattr(core, "_capture", lambda *a, **k: fx("search.json"))
    cli.main(["search", "Madrid", "Valencia", "-d", "2026-12-04", "--sort", "price"])
    prices = [t["fares"][0]["price"] for t in json.loads(capsys.readouterr().out)["trains"]]
    assert prices == sorted(prices)


def test_cli_open_print(capsys):
    cli.main(["open", "Madrid", "Valencia", "-d", "2026-12-05", "--print"])
    out = json.loads(capsys.readouterr().out)
    assert out["opened"] is False and out["shop"]["url"].startswith("https://ventas.ouigo.com/es-ES/_deeplink/")
    assert "origin=MT1" in out["shop"]["url"] and "destination=7103216" in out["shop"]["url"]


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
    assert e.value.code == 2
    assert cap.out == "" and json.loads(cap.err)["error"]["code"] == "unknown_station"


def test_cli_bad_date_exit_2(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["search", "Madrid", "Valencia", "-d", "2026-13-40"])
    assert e.value.code == 2 and json.loads(capsys.readouterr().err)["error"]["code"] == "bad_dates"


def test_blocked_exit_5(monkeypatch, capsys):
    def blocked(*a, **k):
        raise OuigoError("blocked", detail="HTTP 403")
    monkeypatch.setattr(core, "_capture", blocked)
    with pytest.raises(SystemExit) as e:
        cli.main(["search", "Madrid", "Valencia", "-d", "2026-12-04"])
    assert e.value.code == 5


def test_no_trains_is_notice_not_error(monkeypatch):
    monkeypatch.setattr(core, "_capture", lambda *a, **k: '{"outbound":[],"error":null}')
    r = core.search("Madrid", "Valencia", "2026-12-04")
    assert r["count"] == 0 and r["trains"] == [] and r["notice"]


def test_cli_stations_query(capsys):
    cli.main(["stations", "valen"])
    out = json.loads(capsys.readouterr().out)
    assert {s["code"] for s in out["stations"]} == {"7103216"}


def test_mcp_tools_registered():
    import asyncio
    from ouigo_es.mcp_server import mcp
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"search_trains", "cheapest_days", "find_station", "shop_link", "iryo_link"}


@pytest.mark.live
def test_live_search():
    from datetime import date, timedelta
    r = core.search("Madrid", "Valencia", (date.today() + timedelta(days=14)).isoformat())
    assert r["count"] > 0


def test_search_carries_iryo(monkeypatch):
    from test_iryo import GOLDEN
    monkeypatch.setattr(core, "_capture", lambda *a, **k: fx("search.json"))
    r = core.search("Madrid", "Valencia", "2026-12-15")
    assert r["iryo"]["url"] == GOLDEN and r["iryo"]["warning"] is None and "own page" in r["iryo"]["note"]
    assert core.search("Madrid", "Murcia", "2026-12-15")["iryo"] is None


def test_calendar_iryo_uses_cheapest_day(monkeypatch):
    monkeypatch.setattr(core, "_capture", lambda *a, **k: fx("calendar_month.json"))
    r = core.calendar("Madrid", "Valencia", "2026-12-05", "2026-12-20")
    assert r["iryo"]["date"] == r["cheapest"]["date"]
    assert f'%22departure%22:%22{r["cheapest"]["date"]}%22' in r["iryo"]["url"]


def test_mcp_has_instructions():
    from ouigo_es.mcp_server import mcp
    assert "iryo" in mcp.instructions.lower()
