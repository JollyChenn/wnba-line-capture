import csv,os,sys,statistics,collections,datetime
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=r"C:\Users\Axioo\wnba-line-capture"
def ts(s):
    s=(s or "").replace("Z","+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None
GM=list(csv.DictReader(open(os.path.join(D,"data","games_2026.csv"),encoding="utf-8")))
tipof={g["game_id"]:ts(g["tip"]) for g in GM}; dateof={g["game_id"]:g["date"] for g in GM}
pl_game={}
for r in csv.DictReader(open(os.path.join(D,"data","box_2026.csv"),encoding="utf-8")):
    if r["game_id"] in dateof: pl_game[(r["player"].lower(),dateof[r["game_id"]])]=r["game_id"]
# last board quote per (player, gamedate)
last=collections.defaultdict(lambda:None); first=collections.defaultdict(lambda:None)
for r in csv.DictReader(open(os.path.join(D,"xbet_board.csv"),encoding="utf-8")):
    t=ts(r["captured_utc"])
    if not t: continue
    d=t.strftime("%Y%m%d")
    for dd in (d,(t+datetime.timedelta(days=1)).strftime("%Y%m%d")):
        k=(r["player"].lower(),dd)
        if k in pl_game:
            tip=tipof[pl_game[k]]
            if tip and t<tip:
                if last[k] is None or t>last[k]: last[k]=t
                if first[k] is None or t<first[k]: first[k]=t
lg=[(tipof[pl_game[k]]-v).total_seconds()/3600 for k,v in last.items() if v]
fg=[(tipof[pl_game[k]]-v).total_seconds()/3600 for k,v in first.items() if v]
lg.sort()
print(f"xbet_board LAST pre-tip quote, hours before tip: n={len(lg)}")
for q in (5,10,25,50,75,90):
    print(f"   p{q:<3} {lg[int(q/100*len(lg))]:6.2f}h")
print(f"   frac within 2h of tip: {sum(1 for x in lg if x<2)/len(lg)*100:.1f}%   within 6h: {sum(1 for x in lg if x<6)/len(lg)*100:.1f}%")
print(f"   first quote median {statistics.median(fg):.1f}h before tip")
# pinnacle
P=collections.defaultdict(lambda:None)
for r in csv.DictReader(open(os.path.join(D,"pinn_snapshots.csv"),encoding="utf-8")):
    t=ts(r["captured_utc"])
    if not t: continue
    d=t.strftime("%Y%m%d")
    for dd in (d,(t+datetime.timedelta(days=1)).strftime("%Y%m%d")):
        k=(r["player"].lower(),dd)
        if k in pl_game:
            tip=tipof[pl_game[k]]
            if tip and t<tip and (P[k] is None or t>P[k]): P[k]=t
pl=sorted((tipof[pl_game[k]]-v).total_seconds()/3600 for k,v in P.items() if v)
print(f"\npinn_snapshots LAST pre-tip snapshot, hours before tip: n={len(pl)}")
for q in (5,10,25,50,75,90): print(f"   p{q:<3} {pl[int(q/100*len(pl))]:6.2f}h")
print(f"   frac within 2h of tip: {sum(1 for x in pl if x<2)/len(pl)*100:.1f}%   within 6h: {sum(1 for x in pl if x<6)/len(pl)*100:.1f}%")
