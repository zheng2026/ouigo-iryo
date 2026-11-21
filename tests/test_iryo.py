import json
from unittest import mock

import pytest

from ouigo_es import iryo, iryo_cli, mcp_server
from ouigo_es.errors import OuigoError

GOLDEN = (
    "https://iryo.eu/es/booking/travels?passengers=%5B%7B%22type%22:%22AD%22,%22discountCards%22:%5B%5D,%22id%22:%22passenger_1%22%7D%5D"
    "&origin=%7B%22uicStationCode%22:%22X0000%22,%22uicCountryCode%22:%2271%22%7D"
    "&destination=%7B%22uicStationCode%22:%2203216%22,%22uicCountryCode%22:%2271%22%7D"
    "&discount=%5B%5D&payWithPoints=false&currency="
    "&travels=%5B%7B%22origin%22:%22X0000%22,%22destination%22:%2203216%22,%22direction%22:%22outbound%22,%22departure%22:%222026-12-15%22%7D%5D"
    "&tripDirection=outbound&tripIntention=forLeisure&passengerHSelected=false"
    "&client=eyJjbGllbnRJZCI6ImIyYyIsImNoYW5uZWwiOiIiLCJpc1JlcXVlc3RQYXJhbSI6dHJ1ZX0%3D"
)


def test_golden_link():
    assert iryo.build_link("X0000", "03216", "2026-12-15") == GOLDEN


def test_madrid_is_group_and_single_stations():
    assert iryo.resolve("Madrid")["code"] == "X0000"
    assert iryo.resolve("Atocha")["code"] == "60000"
    assert iryo.resolve("Chamartín")["code"] == "17000"


def test_accents_case():
    assert iryo.resolve("VALENCIA")["code"] == "03216"
    assert iryo.resolve("cordoba")["code"] == "50500"
    assert iryo.resolve("Málaga")["code"] == "54413"


def test_typo_suggestion():
    with pytest.raises(OuigoError) as e:
        iryo.resolve("Valenzia")
    assert e.value.code == "unknown_station" and e.value.exit_code == 2
    assert any("València" in s for s in e.value.extra["suggestions"])


def test_warnings():
    assert iryo.iryo_link("Atocha", "Valencia", "2026-12-15")["warning"]
    assert iryo.iryo_link("Valencia", "Atocha", "2026-12-15")["warning"]
    assert iryo.iryo_link("Madrid", "Valencia", "2026-12-15")["warning"] is None
    assert iryo.iryo_link("Chamartín", "Valencia", "2026-12-15")["warning"] is None
    assert iryo.iryo_link("Atocha", "Sevilla", "2026-12-15")["warning"] is None


def test_result_shape():
    r = iryo.iryo_link("Madrid", "Valencia", "2026-12-15")
    assert r["url"] == GOLDEN and r["origin"]["code"] == "X0000" and r["destination"]["code"] == "03216"
    assert r["date"] == "2026-12-15" and "never fetches" in r["notice"]


def test_bad_date_exit_2(capsys):
    with pytest.raises(SystemExit) as e:
        iryo_cli.main(["open", "Madrid", "Valencia", "-d", "15-12-2026", "--print"])
    assert e.value.code == 2


def test_cli_print(capsys):
    with mock.patch("webbrowser.open") as wb:
        iryo_cli.main(["open", "Madrid", "Valencia", "-d", "2026-12-15", "--print"])
    assert capsys.readouterr().out.strip() == GOLDEN
    wb.assert_not_called()


def test_cli_open_and_json(capsys):
    with mock.patch("webbrowser.open", return_value=True) as wb:
        iryo_cli.main(["open", "Madrid", "Valencia", "-d", "2026-12-15", "--json"])
    wb.assert_called_once_with(GOLDEN)
    assert json.loads(capsys.readouterr().out)["url"] == GOLDEN


def test_cli_unknown_station_exit_2(capsys):
    with pytest.raises(SystemExit) as e:
        iryo_cli.main(["open", "Valenzia", "Madrid", "-d", "2026-12-15", "--print"])
    assert e.value.code == 2
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "unknown_station"


def test_mcp_tool_returns_dict():
    with mock.patch("webbrowser.open") as wb:
        r = mcp_server.iryo_link("Madrid", "Valencia", "2026-12-15")
    assert r["url"] == GOLDEN
    wb.assert_not_called()
    assert mcp_server.iryo_link("Madrid", "Valencia", "nope")["error"]["code"] == "bad_dates"
