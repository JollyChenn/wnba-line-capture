# xm_base.py - build the cross-model firing table. STEP 1: describe, do not conclude.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

print("board two-sided quotes:", len(B))

# ---- graded_bets: the settled ground truth the engine itself produced -------------------------
G = load("graded_bets.csv")
print("graded rows:", len(G))
print("graded cols:", list(G[0].keys()) if G else None)

# ---- bets_log: every capture. dedupe to one row per (src, player, market, game) --------------
L = load("bets_log.csv")
print("bets_log rows:", len(L))

nomap = collections.Counter()
FIRE = {}   # (src, pl, mk, gt) -> dict
for r in L:
    pl = (r.get("player") or "").lower()
    mk = r.get("market"); sd = r.get("side"); src = r.get("src") or ""
    ln = f(r.get("line")); od = f(r.get("odds")); cap = ts(r.get("captured_utc"))
    if not (pl and mk and sd and cap and ln is not None): continue
    tm = teamof.get(pl)
    if not tm: nomap["no_team"] += 1; continue
    gt = game_for(tm, cap)
    if not gt: nomap["no_game"] += 1; continue
    k = (src, pl, mk, gt)
    cur = FIRE.get(k)
    if cur is None or cap < cur["cap"]:
        FIRE[k] = dict(src=src, pl=pl, mk=mk, gt=gt, side=sd, line=ln, odds=od, cap=cap,
                       tier=r.get("tier"), ev=f(r.get("ev")), pinn=f(r.get("pinn")),
                       date=r.get("date"))
print("unmapped:", dict(nomap), " unique fires:", len(FIRE))

bysrc = collections.Counter(k[0] for k in FIRE)
print("\nunique fires per src:")
for s, n in bysrc.most_common(): print(f"  {s:<12} {n:>5}")

# how many have an outcome (box score present)?
have = collections.Counter()
for k, v in FIRE.items():
    row = pgrow.get((v["pl"], v["gt"]))
    have[(k[0], row is not None and row.get(v["mk"]) is not None)] += 1
print("\nfires with a settled box score:")
for s in bysrc:
    print(f"  {s:<12} settled {have[(s,True)]:>5}  missing {have[(s,False)]:>5}")

# two-sided board coverage at the fired line?
cov = collections.Counter()
for k, v in FIRE.items():
    sd = side.get((v["pl"], v["mk"], v["gt"]), {})
    ok = ("Over" in sd and "Under" in sd and sd["Over"][1] == sd["Under"][1])
    cov[(k[0], ok)] += 1
print("\nfires with a two-sided board quote (any line):")
for s in bysrc: print(f"  {s:<12} yes {cov[(s,True)]:>5}  no {cov[(s,False)]:>5}")
