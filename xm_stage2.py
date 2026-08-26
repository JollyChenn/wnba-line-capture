# STAGE 2: (a) size-stratified noise ceilings for the stage-1 grid
#          (b) lead/lag significance with a GAME-block permutation
#          (c) drift grid + the short-vs-flat contrast
#          (d) the same total-propagation bet re-run at a LATER horizon (gate = tip-2h)
import os
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_build.py"),encoding="utf-8").read())
import statistics, collections, math, random, functools
print=functools.partial(print,flush=True)
random.seed(20260826)
H=lambda h: datetime.timedelta(hours=h)
def novig(a,b):
    if a is None or b is None or a<=1 or b<=1: return None
    return (1/a)/((1/a)+(1/b))

def build(GATE_H, ANCHOR_H):
    T=[]
    for (pl,mk,gid),ser in PROP.items():
        tp_raw=gmeta[gid][1]; tp=aware(tp_raw)
        now=pgrow.get((pl,tp_raw))
        if not now or now["min"]<8: continue
        q6=two_sided_at(pl,mk,gid,tp-H(GATE_H))
        if not q6: continue
        cap6,line6,ood6,uod6=q6
        if now[mk]==line6: continue
        ovA=at_or_before(ser["Over"],tp-H(ANCHOR_H))
        g6={};gA={}
        t_=at_or_before(PT.get(gid,[]),tp-H(GATE_H));  g6["tot"]=t_[1] if t_ else None
        tA=at_or_before(PT.get(gid,[]),tp-H(ANCHOR_H));gA["tot"]=tA[1] if tA else None
        T.append(dict(pl=pl,mk=mk,gid=gid,tip=tp,date=gmeta[gid][0],line=line6,ood=ood6,uod=uod6,
            over_won=now[mk]>line6, actual=now[mk],
            dline1=(None if not ovA else line6-ovA[1]),
            dood1=(None if not ovA else ood6-ovA[2]),
            dtot=(None if (g6["tot"] is None or gA["tot"] is None) else g6["tot"]-gA["tot"]),
            prevline=prevline.get((pl,mk,tp_raw))))
    for r in T: r["notraised"]=None if r["prevline"] is None else (r["line"]-r["prevline"]<0.5)
    pm={}
    for r in T:
        if r["mk"]=="pts":
            pm[(r["pl"],r["gid"])]=(r["dline1"],r["dood1"])
    for r in T:
        v=pm.get((r["pl"],r["gid"]),(None,None))
        r["pts_dline"],r["pts_dood"]=v
    return T
def pnl(r,sd):
    if sd=="Over": return (r["ood"]-1) if r["over_won"] else -1.0
    return (r["uod"]-1) if not r["over_won"] else -1.0

T6=build(6.0,12.0); T2=build(2.0,8.0)
print("horizon gate=tip-6h anchor=tip-12h : n=%d"%len(T6))
print("horizon gate=tip-2h anchor=tip-8h  : n=%d"%len(T2))
print("")

# ---------------------------------------------------------------- (b) LEAD / LAG
print("="*84)
print("(b) LEAD / LAG SIGNIFICANCE - Pinnacle game total vs 1xbet prop board, game-block null")
print("="*84)
HRS=[18,16,14,12,10,9,8,7,6,5,4,3,2,1]
panel={}
props_by_gid=collections.defaultdict(list)
for (pl,mk,gid) in PROP: props_by_gid[gid].append((pl,mk))
for gid in PT:
    tp=aware(gmeta[gid][1])
    if gid not in gmeta or gmeta[gid][0]=="" : continue
    tot={h:(at_or_before(PT[gid],tp-H(h)) or (None,None,None))[1] for h in HRS}
    if tot[18] is None: continue
    L={};P={}
    for (pl,mk) in props_by_gid[gid]:
        s=PROP[(pl,mk,gid)]
        v={};pv={}
        for h in HRS:
            o=at_or_before(s["Over"],tp-H(h)); u=at_or_before(s["Under"],tp-H(h))
            v[h]=o[1] if o else None
            pv[h]=novig(o[2],u[2]) if (o and u and o[1]==u[1]) else None
        if v[18] is None: continue
        L[(pl,mk)]=v; P[(pl,mk)]=pv
    if L: panel[gid]=(tot,L,P)
def corr(a,b):
    n=len(a)
    if n<3: return None
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa=math.sqrt(sum((x-ma)**2 for x in a)); sb=math.sqrt(sum((x-mb)**2 for x in b))
    if sa==0 or sb==0: return None
    return sum((a[i]-ma)*(b[i]-mb) for i in range(n))/(sa*sb)
WIN=[(18,12),(12,6),(9,3),(6,1)]
print("%-34s %8s %6s %8s"%("pair","rho","n","perm p"))
lag_rows=[]
for (a,b) in WIN:
    for (c_,d_) in WIN:
        xs=[];ys=[]
        for gid,(tot,L,P) in panel.items():
            if tot[a] is None or tot[b] is None: continue
            ps=[pv[d_]-pv[c_] for pv in P.values() if pv[d_] is not None and pv[c_] is not None]
            if not ps: continue
            xs.append(tot[b]-tot[a]); ys.append(statistics.mean(ps))
        if len(xs)<25: continue
        r=corr(xs,ys)
        cnt=0
        for _ in range(2000):
            z=xs[:]; random.shuffle(z)
            rr=corr(z,ys)
            if rr is not None and abs(rr)>=abs(r): cnt+=1
        lag_rows.append((abs(r),"tot[%d->%d] vs p_over[%d->%d]"%(a,b,c_,d_),r,len(xs),(cnt+1)/2001))
for _,lab,r,n_,p in sorted(lag_rows,reverse=True)[:6]:
    print("%-34s %+8.3f %6d %8.4f"%(lab,r,n_,p))
print("  (16 pairs tested -> Bonferroni threshold p<0.0031 ; game-block shuffle of the total move)")
print("")

# ---------------------------------------------------------------- (c)+(d) STAGE-2 GRID
print("="*84)
print("(c)+(d) STAGE-2 GRID - drift channel, Model S interaction, and the propagation bet")
print("        re-run at a LATER decision point (gate = tip-2h) in case the lag is short")
print("="*84)
S=[]
def cell(name, tab, filt, sd): S.append((name,tab,filt,sd))
for sd in ("Over","Under"):
    cell("S:drift_short&line_unmoved:%s"%sd,"6",lambda r: r["dood1"] is not None and r["dood1"]<=-0.05 and r["dline1"]==0.0,sd)
    cell("S:drift_flat&line_unmoved:%s"%sd,"6", lambda r: r["dood1"] is not None and abs(r["dood1"])<0.05 and r["dline1"]==0.0,sd)
    cell("S:drift_long&line_unmoved:%s"%sd,"6", lambda r: r["dood1"] is not None and r["dood1"]>=0.05 and r["dline1"]==0.0,sd)
cell("S:drift_short&modelS_mkts:Over","6",lambda r: r["dood1"] is not None and r["dood1"]<=-0.05 and r["mk"] in ("pra","pr","pts"),"Over")
cell("S:drift_short&notraised:Over","6",lambda r: r["dood1"] is not None and r["dood1"]<=-0.05 and r["notraised"] is True,"Over")
cell("S:drift_short&notraised&modelSmkts:Over","6",lambda r: r["dood1"] is not None and r["dood1"]<=-0.05 and r["notraised"] is True and r["mk"] in ("pra","pr","pts"),"Over")
cell("S:notraised&modelSmkts(control):Over","6",lambda r: r["notraised"] is True and r["mk"] in ("pra","pr","pts"),"Over")
cell("S:totUP&price_not_short:Over","6",lambda r: r["dtot"] is not None and r["dtot"]>=1.0 and r["dood1"] is not None and r["dood1"]>-0.05,"Over")
cell("S:totUP&price_short:Over","6",lambda r: r["dtot"] is not None and r["dtot"]>=1.0 and r["dood1"] is not None and r["dood1"]<=-0.05,"Over")
cell("S:totDN&price_not_long:Under","6",lambda r: r["dtot"] is not None and r["dtot"]<=-1.0 and r["dood1"] is not None and r["dood1"]<0.05,"Under")
for sd in ("Over","Under"):
    cell("S:herPTSprice_short->othermkt:%s"%sd,"6",lambda r: r["pts_dood"] is not None and r["pts_dood"]<=-0.05 and r["mk"]!="pts",sd)
    cell("S:herPTSprice_long->othermkt:%s"%sd,"6",lambda r: r["pts_dood"] is not None and r["pts_dood"]>=0.05 and r["mk"]!="pts",sd)
# late horizon
for sd in ("Over","Under"):
    cell("L2:totUP&line_unmoved:%s"%sd,"2",lambda r: r["dtot"] is not None and r["dtot"]>=1.0 and r["dline1"]==0.0,sd)
    cell("L2:totDN&line_unmoved:%s"%sd,"2",lambda r: r["dtot"] is not None and r["dtot"]<=-1.0 and r["dline1"]==0.0,sd)
cell("L2:drift_short:Over","2",lambda r: r["dood1"] is not None and r["dood1"]<=-0.05,"Over")
cell("L2:drift_long:Under","2",lambda r: r["dood1"] is not None and r["dood1"]>=0.05,"Under")
print("STAGE-2 GRID DECLARED: %d cells, min n = 60"%len(S))

TAB={"6":T6,"2":T2}
GK={}; PK={}
LAB6=("dline1","dood1","dtot","pts_dline","pts_dood","notraised")
def snap(T):
    g={}; p={}; fb={}
    for r in T:
        g.setdefault(r["gid"],{"dtot":r["dtot"]})
        d={k:r[k] for k in LAB6 if k!="dtot"}
        p[(r["pl"],r["gid"],r["mk"])]=d
        fb.setdefault((r["pl"],r["gid"]),d)
    return g,p,fb
SNAP={k:snap(v) for k,v in TAB.items()}
def perm(tabk, gmap, pmap):
    T=TAB[tabk]; g,p,fb=SNAP[tabk]
    for r in T:
        r["dtot"]=g[gmap[r["gid"]]]["dtot"]
        d=pmap[(r["pl"],r["gid"])]
        src=p.get((d[0],d[1],r["mk"])) or fb[d]
        for k in src: r[k]=src[k]
IDS={}
for k,T in TAB.items():
    gids=sorted(set(r["gid"] for r in T)); pgs=sorted(set((r["pl"],r["gid"]) for r in T))
    IDS[k]=(gids,pgs)
def table():
    out={}
    for name,tk,fl,sd in S:
        v=[pnl(r,sd) for r in TAB[tk] if fl(r)]
        if len(v)>=60: out[name]=(len(v),100*statistics.mean(v))
    return out
maxs=[]
for _ in range(600):
    for k in TAB:
        gids,pgs=IDS[k]
        dg=gids[:]; random.shuffle(dg); dp=pgs[:]; random.shuffle(dp)
        perm(k,dict(zip(gids,dg)),dict(zip(pgs,dp)))
    tb=table()
    if tb: maxs.append(max(v[1] for v in tb.values()))
for k in TAB:
    gids,pgs=IDS[k]; perm(k,dict((g,g) for g in gids),dict((p,p) for p in pgs))
maxs.sort(); CE2=maxs[int(.95*len(maxs))]
print("STAGE-2 NOISE CEILING: p50 %+.2f%%  p95 %+.2f%%  max %+.2f%%   -> anything <= %+.2f%% is NOT a finding"%(
    maxs[len(maxs)//2],CE2,maxs[-1],CE2))
print("")
real=table()
def ci(name):
    nm,tk,fl,sd=[x for x in S if x[0]==name][0]
    grp=collections.defaultdict(list)
    for r in TAB[tk]:
        if fl(r): grp[(r["pl"],r["gid"])].append(pnl(r,sd))
    bl=list(grp.values()); res=[]
    for _ in range(1200):
        acc=[]
        for _ in range(len(bl)): acc.extend(random.choice(bl))
        res.append(100*sum(acc)/len(acc))
    res.sort(); return res[30],res[-31]
print("%-44s%6s%9s   %s"%("cell","n","ROI%","95% CI"))
for name,(n_,roi) in sorted(real.items(),key=lambda x:-x[1][1]):
    lo,hi=ci(name)
    print("%-44s%6d%9.2f   [%+6.2f,%+6.2f] %s"%(name,n_,roi,lo,hi,"*** BEATS CEILING ***" if roi>CE2 else ""))
drop=[n for n,tk,fl,sd in S if n not in real]
if drop: print("(dropped n<60: %s)"%", ".join(drop))
print("")
# short-vs-flat CONTRAST, permutation on the drift label at the player-game level
def contrast(fl1,fl2,sd,T):
    a=[pnl(r,sd) for r in T if fl1(r)]; b=[pnl(r,sd) for r in T if fl2(r)]
    return 100*(statistics.mean(a)-statistics.mean(b)), len(a), len(b)
f_sh=lambda r: r["dood1"] is not None and r["dood1"]<=-0.05
f_fl=lambda r: r["dood1"] is not None and abs(r["dood1"])<0.05
obs,na,nb=contrast(f_sh,f_fl,"Over",T6)
gids,pgs=IDS["6"]; hits=0
for _ in range(2000):
    dg=gids[:]; random.shuffle(dg); dp=pgs[:]; random.shuffle(dp)
    perm("6",dict(zip(gids,dg)),dict(zip(pgs,dp)))
    v,_,_=contrast(f_sh,f_fl,"Over",T6)
    if v>=obs: hits+=1
perm("6",dict((g,g) for g in gids),dict((p,p) for p in pgs))
print("CONTRAST  drift-short Overs minus drift-flat Overs = %+.2f pp  (n=%d vs %d)  perm p=%.4f"%(
    obs,na,nb,(hits+1)/2001))
