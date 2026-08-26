# TEST C2 / D2 - does an anchor-deviation (or a momentum step) BEAT THE PRICE at settlement?
# Real two-sided quoted prices. Game-level permutation null. Execution realism.
import os,sys,math,random,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
OBS,anch=pickle.load(open(os.path.join(OUT,"obs.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
def f(x):
    try: return float(x)
    except (TypeError,ValueError): return None
def dec(a):
    v=f(a)
    if v is None: return None
    return 1+(100/(-v) if v<0 else v/100)
def px(pv,idx):
    s=(pv or "").split(",")
    return dec(s[idx]) if len(s)==2 else None

THR_T=[4,8,12]; THR_S=[3,6,9]; BANDS=[(0,45),(45,90),(0,150)]
DIRS=["fade","follow"]
NCELL=2*len(DIRS)*3*len(BANDS)
print("="*104)
print("GRID DECLARED BEFORE RESULTS: 2 markets x 2 directions (fade-to-anchor / follow-the-move)")
print("   x 3 deviation thresholds x 3 elapsed bands = %d cells."%NCELL)
print("   Bets priced at the SAME refresh the signal is read (law 5). Real two-sided quotes (law 4).")
print("   NULL: permute FINAL RESULTS across the 27 games (game-block; the label lives at game level).")
print("="*104)

def build(dirn,mkt,thr,lo,hi):
    bets=[]
    for r in OBS:
        if not (lo<=r["el"]<hi): continue
        if mkt=="tot":
            L=r.get("l_tot"); A=r.get("a_tot"); pvv=r.get("l_tot_px")
            if L is None or A is None or not pvv: continue
            d=L-A
            if abs(d)<thr: continue
            up = d>0
            side_over = (not up) if dirn=="fade" else up
            price=px(pvv,0 if side_over else 1)
            if price is None: continue
            bets.append(dict(gid=r["gid"],mkt="tot",L=L,over=side_over,price=price,el=r["el"],dev=d))
        else:
            L=r.get("l_sp"); A=r.get("a_sp"); pvv=r.get("l_sp_px")
            if L is None or A is None or not pvv: continue
            lm=-L; amg=-A; d=lm-amg
            if abs(d)<thr: continue
            up=d>0     # home outperforming pre-game expectation
            side_home = (not up) if dirn=="fade" else up
            price=px(pvv,0 if side_home else 1)
            if price is None: continue
            bets.append(dict(gid=r["gid"],mkt="sp",L=L,home=side_home,price=price,el=r["el"],dev=d))
    return bets

def grade(bets,res,pxadj=0.0,lineslip=0.0):
    # pxadj: implied prob added (worse price). lineslip: points moved against the bettor.
    pnl=0.0; n=0; w=0
    for b in bets:
        ft,fm=res[b["gid"]]
        p=b["price"]; ip=1.0/p+pxadj
        if ip>=0.999: continue
        p=1.0/ip
        if b["mkt"]=="tot":
            L=b["L"]+(lineslip if b["over"] else -lineslip)
            diff=ft-L
            win = diff>0 if b["over"] else diff<0
            if abs(diff)<1e-9: continue
        else:
            L=b["L"]-(lineslip if b["home"] else -lineslip)
            v=fm+L
            if abs(v)<1e-9: continue
            win = v>0 if b["home"] else v<0
        n+=1; w+=1 if win else 0
        pnl += (p-1) if win else -1
    return (pnl/n if n else 0.0), n, (w/n if n else 0.0)

RES={g:(games[g]["hs"]+games[g]["as_"],games[g]["hs"]-games[g]["as_"]) for g in set(o["gid"] for o in OBS)}
CELLS=[]
for mkt,THR in (("tot",THR_T),("sp",THR_S)):
    for dirn in DIRS:
        for thr in THR:
            for lo,hi in BANDS:
                CELLS.append((mkt,dirn,thr,lo,hi,build(dirn,mkt,thr,lo,hi)))
# ---- CEILING under game-permuted results ----
gids=sorted(RES); NP=1500; bn=[]
for _ in range(NP):
    sh=list(RES.values()); random.shuffle(sh)
    rp=dict(zip(gids,sh))
    m=0.0
    for mkt,dirn,thr,lo,hi,bets in CELLS:
        if len(bets)<8: continue
        roi,n,_=grade(bets,rp)
        if n>=8: m=max(m,abs(roi))
    bn.append(m)
bn.sort(); CEIL=bn[int(.95*NP)]
print("\nNOISE CEILING (%d game-block result permutations, family-wise over the grid):"%NP)
print("  best-cell |ROI| : p50 %+.1f%%   p95 CEILING %+.1f%%   max %+.1f%%"%(100*bn[NP//2],100*CEIL,100*bn[-1]))
print("  With only 27 games, ANY cell under %.1f%% ROI is indistinguishable from noise.\n"%(100*CEIL))
print("%-4s %-7s %4s %-8s %5s %5s %8s %8s %8s %8s %s"%("mkt","dir","thr","band","n","gms","hit%","ROI_q","ROI_mild","ROI_mod","verdict"))
out=[]
for mkt,dirn,thr,lo,hi,bets in CELLS:
    if len(bets)<8: continue
    roi,n,hit=grade(bets,RES)
    r1,_,_=grade(bets,RES,pxadj=0.015)
    r2,_,_=grade(bets,RES,pxadj=0.030,lineslip=0.5)
    ng=len(set(b["gid"] for b in bets))
    out.append((abs(roi),mkt,dirn,thr,lo,hi,n,ng,hit,roi,r1,r2))
out.sort(reverse=True)
for a,mkt,dirn,thr,lo,hi,n,ng,hit,roi,r1,r2 in out:
    print("%-4s %-7s %4d %-8s %5d %5d %7.1f%% %+7.1f%% %+7.1f%% %+7.1f%% %s"%(
        mkt,dirn,thr,"%d-%d"%(lo,hi),n,ng,100*hit,100*roi,100*r1,100*r2,
        "ABOVE CEILING" if a>CEIL else "under ceiling"))
print("\ncells above ceiling: %d / %d"%(sum(1 for o in out if o[0]>CEIL),len(out)))
