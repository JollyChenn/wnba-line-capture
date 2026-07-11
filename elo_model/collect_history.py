# collect_history.py - Phase 1: full WNBA history 2023-2026 from ESPN (stdlib only, gentle 0.4s pacing,
# RESUME-SAFE: reruns skip already-collected game_ids). Writes into elo_model/:
#   games_full.csv  game_id,date,home,away,home_score,away_score,season
#   box_full.csv    game_id,team,player,aid,starter,min,pts,fgm,fga,tpm,tpa,ftm,fta,oreb,dreb,reb,ast,to,stl,blk,pf,pm
#   shots.csv       game_id,period,team_id,shooter,x,y,made,three  (raw coords; zone-bucketing in engine)
#   timeouts.csv    game_id,period,clock,team_txt
import json, urllib.request, csv, os, time, datetime, re, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
UA = {"User-Agent": "Mozilla/5.0"}
B = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/"
D = os.path.dirname(os.path.abspath(__file__))
def getj(u):
    for _ in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25))
        except Exception: time.sleep(3)
    return {}

def season_dates(yr):  # regular season+playoffs window
    d = datetime.date(yr, 5, 1); end = datetime.date(yr, 10, 25)
    while d <= end:
        yield d.strftime("%Y%m%d"); d += datetime.timedelta(days=1)

done = set()
bf = os.path.join(D, "box_full.csv")
if os.path.exists(bf):
    done = {r.split(",")[0] for r in open(bf, encoding="utf-8").read().splitlines()[1:]}
new_files = not os.path.exists(bf)
gf=open(os.path.join(D, "games_full.csv"), "a", newline="", encoding="utf-8"); g_w = csv.writer(gf)
bfh=open(bf, "a", newline="", encoding="utf-8"); b_w = csv.writer(bfh)
sf=open(os.path.join(D, "shots.csv"), "a", newline="", encoding="utf-8"); s_w = csv.writer(sf)
tf=open(os.path.join(D, "timeouts.csv"), "a", newline="", encoding="utf-8"); t_w = csv.writer(tf)
if new_files:
    g_w.writerow("game_id,date,home,away,home_score,away_score,season".split(","))
    b_w.writerow("game_id,team,player,aid,starter,min,pts,fgm,fga,tpm,tpa,ftm,fta,oreb,dreb,reb,ast,to,stl,blk,pf,pm".split(","))
    s_w.writerow("game_id,period,team_id,shooter,x,y,made,three".split(","))
    t_w.writerow("game_id,period,clock,team_txt".split(","))

def num(s):
    try: return float(s)
    except Exception: return ""

SHOT_RE = re.compile(r"^(.*?) (makes|misses)")
for yr in (2023, 2024, 2025, 2026):
    seen_dates = 0
    for ds in season_dates(yr):
        sb = getj(B + "scoreboard?dates=" + ds)
        for ev in sb.get("events", []):
            gid = str(ev["id"])
            comp = ev["competitions"][0]
            if comp.get("status", {}).get("type", {}).get("state") != "post" or gid in done:
                continue
            cs = {c["homeAway"]: c for c in comp["competitors"]}
            j = getj(B + "summary?event=" + gid)
            box = j.get("boxscore", {}).get("players", [])
            if not box: continue
            g_w.writerow([gid, ds, cs["home"]["team"]["abbreviation"], cs["away"]["team"]["abbreviation"],
                          cs["home"].get("score"), cs["away"].get("score"), yr])
            for tm in box:
                tab = tm["team"]["abbreviation"]
                for st in tm.get("statistics", []):
                    for a in st.get("athletes", []):
                        v = a.get("stats", [])
                        if len(v) < 14 or v[0] in ("", "--"): continue
                        def split2(x): return (x.split("-") + [""])[:2]
                        fgm, fga = split2(v[2]); tpm, tpa = split2(v[3]); ftm, fta = split2(v[4])
                        b_w.writerow([gid, tab, a["athlete"]["displayName"], a["athlete"].get("id"),
                                      1 if a.get("starter") else 0, num(v[0]), num(v[1]), num(fgm), num(fga),
                                      num(tpm), num(tpa), num(ftm), num(fta), num(v[10]), num(v[11]), num(v[5]),
                                      num(v[6]), num(v[7]), num(v[8]), num(v[9]), num(v[12]), num(v[13])])
            for p in j.get("plays", []):
                c = p.get("coordinate") or {}
                x, y = c.get("x"), c.get("y")
                txt = p.get("text", "")
                if p.get("shootingPlay") and x is not None and -100 < x < 100 and -100 < y < 100:
                    m = SHOT_RE.match(txt)
                    if m:
                        s_w.writerow([gid, p.get("period", {}).get("number"), (p.get("team") or {}).get("id"),
                                      m.group(1), x, y, 1 if m.group(2) == "makes" else 0,
                                      1 if "three point" in txt else 0])
                elif "imeout" in txt:
                    t_w.writerow([gid, p.get("period", {}).get("number"),
                                  (p.get("clock") or {}).get("displayValue"), txt[:40]])
            done.add(gid)
            for _f in (g_w,b_w,s_w,t_w): pass
            gf.flush(); bfh.flush(); sf.flush(); tf.flush()
            time.sleep(0.4)
        if sb.get("events"): seen_dates += 1
    print(f"{yr}: cumulative games {len(done)}", flush=True)
print("DONE", len(done), "games")
