# TRACK 3 step 1: CLV distribution from stored graded_bets columns
import csv, os, sys, math, statistics, collections, random
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"
R = list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"), encoding="utf-8")))

def fnum(x):
    try: return float(x)
    except: return None

def mci(v):
    n=len(v)
    if n<2: return (statistics.mean(v) if v else float('nan'), float('nan'), float('nan'), n)
    m=statistics.mean(v); s=statistics.stdev(v)/math.sqrt(n)
    return (m, m-1.96*s, m+1.96*s, n)

def report(name, rows):
    dec=[r for r in rows if r["result"] in ("WIN","loss")]
    pnl=[float(r["pnl"]) for r in dec]
    roi=mci(pnl)
    out={"name":name,"n_all":len(rows),"n_dec":len(dec),
         "roi":roi[0]*100 if dec else float('nan'),
         "roi_lo":roi[1]*100,"roi_hi":roi[2]*100,
         "wins":sum(1 for r in dec if r["result"]=="WIN")}
    for col in ("odds_clv","line_clv","sharp_clv","sharp_odds_clv"):
        v=[fnum(r[col]) for r in rows]; v=[x for x in v if x is not None]
        m,lo,hi,n=mci(v) if v else (float('nan'),)*3+(0,)
        beat=sum(1 for x in v if x>0); ties=sum(1 for x in v if x==0)
        out[col]=(m,lo,hi,n,beat,ties)
    return out

fams=collections.defaultdict(list)
for r in R: fams[r["src"]].append(r)

print("=== FAMILY CLV / ROI TABLE (stored columns) ===")
hdr=f"{'family':12} {'n':>5} {'dec':>4} {'ROI%':>7} {'ROI CI':>18} | {'oddsCLV%':>9} {'n':>4} {'beat%':>6} | {'lineCLV':>8} {'n':>4} {'beat%':>6} | {'sharpLine':>9} {'n':>4} | {'sharpOdds%':>10} {'n':>4} {'beat%':>6}"
print(hdr)
groups=[("ALL",R)]+sorted(fams.items(), key=lambda kv:-len(kv[1]))
res={}
for name,rows in groups:
    o=report(name,rows); res[name]=o
    def fm(c,scale=1.0,pct=False):
        m,lo,hi,n,beat,ties=o[c]
        if n==0: return ("     n/a","   0","   n/a")
        bp = beat/(n-ties)*100 if (n-ties)>0 else float('nan')
        return (f"{m*scale:+9.2f}", f"{n:4d}", f"{bp:5.1f}%")
    a=fm("odds_clv",100); b=fm("line_clv"); c=fm("sharp_clv"); d=fm("sharp_odds_clv",100)
    print(f"{name:12} {o['n_all']:5d} {o['n_dec']:4d} {o['roi']:+7.1f} [{o['roi_lo']:+6.1f},{o['roi_hi']:+6.1f}] | {a[0]} {a[1]} {a[2]} | {b[0]} {b[1]} {b[2]} | {c[0]} {c[1]} | {d[0]} {d[1]} {d[2]}")

# ties diagnostic: how many odds_clv exactly 0 / line_clv exactly 0
for col in ("odds_clv","line_clv","sharp_clv","sharp_odds_clv"):
    v=[fnum(r[col]) for r in R]; v=[x for x in v if x is not None]
    z=sum(1 for x in v if x==0)
    print(f"{col}: n={len(v)} exact-zero={z} ({z/len(v)*100:.1f}%)  mean={statistics.mean(v):+.4f} median={statistics.median(v):+.4f}")
