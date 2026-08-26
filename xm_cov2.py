import os
D=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D,"xm_build.py"),encoding="utf-8").read())
import datetime, statistics, collections
H=lambda h: datetime.timedelta(hours=h)
hb=[]
for gid,v in PT.items():
    tp=aware(gmeta[gid][1])
    for c,p,pr in v: hb.append((tp-c).total_seconds()/3600)
print("pinn total capture hours-before-tip: n",len(hb))
print("  pcts:", [round(statistics.quantiles(hb,n=20)[i],1) for i in range(19)])
first=[]; last=[]
for gid,v in PT.items():
    tp=aware(gmeta[gid][1])
    first.append((tp-v[0][0]).total_seconds()/3600); last.append((tp-v[-1][0]).total_seconds()/3600)
print("first capture h-before-tip: median",round(statistics.median(first),1),"p90",round(sorted(first)[int(.9*len(first))],1))
print("last  capture h-before-tip: median",round(statistics.median(last),1))
print("games with first capture >=9h:",sum(1 for x in first if x>=9),"; >=12h:",sum(1 for x in first if x>=12))
# 1xbet game lines
hb2=[]
for gid,v in XT.items():
    tp=aware(gmeta[gid][1])
    for c,p,pr in v: hb2.append((tp-c).total_seconds()/3600)
if hb2: print("xbet total capture h-before-tip: n",len(hb2),"median",round(statistics.median(hb2),1),"max",round(max(hb2),1))
