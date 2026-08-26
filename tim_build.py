import csv, os, sys, math, random, statistics, datetime, collections, re, json
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

MK = re.compile(r"^(.+?) makes (.+)$")
qp = collections.defaultdict(lambda: [0.0]*4)   # (gid, player) -> q1..q4 pts
appear = collections.defaultdict(set)           # (gid, player) -> set of periods seen
P = load("elo_model/plays_full.csv")
badname = collections.Counter()
for r in P:
    gid = r.get("game_id")
    if gid not in gmeta: continue
    try: per = int(r.get("period") or 0)
    except Exception: continue
    if per < 1: continue
    q = min(per, 4) - 1
    txt = r.get("text") or ""
    m = MK.match(txt)
    if not m: continue
    nm = m.group(1).strip().lower(); tail = m.group(2).lower()
    pts = 1 if "free throw" in tail else (3 if "three point" in tail else 2)
    qp[(gid, nm)][q] += pts

# validate against box
box_pts = {}
for r in load("data/box_2026.csv"):
    box_pts[(r.get("game_id"), (r.get("player") or "").lower())] = f(r.get("pts")) or 0
ok=0; bad=0; miss=0; diffs=[]
for k, v in qp.items():
    if k in box_pts:
        d = sum(v) - box_pts[k]
        diffs.append(d)
        if abs(d) < 0.5: ok += 1
        else: bad += 1
    else: miss += 1
print(f"parsed player-games {len(qp)}  match-box-exact {ok}  mismatch {bad}  name-not-in-box {miss}")
if diffs: print("  mean abs diff", round(statistics.mean(abs(x) for x in diffs),3), "median", statistics.median(diffs))
# which games covered
covg = set(g for (g,_) in qp)
print("games with parsed plays:", len(covg))
dates = sorted(gmeta[g][0] for g in covg)
print("date range", dates[0], dates[-1])
# sample player quarter profile
c = collections.Counter()
for (g,nm) in qp: c[nm]+=1
print("top players by parsed games:", c.most_common(5))
json.dump({f"{g}|{n}": v for (g,n),v in qp.items()}, open(os.path.join(D,"tim_qp.json"),"w"))
print("wrote tim_qp.json")
