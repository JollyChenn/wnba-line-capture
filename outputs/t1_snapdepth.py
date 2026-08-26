import csv, os, sys, datetime, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
R=r"C:\Users\Axioo\wnba-line-capture"
LS=list(csv.DictReader(open(os.path.join(R,"live_snapshots.csv"),encoding="utf-8",errors="replace")))
by=collections.defaultdict(list)
for r in LS: by[r["game_id"]].append(r)
per=collections.Counter()
print(f"{'game':>10} {'snaps':>5} {'periods':>12} {'maxscore':>9} {'clock@last':>10}")
ns=[]
for g,v in sorted(by.items()):
    ps=sorted(set(int(x['period']) for x in v if x['period'].isdigit()))
    for p in ps: per[p]+=1
    mx=max((float(x['home_score'] or 0)+float(x['away_score'] or 0)) for x in v)
    ns.append(len(v))
    print(f"{g:>10} {len(v):>5} {str(ps):>12} {mx:>9.0f} {v[-1]['clock']:>10}")
print("\nsnaps per game: median",statistics.median(ns),"min",min(ns),"max",max(ns))
print("games reaching period 4:",sum(1 for v in by.values() if any(x['period']=='4' for x in v)),"of",len(by))
print("period row counts:",dict(per))
print("cols:",list(LS[0].keys()))
