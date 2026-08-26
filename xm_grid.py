# CROSS-MARKET MOVEMENT GRID + GLOBAL NOISE CEILING (declared before results are read)
import os
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_table.py"),encoding="utf-8").read())
import datetime, statistics, collections, math, random
random.seed(20260826)
MINN=60; K=1000

# ---------------- feature engineering ----------------
for r in T: r["same_up"]=0; r["same_dn"]=0; r["slate_movers"]=0
by_date=collections.defaultdict(list)
for r in T:
    if r["dline1"] is not None: by_date[r["date"]].append(r)
for d,rows in by_date.items():
    ups=[x for x in rows if x["dline1"]>=1.0]; dns=[x for x in rows if x["dline1"]<=-1.0]
    for r in rows:
        r["same_up"]=sum(1 for x in ups if x["pl"]!=r["pl"])
        r["same_dn"]=sum(1 for x in dns if x["pl"]!=r["pl"])
        r["slate_movers"]=len(ups)+len(dns)
ptsmove={}
for r in T:
    if r["mk"]=="pts" and r["dline1"] is not None: ptsmove[(r["pl"],r["gid"])]=r["dline1"]
for r in T: r["pts_dline"]=ptsmove.get((r["pl"],r["gid"]))

PTSFAM=("pra","pr","pa"); NONSC=("reb","ast","ra")

def mk_cells():
    C=[]
    uA=lambda r: r["dtot"] is not None and r["dline1"] is not None
    tb={"totUP":  lambda r: r["dtot"]>=1.0,
        "totDN":  lambda r: r["dtot"]<=-1.0,
        "totFLAT":lambda r: abs(r["dtot"])<1.0}
    for tn,tf in tb.items():
        for pn,pf in (("herline_unmoved",lambda r:r["dline1"]==0.0),("any",lambda r:True)):
            for sd in ("Over","Under"):
                C.append(("A","A:%s&%s:%s"%(tn,pn,sd),uA,(lambda tf=tf,pf=pf: (lambda r: tf(r) and pf(r)))(),sd))
    uB=lambda r: r["dabsspr"] is not None and r["hspr6"] is not None
    sb={"sprWIDEN": lambda r: r["dabsspr"]>=1.0,
        "sprNARROW":lambda r: r["dabsspr"]<=-1.0,
        "sprFLAT":  lambda r: abs(r["dabsspr"])<1.0}
    for sn,sf in sb.items():
        for rn,rf in (("fav",lambda r:r["hspr6"]<0),("dog",lambda r:r["hspr6"]>0)):
            for sd in ("Over","Under"):
                C.append(("B","B:%s&%s:%s"%(sn,rn,sd),uB,(lambda sf=sf,rf=rf: (lambda r: sf(r) and rf(r)))(),sd))
    uC=lambda r: r["pts_dline"] is not None and r["mk"]!="pts"
    for dn_,df in (("ptsUP",lambda r:r["pts_dline"]>=1.0),("ptsDN",lambda r:r["pts_dline"]<=-1.0)):
        for gn,gf in (("tgt_ptsfam",lambda r:r["mk"] in PTSFAM),("tgt_nonsc",lambda r:r["mk"] in NONSC),("tgt_all",lambda r:True)):
            for sd in ("Over","Under"):
                C.append(("C","C:%s&%s:%s"%(dn_,gn,sd),uC,(lambda df=df,gf=gf:(lambda r: df(r) and gf(r)))(),sd))
    uD=lambda r: r["dline1"] is not None
    db={"upPACK":  lambda r: r["dline1"]>=1.0 and r["same_up"]>=3,
        "upALONE": lambda r: r["dline1"]>=1.0 and r["same_up"]<=1,
        "dnPACK":  lambda r: r["dline1"]<=-1.0 and r["same_dn"]>=3,
        "dnALONE": lambda r: r["dline1"]<=-1.0 and r["same_dn"]<=1,
        "nomove":  lambda r: r["dline1"]==0.0}
    for dn_,df in db.items():
        for sd in ("Over","Under"):
            C.append(("D","D:%s:%s"%(dn_,sd),uD,df,sd))
    uE=lambda r: r["dood1"] is not None
    eb={"short": lambda r: r["dood1"]<=-0.05,
        "long":  lambda r: r["dood1"]>=0.05,
        "flat":  lambda r: abs(r["dood1"])<0.05}
    ib={"x_any":  lambda r: True,
        "x_totUP":lambda r: r["dtot"] is not None and r["dtot"]>=1.0,
        "x_totDN":lambda r: r["dtot"] is not None and r["dtot"]<=-1.0}
    for en,ef in eb.items():
        for in_,if_ in ib.items():
            for sd in ("Over","Under"):
                C.append(("E","E:%s&%s:%s"%(en,in_,sd),uE,(lambda ef=ef,if_=if_:(lambda r: ef(r) and if_(r)))(),sd))
    return C
CELLS=mk_cells()
print("GRID DECLARED: %d cells, min n = %d, K = %d permutations"%(len(CELLS),MINN,K))
print("universe T = %d two-sided board quotes priced at the last quote <= tip-%.0fh"%(len(T),GATE_H))
print("")

AKEYS=("dtot","dabsspr","hspr6","spr6","tot6")
PKEYS=("dline1","dood1","pts_dline","same_up","same_dn","slate_movers")
GL={}; PL={}
for r in T:
    GL.setdefault(r["gid"], dict((k,r[k]) for k in AKEYS))
    PL[(r["pl"],r["gid"],r["mk"])]=dict((k,r[k]) for k in PKEYS)
GIDS=sorted(GL); PGS=sorted(set((r["pl"],r["gid"]) for r in T))
rows_by_gid=collections.defaultdict(list); rows_by_pg=collections.defaultdict(list)
for r in T: rows_by_gid[r["gid"]].append(r); rows_by_pg[(r["pl"],r["gid"])].append(r)

def apply_labels(gmap, pmap):
    for gid,rows in rows_by_gid.items():
        src=GL[gmap[gid]]
        for r in rows:
            for k in AKEYS: r[k]=src[k]
    for pg,rows in rows_by_pg.items():
        drows=rows_by_pg[pmap[pg]]
        dmk=dict((x["mk"],x) for x in drows)
        for r in rows:
            d=dmk.get(r["mk"]) or drows[0]
            src=PL[(d["pl"],d["gid"],d["mk"])]
            for k in PKEYS: r[k]=src[k]
IDG=dict((g,g) for g in GIDS); IDP=dict((p,p) for p in PGS)

def roi_table():
    out={}
    for fam,name,uf,lf,sd in CELLS:
        v=[pnl(r,sd) for r in T if uf(r) and lf(r)]
        if len(v)>=MINN: out[name]=(len(v),100*statistics.mean(v))
    return out

maxs=[]
for k in range(K):
    dg=GIDS[:]; random.shuffle(dg); gmap=dict(zip(GIDS,dg))
    dp=PGS[:];  random.shuffle(dp); pmap=dict(zip(PGS,dp))
    apply_labels(gmap,pmap)
    tb=roi_table()
    if tb: maxs.append(max(v[1] for v in tb.values()))
apply_labels(IDG,IDP)
maxs.sort()
CEIL=maxs[int(0.95*len(maxs))]
print("="*80)
print("NOISE CEILING  (p95 of the best-cell ROI across the whole %d-cell grid under the null:"%len(CELLS))
print("  game labels relabelled game-block, player-game labels relabelled player-game-block)")
print("  p50 = %+.2f%%   p95 = %+.2f%%   p99 = %+.2f%%   max = %+.2f%%"%(
      maxs[len(maxs)//2],CEIL,maxs[int(0.99*len(maxs))],maxs[-1]))
print("  ANY CELL BELOW %+.2f%% IS NOT A FINDING."%CEIL)
print("="*80); print("")

real=roi_table()
CIDX=dict((c[1],c) for c in CELLS)
def boot(name):
    fam,_,uf,lf,sd = CIDX[name]
    blocks=collections.defaultdict(list)
    key=(lambda r:r["gid"]) if fam in ("A","B") else (lambda r:(r["pl"],r["gid"]))
    for r in T:
        if uf(r) and lf(r): blocks[key(r)].append(pnl(r,sd))
    bl=list(blocks.values())
    if not bl: return (None,None)
    res=[]
    for _ in range(1500):
        s=[]
        for _ in range(len(bl)): s.extend(random.choice(bl))
        if s: res.append(100*statistics.mean(s))
    res.sort()
    return (res[int(.025*len(res))], res[int(.975*len(res))])

def pval(name):
    """one-sided permutation p for THIS cell alone, at its own block level."""
    fam,_,uf,lf,sd = CIDX[name]
    obs=real[name][1]; hits=0; tot=0
    for _ in range(K):
        dg=GIDS[:]; random.shuffle(dg); gmap=dict(zip(GIDS,dg))
        dp=PGS[:];  random.shuffle(dp); pmap=dict(zip(PGS,dp))
        apply_labels(gmap,pmap)
        v=[pnl(r,sd) for r in T if uf(r) and lf(r)]
        if len(v)>=MINN//2:
            tot+=1
            if 100*statistics.mean(v)>=obs: hits+=1
    apply_labels(IDG,IDP)
    return (hits+1)/(tot+1)

print("%-34s%6s%9s%26s  %s"%("cell","n","ROI%","95% CI (block boot)","verdict"))
for fam in ("A","B","C","D","E"):
    print("--- family %s ---"%fam)
    ent=[(n,v) for n,v in real.items() if n.startswith(fam+":")]
    ent.sort(key=lambda x:-x[1][1])
    for name,(n,roi) in ent:
        lo,hi=boot(name)
        flag="  *** BEATS CEILING ***" if roi>CEIL else ""
        print("%-34s%6d%9.2f   [%+7.2f,%+7.2f]%s"%(name,n,roi,lo,hi,flag))
print("")
print("BASELINES: all Overs n=%d ROI=%+.2f%%   all Unders ROI=%+.2f%%"%(
      len(T),100*statistics.mean(pnl(r,'Over') for r in T),100*statistics.mean(pnl(r,'Under') for r in T)))
best=[ (v[1],n) for n,v in real.items() ]
best.sort(reverse=True)
print("BEST CELL: %s at %+.2f%%  vs ceiling %+.2f%%"%(best[0][1],best[0][0],CEIL))
for roi,n in best[:3]:
    if roi>CEIL: print("  per-cell permutation p for %s = %.4f"%(n,pval(n)))
