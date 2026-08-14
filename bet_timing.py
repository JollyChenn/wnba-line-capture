# When to place a flip/hotover bet. Not the board in general - THESE bets.
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D=r"C:\Users\Axioo\wnba-line-capture"
def load(p):
    fp=os.path.join(D,p)
    return list(csv.DictReader(open(fp,encoding="utf-8",errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError,ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None
MK=("pts","pra","pr","pa","reb","ast","ra"); BET=("pra","pr","pts")
gm={g["game_id"]:(g.get("date",""),ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog=collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    dt,tp=gm.get(r.get("game_id"),("",None))
    if not (dt and tp): continue
    p,rb,a=f(r.get("pts")) or 0,f(r.get("reb")) or 0,f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=dt,tip=tp,pts=p,reb=rb,ast=a,
        pra=p+rb+a,pr=p+rb,pa=p+a,ra=rb+a))
for v in plog.values(): v.sort(key=lambda x:x["date"])
byp=collections.defaultdict(list)
for pl,v in plog.items():
    for g in v: byp[pl].append((g["tip"],g["date"],g))
for v in byp.values(): v.sort()
def ga(pl,when):
    for tip,dt,rec in byp.get(pl,[]):
        if when<=tip<=when+datetime.timedelta(hours=36): return dt,rec
    return None,None
raw=collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t,o,ln=ts(b.get("captured_utc")),f(b.get("odds")),f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MK and b.get("side")=="Over":
        raw[((b.get("player") or "").lower(),b.get("market"),ln)].append((t,o))
for v in raw.values(): v.sort()
seen,BETS=set(),[]
for b in sorted(load("bets_log.csv"),key=lambda r:r.get("captured_utc") or ""):
    if b.get("side")!="Over" or (b.get("src") or "") not in ("flip","hotover"): continue
    pl,mk,ln=(b.get("player") or "").lower(),b.get("market"),f(b.get("line"))
    if mk not in BET or ln is None: continue
    dt,rec=ga(pl,ts(b.get("captured_utc")))
    if not rec or rec[mk]==ln: continue
    k=(dt,pl,mk)
    if k in seen: continue
    seen.add(k)
    s=[x for x in raw.get((pl,mk,ln),[]) if 0<=(rec["tip"]-x[0]).total_seconds()<=36*3600]
    if len(s)<2: continue
    BETS.append(dict(series=s,tip=rec["tip"],won=rec[mk]>ln))
print(f"{len(BETS)} flip/hotover bets with a full price series\n")
print("WHAT PRICE WOULD YOU HAVE GOT, BY WHEN YOU PLACED IT?")
print("="*88)
print(f"  {'placed':<16}{'bets':>6}{'avg price':>11}{'units':>10}{'ROI':>9}")
for lo,hi,nm in ((24,12,"12-24h before"),(12,8,"8-12h"),(8,6,"6-8h"),(6,4,"4-6h"),(4,2,"2-4h"),
                 (2,1,"1-2h"),(1,0,"under 1h")):
    got=[]
    for b in BETS:
        av=[o for t,o in b["series"] if lo>(b["tip"]-t).total_seconds()/3600>=hi]
        if av: got.append((av[-1],b["won"]))
    if len(got)<15:
        print(f"  {nm:<16}{len(got):>6}   too few"); continue
    u=sum((o-1) if w else -1.0 for o,w in got)
    print(f"  {nm:<16}{len(got):>6}{sum(o for o,_ in got)/len(got):>11.3f}{u:>+10.2f}{100*u/len(got):>8.1f}%")
first=[(b["series"][0][1],b["won"]) for b in BETS]
last=[(b["series"][-1][1],b["won"]) for b in BETS]
for nm,g in (("FIRST price we saw",first),("LAST price we saw",last)):
    u=sum((o-1) if w else -1.0 for o,w in g)
    print(f"  {nm:<16}{len(g):>6}{sum(o for o,_ in g)/len(g):>11.3f}{u:>+10.2f}{100*u/len(g):>8.1f}%")
gaps=sorted((b["tip"]-b["series"][-1][0]).total_seconds()/3600 for b in BETS)
print(f"\n  our LAST capture on these bets lands a median {gaps[len(gaps)//2]:.1f}h before tip")
print(f"  (25th {gaps[len(gaps)//4]:.1f}h, 75th {gaps[3*len(gaps)//4]:.1f}h)")
