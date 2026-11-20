"""Record real response BODIES (never headers) Ouigo's own page receives. Listen only."""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
date = sys.argv[1] if len(sys.argv) > 1 else "2026-12-04"
URL = ("https://ventas.ouigo.com/es-ES/_deeplink/journey-search?origin=MT1&destination=7103216"
       f"&outboundDate={date}&passengers%5B0%5D%5Btype%5D=A")
seen = []

def on_response(resp):
    u = resp.url
    if "/api/" not in u:
        return
    try:
        body = resp.text()
    except Exception:
        return
    seen.append((u.split("/api/")[-1], resp.status, resp.request.post_data, body))

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    page = b.new_page()
    page.on("response", on_response)
    page.goto(URL, wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(15000)
    print("title:", page.title())
    if not any(s[0].startswith("Data/GetStations") for s in seen):
        time.sleep(2)
        page.goto("https://www.ouigo.com/es-es", wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(10000)
    b.close()

for path, status, rb, body in seen:
    print(status, path, len(body))
def save(name, body):
    (OUT / name).write_text(body)
    print("saved", name)
for path, status, rb, body in seen:
    if status != 200: continue
    if path.startswith("Sale/journeysearch") and not (OUT/"search.json").exists(): save("search.json", body)
    elif path.startswith("Calendar/prices"):
        r = json.loads(rb or "{}")
        span = int(r["end"][8:10]) - int(r["begin"][8:10]) if r.get("begin") else 0
        save("calendar_month.json" if span > 10 else "calendar_5day.json", body)
        print("  req range", r.get("begin"), r.get("end"))
    elif path.startswith("Data/GetStations"): save("stations.json", body)
