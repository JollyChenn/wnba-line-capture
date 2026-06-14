# board_scan.py — find overshoot-overs across the WHOLE board, including players we don't
# signal-pick. Compute every board player's trailing median/proj/sd from box_2026, then flag
# any 1xbet OVER line sitting well below their median (the deep-overshoot the bot currently misses).
import csv, statistics, math, cloud_xbet as cx
from collections import defaultdict

# 1) board pull (same data the bot sees)
near = cx.espn_near(600)
teams = set(t for a, h, _ in near for t in (a, h) if t)
nearkw = [cx.TEAMKW.get(t, [t.lower()]) for t in teams]
disc = cx.get(f"{cx.BASE}/LineFeed/Get1x2_VZip?sports=3&champs={cx.CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
games_e = [e for e in disc.get("Value", []) if isinstance(e, dict) and e.get("O1") and e.get("I")]
target = [e for e in games_e if any(all(w in f"{e.get('O1','')} {e.get('O2','')}".lower() for w in kw) for kw in nearkw)]
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

# 2) every player's trailing log from box_2026
gd = {r["game_id"]: r.get("date") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
log = defaultdict(list)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    d = gd.get(r["game_id"])
    try:
        log[r["player"].lower()].append((d, float(r["pts"]), float(r["reb"]), float(r["ast"])))
    except (ValueError, TypeError):
        pass

def series(plow, st):
    g = sorted([x for x in log.get(plow, []) if x[0]], key=lambda t: t[0])
    f = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3],
         "pra": lambda x: x[1] + x[2] + x[3]}.get(st)
    return [f(x) for x in g] if f else []

# 3) flag deep overshoot-overs
print(f"{'player':20}{'mkt':5}{'OVER':>7}{'odds':>6}{'med':>6}{'proj':>6}{'below':>6}{'hit':>5}{'EV':>6}")
hits = []
for plow, mk in sorted(props.items()):
    for (st, sd), outs in mk.items():
        if sd != "Over":
            continue
        line, odds = min(outs, key=lambda t: t[0])
        v = series(plow, st)
        if len(v) < 5:
            continue
        v10 = v[-10:]
        med = statistics.median(v10)
        t3 = statistics.mean(v[-3:])
        proj = med + 0.25 * (t3 - med)                      # same calibrated proj the backtest validated
        s = statistics.pstdev(v10) or 1
        if line > med - 3:                                  # only deep overshoots
            continue
        hit = 1 - cx._ncdf((line - proj) / s)
        ev = odds * hit - 1
        print(f"{plow[:19]:20}{st:5}{line:>7}{odds:>6}{med:>6.1f}{proj:>6.1f}{line-med:>6.1f}{hit*100:>4.0f}%{ev*100:>+5.0f}%")
        if ev > 0:
            hits.append((plow, st, line, odds, med, hit, ev))
print("\n🎯 DEEP overshoot-overs that are +EV right now:")
for plow, st, line, odds, med, hit, ev in sorted(hits, key=lambda x: -x[6]):
    print(f"  {plow} {st.upper()} OVER {line} @ {odds}  (median {med:.1f}, hit {hit*100:.0f}%, EV {ev*100:+.0f}%)")
if not hits:
    print("  (none — no over line is 3+ below a player's median at +EV odds)")
