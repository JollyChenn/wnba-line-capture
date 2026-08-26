import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
bb=load("xbet_board.csv")
print("xbet_board rows",len(bb),"range",min(r["captured_utc"] for r in bb),max(r["captured_utc"] for r in bb))
xg=load("xbet_gamelines.csv")
print("xbet_gamelines rows",len(xg),"range",min(r["captured_utc"] for r in xg),max(r["captured_utc"] for r in xg))
# per player-market-game series
ser=collections.defaultdict(list)
for r in bb:
    t=ts(r.get("captured_utc")); ln=f(r.get("line")); od=f(r.get("odds"))
    if not t or ln is None or od is None: continue
    pl=(r.get("player") or "").lower(); mk=r.get("market")
    if mk not in ALL_MK: continue
    tm=teamof.get(pl)
    if not tm: continue
    gt=game_for(tm,t)
    if not gt: continue
    ser[(pl,mk,gt,r.get("side"))].append((t,ln,od))
print("series keys",len(ser))
ncap=[len(v) for k,v in ser.items() if k[3]=="Over"]
print("captures per (pl,mk,game) Over: median",statistics.median(ncap),"mean",round(statistics.mean(ncap),1))
# distinct lines
dl=[len(set(x[1] for x in v)) for k,v in ser.items() if k[3]=="Over"]
print("distinct line values: ", collections.Counter(dl).most_common(8))
# hours before tip distribution of captures
hb=[]
for k,v in ser.items():
    if k[3]!="Over": continue
    for t,ln,od in v: hb.append(round((k[2]-t).total_seconds()/3600))
c=collections.Counter(hb)
print("hours-before-tip histogram (top):", sorted(c.items())[:5], "...", sorted(c.items())[-5:])
buck=collections.Counter()
for h in hb:
    for b in (0,3,6,9,12,18,24,36,48,72):
        pass
    buck[min([b for b in (0,1,2,3,4,6,9,12,18,24,36,48,96) if h<=b] or [999])]+=1
print("bucket<=h:",sorted(buck.items()))
# how many player-games have >=1 quote at <=6h and >=1 at >=12h
ok=0; tot=0
for k,v in ser.items():
    if k[3]!="Over": continue
    tot+=1
    hs=[(k[2]-t).total_seconds()/3600 for t,_,_ in v]
    if any(h<=6 for h in hs) and any(h>=12 for h in hs): ok+=1
print("player-games with both <=6h and >=12h quotes:",ok,"/",tot)
