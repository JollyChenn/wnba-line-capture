import os,sys,pickle,math,random,statistics,collections,datetime,csv
import numpy as np
from scipy.stats import rankdata
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
rng=np.random.default_rng(20260826)
D=os.path.dirname(os.path.abspath(__file__))
G=pickle.load(open(os.path.join(D,"gm_grid.pkl"),"rb"))
S3=pickle.load(open(os.path.join(D,"gm_sub3.pkl"),"rb"))
rows=G["rows"]; gvec=G["gvec"]; gk=G["gk"]; games=G["games"]; CONST=S3["CONST"]; teammean=S3["teammean"]
MK=("pra","pr","pts")
def gamekey(r): return (r["gt"], r["tm"] if r["home"] else r["opp"], r["opp"] if r["home"] else r["tm"])
def sp(x,y):
    a,b=rankdata(x),rankdata(y); a=a-a.mean(); b=b-b.mean()
    d=np.sqrt((a*a).sum()*(b*b).sum()); return float((a*b).sum()/d) if d else 0.0
def roi(rr,sd="Over"):
    if not rr: return (0,0.0,0.0,(0.0,0.0))
    pnl=[]
    for r in rr:
        w=r["over_won"] if sd=="Over" else (not r["over_won"])
        od=r["over_od"] if sd=="Over" else r["under_od"]
        pnl.append((od-1) if w else -1.0)
    m=statistics.mean(pnl); s=statistics.pstdev(pnl)/math.sqrt(len(pnl))
    hit=sum(1 for r in rr if (r["over_won"] if sd=="Over" else not r["over_won"]))/len(rr)
    return (len(rr),m*100,hit*100,((m-1.96*s)*100,(m+1.96*s)*100))

ms=[r for r in rows if r["mk"] in MK and r.get("starred") is True]
print("=== Q1  TEAM_TOTAL, the untested market ===")
print("Pinnacle team_total coverage: %d board quotes / %d games, %s..%s"%(
    len(rows),len(games),min(r["date"] for r in rows),max(r["date"] for r in rows)))
for nm,rr,sd in [("ALL board OVER",rows,"Over"),("Model-S-shaped OVER",ms,"Over")]:
    q=sorted(r["F"]["tt_own"] for r in rr); a,b=q[len(q)//3],q[2*len(q)//3]
    print("  %s  (her team's posted team_total)"%nm)
    for lab,sel in [("LOW  tt_own",lambda r:r["F"]["tt_own"]<=a),("MID",lambda r:a<r["F"]["tt_own"]<=b),("HIGH tt_own",lambda r:r["F"]["tt_own"]>b)]:
        n,R,h,ci=roi([r for r in rr if sel(r)],sd)
        print("     %-12s n=%4d  hit=%.1f%%  ROI=%+6.2f%%  CI[%+.1f,%+.1f]"%(lab,n,h,R,ci[0],ci[1]))

print()
print("  implied share = her line / her team's team_total ; historical share = median(her stat / team pts)")
for nm,rr in [("ALL board OVER",rows),("Model-S-shaped OVER",ms)]:
    q=sorted(r["F"]["share_gap"] for r in rr); a,b=q[len(q)//3],q[2*len(q)//3]
    print("  %s"%nm)
    for lab,sel in [("share_gap LOW (book asks less of her than usual)",lambda r:r["F"]["share_gap"]<=a),
                    ("share_gap MID",lambda r:a<r["F"]["share_gap"]<=b),
                    ("share_gap HIGH (book asks MORE of her than usual)",lambda r:r["F"]["share_gap"]>b)]:
        n,R,h,ci=roi([r for r in rr if sel(r)],"Over")
        print("     %-50s n=%4d hit=%.1f%% ROI=%+6.2f%% CI[%+.1f,%+.1f]"%(lab,n,h,R,ci[0],ci[1]))

print()
print("=== per-universe noise ceilings (game-relabel null, 500 perms) ===")
UNIV={"board_OVER":(lambda r:True,"Over"),"board_UNDER":(lambda r:True,"Under"),
      "modelS_OVER":(lambda r: r["mk"] in MK and r.get("starred") is True,"Over")}
FEATS=["tot","spr_abs","spr_signed","mlp","tt_own","tt_opp","tt_diff","impshare","share_gap","lg_full","lg_delta"]
MINN={"board_OVER":100,"board_UNDER":100,"modelS_OVER":60}
def build(assign):
    F=[None]*len(rows)
    for g,idxs in gk.items():
        tot,sh,mh,tth,tta=assign[g]
        for i in idxs:
            r=rows[i]
            if r["home"]: spr,mlp,own,opp=sh,mh,tth,tta
            else: spr,mlp,own,opp=-sh,1-mh,tta,tth
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
            vals=sorted(F[i][fn] for i in idx); n=len(vals); q1,q2=vals[n//3],vals[2*n//3]
            bk=collections.defaultdict(list)
            for i in idx:
                v=F[i][fn]; bk[0 if v<=q1 else (1 if v<=q2 else 2)].append(i)
            for b,ii in bk.items():
                if len(ii)<MINN[un]: continue
                p=0
                for i in ii:
                    r=rows[i]; w=r["over_won"] if sd=="Over" else (not r["over_won"])
                    od=r["over_od"] if sd=="Over" else r["under_od"]
                    p+=(od-1) if w else -1
                out[(un,fn,b)]=(len(ii),p/len(ii)*100)
    return out
best={u:[] for u in UNIV}
for _ in range(500):
    o=rng.permutation(len(games))
    c=cells(build({games[t]:gvec[games[s]] for t,s in enumerate(o)}))
    for u in UNIV:
        v=[x[1] for k,x in c.items() if k[0]==u]
        if v: best[u].append(max(v))
real=cells(build({g:gvec[g] for g in games}))
for u in UNIV:
    bb=sorted(best[u]); ce=bb[int(0.95*len(bb))]
    bestreal=max((x[1],k) for k,x in real.items() if k[0]==u)
    print("  %-12s cells=%2d  p95 best-cell ROI under null = %+6.2f%%   BEST REAL = %+6.2f%% (%s)  -> %s"%(
        u,sum(1 for k in real if k[0]==u),ce,bestreal[0],bestreal[1][1]+" bin"+str(bestreal[1][2]),
        "BEATS" if bestreal[0]>ce else "under ceiling"))

print()
print("=== Q5  redundancy vs the game TOTAL: stratify the best candidate inside total terciles ===")
q=sorted(r["F"]["tot"] for r in rows); a,b=q[len(q)//3],q[2*len(q)//3]
for lab,sel in [("LOW total",lambda r:r["F"]["tot"]<=a),("MID total",lambda r:a<r["F"]["tot"]<=b),("HIGH total",lambda r:r["F"]["tot"]>b)]:
    rr=[r for r in ms if sel(r)]
    if len(rr)<40: continue
    qq=sorted(x["F"]["line_gap"] for x in rr); a2,b2=qq[len(qq)//3],qq[2*len(qq)//3]
    hi=[x for x in rr if x["F"]["line_gap"]>b2]
    n,R,h,ci=roi(hi,"Over")
    n0,R0,h0,ci0=roi(rr,"Over")
    print("  %-10s  all n=%4d ROI=%+6.2f%%   | top-tercile lg_full n=%3d ROI=%+6.2f%% CI[%+.1f,%+.1f]"%(lab,n0,R0,n,R,ci[0],ci[1]))

print()
print("=== characterising the ONE surviving correlation (a player-level, NOT game-market, effect) ===")
# control: does the share estimator beat a plain long-window median? (window vs share)
import pickle as pk
allrows=S3["rows"]
teampts={}
for g in csv.DictReader(open(os.path.join(D,"data/games_2026.csv"),encoding="utf-8")):
    try:
        t=datetime.datetime.fromisoformat(g["tip"].replace("Z","+00:00"))
    except Exception: continue
    if g["home_score"] and g["away_score"]:
        teampts[(g["home"],t)]=float(g["home_score"]); teampts[(g["away"],t)]=float(g["away_score"])
print("  (see gm_decomp.py output: lg_const = hshare*88.18 - line beats medgap; lg_delta = tonight's team_total contribution = rho +0.004 p=0.81)")
n,R,h,ci=roi(ms,"Over"); print("  Model-S-shaped baseline: n=%d hit=%.1f%% ROI=%+.2f%% CI[%+.1f,%+.1f]"%(n,h,R,ci[0],ci[1]))

print()
print("=== real live Model S bets that also have a Pinnacle team_total ===")
gb=list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"),encoding="utf-8",errors="replace")))
sel=[b for b in gb if b.get("src") in ("flip","hotover","overshoot") and b.get("market") in MK
     and b.get("side")=="Over" and b.get("date","")>="20260711"]
print("  graded Model-S-src OVER bets since Pinnacle coverage began: n=%d"%len(sel))
if sel:
    p=sum(float(b["pnl"]) for b in sel if b.get("pnl"))
    print("  pnl=%+.2fu  ROI=%+.2f%%  -> far too few to stratify by any game market"%(p,100*p/len(sel)))
