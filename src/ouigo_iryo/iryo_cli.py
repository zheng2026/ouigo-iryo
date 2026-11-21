import argparse
import json
import sys
import webbrowser

from . import iryo
from .errors import OuigoError


def build_parser():
    p = argparse.ArgumentParser(prog="iryo", description="Iryo booking links (no fares: Iryo blocks automation).")
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open", help="open Iryo's own search page for this trip (you pick and pay there)")
    o.add_argument("origin"); o.add_argument("destination")
    o.add_argument("-d", "--date", required=True, help="YYYY-MM-DD")
    o.add_argument("--print", dest="print_only", action="store_true", help="only print the link")
    o.add_argument("--json", dest="as_json", action="store_true", help="print the full result as JSON")
    t = sub.add_parser("stations", help="list/find stations")
    t.add_argument("query", nargs="?")
    return p


def run(args):
    if args.cmd == "open":
        r = iryo.iryo_link(args.origin, args.destination, args.date)
        if r["warning"]:
            print(f"warning: {r['warning']}", file=sys.stderr)
        if args.as_json:
            r["opened"] = False if args.print_only else bool(webbrowser.open(r["url"]))
            return json.dumps(r, ensure_ascii=False, indent=2)
        if args.print_only:
            return r["url"]
        webbrowser.open(r["url"])
        return r["url"]
    st = iryo.search_stations(args.query) if args.query else iryo.STATIONS
    return json.dumps({"count": len(st), "stations": st}, ensure_ascii=False, indent=2)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        print(run(args))
    except OuigoError as e:
        print(json.dumps(e.payload(), ensure_ascii=False), file=sys.stderr)
        sys.exit(e.exit_code)
    except ValueError as e:
        print(json.dumps({"error": {"code": "bad_input", "detail": str(e)}}), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(json.dumps({"error": {"code": "internal", "type": type(e).__name__}}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
