import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
# tips by team-pair
bypair = collections.defaultdict(list)
for gid,(dt,tp,hm,aw) in gmeta.items():
    bypair[tuple(sorted((hm,aw)))].append((tp,gid,dt))
rows=load("gamelines.csv")
print("gamelines rows", len(rows), "date range", min(r["captured_utc"] for r in rows), max(r["captured_utc"] for r in rows))
seen=set(); matched=0; unmatched=[]
for r in rows:
    tm=(r.get("teams") or "").split("|")
    if len(tm)!=2: continue
    ab=tuple(sorted(FULL.get(t.strip(),"") for t in tm))
    if "" in ab: continue
    st=ts(r.get("start")) 
    if st is None: continue
    if st.tzinfo is None: st=st.replace(tzinfo=datetime.timezone.utc)
    k=(ab,r.get("start"))
    if k in seen: continue
    seen.add(k)
    best=None
    for tp,gid,dt in bypair.get(ab,[]):
        d=abs((tp-st).total_seconds())
        if best is None or d<best[0]: best=(d,gid,tp)
    if best and best[0]<=36*3600: matched+=1
    else: unmatched.append((ab,r.get("start"),best[0]/3600 if best else None))
print("distinct pinn games:",len(seen),"matched",matched)
print("unmatched sample",unmatched[:5])
# check offset distribution
offs=[]
for (ab,stq) in list(seen):
    st=ts(stq); st=st.replace(tzinfo=datetime.timezone.utc) if st.tzinfo is None else st
    for tp,gid,dt in bypair.get(ab,[]):
        d=(tp-st).total_seconds()/3600
        if abs(d)<36: offs.append(round(d,2))
print("tip - start offsets (h):", collections.Counter(offs).most_common(6))
# box coverage: last game date
bx=load("data/box_2026.csv")
gids=set(r["game_id"] for r in bx)
print("box games", len(gids))
dts=sorted(gmeta[g][0] for g in gids if g in gmeta)
print("box date range", dts[0], dts[-1])
