"""Iryo link builder. Pure: no network, no browser, nothing is ever sent to Iryo.

Iryo blocks automated access, so this only BUILDS a booking link that a person opens.
"""
import difflib
import json
from datetime import date as _date
from urllib.parse import quote

from .errors import OuigoError
from .stations import _norm

BASE = "https://iryo.eu/es/booking/travels"
CLIENT = "eyJjbGllbnRJZCI6ImIyYyIsImNoYW5uZWwiOiIiLCJpc1JlcXVlc3RQYXJhbSI6dHJ1ZX0%3D"
NOTICE = "Iryo shows trains and fares on its own page; this tool never fetches them."

ATOCHA, CHAMARTIN = "60000", "17000"

STATIONS = [
    {"code": "X0000", "name": "Madrid (todas las estaciones)", "city": "Madrid", "group": True,
     "aliases": ["Madrid", "Madrid todas", "Madrid todas las estaciones"]},
    {"code": "60000", "name": "Madrid Puerta de Atocha-Almudena Grandes", "city": "Madrid",
     "aliases": ["Atocha", "Madrid Atocha", "Madrid Puerta de Atocha"]},
    {"code": "17000", "name": "Madrid Chamartín-Clara Campoamor", "city": "Madrid",
     "aliases": ["Chamartin", "Madrid Chamartin", "Clara Campoamor"]},
    {"code": "03216", "name": "València Joaquín Sorolla", "city": "València",
     "aliases": ["Valencia", "Valencia Joaquin Sorolla", "Joaquin Sorolla"]},
    {"code": "03208", "name": "Cuenca Fernando Zóbel", "city": "Cuenca", "aliases": ["Cuenca", "Fernando Zobel"]},
    {"code": "04040", "name": "Zaragoza Delicias", "city": "Zaragoza", "aliases": ["Zaragoza", "Delicias"]},
    {"code": "50500", "name": "Córdoba Julio Anguita", "city": "Córdoba", "aliases": ["Cordoba", "Julio Anguita"]},
    {"code": "51003", "name": "Sevilla Santa Justa", "city": "Sevilla", "aliases": ["Sevilla", "Seville", "Santa Justa"]},
    {"code": "60911", "name": "Alicante/Alacant Terminal", "city": "Alicante",
     "aliases": ["Alicante", "Alacant", "Alicante Terminal"]},
    {"code": "71801", "name": "Barcelona Sants", "city": "Barcelona", "aliases": ["Barcelona", "Sants"]},
    {"code": "60600", "name": "Albacete Los Llanos", "city": "Albacete", "aliases": ["Albacete", "Los Llanos"]},
    {"code": "02003", "name": "Antequera Santa Ana", "city": "Antequera", "aliases": ["Antequera", "Santa Ana"]},
    {"code": "04104", "name": "Camp de Tarragona", "city": "Tarragona", "aliases": ["Tarragona", "Camp Tarragona"]},
    {"code": "54413", "name": "Málaga María Zambrano", "city": "Málaga",
     "aliases": ["Malaga", "Maria Zambrano", "Malaga Maria Zambrano"]},
]
BY_CODE = {s["code"]: s for s in STATIONS}

# Verified connections, used for warnings only. Unknown pairs get no warning.
CONNECTIONS = {"03216": {"03208", "17000"}}
_MADRID_SINGLE = {ATOCHA, CHAMARTIN}


def _keys(st: dict) -> set[str]:
    k = {_norm(st["name"]), _norm(st["code"])}
    k.update(_norm(a) for a in st["aliases"])
    return k


def search_stations(query: str) -> list[dict]:
    q = _norm(query)
    return [s for s in STATIONS if any(q in k for k in _keys(s))]


def resolve(query: str) -> dict:
    q = _norm(query)
    exact = [s for s in STATIONS if q in _keys(s)]
    if exact:
        return exact[0]
    sub = [s for s in STATIONS if q and any(q in k for k in _keys(s))]
    if len(sub) == 1:
        return sub[0]
    names = {}
    for s in STATIONS:
        for k in _keys(s):
            names[k] = s["name"]
    close = difflib.get_close_matches(q, list(names), n=3, cutoff=0.5)
    suggestions = list(dict.fromkeys(names[c] for c in close)) or [s["name"] for s in sub[:5]]
    raise OuigoError("unknown_station", query=query, suggestions=suggestions)


def _check_date(date: str):
    try:
        _date.fromisoformat(date)
    except ValueError:
        raise OuigoError("bad_dates", detail=f"not a YYYY-MM-DD date: {date!r}")


def _q(obj) -> str:
    return quote(json.dumps(obj, separators=(",", ":")), safe=":,")


def build_link(origin_code: str, dest_code: str, date: str) -> str:
    _check_date(date)
    st = lambda c: {"uicStationCode": c, "uicCountryCode": "71"}
    passengers = [{"type": "AD", "discountCards": [], "id": "passenger_1"}]
    travels = [{"origin": origin_code, "destination": dest_code, "direction": "outbound", "departure": date}]
    return (f"{BASE}?passengers={_q(passengers)}&origin={_q(st(origin_code))}"
            f"&destination={_q(st(dest_code))}&discount=%5B%5D&payWithPoints=false&currency="
            f"&travels={_q(travels)}&tripDirection=outbound&tripIntention=forLeisure"
            f"&passengerHSelected=false&client={CLIENT}")


def _warning(o: dict, d: dict) -> str | None:
    for single, other in ((o, d), (d, o)):
        known = CONNECTIONS.get(other["code"])
        if known and single["code"] in _MADRID_SINGLE and single["code"] not in known:
            return (f"Iryo's {other['city']} trains use Madrid-Chamartín, not Atocha; "
                    "try 'Madrid' or 'Chamartín'.")
    return None


def iryo_link(origin: str, destination: str, date: str) -> dict:
    o, d = resolve(origin), resolve(destination)
    _check_date(date)
    return {"url": build_link(o["code"], d["code"], date),
            "origin": {"code": o["code"], "name": o["name"]},
            "destination": {"code": d["code"], "name": d["name"]},
            "date": date, "warning": _warning(o, d), "notice": NOTICE}


COMPANION_NOTE = "Iryo shows its trains and prices only on its own page: open the link to compare."


def companion(origin: str, destination: str, date: str) -> dict | None:
    """Iryo link for the same route and day, attached to Ouigo answers. None if Iryo does not serve a station."""
    try:
        r = iryo_link(origin, destination, date)
    except OuigoError:
        return None
    return {"url": r["url"], "origin": r["origin"], "destination": r["destination"],
            "date": date, "warning": r["warning"], "note": COMPANION_NOTE}
