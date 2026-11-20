import argparse
import json
import sys

from . import core, stations
from .errors import OuigoError


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def build_parser():
    p = argparse.ArgumentParser(prog="ouigo", description="Unofficial Ouigo Espana fares (JSON output).")
    p.add_argument("--debug", action="store_true", help="show the browser and log response URLs (never headers)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="trains and prices for one day")
    s.add_argument("origin"); s.add_argument("destination")
    s.add_argument("-d", "--date", required=True, help="YYYY-MM-DD")
    s.add_argument("--after", help="only departures at or after HH:MM")
    s.add_argument("--limit", type=int, help="max trains")
    c = sub.add_parser("calendar", help="cheapest price per day")
    c.add_argument("origin"); c.add_argument("destination")
    c.add_argument("--from", dest="start", required=True); c.add_argument("--to", dest="end", required=True)
    t = sub.add_parser("stations", help="list/find stations")
    t.add_argument("query", nargs="?")
    t.add_argument("--refresh", action="store_true", help="re-read the list from Ouigo's page")
    return p


def run(args) -> dict | list:
    if args.cmd == "search":
        r = core.search(args.origin, args.destination, args.date, debug=args.debug)
        trains = r["trains"]
        if args.after:
            trains = [t for t in trains if t["departure"] >= args.after]
            if not trains:
                raise OuigoError("no_trains", date=args.date, after=args.after)
        if args.limit:
            trains = trains[: args.limit]
        r["trains"], r["count"] = trains, len(trains)
        return r
    if args.cmd == "calendar":
        return core.calendar(args.origin, args.destination, args.start, args.end, debug=args.debug)
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
        sys.exit(2)
    except ValueError as e:
        print(json.dumps({"error": "bad_input", "detail": str(e)}), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
