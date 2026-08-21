# b2b_check.py - the back-to-back cell from fresh_hunt, tested at the level the label lives at.
# ---------------------------------------------------------------------------------------------
# fresh_hunt: b2b OVERS -25.9% [CI -50.7,-7.9], b2b UNDERS +11.6% [CI -7.1,+37.4], n=172 quotes.
# Back-to-back is a TEAM-schedule label: every player on a tired team shares it. So the honest
# null relabels TEAM-GAMES (which team-nights count as b2b), holding outcomes where they are.
# Also: out-of-sample split by date, per-market breakdown, and the effect on the RAW stat -
# if fatigue is real, actual production on b2b nights should sit below her median, full stop.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260821)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")
gof, dateof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid; dateof[t2] = d2
_mc = {}
def med_team(pl, mk, gt):
    k = (pl, mk, gt)
    if k in _mc: return _mc[k]
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    out = None
    if g:
        cur = g[-1]["tm"]; g2 = [r for r in g if r["tm"] == cur]
        if len(g2) >= 5: out = statistics.median([r[mk] for r in g2[-10:]])
    _mc[k] = out
    return out
def restdays(pl, gt):
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    return (gt - g[-1]["tip"]).total_seconds()/86400 if g else None

Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    rd = restdays(pl, gt)
    if rd is None: continue
    md = med_team(pl, mk, gt)
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, date=dateof.get(gt, ""),
                  ln=ln, o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  b2b=(rd < 1.2), act=now[mk], med=md))
B2 = [r for r in Q if r["b2b"]]
tn = {(r["tm"], r["gt"]) for r in B2}
print(f"{len(Q)} quotes; {len(B2)} on back-to-backs across {len(tn)} team-nights,"
      f" {len({r['gid'] for r in B2})} games")
def roi(rows, sd): return 100*sum((r[sd+'_od']-1) if r[sd+'_won'] else -1.0 for r in rows)/len(rows) if rows else 0
print(f"  b2b OVERS {roi(B2,'o'):+.1f}%   b2b UNDERS {roi(B2,'u'):+.1f}%")
print("")
# team-night relabelling null
lab0 = {}
for r in Q: lab0.setdefault((r["tm"], r["gt"]), r["b2b"])
keys = list(lab0); vals = [lab0[k] for k in keys]
realo = roi(B2, "o")
beat = 0; T = 4000
for _ in range(T):
    random.shuffle(vals)
    lab = dict(zip(keys, vals))
    g = [r for r in Q if lab[(r["tm"], r["gt"])]]
    if len(g) < 100: continue
    if roi(g, "o") <= realo: beat += 1
print(f"  TEAM-NIGHT permutation on the OVER collapse: p = {beat/T:.4f}")
# out of sample
dts = sorted({r["date"] for r in B2}); cut = dts[len(dts)//2]
a = [r for r in B2 if r["date"] < cut]; b = [r for r in B2 if r["date"] >= cut]
print(f"  OOS: first half (n={len(a)}) overs {roi(a,'o'):+.1f}%  |  second half (n={len(b)}) overs {roi(b,'o'):+.1f}%")
# raw production check - does she actually produce less on b2b nights?
d_b2b = [r["act"] - r["med"] for r in B2 if r["med"] is not None]
d_rest = [r["act"] - r["med"] for r in Q if not r["b2b"] and r["med"] is not None]
print(f"  actual minus median: b2b {statistics.mean(d_b2b):+.2f} (n={len(d_b2b)})"
      f"  vs rested {statistics.mean(d_rest):+.2f} (n={len(d_rest)})")
print("")
for m in ALLMK:
    g = [r for r in B2 if r["mk"] == m]
    if len(g) < 15: continue
    print(f"    {m:<5} n={len(g):<4} overs {roi(g,'o'):+7.1f}%   unders {roi(g,'u'):+7.1f}%")
