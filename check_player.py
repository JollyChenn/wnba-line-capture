# check_player.py — show a player's every market (median / proj / sd) next to the live 1xbet line,
# with the under AND over hit-rate, so we can judge a specific bet.
import csv, statistics, cloud_xbet as cx
from collections import defaultdict

near = cx.espn_near(600)
teams = set(t for a, h, _ in near for t in (a, h) if t)
nearkw = [cx.TEAMKW.get(t, [t.lower()]) for t in teams]
disc = cx.get(f"{cx.BASE}/LineFeed/Get1x2_VZip?sports=3&champs={cx.CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
games = [e for e in disc.get("Value", []) if isinstance(e, dict) and e.get("O1") and e.get("I")]
target = [e for e in games if any(all(w in f"{e.get('O1','')} {e.get('O2','')}".lower() for w in kw) for kw in nearkw)]
props = {}
for e in target:
    mv = cx.get(cx.gz(e["I"])); sg = (mv.get("Value", {}) or {}).get("SG", []) if mv else []
    stat = next((s for s in sg if "stat" in str(s.get("TG", "")).lower()), None)
    if not stat:
        continue
    val = (cx.get(cx.gz(stat["I"])) or {}).get("Value", {}) or {}
    def walk(o):
        if isinstance(o, dict):
            pl = o.get("PL"); T = o.get("T")
            if isinstance(pl, dict) and T in cx.T2S and o.get("P") is not None and o.get("C"):
                st, sd = cx.T2S[T]
                props.setdefault(str(pl.get("N", "")).lower(), {}).setdefault((st, sd), []).append((float(o["P"]), float(o["C"])))
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(val)

gd = {r["game_id"]: r.get("date") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
log = defaultdict(list)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    try:
        log[r["player"].lower()].append((gd.get(r["game_id"]), float(r["pts"]), float(r["reb"]), float(r["ast"])))
    except (ValueError, TypeError):
        pass
pick = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3], "ra": lambda x: x[2] + x[3], "pra": lambda x: x[1] + x[2] + x[3]}

for who in ["breanna stewart", "bridget carleton"]:
    g = sorted([x for x in log.get(who, []) if x[0]], key=lambda t: t[0])
    print(f"\n=== {who.title()} ===  last5 pts {[int(x[1]) for x in g[-5:]]} reb {[int(x[2]) for x in g[-5:]]} ast {[int(x[3]) for x in g[-5:]]}")
    for st, f in pick.items():
        v = [f(x) for x in g]
        if len(v) < 5:
            continue
        v10 = v[-10:]; med = statistics.median(v10); proj = med + 0.25 * (statistics.mean(v[-3:]) - med); s = statistics.pstdev(v10) or 1
        ln = props.get(who, {}).get((st, "Over"))
        lnstr = ""
        if ln:
            line, odds = min(ln, key=lambda t: t[0])
            pu = cx._ncdf((line - proj) / s)
            lnstr = f"  ->  1xbet {line}@{odds}:  UNDER hit {pu*100:.0f}%  /  OVER hit {(1-pu)*100:.0f}%"
        print(f"  {st.upper():4} med {med:.1f}  proj {proj:.1f}  sd {s:.1f}{lnstr}")
