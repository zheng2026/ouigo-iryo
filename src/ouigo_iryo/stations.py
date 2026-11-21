"""Station list (bundled stations.json) and forgiving name matching."""
import difflib
import json
import unicodedata
from pathlib import Path

from .errors import OuigoError

STATIONS_FILE = Path(__file__).with_name("stations.json")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().replace("-", " ").split())


def parse_stations(raw: list) -> list[dict]:
    """Raw GetStations body -> our compact schema."""
    return [
        {
            "code": s["_u_i_c_station_code"],
            "name": s["name"],
            "short_code": s.get("short_code"),
            "synonyms": s.get("synonyms", []),
            "connected": s.get("connected_stations", []),
            "hidden": bool(s.get("hidden")),
        }
        for s in raw
    ]


def load_stations() -> list[dict]:
    return json.loads(STATIONS_FILE.read_text(encoding="utf-8"))


def save_stations(stations: list[dict]) -> None:
    STATIONS_FILE.write_text(json.dumps(stations, ensure_ascii=False, indent=1), encoding="utf-8")


def _keys(st: dict) -> set[str]:
    k = {_norm(st["name"]), _norm(st["code"])}
    k.update(_norm(x) for x in st.get("synonyms", []))
    if st.get("short_code"):
        k.add(_norm(st["short_code"]))
    return k


def search_stations(query: str, stations: list[dict] | None = None) -> list[dict]:
    """Substring search on name/synonyms/codes (for `ouigo stations <query>`)."""
    stations = stations or load_stations()
    q = _norm(query)
    return [s for s in stations if any(q in k for k in _keys(s))]


def resolve(query: str, stations: list[dict] | None = None) -> dict:
    """Exact (accent/case-insensitive) match on name, synonym or code; else unknown_station."""
    stations = stations or load_stations()
    q = _norm(query)
    exact = [s for s in stations if q in _keys(s)]
    if exact:
        # "Madrid" matches the umbrella MT1 and two hidden stations: prefer visible ones.
        exact.sort(key=lambda s: s["hidden"])
        return exact[0]
    sub = [s for s in stations if not s["hidden"] and any(q and q in k for k in _keys(s))]
    if len(sub) == 1:
        return sub[0]
    names = {_norm(s["name"]): s["name"] for s in stations if not s["hidden"]}
    for s in stations:
        if not s["hidden"]:
            for syn in s.get("synonyms", []):
                names[_norm(syn)] = s["name"]
    close = difflib.get_close_matches(q, list(names), n=3, cutoff=0.5)
    suggestions = list(dict.fromkeys(names[c] for c in close)) or [s["name"] for s in sub[:5]]
    raise OuigoError("unknown_station", query=query, suggestions=suggestions)
