# tonight_shade.py - read the opponent-shade and cushion for the bets currently on the card.
# ---------------------------------------------------------------------------------------------
# Shade is not a gate and is not going to become one on a p of 0.0186/0.0816. But it is the one
# live candidate, and the only way it ever gets proven is forward: record its reading on every
# card BEFORE the games, so in six weeks there is a real out-of-sample record instead of another
# retrospective slice. This prints the reading for tonight's pending bets and, for context, what
# it said about the bets that have already settled.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

tip_on, oppof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
def med_before(pl, mk, gt):
    v = [r[mk] for r in hist.get(pl, []) if r["tip"] < gt]
    return statistics.median(v[-10:]) if len(v) >= 4 else None

shade = collections.defaultdict(list)
for (pl, mk, gt), sdq in side.items():
    if mk != "pts" or "Over" not in sdq: continue
    tm = teamof.get(pl)
    if not tm: continue
    m = med_before(pl, "pts", gt)
    if m is not None: shade[(tm, gt)].append((pl, sdq["Over"][1], m, sdq["Over"][1] - m))

def read(name, mk, line, tipstr):
    pl = name.lower(); tm = teamof.get(pl)
    if not tm: return None
    gt = None
    for (t2, g2), o in oppof.items():
        pass
    try: want = datetime.datetime.fromisoformat(tipstr.replace("Z", "+00:00"))
    except Exception: want = None
    cands = [g for (t2, g) in oppof if t2 == tm]
    if want is not None:
        cands = [g for g in cands if abs((g - want).total_seconds()) < 7200]
    if not cands: return None
    gt = min(cands, key=lambda g: abs((g - want).total_seconds()) if want else 0)
    op = oppof.get((tm, gt))
    o_s = shade.get((op, gt), []); w_s = [x for x in shade.get((tm, gt), []) if x[0] != pl]
    med = med_before(pl, mk, gt)
    return dict(tm=tm, opp=op, gt=gt, med=med,
                cush=(med - line) if med is not None else None,
                oppn=len(o_s), oppv=(statistics.mean(x[3] for x in o_s) if len(o_s) >= 3 else None),
                ownv=(statistics.mean(x[3] for x in w_s) if len(w_s) >= 3 else None),
                detail=sorted(o_s, key=lambda x: x[3]))

rows = list(csv.DictReader(open(os.path.join(D, "model_forward.csv"), encoding="utf-8")))
pend = [r for r in rows if not (r.get("result") or "").strip()]
done = [r for r in rows if (r.get("result") or "").upper() in ("WIN", "LOSS")]

print("="*100)
print("  TONIGHT - pending on the card")
print("="*100)
for r in pend:
    d = read(r["player"], r["market"], float(r["line"]), r.get("tip", ""))
    if not d:
        print(f"  {r['player']:<20} {r['market'].upper()} {r['line']}  - could not resolve her game"); continue
    cs = f"{d['cush']:+.1f}" if d["cush"] is not None else "  ?"
    ov = f"{d['oppv']:+.2f}" if d["oppv"] is not None else "  ?"
    wv = f"{d['ownv']:+.2f}" if d["ownv"] is not None else "  ?"
    flag = ""
    if d["cush"] is not None and d["oppv"] is not None:
        flag = "  <<< cushion 3+ AND opponent shaded down" if (d["cush"] >= 3 and d["oppv"] <= 0) else ""
    print(f"  {r['player']:<20} {r['market'].upper():<4} {r['line']:<6} @{r['odds']:<6} {d['tm']} v {d['opp']}")
    print(f"      her median {d['med']}   cushion {cs}   opponent shade {ov} (n={d['oppn']})"
          f"   own-team shade {wv}{flag}")
    if d["detail"]:
        print("      opponent board: " + ", ".join(
            f"{p.split()[-1]} {ln:g}v{m:g}({v:+.1f})" for p, ln, m, v in d["detail"][:6]))
    print("")

print("="*100)
print("  WHAT SHADE SAID ABOUT THE SETTLED CARD BETS")
print("="*100)
ok = 0; tot = 0
for r in done:
    d = read(r["player"], r["market"], float(r["line"]), r.get("tip", ""))
    if not d or d["oppv"] is None or d["cush"] is None: continue
    tot += 1
    hit = (r["result"].upper() == "WIN")
    q = "DOWN" if d["oppv"] <= 0 else "up  "
    deep = "yes" if d["cush"] >= 3 else "no "
    print(f"  {r['player']:<20} {r['market'].upper():<4} {r['line']:<6} cushion {d['cush']:+5.1f} ({deep})"
          f"  opp {d['oppv']:+.2f} ({q})   -> {'WIN ' if hit else 'loss'}")
print("")
