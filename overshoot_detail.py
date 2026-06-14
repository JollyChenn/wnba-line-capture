# overshoot_detail.py — for every deep overshoot-over, show the MODEL'S read: recent form
# (hot/cold) and minutes trend (expanding/shrinking). That tells us if the low line is a
# confirmed edge (hot/steady) or a possible trap (cold/shrinking = book may be right).
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
        log[r["player"].lower()].append((gd.get(r["game_id"]), float(r["pts"]), float(r["reb"]), float(r["ast"]), float(r["min"])))
    except (ValueError, TypeError):
        pass
pick = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3], "pra": lambda x: x[1] + x[2] + x[3]}

print("DEEP overshoot-overs + the model's signal:")
for plow, mk in sorted(props.items()):
    for (st, sd), outs in mk.items():
        if sd != "Over" or st not in pick:
            continue
        line, odds = min(outs, key=lambda t: t[0])
        g = sorted([x for x in log.get(plow, []) if x[0]], key=lambda t: t[0])
        v = [pick[st](x) for x in g]
        if len(v) < 5:
            continue
        v10 = v[-10:]; med = statistics.median(v10)
        if line > med - 3:
            continue
        t3 = statistics.mean(v[-3:]); proj = med + 0.25 * (t3 - med); s = statistics.pstdev(v10) or 1
        hit = 1 - cx._ncdf((line - proj) / s); ev = odds * hit - 1
        if ev <= 0:
            continue
        mins = [x[4] for x in g]
        t5m, t10m = statistics.mean(mins[-5:]), statistics.mean(mins[-10:] if len(mins) >= 4 else mins)
        form = "HOT🔥" if t3 >= med + 3 else "COLD🥶" if t3 <= med - 3 else "steady"
        mtr = "expanding↑" if t5m - t10m >= 3 else "shrinking↓" if t5m - t10m <= -3 else "flat mins"
        verdict = "✅ confirmed" if form != "COLD🥶" and mtr != "shrinking↓" else "⚠️ possible trap (book may be right)"
        print(f"  {plow.title():20} {st.upper()} O{line}@{odds}")
        print(f"     median {med:.1f} | last3 {t3:.1f} ({form}) | mins {t5m:.0f} vs {t10m:.0f} ({mtr}) | hit {hit*100:.0f}% EV {ev*100:+.0f}%  -> {verdict}")
