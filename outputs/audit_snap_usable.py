import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
def load(p):
    with open(p, encoding="utf-8-sig", newline="") as fh: return list(csv.DictReader(fh))
def ts(s):
    s=(s or "").strip().replace("Z","")
    for f in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M"):
        try: return datetime.datetime.strptime(s,f)
        except Exception: pass
    return None
def clk(c):
    try:
        if ":" in c:
            m,sec=c.split(":"); return int(m)*60+float(sec)
        return float(c)
    except Exception: return None

snaps=load(os.path.join(R,"live_snapshots.csv"))
by=collections.defaultdict(list)
for s in snaps:
    t=ts(s["ts"])
    if t: by[s["game_id"]].append((t,s))
for k in by: by[k].sort(key=lambda x:x[0])

# elapsed game seconds: WNBA 4x10min = 2400s
def elapsed(s):
    try: p=int(s["period"])
    except Exception: return None
    c=clk(s.get("clock",""))
    if c is None: return None
    if p<=4: return (p-1)*600 + (600-c)
    return 2400 + (p-5)*300 + (300-c)

print("=== HONEST COVERAGE: FRACTION OF REAL GAME CLOCK OBSERVED ===")
print("gid        first_elapsed  last_elapsed  covered_s  frac_of_2400  q4rows  snaps")
fracs=[]; q4rows_tot=0
rowsout=[]
for gid,arr in by.items():
    es=[elapsed(s) for _,s in arr]
    es=[e for e in es if e is not None]
    if not es: continue
    lo,hi=min(es),max(es)
    cov=hi-lo
    frac=cov/2400.0
    fracs.append(frac)
    q4=sum(1 for _,s in arr if (s.get("period") or "")=="4")
    q4rows_tot+=q4
    rowsout.append((gid,lo,hi,cov,frac,q4,len(arr)))
for r in sorted(rowsout,key=lambda x:-x[4]):
    print("%s %10.0f %12.0f %10.0f %11.2f %7d %6d" % r)
fracs.sort()
print("")
print("median frac of regulation observed = %.2f   mean=%.2f   min=%.2f max=%.2f" % (statistics.median(fracs), statistics.mean(fracs), fracs[0], fracs[-1]))
print("games observing >=80%% of regulation: %d/%d" % (sum(1 for f in fracs if f>=0.80), len(fracs)))
print("games observing >=50%% of regulation: %d/%d" % (sum(1 for f in fracs if f>=0.50), len(fracs)))
print("total Q4 snapshot rows across ALL games: %d" % q4rows_tot)

print("")
print("=== CONDITIONING COLLAPSE: games surviving typical live-state filters ===")
def games_with(pred):
    out=[]
    for gid,arr in by.items():
        if any(pred(s) for _,s in arr): out.append(gid)
    return out
def margin(s):
    try: return abs(int(s["home_score"])-int(s["away_score"]))
    except Exception: return None
tests=[
 ("any Q4 row", lambda s: (s.get("period") or "")=="4"),
 ("Q4 with <5:00 left", lambda s: (s.get("period") or "")=="4" and (clk(s.get("clock","")) or 999)<300),
 ("Q4 <5:00 AND margin<=8", lambda s: (s.get("period") or "")=="4" and (clk(s.get("clock","")) or 999)<300 and (margin(s) is not None and margin(s)<=8)),
 ("Q4 <2:00", lambda s: (s.get("period") or "")=="4" and (clk(s.get("clock","")) or 999)<120),
 ("Q1 row present", lambda s: (s.get("period") or "")=="1"),
 ("halftime-ish (P2 clock<60)", lambda s: (s.get("period") or "")=="2" and (clk(s.get("clock","")) or 999)<60),
 ("margin>=15 (blowout)", lambda s: (margin(s) or 0)>=15),
]
for name,pred in tests:
    g=games_with(pred)
    nrow=sum(1 for _,s in [x for gid in g for x in by[gid]] if pred(s))
    print("  %-26s games=%2d/27   snapshot rows=%4d" % (name, len(g), nrow))

print("")
print("=== MDE UNDER CONDITIONING ===")
for name,ng in [("all in-play games",27),("Q4 available",11),("Q4 <5:00",None),("Q4 <5:00 & close",None)]:
    pass
for name,pred in tests[:4]:
    g=games_with(pred); n=len(g)
    if n<2:
        print("  %-26s n=%d  MDE: NOT ESTIMABLE" % (name,n)); continue
    print("  %-26s n=%2d  MDE=%.2f SD/game   ROI-MDE@10%%SD=%.1f%%   winrate CI halfwidth=+-%.1fpp" % (name,n,2.8/math.sqrt(n),2.8*10/math.sqrt(n),1.96*0.5/math.sqrt(n)*100))

print("")
print("=== IS 98.3%% SELF-SELECTED ON POLLER UPTIME? ===")
lines=load(os.path.join(R,"live_lines.csv"))
lts=set(r["ts"] for r in lines); sts=set(s["ts"] for s in snaps)
print("distinct ts in live_lines=%d  in snapshots=%d  intersection=%d" % (len(lts),len(sts),len(lts&sts)))
print("snapshot ts NOT in live_lines: %d" % len(sts-lts))
print("-> both sinks written by one poller tick; a live_lines in-play row can only exist")
print("   on a tick that also wrote a snapshot, so the 98.3%% is near-mechanical.")

# gap structure between consecutive snapshots in real time
gaps=[]
for gid,arr in by.items():
    for i in range(len(arr)-1):
        gaps.append((arr[i+1][0]-arr[i][0]).total_seconds())
gaps.sort()
print("")
print("=== SNAPSHOT CADENCE (real seconds between consecutive snaps, within game) ===")
print("n=%d  p50=%.0fs p75=%.0fs p90=%.0fs p99=%.0fs max=%.0fs" % (len(gaps),
      gaps[len(gaps)//2], gaps[int(.75*len(gaps))], gaps[int(.90*len(gaps))], gaps[int(.99*len(gaps))], gaps[-1]))
print("gaps >5min: %d (%.1f%%)   gaps >15min: %d" % (sum(1 for g in gaps if g>300), sum(1 for g in gaps if g>300)/len(gaps)*100, sum(1 for g in gaps if g>900)))

# jackknife: drop each game, recompute median frac
print("")
print("=== LEAVE-2-OUT ON THE 'USABLE DEPTH' STATISTIC ===")
best=sorted(rowsout,key=lambda x:-x[4])
print("top-2 deepest games: %s (%.2f), %s (%.2f)" % (best[0][0],best[0][4],best[1][0],best[1][4]))
rest=[r[4] for r in best[2:]]
print("median frac WITHOUT top-2 = %.2f (was %.2f); games>=0.8 left = %d" % (statistics.median(rest), statistics.median(fracs), sum(1 for f in rest if f>=0.8)))
