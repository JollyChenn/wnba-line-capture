import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
exec(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G=load("data/games_2026.csv"); wins=[]; gmap={}
for r in G:
    t=ts(r["tip"])
    if t: wins.append((r["game_id"],t,t+datetime.timedelta(minutes=150),r["home"],r["away"])); gmap[r["game_id"]]=(r["date"],r["home"],r["away"])
def abbrs(s): return [FULL.get(n.strip(),n.strip()) for n in (s or "").split("|")]
main=[]
for r in load("live_lines.csv"):
    if r["alt"]!="0": continue
    t=ts(r["ts"])
    if not t: continue
    ab=abbrs(r["teams"])
    if len(ab)!=2: continue
    for gid,a,b,h,aw in wins:
        if a<=t<=b and set(ab)=={h,aw}: r["_gid"]=gid; r["_t"]=t; main.append(r); break
S=collections.defaultdict(list)
for r in sorted(main,key=lambda x:x["_t"]): S[(r["_gid"],r["type"],r["side"] or "")].append(r)
KEPT={k:v for k,v in S.items() if len(v)>=25}
def vf(r):
    a,b=(r["prices"] or ",").split(",")[:2]; pa,pb=am(a),am(b)
    return pa/(pa+pb) if (pa is not None and pb is not None and pa+pb) else None
def hyb(r): return f(r["points"]) if r["type"]!="moneyline" else vf(r)

# ---- A. universality: is r1 high in EVERY series, or driven by a few? ----
print("=== A. per-series lag-1 autocorr, all 100 kept series (hybrid value) ===")
r1s=[]
for k,v in KEPT.items():
    xs=[hyb(r) for r in v]; xs=[x for x in xs if x is not None]
    if len(xs)<25: continue
    m=statistics.fmean(xs); d=[x-m for x in xs]; den=sum(x*x for x in d)
    if den<=0: 
        r1s.append((k,None)); continue
    r1s.append((k, sum(d[i]*d[i+1] for i in range(len(d)-1))/den))
ok=[x for _,x in r1s if x is not None]
print(f"  series={len(r1s)} computable={len(ok)} degenerate(flat)={len(r1s)-len(ok)}")
print(f"  min={min(ok):+.3f} p05={sorted(ok)[max(0,int(.05*len(ok)))]:+.3f} med={statistics.median(ok):+.3f} max={max(ok):+.3f}")
print(f"  share r1>0.5: {sum(1 for x in ok if x>0.5)}/{len(ok)}   share r1>0.7: {sum(1 for x in ok if x>0.7)}/{len(ok)}")
print(f"  iid null expectation r1 ~= -1/T ~= {-1/statistics.fmean([len(v) for v in KEPT.values()]):+.3f}")

# ---- B. within-game-centred statistic: does n_eff still collapse to ~#games? ----
print("\n=== B. design effect for a WITHIN-GAME-CENTRED statistic (game fixed effect removed) ===")
print("   (tests whether n_eff~#games is a property of the data or of choosing a level variable)")
Bn=2000
for mk in ["total","spread","team_total","moneyline"]:
    bg=collections.defaultdict(list)
    for k,v in KEPT.items():
        if k[1]!=mk: continue
        xs=[(r,hyb(r)) for r in v]; xs=[(r,x) for r,x in xs if x is not None]
        if len(xs)<25: continue
        mu=statistics.fmean([x for _,x in xs])
        for r,x in xs: bg[k[0]].append(x-mu)          # series-demeaned
    games=sorted(bg); allx=[x for g in games for x in bg[g]]
    n=len(allx); sd=statistics.pstdev(allx); vi=sd*sd/n
    ms=[]
    for _ in range(Bn):
        s=[random.choice(games) for _ in games]
        ms.append(statistics.fmean([x for g in s for x in bg[g]]))
    de=statistics.pvariance(ms)/vi
    print(f"  {mk:11s} obs={n:5d} deff={de:6.1f}x n_eff={n/de:7.1f}   (claim for level stat: 45-60x, n_eff 20-38)")

# ---- C. NOVELTY: overlap with the 4 alive prop-level effects ----
print("\n=== C. overlap between the 27 in-play-odds games and the prop-board universe ===")
ipg=set(r["_gid"] for r in main)
ipkeys=set()
for g in ipg:
    d,h,a=gmap[g]; ipkeys.add((d,h,a))
print("  in-play games:", len(ipg), " dates:", sorted(set(gmap[g][0] for g in ipg)))
BD=load("xbet_board.csv")
print("  xbet_board rows:", len(BD), "cols:", (list(BD[0].keys()) if BD else None))
GB=load("graded_bets.csv")
print("  graded_bets rows:", len(GB), "cols:", (list(GB[0].keys())[:14] if GB else None))
