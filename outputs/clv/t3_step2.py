# TRACK 3 step 2: does sharp CLV predict realised ROI? quadrant map. game-block bootstrap.
import csv, os, sys, math, statistics, collections, random
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"
R = list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"), encoding="utf-8")))
def fnum(x):
    try: return float(x)
    except: return None

# ---- attach game block: (date, player's team) unknown here; use DATE as the slate block (conservative)
GM = list(csv.DictReader(open(os.path.join(D,"data","games_2026.csv"), encoding="utf-8")))
BOX = collections.defaultdict(dict)
for r in csv.DictReader(open(os.path.join(D,"data","box_2026.csv"), encoding="utf-8")):
    BOX[r["game_id"]][r["player"].lower()] = r.get("team","")
g_by_date = collections.defaultdict(list)
for g in GM: g_by_date[g["date"]].append(g)
pl_game = {}
for g in GM:
    for p in BOX.get(g["game_id"], {}):
        pl_game[(p, g["date"])] = g["game_id"]
for r in R:
    r["_gid"] = pl_game.get((r["player"].lower(), r["date"]), "d"+r["date"])

def block_boot(rows, valf, nb=4000):
    blocks = collections.defaultdict(list)
    for r in rows:
        v = valf(r)
        if v is not None: blocks[r["_gid"]].append(v)
    bl = list(blocks.values())
    if len(bl) < 3: return (float('nan'),)*3 + (0,0)
    allv=[x for b in bl for x in b]
    pt = statistics.mean(allv)
    ms=[]
    for _ in range(nb):
        s=[random.choice(bl) for _ in range(len(bl))]
        fl=[x for b in s for x in b]
        ms.append(sum(fl)/len(fl))
    ms.sort()
    return pt, ms[int(.025*nb)], ms[int(.975*nb)], len(allv), len(bl)

fams=collections.defaultdict(list)
for r in R: fams[r["src"]].append(r)
groups=[("ALL",R)]+sorted(fams.items(), key=lambda kv:-len(kv[1]))

print("=== QUADRANT: sharp odds-CLV (predicted EV by Pinnacle fair price) vs REALISED ROI ===")
print("   game-block bootstrap CI on both. sharp_odds_clv = our_decimal / pinn_vig_free_fair - 1")
print(f"{'family':12} {'games':>6} | {'sharpOddsCLV%':>14} {'CI':>18} {'n':>5} | {'ROI% (same rows)':>16} {'CI':>18} {'n':>5} | {'ROI% all rows':>13} {'n':>5}")
rowsout=[]
for name,rows in groups:
    sub=[r for r in rows if fnum(r["sharp_odds_clv"]) is not None and r["result"] in ("WIN","loss")]
    c=block_boot(sub, lambda r: fnum(r["sharp_odds_clv"]))
    p=block_boot(sub, lambda r: float(r["pnl"]))
    dec=[r for r in rows if r["result"] in ("WIN","loss")]
    a=block_boot(dec, lambda r: float(r["pnl"]))
    if c[3]==0:
        print(f"{name:12} {'-':>6} | {'n/a':>14} {'':>18} {0:5d} | {'':>16} {'':>18} {'':>5} | {a[0]*100:+13.1f} {a[3]:5d}")
        continue
    print(f"{name:12} {c[4]:6d} | {c[0]*100:+14.2f} [{c[1]*100:+7.2f},{c[2]*100:+7.2f}] {c[3]:5d} | {p[0]*100:+16.1f} [{p[1]*100:+7.1f},{p[2]*100:+7.1f}] {p[3]:5d} | {a[0]*100:+13.1f} {a[3]:5d}")
    rowsout.append((name,c[0]*100,p[0]*100,c[3]))

# correlation across families (weighted by n)
if len(rowsout)>=3:
    xs=[r[1] for r in rowsout]; ys=[r[2] for r in rowsout]
    mx=statistics.mean(xs); my=statistics.mean(ys)
    num=sum((a-mx)*(b-my) for a,b in zip(xs,ys)); den=math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
    print(f"\nacross-family corr(sharpOddsCLV, ROI) = {num/den if den else float('nan'):+.3f}  (k={len(rowsout)} families -- descriptive only)")

# BET-LEVEL: does sharp_odds_clv predict pnl?  binned
print("\n=== BET-LEVEL: sharp odds-CLV decile vs realised ROI (all rows with a sharp fair price) ===")
sub=[r for r in R if fnum(r["sharp_odds_clv"]) is not None and r["result"] in ("WIN","loss")]
sub.sort(key=lambda r: fnum(r["sharp_odds_clv"]))
k=5; sz=len(sub)//k
print(f"{'quintile':10} {'sharpCLV%':>10} {'ROI%':>8} {'CI':>18} {'n':>5} {'games':>6}")
for i in range(k):
    s=sub[i*sz:(i+1)*sz if i<k-1 else len(sub)]
    b=block_boot(s, lambda r: float(r["pnl"]))
    print(f"Q{i+1:<9} {statistics.mean([fnum(r['sharp_odds_clv']) for r in s])*100:+10.2f} {b[0]*100:+8.1f} [{b[1]*100:+7.1f},{b[2]*100:+7.1f}] {b[3]:5d} {b[4]:6d}")

# same for self odds_clv and line_clv (sign test)
for col in ("odds_clv","line_clv","sharp_clv"):
    sub=[r for r in R if fnum(r[col]) is not None and r["result"] in ("WIN","loss")]
    pos=[r for r in sub if fnum(r[col])>0]; neg=[r for r in sub if fnum(r[col])<0]; zer=[r for r in sub if fnum(r[col])==0]
    print(f"\n{col}: POS n={len(pos)} ROI={block_boot(pos,lambda r:float(r['pnl']))[0]*100:+.1f}% | ZERO n={len(zer)} ROI={block_boot(zer,lambda r:float(r['pnl']))[0]*100:+.1f}% | NEG n={len(neg)} ROI={block_boot(neg,lambda r:float(r['pnl']))[0]*100:+.1f}%")
