import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(D)
_s=open(os.path.join(D,"mega_sweep.py"),encoding="utf-8").read().split('print(f"{len(B)} two-sided board quotes')[0]
exec(_s.replace('D = os.path.dirname(os.path.abspath(__file__))','pass'))
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G={g:r for g,r in [(x['game_id'],x) for x in load("data/games_2026.csv")]}
L=load("live_lines.csv")
wins=[(g,t[1],t[1]+datetime.timedelta(hours=3),{t[2],t[3]}) for g,t in gmeta.items()]
def abbr(x): x=(x or "").strip(); return FULL.get(x,x)
rows=collections.defaultdict(list)
for r in L:
    t=ts(r.get("ts"))
    if not t or str(r.get("alt"))!="0" or r.get("type")!="total": continue
    tm=[abbr(z) for z in (r.get("teams") or "").split("|")]
    if len(tm)!=2: continue
    for g,tp,en,s in wins:
        if set(tm)==s and tp<=t<=en:
            rows[g].append(((t-tp).total_seconds()/60, f(r.get("points")))); break
print("LATE-WINDOW TOTAL vs FINAL SCORE  (a true in-play total must converge)")
print(f"{'game':<12}{'last t+min':>11}{'last total':>11}{'final':>8}{'err':>8}")
errs=[]; e60=[]
for g in sorted(rows):
    v=sorted(rows[g]); 
    fin=(f(G[g]['home_score']) or 0)+(f(G[g]['away_score']) or 0)
    if fin<=0: continue
    el,tot=v[-1]
    errs.append(abs(tot-fin))
    if el>=60: e60.append(abs(tot-fin))
    print(f"{g:<12}{el:>11.0f}{tot:>11.1f}{fin:>8.0f}{tot-fin:>8.1f}")
print(f"\nmean |last total - final| = {statistics.mean(errs):.1f} (n={len(errs)})")
print(f"  restricted to last quote at t+60min or later: {statistics.mean(e60):.1f} (n={len(e60)})")
print("Reference: PRE-GAME Pinnacle total forecasts final with r=0.816; typical pre-game abs err ~11-13.")
# pregame benchmark from gamelines.csv
pg=collections.defaultdict(list)
for r in load("gamelines.csv"):
    if r.get("type")!="total": continue
    t=ts(r.get("ts"))
    tm=[abbr(z) for z in (r.get("teams") or "").split("|")]
    if not t or len(tm)!=2: continue
    for g,tp,en,s in wins:
        if set(tm)==s and tp-datetime.timedelta(hours=6)<=t<tp: pg[g].append(f(r.get("points"))); break
pe=[]
for g,v in pg.items():
    fin=(f(G[g]['home_score']) or 0)+(f(G[g]['away_score']) or 0)
    v=[x for x in v if x]
    if fin>0 and v: pe.append(abs(statistics.median(v)-fin))
if pe: print(f"MEASURED pre-game (<=6h before tip) abs err on same corpus: {statistics.mean(pe):.1f} (n={len(pe)})")
