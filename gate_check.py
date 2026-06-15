# gate_check.py — recheck the overshoot GATES before any bet. For every 1xbet over line >=3 below the
# player's median, print PASS or the exact gate that rejected it (injury / team-change / minutes / cold / sharp).
import csv, statistics, cloud_xbet as cx
from collections import defaultdict

near = cx.espn_near(1080)
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
        log[r["player"].lower()].append((gd.get(r["game_id"]), float(r["pts"]), float(r["reb"]), float(r["ast"]), float(r["min"]), r.get("team", "")))
    except (ValueError, TypeError):
        pass
pick = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3], "pra": lambda x: x[1] + x[2] + x[3]}
pin = cx.pinnacle_lines(); inj = cx.injuries()

def pinn(name, st):
    p = pin.get(cx._pkey(name), {})
    if st == "pts": return p.get("pts")
    if st == "pr" and p.get("pts") and p.get("reb"): return p["pts"] + p["reb"]
    if st == "pa" and p.get("pts") and p.get("ast"): return p["pts"] + p["ast"]
    if st == "pra" and all(p.get(k) for k in ("pts", "reb", "ast")): return p["pts"] + p["reb"] + p["ast"]
    return None

print(f"GATE CHECK ({len(props)} board players, Pinnacle posted {len(pin)} players)\n")
npass = nrej = 0
for plow, mk in sorted(props.items()):
    name = plow.title()
    g = sorted([x for x in log.get(plow, []) if x[0]])
    if not g:
        continue
    cur = g[-1][5]; g2 = [x for x in g if x[5] == cur]
    for (st, sd), outs in mk.items():
        if sd != "Over" or st not in pick:
            continue
        line, odds = min(outs, key=lambda t: t[0])
        base = g2 if len(g2) >= 5 else g
        v = [pick[st](x) for x in base]
        if len(v) < 5:
            continue
        med = statistics.median(v[-10:]); t3 = statistics.mean(v[-3:])
        if line > med - 3:                                  # not a deep overshoot -> not even a candidate
            continue
        why = []
        if cx.status_of(name, inj) != "OK":
            why.append(f"INJURY={cx.status_of(name, inj)}")
        if len(g2) < 5:
            why.append(f"TEAM-CHANGE (only {len(g2)} current-team games)")
        else:
            mn = [x[4] for x in g2]
            r5, prev5 = mn[-5:], mn[-10:-5]                  # disjoint windows (matches cloud_xbet's fixed guard)
            if len(prev5) >= 3 and statistics.mean(r5) - statistics.mean(prev5) <= -3:
                why.append("MINUTES-SHRINK")
        if t3 <= med - 3:
            why.append(f"COLD (t3 {t3:.0f}≤med−3)")
        pv = pinn(name, st)
        if pv is not None and pv <= line + 1.5:
            why.append(f"STALE-MEDIAN (Pinn {pv:.0f}≈line)")
        if why:
            nrej += 1; print(f"  ❌ {name[:17]:18}{st.upper():4} o{line:<5} med{med:.0f}  → {', '.join(why)}")
        else:
            npass += 1; print(f"  ✅ {name[:17]:18}{st.upper():4} o{line:<5} med{med:.0f}  → PASS all gates")
print(f"\n  {npass} PASS · {nrej} REJECTED by a gate")
