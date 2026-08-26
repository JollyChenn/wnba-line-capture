# CROSS-MARKET MOVEMENT GRID + GLOBAL NOISE CEILING  (fast integer-coded version)
#   horizon: every bet is SELECTED and PRICED at the last two-sided 1xbet quote at or before
#   tip - 6h.  "early" observation for every movement feature is the last quote at or before
#   tip - 12h.  Nothing after tip-6h is ever used.
import os
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_table.py"),encoding="utf-8").read())
import statistics, collections, math, random
random.seed(20260826)
MINN=60; K=1000

# ---------- features ----------
for r in T: r["same_up"]=0; r["same_dn"]=0
by_date=collections.defaultdict(list)
for r in T:
    if r["dline1"] is not None: by_date[r["date"]].append(r)
for d,rows in by_date.items():
    ups=[x for x in rows if x["dline1"]>=1.0]; dns=[x for x in rows if x["dline1"]<=-1.0]
    for r in rows:
        r["same_up"]=sum(1 for x in ups if x["pl"]!=r["pl"])
        r["same_dn"]=sum(1 for x in dns if x["pl"]!=r["pl"])
ptsmove={}
for r in T:
    if r["mk"]=="pts" and r["dline1"] is not None: ptsmove[(r["pl"],r["gid"])]=r["dline1"]
for r in T: r["pts_dline"]=ptsmove.get((r["pl"],r["gid"]))
PTSFAM=("pra","pr","pa"); NONSC=("reb","ast","ra")

# ---------- integer coding ----------
def code_tot(dtot):        # 0 up 1 dn 2 flat 3 missing
    if dtot is None: return 3
    return 0 if dtot>=1.0 else (1 if dtot<=-1.0 else 2)
def code_spr(d):
    if d is None: return 3
    return 0 if d>=1.0 else (1 if d<=-1.0 else 2)
def code_mv(dl):           # 0 up 1 dn 2 nomove 3 missing/other
    if dl is None: return 3
    return 0 if dl>=1.0 else (1 if dl<=-1.0 else (2 if dl==0.0 else 3))
def code_drift(do):
    if do is None: return 3
    return 0 if do<=-0.05 else (1 if do>=0.05 else 2)

CELLS=[]; NAME=[]
def add(fam,name): CELLS.append((fam,name)); NAME.append(name); return len(CELLS)-1
IX={}
for tn in ("totUP","totDN","totFLAT"):
    for pn in ("herline_unmoved","any"):
        for sd in ("Over","Under"): IX[("A",tn,pn,sd)]=add("A","A:%s&%s:%s"%(tn,pn,sd))
for sn in ("sprWIDEN","sprNARROW","sprFLAT"):
    for rn in ("fav","dog"):
        for sd in ("Over","Under"): IX[("B",sn,rn,sd)]=add("B","B:%s&%s:%s"%(sn,rn,sd))
for dn_ in ("ptsUP","ptsDN"):
    for gn in ("tgt_ptsfam","tgt_nonsc","tgt_all"):
        for sd in ("Over","Under"): IX[("C",dn_,gn,sd)]=add("C","C:%s&%s:%s"%(dn_,gn,sd))
for dn_ in ("upPACK","upALONE","dnPACK","dnALONE","nomove"):
    for sd in ("Over","Under"): IX[("D",dn_,sd)]=add("D","D:%s:%s"%(dn_,sd))
for en in ("short","long","flat"):
    for in_ in ("x_any","x_totUP","x_totDN"):
        for sd in ("Over","Under"): IX[("E",en,in_,sd)]=add("E","E:%s&%s:%s"%(en,in_,sd))
NC=len(CELLS)
print("GRID DECLARED: %d cells | min n = %d | K = %d permutations"%(NC,MINN,K))
print("universe T = %d two-sided board quotes, selected AND priced at the last quote <= tip-6h"%len(T))
print("")

TOTN=("totUP","totDN","totFLAT"); SPRN=("sprWIDEN","sprNARROW","sprFLAT"); DRN=("short","long","flat")
A_IDX=[[ [IX[("A",TOTN[t],p,s)] for s in ("Over","Under")] for p in ("herline_unmoved","any")] for t in range(3)]
B_IDX=[[ [IX[("B",SPRN[t],p,s)] for s in ("Over","Under")] for p in ("fav","dog")] for t in range(3)]
C_IDX=[[ [IX[("C",("ptsUP","ptsDN")[t],g,s)] for s in ("Over","Under")] for g in ("tgt_ptsfam","tgt_nonsc","tgt_all")] for t in range(2)]
D_IDX={n:[IX[("D",n,s)] for s in ("Over","Under")] for n in ("upPACK","upALONE","dnPACK","dnALONE","nomove")}
E_IDX=[[ [IX[("E",DRN[t],i,s)] for s in ("Over","Under")] for i in ("x_any","x_totUP","x_totDN")] for t in range(3)]

# static per-row payload
ROWS=[]
for r in T:
    tg = 0 if r["mk"] in PTSFAM else (1 if r["mk"] in NONSC else 2)   # 2 = pts itself
    fav = None if r["hspr6"] is None else (0 if r["hspr6"]<0 else 1)
    ROWS.append(dict(gid=r["gid"], pg=(r["pl"],r["gid"]), mk=r["mk"], tg=tg, fav=fav,
                     po=pnl(r,"Over"), pu=pnl(r,"Under"),
                     has_spr=(r["dabsspr"] is not None and r["hspr6"] is not None)))
# permutable labels
GLAB={}          # gid -> (code_tot, code_spr)
for r in T: GLAB.setdefault(r["gid"], (code_tot(r["dtot"]), code_spr(r["dabsspr"])))
PLAB=collections.defaultdict(dict)   # pg -> mk -> (code_mv, same_up, same_dn, code_drift, pts_dline_code)
for r in T:
    PLAB[(r["pl"],r["gid"])][r["mk"]]=(code_mv(r["dline1"]), r["same_up"], r["same_dn"],
                                        code_drift(r["dood1"]), code_mv(r["pts_dline"]))
GIDS=sorted(GLAB); PGS=sorted(PLAB)
PGFIRST={pg:next(iter(v.values())) for pg,v in PLAB.items()}

def tally(gmap,pmap):
    n=[0]*NC; s=[0.0]*NC
    for R in ROWS:
        gt,gs = GLAB[gmap[R["gid"]]]
        dpg=pmap[R["pg"]]; lv=PLAB[dpg]
        mv,su,sd_,dr,pm = lv.get(R["mk"], PGFIRST[dpg])
        po,pu=R["po"],R["pu"]
        # A : game total x her line unmoved
        if gt<3 and mv<3:
            for p in ((0,1) if mv==2 else (1,)):
                a=A_IDX[gt][p]
                n[a[0]]+=1; s[a[0]]+=po; n[a[1]]+=1; s[a[1]]+=pu
        # B : spread widen/narrow x fav/dog
        if gs<3 and R["fav"] is not None and R["has_spr"]:
            b=B_IDX[gs][R["fav"]]
            n[b[0]]+=1; s[b[0]]+=po; n[b[1]]+=1; s[b[1]]+=pu
        # C : her pts line move -> other markets
        if pm<2 and R["tg"]!=2:
            for g in ((R["tg"],2)):
                c=C_IDX[pm][g]
                n[c[0]]+=1; s[c[0]]+=po; n[c[1]]+=1; s[c[1]]+=pu
        # D : steam
        if mv<3:
            key=None
            if mv==0: key="upPACK" if su>=3 else ("upALONE" if su<=1 else None)
            elif mv==1: key="dnPACK" if sd_>=3 else ("dnALONE" if sd_<=1 else None)
            else: key="nomove"
            if key:
                d=D_IDX[key]; n[d[0]]+=1; s[d[0]]+=po; n[d[1]]+=1; s[d[1]]+=pu
        # E : drift x total move
        if dr<3:
            ii=[0]
            if gt==0: ii.append(1)
            elif gt==1: ii.append(2)
            for i in ii:
                e=E_IDX[dr][i]
                n[e[0]]+=1; s[e[0]]+=po; n[e[1]]+=1; s[e[1]]+=pu
    return n,s
IDG=dict((g,g) for g in GIDS); IDP=dict((p,p) for p in PGS)

# ---------- NOISE CEILING FIRST ----------
maxs=[]
for k in range(K):
    dg=GIDS[:]; random.shuffle(dg); gmap=dict(zip(GIDS,dg))
    dp=PGS[:];  random.shuffle(dp); pmap=dict(zip(PGS,dp))
    n,s=tally(gmap,pmap)
    best=max((100*s[i]/n[i]) for i in range(NC) if n[i]>=MINN)
    maxs.append(best)
maxs.sort()
CEIL=maxs[int(0.95*len(maxs))]
print("="*84)
print("NOISE CEILING - p95 of the BEST-CELL ROI over the whole %d-cell grid under the null."%NC)
print("  Null: game-level labels (total move, spread move) relabelled by shuffling GAMES;")
print("        player-game-level labels (her line move, her price drift, her pts-line move,")
print("        slate steam counts) relabelled by shuffling PLAYER-GAMES. Prices/outcomes fixed.")
print("  p50 %+.2f%%   p90 %+.2f%%   p95 %+.2f%%   p99 %+.2f%%   max %+.2f%%"%(
      maxs[len(maxs)//2],maxs[int(.90*len(maxs))],CEIL,maxs[int(.99*len(maxs))],maxs[-1]))
print("  >>> ANY CELL AT OR BELOW %+.2f%% IS NOT A FINDING. <<<"%CEIL)
print("="*84); print("")

# ---------- real ----------
n0,s0=tally(IDG,IDP)
def blocks_for(fam,idx):
    """rebuild the row->cell membership once, for CI bootstrap."""
    out=collections.defaultdict(list)
    for R,rr in zip(ROWS,T):
        pass
    return out
print("%-32s%7s%9s   %-20s %s"%("cell","n","ROI%","95% CI block-boot","vs ceiling"))
# membership map for the real assignment (for bootstrap)
memb=collections.defaultdict(list)
def tally_record():
    for R in ROWS:
        gt,gs=GLAB[R["gid"]]; lv=PLAB[R["pg"]]
        mv,su,sd_,dr,pm=lv.get(R["mk"],PGFIRST[R["pg"]])
        po,pu=R["po"],R["pu"]
        if gt<3 and mv<3:
            for p in ((0,1) if mv==2 else (1,)):
                a=A_IDX[gt][p]; memb[a[0]].append((R["gid"],po)); memb[a[1]].append((R["gid"],pu))
        if gs<3 and R["fav"] is not None and R["has_spr"]:
            b=B_IDX[gs][R["fav"]]; memb[b[0]].append((R["gid"],po)); memb[b[1]].append((R["gid"],pu))
        if pm<2 and R["tg"]!=2:
            for g in ((R["tg"],2)):
                c=C_IDX[pm][g]; memb[c[0]].append((R["pg"],po)); memb[c[1]].append((R["pg"],pu))
        if mv<3:
            key=None
            if mv==0: key="upPACK" if su>=3 else ("upALONE" if su<=1 else None)
            elif mv==1: key="dnPACK" if sd_>=3 else ("dnALONE" if sd_<=1 else None)
            else: key="nomove"
            if key:
                d=D_IDX[key]; memb[d[0]].append((R["pg"],po)); memb[d[1]].append((R["pg"],pu))
        if dr<3:
            ii=[0]
            if gt==0: ii.append(1)
            elif gt==1: ii.append(2)
            for i in ii:
                e=E_IDX[dr][i]; memb[e[0]].append((R["gid"],po)); memb[e[1]].append((R["gid"],pu))
tally_record()
def ci(i):
    grp=collections.defaultdict(list)
    for k_,v in memb[i]: grp[k_].append(v)
    bl=list(grp.values())
    res=[]
    for _ in range(1200):
        acc=[];
        for _ in range(len(bl)): acc.extend(random.choice(bl))
        res.append(100*sum(acc)/len(acc))
    res.sort(); return res[30],res[-31]
RES=[]
for fam in ("A","B","C","D","E"):
    print("--- family %s ---"%fam)
    ent=[(i,n0[i],100*s0[i]/n0[i]) for i in range(NC) if CELLS[i][0]==fam and n0[i]>=MINN]
    ent.sort(key=lambda x:-x[2])
    for i,n_,roi in ent:
        lo,hi=ci(i)
        flag="*** BEATS CEILING ***" if roi>CEIL else ""
        print("%-32s%7d%9.2f   [%+6.2f,%+6.2f]      %s"%(NAME[i],n_,roi,lo,hi,flag))
        RES.append((roi,NAME[i],n_,lo,hi,i))
    drop=[NAME[i] for i in range(NC) if CELLS[i][0]==fam and n0[i]<MINN]
    if drop: print("   (dropped, n<%d: %s)"%(MINN,", ".join("%s n=%d"%(NAME[i],n0[i]) for i in range(NC) if CELLS[i][0]==fam and n0[i]<MINN)))
print("")
print("BASELINE all Overs n=%d ROI=%+.2f%% | all Unders ROI=%+.2f%%"%(
      len(T),100*statistics.mean(x["po"] for x in ROWS),100*statistics.mean(x["pu"] for x in ROWS)))
RES.sort(reverse=True)
print("BEST CELL %s  ROI %+.2f%%  n=%d   CEILING %+.2f%%   -> %s"%(
      RES[0][1],RES[0][0],RES[0][2],CEIL,"FINDING" if RES[0][0]>CEIL else "NOT A FINDING"))

# per-cell one-sided permutation p-values for the top 5 cells
print("")
print("per-cell one-sided permutation p (own block level, K=%d):"%K)
top=[r[5] for r in RES[:5]]
hits=[0]*NC; tot=[0]*NC
for k in range(K):
    dg=GIDS[:]; random.shuffle(dg); gmap=dict(zip(GIDS,dg))
    dp=PGS[:];  random.shuffle(dp); pmap=dict(zip(PGS,dp))
    n,s=tally(gmap,pmap)
    for i in top:
        if n[i]>=MINN//2:
            tot[i]+=1
            if 100*s[i]/n[i] >= 100*s0[i]/n0[i]: hits[i]+=1
for r in RES[:5]:
    i=r[5]; print("   %-32s ROI %+6.2f%%  p=%.4f"%(NAME[i],r[0],(hits[i]+1)/(tot[i]+1)))
