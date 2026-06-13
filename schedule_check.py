# schedule_check.py — cross-check the WNBA schedule from TWO independent sources
# (ESPN + the-odds-api) so we never trust one source's dates/tips. Flags any game
# that's missing from one side, or whose tip-time disagrees by >15 min.
import urllib.request, json, datetime, os
from zoneinfo import ZoneInfo
from cloud_xbet import TEAMKW   # reuse the canonical abbreviation -> keyword map

MY = ZoneInfo("Asia/Kuala_Lumpur")
H = {"User-Agent": "Mozilla/5.0"}
now = datetime.datetime.now(datetime.timezone.utc)


def norm(name):
    n = (name or "").lower()
    for ab, kws in TEAMKW.items():
        if any(w in n for w in kws):
            return ab
    return (name or "???")[:3].upper()


# 1) ESPN (keyless, primary)
espn = {}
for d in range(0, 4):
    day = (now + datetime.timedelta(days=d)).strftime("%Y%m%d")
    try:
        j = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates=" + day, headers=H), timeout=20))
    except Exception:
        continue
    for ev in j.get("events", []):
        if ev.get("status", {}).get("type", {}).get("state") != "pre":
            continue
        c = (ev.get("competitions") or [{}])[0].get("competitors", [])
        a = next((t for t in c if t.get("homeAway") == "away"), {})
        hh = next((t for t in c if t.get("homeAway") == "home"), {})
        tip = datetime.datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        espn[(norm((a.get("team") or {}).get("displayName", "")), norm((hh.get("team") or {}).get("displayName", "")))] = tip

# 2) the-odds-api events (independent; the /events endpoint is FREE — no quota cost)
KEY = (os.environ.get("ODDS_API_KEYS", "").split(",")[0].strip()) or "387645d689cd646ead0f9680f15e3713"
oddsapi, err = {}, None
try:
    j = json.load(urllib.request.urlopen(urllib.request.Request(
        f"https://api.the-odds-api.com/v4/sports/basketball_wnba/events?apiKey={KEY}", headers=H), timeout=20))
    for ev in j:
        tip = datetime.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        if tip < now - datetime.timedelta(minutes=30):
            continue
        oddsapi[(norm(ev.get("away_team", "")), norm(ev.get("home_team", "")))] = tip
except Exception as e:
    err = str(e)[:80]

# 3) cross-check
print(f"ESPN: {len(espn)} upcoming   |   the-odds-api: {len(oddsapi)} upcoming" + (f"   (odds-api err: {err})" if err else ""))
print("=" * 78)
print(f"{'game':11}{'ESPN tip (MYT)':20}{'odds-api tip (MYT)':22}status")
print("-" * 78)
allk = sorted(set(espn) | set(oddsapi), key=lambda k: (espn.get(k) or oddsapi.get(k)))
mismatches = 0
for k in allk:
    e, o = espn.get(k), oddsapi.get(k)
    es = e.astimezone(MY).strftime("%a %I:%M%p") if e else "-- missing --"
    osd = o.astimezone(MY).strftime("%a %I:%M%p") if o else "-- missing --"
    if e and o:
        diff = abs((e - o).total_seconds()) / 60
        status = "OK (both agree)" if diff <= 15 else f"WARN tip differs {int(diff)}min"
    elif e:                                       # only ESPN has it
        hrs = (e - now).total_seconds() / 3600
        status = "info: ESPN-only (>2d out, book not posted yet)" if hrs > 48 else "WARN near game missing from odds-api"
    else:                                         # only the-odds-api has it
        status = "WARN missing from ESPN"
    if status.startswith("WARN"):
        mismatches += 1
    print(f"{k[0]}@{k[1]:<7}{es:20}{osd:22}{status}")
print("-" * 78)
print(f"{mismatches} discrepancy(ies)." + (" Schedule agrees across both sources." if mismatches == 0 else " Review the WARNs above before trusting those games."))
