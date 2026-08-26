# Q5 artifact check: is "the book shades concentrated scorers' lines up" real, or just the
# half-point grid on small lines?  linegap = line - trailing team-filtered median.
import csv, os, sys, math, random, statistics, datetime, collections, json
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
R = json.load(open(os.path.join(D, "tim_rows.json")))
SCOR = ("pts", "pra", "pr", "pa")
byp = collections.defaultdict(list)
for r in R: byp[r["pl"]].append(r)
for v in byp.values(): v.sort(key=lambda x: x["gt"])
FEAT0 = {p: dict(h1share=v[0]["h1share"], q4share=v[0]["q4share"], qconc=v[0]["qconc"],
                 q4app=v[0]["q4app"], cv=v[0]["cv"]) for p, v in byp.items()}
for r in R: r.update(FEAT0[r["pl"]])
hist_t = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): hist_t[pl].append(row)
for v in hist_t.values(): v.sort(key=lambda x: x["tip"])
rows = []
for r in R:
    if r["mk"] not in SCOR: continue
    gt = datetime.datetime.fromisoformat(r["gt"])
    prior = [x for x in hist_t.get(r["pl"], []) if x["tip"] < gt and x["tm"] == r["tm"]]
    if len(prior) < 5: continue
    med = statistics.median(x[r["mk"]] for x in prior[-10:])
    q = dict(r); q["med"] = med; q["linegap"] = r["line"] - med
    rows.append(q)
def rankv(a):
    n = len(a); d = [0.0]*n; o = sorted(range(n), key=lambda i: a[i]); i = 0
    while i < n:
        j = i
        while j+1 < n and a[o[j+1]] == a[o[i]]: j += 1
        rk = (i+j)/2+1
        for k in range(i, j+1): d[o[k]] = rk
        i = j+1
    return d
def sprho(u, v):
    ru, rv = rankv(u), rankv(v); n = len(u); mu = (n+1)/2
    su = math.sqrt(sum((x-mu)**2 for x in ru)); sv = math.sqrt(sum((x-mu)**2 for x in rv))
    return sum((a-mu)*(b-mu) for a, b in zip(ru, rv))/(su*sv) if su and sv else 0.0
print("scoring-market rows with trailing median: %d" % len(rows))
print("rho(linegap, line level)  = %+0.3f   rho(linegap, qconc) = %+0.3f   rho(linegap, q4app) = %+0.3f"
      % (sprho([r["linegap"] for r in rows], [r["line"] for r in rows]),
         sprho([r["linegap"] for r in rows], [r["qconc"] for r in rows]),
         sprho([r["linegap"] for r in rows], [r["q4app"] for r in rows])))
print("\nmean linegap by line tertile (the half-point-grid artifact):")
lv = sorted(r["line"] for r in rows); l1, l2 = lv[len(lv)//3], lv[2*len(lv)//3]
for tl, tf in (("lineLO", lambda r: r["line"] < l1), ("lineMD", lambda r: l1 <= r["line"] < l2), ("lineHI", lambda r: r["line"] >= l2)):
    g = [r for r in rows if tf(r)]
    print("   %-7s n=%-5d mean linegap %+0.3f  mean line %.1f" % (tl, len(g), statistics.mean(x["linegap"] for x in g), statistics.mean(x["line"] for x in g)))
print("\nrho(linegap, qconc) WITHIN line tertiles  (if it collapses, Q5 was the grid, not timing):")
for tl, tf in (("lineLO", lambda r: r["line"] < l1), ("lineMD", lambda r: l1 <= r["line"] < l2), ("lineHI", lambda r: r["line"] >= l2)):
    g = [r for r in rows if tf(r)]
    print("   %-7s n=%-5d rho(linegap,qconc) %+0.3f   rho(linegap,h1share) %+0.3f   rho(linegap,q4share) %+0.3f" % (
        tl, len(g), sprho([r["linegap"] for r in g], [r["qconc"] for r in g]),
        sprho([r["linegap"] for r in g], [r["h1share"] for r in g]),
        sprho([r["linegap"] for r in g], [r["q4share"] for r in g])))
print("\ndone")

# addendum: is the linegap~qconc link just mean-minus-median skew?
sk = []
for r in rows:
    gt = datetime.datetime.fromisoformat(r["gt"])
    prior = [x for x in hist_t.get(r["pl"], []) if x["tip"] < gt and x["tm"] == r["tm"]][-10:]
    if len(prior) < 5: continue
    vals = [x[r["mk"]] for x in prior]
    r["skew"] = statistics.mean(vals) - statistics.median(vals)
    sk.append(r)
print("ADDENDUM n=%d  rho(qconc, mean-minus-median skew) = %+0.3f   rho(linegap, skew) = %+0.3f"
      % (len(sk), sprho([r["qconc"] for r in sk], [r["skew"] for r in sk]),
         sprho([r["linegap"] for r in sk], [r["skew"] for r in sk])))
resid = [r["linegap"] - r["skew"] for r in sk]
print("        rho(linegap MINUS skew, qconc) = %+0.3f" % sprho(resid, [r["qconc"] for r in sk]))
