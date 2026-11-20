"""Open Ouigo's public search link in ordinary headless Chrome and LISTEN to the JSON
responses Ouigo's own page receives. No API calls of our own, no headers or tokens read,
no bot-check evasion: if blocked we stop and say so."""
import calendar as _cal
import json
import sys
import time
from datetime import date as _date, datetime, timedelta, timezone
from urllib.parse import quote

from .errors import OuigoError
from .stations import parse_stations, resolve, load_stations

DEEPLINK = ("https://ventas.ouigo.com/es-ES/_deeplink/journey-search?origin={o}&destination={d}"
            "&outboundDate={date}&passengers%5B0%5D%5Btype%5D=A")
WAIT_S = 25
MIN_GAP_S = 2.0
_last_load = [0.0]


def _log(debug, *a):
    if debug:
        print(*a, file=sys.stderr)


def _capture(url: str, want, debug: bool = False, retry: bool = True):
    """Load `url`, return the first body for which want(api_path, post_data, status, body) is truthy.
    Only response URLs, bodies and our own request body are looked at, never headers."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    gap = MIN_GAP_S - (time.monotonic() - _last_load[0])
    if gap > 0:
        time.sleep(gap)
    hits: list = []
    blocked: list = []

    def on_response(resp):
        u = resp.url
        if resp.request.is_navigation_request() and resp.status in (403, 429, 503):
            blocked.append(f"HTTP {resp.status} on {u.split('?')[0]}")
            return
        if "/api/" not in u:
            return
        _log(debug, "response", resp.status, u.split("/api/")[-1][:100])
        try:
            body = resp.text()
        except Exception:
            return
        path = u.split("/api/")[-1]
        if want(path, resp.request.post_data, resp.status, body):
            hits.append(body)

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=not debug)
            except Exception as e:
                raise OuigoError("browser_unavailable", detail=str(e).splitlines()[0])
            try:
                page = browser.new_page()
                page.on("response", on_response)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=WAIT_S * 1000)
                    end = time.monotonic() + WAIT_S
                    while not hits and not blocked and time.monotonic() < end:
                        page.wait_for_timeout(300)
                except PWTimeout:
                    pass
                title = ""
                try:
                    title = page.title()
                except Exception:
                    pass
                if blocked or "just a moment" in title.lower() or "captcha" in title.lower():
                    raise OuigoError("blocked", detail=(blocked[0] if blocked else f"challenge page: {title!r}"),
                                     note="Stopped; not trying to get past it.")
                if not hits:
                    if retry:
                        _last_load[0] = time.monotonic()
                        browser.close()
                        return _capture(url, want, debug, retry=False)
                    raise OuigoError("timeout", detail=f"no matching response within {WAIT_S}s")
                return hits[0]
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    finally:
        _last_load[0] = time.monotonic()


def _is_search(path, post, status, body):
    return path.startswith("Sale/journeysearch") and status == 200


def _month_matcher(month_first: _date):
    def want(path, post, status, body):
        if not (path.startswith("Calendar/prices") and status == 200):
            return False
        try:
            r = json.loads(post or "{}")
            return r.get("begin", "")[:10] == month_first.isoformat() and r.get("end", "")[:7] == month_first.isoformat()[:7]
        except Exception:
            return False
    return want


# ---- parsers (pure, tested on recorded fixtures) ----

def _hm(ts: str) -> str:
    return ts[11:16]


def parse_search(body, date: str) -> list[dict]:
    data = json.loads(body) if isinstance(body, (str, bytes)) else body
    trains = []
    for j in data.get("outbound") or []:
        segs = j.get("segments") or []
        if not segs:
            continue
        dep = j["departure_station"]["departure_timestamp"]
        arr = j["arrival_station"]["arrival_timestamp"]
        dur = int((datetime.fromisoformat(arr) - datetime.fromisoformat(dep)).total_seconds() // 60)
        fares = sorted(
            ({"name": p["name"], "family": p["product_family_id"], "price": p["price"]} for p in j.get("packages") or []),
            key=lambda f: f["price"],
        )
        trains.append({
            "service": "+".join(s["service_name"] for s in segs),
            "departure": _hm(dep),
            "arrival": _hm(arr),
            "duration_min": dur,
            "origin_station": j["departure_station"]["name"],
            "destination_station": j["arrival_station"]["name"],
            "price": j["price"],
            "currency": "EUR",
            "fares": fares,
            "sold_out": bool(j.get("full")),
        })
    trains.sort(key=lambda t: (t["price"] is None, t["price"], t["departure"]))
    return trains


def parse_calendar(body) -> list[dict]:
    data = json.loads(body) if isinstance(body, (str, bytes)) else body
    return [{"date": d["date"], "price": d.get("price"), "is_promo": bool(d.get("is_promo")),
             "is_best_price": bool(d.get("is_best_price"))} for d in data]


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _st(s):
    return {"code": s["code"], "name": s["name"]}


# ---- public API ----

def search(origin: str, destination: str, date: str, debug: bool = False) -> dict:
    o, d = resolve(origin), resolve(destination)
    _date.fromisoformat(date)
    body = _capture(DEEPLINK.format(o=quote(o["code"]), d=quote(d["code"]), date=date), _is_search, debug)
    trains = parse_search(body, date)
    if not trains:
        raise OuigoError("no_trains", date=date)
    return {"source": "ouigo", "date": date, "origin": _st(o), "destination": _st(d),
            "passengers": {"adults": 1}, "count": len(trains), "trains": trains, "fetched_at": _now()}


def calendar(origin: str, destination: str, start: str, end: str, debug: bool = False) -> dict:
    o, d = resolve(origin), resolve(destination)
    s, e = _date.fromisoformat(start), _date.fromisoformat(end)
    if e < s:
        raise OuigoError("bad_dates", detail="end is before start")
    days, m = [], _date(s.year, s.month, 1)
    while m <= e:
        # The page asks for the whole month of the date it is opened on.
        probe = max(m, _date.today() + timedelta(days=1)) if m.month == _date.today().month and m.year == _date.today().year else m
        body = _capture(DEEPLINK.format(o=quote(o["code"]), d=quote(d["code"]), date=probe.isoformat()),
                        _month_matcher(m), debug)
        days += [x for x in parse_calendar(body) if start <= x["date"] <= end]
        m = _date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    priced = [x for x in days if x["price"] is not None]
    cheapest = min(priced, key=lambda x: (x["price"], x["date"])) if priced else None
    return {"source": "ouigo", "origin": _st(o), "destination": _st(d), "days": days,
            "cheapest": {"date": cheapest["date"], "price": cheapest["price"]} if cheapest else None,
            "fetched_at": _now()}


def refresh_stations(debug: bool = False) -> list[dict]:
    """Re-read the station list the site itself loads (via a public search page)."""
    from .stations import save_stations
    nxt = (_date.today() + timedelta(days=14)).isoformat()
    body = _capture(DEEPLINK.format(o="MT1", d="7103216", date=nxt),
                    lambda p, post, st, b: p.startswith("Data/GetStations") and st == 200, debug)
    st = parse_stations(json.loads(body))
    save_stations(st)
    return st
