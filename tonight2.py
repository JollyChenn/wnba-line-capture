# tonight2.py - tonight's card with medians built the way the ENGINE builds them.
# ---------------------------------------------------------------------------------------------
# tonight_shade.py used a median over a player's last 10 games regardless of team. The engine does
# not: overshoot_overs filters to CURRENT-TEAM games first (cloud_xbet.py:434) precisely so an
# All-Star appearance or a mid-season trade cannot poison the number. Allisha Gray shows the gap -
# 24.0 unfiltered against 26.0 on ATL only, because of one All-Star game, which moves her cushion
# from +1.5 to +3.5 and flips which side of the "cushion 3+" line she sits on.
#
# That contamination is in every cushion number I produced today. Here the median is rebuilt the
# engine's way for tonight's two bets and for the opponent boards that feed the shade reading.
import csv, os, sys, statistics, collections, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

oppof = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm

def med_team(pl, mk, gt):
    """last 10 in this market, CURRENT-TEAM games only, strictly before gt - the engine's way"""
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    if not g: return None, 0
    cur = g[-1]["tm"]
    g = [r for r in g if r["tm"] == cur]
    if len(g) < 5: return None, len(g)
    return statistics.median([r[mk] for r in g[-10:]]), len(g)

rows = [r for r in csv.DictReader(open(os.path.join(D, "model_forward.csv"), encoding="utf-8"))
        if not (r.get("result") or "").strip()]
print("="*96)
print("  TONIGHT, medians rebuilt the engine's way")
print("="*96)
for r in rows:
    pl = r["player"].lower(); mk = r["market"]; line = float(r["line"])
    tm = teamof.get(pl)
    want = datetime.datetime.fromisoformat(r["tip"].replace("Z", "+00:00"))
    cands = [g for (t2, g) in oppof if t2 == tm and abs((g - want).total_seconds()) < 7200]
    if not cands:
        print(f"  {r['player']}: game not resolved"); continue
    gt = cands[0]; op = oppof[(tm, gt)]
    med, ng = med_team(pl, mk, gt)
    # opponent shade, also on team-filtered medians
    sh = []
    for (p2, m2, g2), sdq in side.items():
        if m2 != "pts" or g2 != gt or "Over" not in sdq: continue
        if teamof.get(p2) != op: continue
        m, _ = med_team(p2, "pts", gt)
        if m is not None: sh.append((p2, sdq["Over"][1], m, sdq["Over"][1] - m))
    cush = (med - line) if med is not None else None
    ov = statistics.mean(x[3] for x in sh) if len(sh) >= 3 else None
    cell = (cush is not None and cush >= 3 and ov is not None and ov <= 0)
    print(f"  {r['player']:<18} {mk.upper():<4} Over {line:<6} @{r['odds']:<6} {tm} v {op}  [{r['src']}]")
    print(f"      current-team median {med}  ({ng} games)   cushion {cush:+.1f}"
          + (f"   opponent shade {ov:+.2f} (n={len(sh)})" if ov is not None else "   opponent shade n/a"))
    if sh:
        print("      opponent board: " + ", ".join(
            f"{p.split()[-1]} {ln:g}v{m:g}({v:+.1f})" for p, ln, m, v in sorted(sh, key=lambda x: x[3])[:6]))
    print(f"      cushion 3+ AND opponent shaded down: {'YES' if cell else 'no'}")
    print("")
