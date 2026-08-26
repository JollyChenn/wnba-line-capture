import os,sys,pickle,math,random,statistics,collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
rng=np.random.default_rng(20260826); random.seed(20260826)
D=os.path.dirname(os.path.abspath(__file__))
S=pickle.load(open(os.path.join(D,"gm_sub3.pkl"),"rb")); sub=S["sub"]; CONST=S["CONST"]; teammean=S["teammean"]
def gamekey(r): return (r["gt"], r["tm"] if r["home"] else r["opp"], r["opp"] if r["home"] else r["tm"])

# apples-to-apples total check
both=[r for r in sub if r.get("tot") is not None and r["F"]["tot"] is not None]
from scipy.stats import rankdata
def sp(x,y):
    a,b=rankdata(x),rankdata(y); a=a-a.mean(); b=b-b.mean()
    d=np.sqrt((a*a).sum()*(b*b).sum()); return float((a*b).sum()/d) if d else 0.0
print("IDENTICAL %d rows: rho(mega_sweep tot)=%+.4f   rho(clean main-line tot)=%+.4f"%(
    len(both), sp([r["tot"] for r in both],[float(r["over_won"]) for r in both]),
    sp([r["F"]["tot"] for r in both],[float(r["over_won"]) for r in both])))

# ---------- declare the grid UP FRONT ----------
MK=("pra","pr","pts")
UNIV={"board_OVER":  (lambda r: True, "Over"),
      "board_UNDER": (lambda r: True, "Under"),
      "modelS_OVER": (lambda r: r["mk"] in MK and r.get("starred") is True, "Over")}
FEATS=["tot","spr_abs","spr_signed","mlp","tt_own","tt_opp","tt_diff","impshare","share_gap","lg_full","lg_delta"]
NBIN=3
MINN={"board_OVER":100,"board_UNDER":100,"modelS_OVER":60}
print(f"\nGRID DECLARED: {len(UNIV)} universes x {len(FEATS)} features x {NBIN} terciles = {len(UNIV)*len(FEATS)*NBIN} cells")

rows=[r for r in sub if r["F"]["tt_own"] is not None and r["hmshare"] is not None]
print("grid rows:",len(rows)," games:",len(set(gamekey(r) for r in rows)))
gk=collections.defaultdict(list)
for i,r in enumerate(rows): gk[gamekey(r)].append(i)
games=list(gk)
# per-game pinnacle vector, oriented per row (needs home flag) -> store raw home-oriented values
gvec={}
for g in games:
    r=rows[gk[g][0]]
    # rebuild home-oriented raw from row's own orientation
    own,opp=r["F"]["tt_own"],r["F"]["tt_opp"]; spr=r["F"]["spr_signed"]; mlp=r["F"]["mlp"]
    if r["home"]: gvec[g]=(r["F"]["tot"],spr,mlp,own,opp)
    else:         gvec[g]=(r["F"]["tot"],-spr,1-mlp,opp,own)

def build(assign):
    """assign: game -> (tot,spr_home,ml_home,tt_home,tt_away); returns per-row feature dict arrays"""
    F=[None]*len(rows)
    for g,idxs in gk.items():
        tot,sh,mh,tth,tta=assign[g]
        for i in idxs:
            r=rows[i]
            if r["home"]: spr,mlp,own,opp=sh,mh,tth,tta
            else:         spr,mlp,own,opp=-sh,1-mh,tta,tth
            hm=r["hmshare"]; ln=r["line"]; tmean=teammean[r["tm"]]
            F[i]=dict(tot=tot,spr_abs=abs(spr),spr_signed=spr,mlp=mlp,tt_own=own,tt_opp=opp,
                      tt_diff=own-opp,impshare=ln/own,share_gap=ln/own-hm,
                      lg_full=own*hm-ln,lg_delta=(own-tmean)*hm)
    return F

def cells(F):
    out={}
    for un,(filt,sd) in UNIV.items():
        idx=[i for i,r in enumerate(rows) if filt(r)]
        for fn in FEATS:
            vals=sorted(F[i][fn] for i in idx)
            n=len(vals)
            q1,q2=vals[n//3],vals[2*n//3]
            buckets=collections.defaultdict(list)
            for i in idx:
                v=F[i][fn]
                b=0 if v<=q1 else (1 if v<=q2 else 2)
                buckets[b].append(i)
            for b,ii in buckets.items():
                if len(ii)<MINN[un]: continue
                p=0
                for i in ii:
                    r=rows[i]
                    w=r["over_won"] if sd=="Over" else (not r["over_won"])
                    od=r["over_od"] if sd=="Over" else r["under_od"]
                    p+=(od-1) if w else -1
                out[(un,fn,b)]=(len(ii),p/len(ii)*100)
    return out

real=cells(build({g:gvec[g] for g in games}))
NP=500
best=[];worst=[]
for _ in range(NP):
    order=rng.permutation(len(games))
    assign={games[t]:gvec[games[s]] for t,s in enumerate(order)}
    c=cells(build(assign))
    v=[x[1] for x in c.values()]
    best.append(max(v)); worst.append(min(v))
best.sort(); worst.sort()
CEIL=best[int(0.95*NP)]; FLOOR=worst[int(0.05*NP)]
print("\n*** NOISE CEILING (game-relabel null, %d perms, %d cells) ***"%(NP,len(real)))
print("    p95 of BEST-cell ROI  = %+.2f%%     p5 of WORST-cell ROI = %+.2f%%"%(CEIL,FLOOR))
print("    median best-cell ROI  = %+.2f%%"%best[NP//2])
print("\n%-13s %-11s %-4s %6s %9s  %s"%("universe","feature","bin","n","ROI%","vs ceiling"))
for k in sorted(real,key=lambda k:-real[k][1]):
    n,r_=real[k]
    flag="BEATS CEILING" if r_>CEIL else ("below floor" if r_<FLOOR else "")
    print("%-13s %-11s %-4d %6d %+9.2f  %s"%(k[0],k[1],k[2],n,r_,flag))
pickle.dump(dict(rows=rows,gvec=gvec,gk=gk,games=games,CEIL=CEIL,FLOOR=FLOOR,real=real),
            open(os.path.join(D,"gm_grid.pkl"),"wb"))
