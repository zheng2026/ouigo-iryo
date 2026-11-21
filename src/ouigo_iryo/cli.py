import argparse
import json
import sys
import webbrowser

from . import core, stations
from .errors import OuigoError


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def build_parser():
    p = argparse.ArgumentParser(prog="ouigo", description="Unofficial Ouigo Espana fares (JSON output).")
    p.add_argument("--debug", action="store_true", help="show the browser and log response URLs (never headers)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="trains and fares for one day")
    s.add_argument("origin"); s.add_argument("destination")
    s.add_argument("-d", "--date", required=True, help="YYYY-MM-DD")
    s.add_argument("--after", help="only departures at or after HH:MM")
    s.add_argument("--sort", choices=["time", "price"], default="time",
                   help="train order: departure time (default, as renfe-cli) or cheapest fare first")
    s.add_argument("--limit", type=int, help="max trains")
    c = sub.add_parser("calendar", help="cheapest price per day")
    c.add_argument("origin"); c.add_argument("destination")
    c.add_argument("--from", dest="start", required=True); c.add_argument("--to", dest="end", required=True)
    o = sub.add_parser("open", help="open Ouigo's own search page for this trip (you pick and pay there)")
    o.add_argument("origin"); o.add_argument("destination")
    o.add_argument("-d", "--date", required=True, help="YYYY-MM-DD")
    o.add_argument("--print", dest="print_only", action="store_true", help="only print the link")
    t = sub.add_parser("stations", help="list/find stations")
    t.add_argument("query", nargs="?")
    t.add_argument("--refresh", action="store_true", help="re-read the list from Ouigo's page")
    return p


def _cheapest(t):
    return t["fares"][0]["price"] if t["fares"] else float("inf")


def run(args) -> dict | list:
    if args.cmd == "search":
        r = core.search(args.origin, args.destination, args.date, debug=args.debug)
        trains = r["trains"]
        if args.after:
            trains = [t for t in trains if t["departure"][11:16] >= args.after]
            if not trains and r["count"]:
                r["notice"] = f"No Ouigo trains at or after {args.after}."
        if args.sort == "price":
            trains = sorted(trains, key=lambda t: (_cheapest(t), t["departure"]))
        if args.limit:
            trains = trains[: args.limit]
        r["trains"], r["count"] = trains, len(trains)
        return r
    if args.cmd == "calendar":
        return core.calendar(args.origin, args.destination, args.start, args.end, debug=args.debug)
    if args.cmd == "open":
        r = core.open_link(args.origin, args.destination, args.date)
        r["opened"] = False if args.print_only else bool(webbrowser.open(r["shop"]["url"]))
        return r
    if args.refresh:
        st = core.refresh_stations(debug=args.debug)
    else:
        st = stations.load_stations()
    if args.query:
        st = stations.search_stations(args.query, st)
    return {"count": len(st), "stations": st}


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        _out(run(args))
    except OuigoError as e:
        print(json.dumps(e.payload(), ensure_ascii=False), file=sys.stderr)
        sys.exit(e.exit_code)
    except ValueError as e:
        print(json.dumps({"error": {"code": "bad_input", "detail": str(e)}}), file=sys.stderr)
        sys.exit(2)
    except Exception as e:  # internal error: show only the exception type, as renfe-cli does
        print(json.dumps({"error": {"code": "internal", "type": type(e).__name__}}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
