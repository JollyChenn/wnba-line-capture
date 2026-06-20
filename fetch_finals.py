# fetch_finals.py — one-off: pull missing FINAL games + boxes from ESPN and patch
# games_2026.csv (fill blank scores) + box_2026.csv (append player rows). Mirrors
# daily_picks.fetch_day/fetch_box exactly so the schema matches. Safe to re-run (idempotent:
# only fills blank scores; only appends boxes for game_ids not already present).
import csv, os, sys, datetime, requests

SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"
_H = {"User-Agent": "Mozilla/5.0"}
IDX = {"min": 0, "pts": 1, "fg": 2, "tp": 3, "ft": 4, "reb": 5, "ast": 6,
       "to": 7, "stl": 8, "blk": 9, "oreb": 10, "dreb": 11, "pf": 12, "pm": 13}
GAMES_CSV = os.path.join("data", "games_2026.csv")
BOX_CSV = os.path.join("data", "box_2026.csv")


def _f(x):
    try:
        return float(str(x).replace("%", ""))
    except (ValueError, TypeError):
        return 0.0


def fetch_day(d):
    try:
        r = requests.get(SB, params={"dates": d.strftime("%Y%m%d")}, headers=_H, timeout=20)
        r.raise_for_status(); js = r.json()
    except Exception as e:
        print("  scoreboard fail", d, str(e)[:50]); return []
    fin = []
    for ev in js.get("events", []):
        if (ev.get("season") or {}).get("type") != 2:
            continue
        comp = (ev.get("competitions") or [{}])[0]
        cs = comp.get("competitors", [])
        home = next((t for t in cs if t.get("homeAway") == "home"), {})
        away = next((t for t in cs if t.get("homeAway") == "away"), {})
        if not (ev.get("status") or {}).get("type", {}).get("completed"):
            continue
        fin.append({"game_id": str(ev.get("id")), "date": d.strftime("%Y%m%d"),
                    "home": (home.get("team") or {}).get("abbreviation"),
                    "away": (away.get("team") or {}).get("abbreviation"),
                    "tip": ev.get("date", ""),
                    "home_score": _f(home.get("score")), "away_score": _f(away.get("score"))})
    return fin


def fetch_box(gid):
    r = requests.get(SUMMARY, params={"event": gid}, headers=_H, timeout=20)
    r.raise_for_status()
    rows = []
    for tm in r.json().get("boxscore", {}).get("players", []):
        code = (tm.get("team") or {}).get("abbreviation")
        for sg in tm.get("statistics", []) or []:
            for a in sg.get("athletes", []) or []:
                st = a.get("stats", []) or []
                if len(st) <= IDX["pm"]:
                    continue
                mn = _f(st[IDX["min"]])
                if not (mn > 0):
                    continue
                ath = a.get("athlete", {}) or {}
                rows.append({"game_id": str(gid), "team": code, "player": ath.get("displayName"),
                             "aid": ath.get("id"), "min": mn, "pts": _f(st[IDX["pts"]]),
                             "reb": _f(st[IDX["reb"]]), "ast": _f(st[IDX["ast"]]),
                             "fga": _f(str(st[IDX["fg"]]).split("-")[-1]),
                             "fta": _f(str(st[IDX["ft"]]).split("-")[-1]), "to": _f(st[IDX["to"]])})
    return rows


dates = [datetime.date(2026, 6, 19), datetime.date(2026, 6, 20)]
if len(sys.argv) > 1:                                   # allow override: python fetch_finals.py 20260619 20260620
    dates = [datetime.datetime.strptime(a, "%Y%m%d").date() for a in sys.argv[1:]]

fin = []
for d in dates:
    f = fetch_day(d)
    print(f"{d}: {len(f)} completed game(s)")
    fin += f

# ---- patch games_2026.csv: fill blank scores for completed games (match by game_id) ----
grows = list(csv.DictReader(open(GAMES_CSV, encoding="utf-8")))
gflds = grows[0].keys() if grows else ["game_id", "date", "home", "away", "tip", "home_score", "away_score"]
gby = {r["game_id"]: r for r in grows}
fin_by = {g["game_id"]: g for g in fin}
filled = 0
for gid, g in fin_by.items():
    if gid in gby:
        if not gby[gid].get("home_score"):
            gby[gid]["home_score"] = g["home_score"]; gby[gid]["away_score"] = g["away_score"]; filled += 1
    else:
        gby[gid] = g; filled += 1
with open(GAMES_CSV, "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=list(gflds))
    wr.writeheader()
    for r in sorted(gby.values(), key=lambda x: (x["date"], x["game_id"])):
        wr.writerow(r)
print(f"games_2026.csv: filled/added {filled} game score(s)")

# ---- append box rows for completed games we don't already have ----
have = {r["game_id"] for r in csv.DictReader(open(BOX_CSV, encoding="utf-8"))} if os.path.exists(BOX_CSV) else set()
bflds = ["game_id", "team", "player", "aid", "min", "pts", "reb", "ast", "fga", "fta", "to"]
newrows = []
for gid in fin_by:
    if gid in have:
        continue
    try:
        b = fetch_box(gid)
        newrows += b
        print(f"  box {gid}: +{len(b)} players")
    except Exception as e:
        print(f"  box {gid} FAIL: {str(e)[:50]}")
if newrows:
    with open(BOX_CSV, "a", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=bflds)
        for r in newrows:
            wr.writerow(r)
print(f"box_2026.csv: appended {len(newrows)} player row(s)")
