# board_dump.py — pull the full 1xbet WNBA board and list EVERY over line vs our median,
# flagging deep overshoots (line >= 3 below median AND below our projection). Reuses cloud_xbet's
# pull so it's the exact same data the bot sees.
import os, cloud_xbet as cx

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

picks = cx.load_picks()
med = {(p.lower(), pk["base"]): (pk["anchor"], pk["proj"], pk.get("sd", 0)) for p, pks in picks.items() for pk in pks}
print(f"board players: {len(props)}\n{'player':20}{'mkt':5}{'OVER':>7}{'odds':>6}{'ourMed':>8}{'proj':>7}{'gap':>6}  hit%  flag")
hits = []
for plow, mk in sorted(props.items()):
    for (st, sd), outs in mk.items():
        if sd != "Over":
            continue
        line, odds = min(outs, key=lambda t: t[0])
        m = med.get((plow, st))
        if not m:
            print(f"{plow[:19]:20}{st:5}{line:>7}{odds:>6}{'  --':>8}{'':>7}{'':>6}   (no model line)")
            continue
        anc, proj, s = m
        gap = line - anc
        hit = (1 - cx._ncdf((line - proj) / s)) if s else 0
        flag = "🎯 OVERSHOOT-OVER" if (line <= anc - 3 and line < proj) else ("below med" if line < anc else "")
        print(f"{plow[:19]:20}{st:5}{line:>7}{odds:>6}{anc:>8.1f}{proj:>7.1f}{gap:>6.1f}  {hit*100:>3.0f}%  {flag}")
        if flag.startswith("🎯") and odds * hit > 1:
            hits.append((plow, st, line, odds, hit))
print("\nDEEP overshoot-overs that are +EV at the posted odds:")
for plow, st, line, odds, hit in hits:
    print(f"  🎯 {plow} {st.upper()} OVER {line} @ {odds}  (hit {hit*100:.0f}%, EV {(odds*hit-1)*100:+.0f}%)")
if not hits:
    print("  (none on the board right now)")
