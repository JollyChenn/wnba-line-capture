import os
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_build.py"),encoding="utf-8").read())
print("PT games",len(PT),"PS",len(PS),"PM",len(PM),"XT",len(XT))
print("PROP keys",len(PROP))
import datetime, statistics, collections
H=lambda h: datetime.timedelta(hours=h)
cov=collections.Counter()
moves=[]
for gid,v in PT.items():
    tp=aware(gmeta[gid][1])
    a=at_or_before(v, tp-H(24)); b=at_or_before(v, tp-H(6))
    if a and b and b[0]>a[0]:
        moves.append(b[1]-a[1]); cov["both"]+=1
    elif b: cov["only6"]+=1
    else: cov["none"]+=1
print("pinn total 24h->6h moves:",cov, "n",len(moves))
if moves:
    print("  mean",round(statistics.mean(moves),3),"sd",round(statistics.pstdev(moves),3),
          "dist",collections.Counter(round(m,1) for m in moves).most_common(10))
# player coverage with two-sided quote at 6h + earlier quote + settled result
n_ok=0; n_tot=0; with_tot=0
for (pl,mk,gid),s in PROP.items():
    tp=aware(gmeta[gid][1])
    now=pgrow.get((pl, gmeta[gid][1]))
    if not now: continue
    n_tot+=1
    q6=two_sided_at(pl,mk,gid,tp-H(6))
    if not q6: continue
    n_ok+=1
    if gid in PT and at_or_before(PT[gid], tp-H(24)): with_tot+=1
print("player-market-games with box result:",n_tot," with two-sided @<=6h:",n_ok," + pinn total 24h:",with_tot)
