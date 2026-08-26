# ALTERNATE-LINE ERROR AMPLIFICATION
# Step 2: is the ladder a parametric shift or individually shaped?
# Step 3: bettable version - sharp gap at main rung vs alternate rungs (feasibility first)
# Step 4: fair price per rung vs posted, from her own current-team distribution
import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)

rows = load("xbet_board.csv")
inst = collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t, o, ln = b.get("captured_utc"), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")), b.get("market"), t)][ln][b.get("side")] = o

def vf(oo, ou):
    po, pu = 1.0/oo, 1.0/ou
    return po/(po+pu)

# ---- attach each instant to its game + outcome, and to her PRIOR distribution ----
LAD = []   # one row per (player, market, game, instant) with >=1 two-sided rung
for (pl, mk, tstr), v in inst.items():
    rung = {ln: s for ln, s in v.items() if "Over" in s and "Under" in s}
    if not rung: continue
    tm = teamof.get(pl)
    if not tm: continue
    t = ts(tstr); g2 = game_for(tm, t)
    if not g2: continue
    now = pgrow.get((pl, g2))
    if not now or now["min"] < 8: continue
    prior = [x for x in hist.get(pl, []) if x["tip"] < g2 and x["tm"] == now["tm"]]
    if len(prior) < 5: continue
    vals = [x[mk] for x in prior[-15:]]
    LAD.append(dict(pl=pl, mk=mk, gt=g2, t=t, rung=rung, actual=now[mk],
                    hrs=(g2-t).total_seconds()/3600.0,
                    mu=statistics.mean(vals), sd=statistics.pstdev(vals) if len(vals)>1 else 0.0,
                    vals=vals, n_prior=len(vals)))
print(f"ladder rows (player-market-game-instant with >=1 two-sided rung): {len(LAD)}")
multi = [r for r in LAD if len(r["rung"]) >= 2]
print(f"  with >=2 SIMULTANEOUS two-sided rungs: {len(multi)}")
print(f"  distinct player-market-games with a simultaneous ladder: {len(set((r['pl'],r['mk'],r['gt']) for r in multi))}")
print(f"  distinct GAMES involved: {len(set(r['gt'] for r in multi))}")
print(f"  markets: {collections.Counter(r['mk'] for r in multi).most_common()}")

# =========================================================================
print("\n" + "="*78)
print("STEP 2  IS THE LADDER A PARAMETRIC SHIFT?")
print("="*78)
# observed ladder slope dP/dline, vs the slope her OWN distribution implies
obs, imp, sds = [], [], []
detail = []
for r in multi:
    ks = sorted(r["rung"])
    for i in range(len(ks)-1):
        a, b2 = ks[i], ks[i+1]
        d = b2-a
        if d <= 0: continue
        pa_ = vf(r["rung"][a]["Over"], r["rung"][a]["Under"])
        pb_ = vf(r["rung"][b2]["Over"], r["rung"][b2]["Under"])
        o_slope = (pa_-pb_)/d
        # her empirical slope: fraction of her last-15 in (a, b2]
        v = r["vals"]
        e_slope = sum(1 for x in v if a < x <= b2)/len(v)/d
        if r["sd"] <= 0: continue
        obs.append(o_slope); imp.append(e_slope); sds.append(r["sd"])
        detail.append((o_slope, e_slope, r["sd"], r["mk"], r["pl"], r["gt"]))
print(f"pairs of adjacent rungs, n={len(obs)}")
print(f"  BOOK ladder slope  dP/dpt : median {statistics.median(obs):+.4f}")
print(f"  HER empirical slope dP/dpt: median {statistics.median(imp):+.4f}")
rat = [o/e for o,e in zip(obs,imp) if e>0.0005]
print(f"  ratio book/empirical      : median {statistics.median(rat):.3f}  n={len(rat)}")

# does the book's slope scale with her volatility? (it MUST if she was modelled individually)
lo = [o for o,s in zip(obs,sds) if s < statistics.median(sds)]
hi = [o for o,s in zip(obs,sds) if s >= statistics.median(sds)]
print(f"\n  volatility split (median SD = {statistics.median(sds):.2f}):")
print(f"    LOW  vol players: book slope median {statistics.median(lo):+.4f}  n={len(lo)}")
print(f"    HIGH vol players: book slope median {statistics.median(hi):+.4f}  n={len(hi)}")
elo = [e for e,s in zip(imp,sds) if s < statistics.median(sds)]
ehi = [e for e,s in zip(imp,sds) if s >= statistics.median(sds)]
print(f"    (truth: LOW {statistics.median(elo):+.4f} vs HIGH {statistics.median(ehi):+.4f} -- truth MUST fall with vol)")
# rank correlation book slope vs sd
def spear(x, y):
    n=len(x)
    rx=[0]*n; ry=[0]*n
    for arr,rk in ((x,rx),(y,ry)):
        order=sorted(range(n), key=lambda i: arr[i])
        i=0
        while i<n:
            j=i
            while j+1<n and arr[order[j+1]]==arr[order[i]]: j+=1
            avg=(i+j)/2+1
            for k in range(i,j+1): rk[order[k]]=avg
            i=j+1
    mx=sum(rx)/n; my=sum(ry)/n
    num=sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    den=math.sqrt(sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))
    return num/den if den else 0.0
print(f"    Spearman(book slope, her SD)      = {spear(obs, sds):+.3f}")
print(f"    Spearman(empirical slope, her SD) = {spear(imp, sds):+.3f}")
