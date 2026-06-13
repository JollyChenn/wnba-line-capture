# pinnacle_clv.py — pull Pinnacle WNBA player-prop lines via the guest API (no login,
# no quota) and stack the SHARP line against our model. Pinnacle ~ the true close, so
# this is the real edge test: does the sharp book agree our number is off?
#   Pinnacle offers single stats (Points/Rebounds/Assists) -> perfect for our points lead.
import csv, json, re
from collections import defaultdict
from curl_cffi import requests as creq

H = {"X-API-Key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "User-Agent": "Mozilla/5.0"}
B = "https://guest.api.arcadia.pinnacle.com/0.1"
STAT = {"Points": "pts", "Rebounds": "reb", "Assists": "ast"}


def dec(a):
    a = float(a)
    return round(1 + (100 / abs(a) if a < 0 else a / 100), 2)


def key_of(n):
    p = re.sub(r"[^a-z .'-]", "", n.lower()).replace(".", " ").split()
    return (p[0][0] + " " + p[-1]) if len(p) >= 2 else n.lower()


# 1) pull Pinnacle WNBA props (matchups = player+stat, markets = line+odds)
mm = creq.get(B + "/sports/4/matchups", impersonate="chrome", timeout=25, headers=H).json()
mk = creq.get(B + "/sports/4/markets/straight", impersonate="chrome", timeout=25, headers=H).json()
mkt = {x["matchupId"]: x for x in mk if x.get("type") == "total" and x.get("prices")}
pin = defaultdict(dict)
for m in mm:
    if "wnba" not in json.dumps(m.get("league", {})).lower():
        continue
    sp = m.get("special") or {}
    mt = re.match(r"(.+?) Total (Points|Rebounds|Assists)\b", sp.get("description", ""))
    if not mt or m["id"] not in mkt:
        continue
    pr = mkt[m["id"]]["prices"]
    over_id = next((p["id"] for p in m["participants"] if p["name"] == "Over"), None)
    over = next((dec(p["price"]) for p in pr if p["participantId"] == over_id), None)
    under = next((dec(p["price"]) for p in pr if p["participantId"] != over_id), None)
    pin[key_of(mt.group(1))][STAT[mt.group(2)]] = {"line": pr[0]["points"], "over": over, "under": under}
print(f"Pinnacle WNBA: {sum(len(v) for v in pin.values())} prop lines across {len(pin)} players")

# 2) stack vs our model (latest slate); single-stat markets Pinnacle actually offers
rows = list(csv.DictReader(open("picks_log.csv", encoding="utf-8")))
latest = max(r["pick_date"] for r in rows)
print(f"\nslate {latest}   (proj = our forecast ; Pinnacle line ~ the sharp's median)")
print(f"{'player':17}{'mkt':5}{'our med/proj':14}{'Pinnacle (line/u/o)':22}read")
print("-" * 82)
seen = set()
for r in rows:
    if r["pick_date"] != latest:
        continue
    base = r["market"].split("_")[0]
    if base not in ("pts", "reb", "ast") or (r["player"], base) in seen:
        continue
    seen.add((r["player"], base))
    pp = pin.get(key_of(r["player"]), {}).get(base)
    if not pp:
        continue
    proj = float(r["proj"]); pl = pp["line"]; med = float(r["anchor"])
    gap = proj - pl
    read = "sharp ABOVE our proj -> under has value" if gap <= -1.5 else \
           ("aligned (no edge vs sharp)" if abs(gap) < 1.5 else "sharp BELOW our proj -> we may be high")
    pin_s = f"{pl} u{pp['under']} o{pp['over']}"
    mp = f"{med:.0f}/{proj:.1f}"
    print(f"{r['player']:17}{base:5}{mp:14}{pin_s:22}{read}")
