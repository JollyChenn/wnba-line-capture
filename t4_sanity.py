import json, os, sys, collections, statistics, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(D, "outputs", "t4_base.json")))
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")

def roi(bets, pk="over"):
    if not bets: return 0.0, 0, 0
    p = sum((b[pk]-1) if b["actual"] > b["line"] else (0.0 if b["actual"] == b["line"] else -1.0) for b in bets)
    w = sum(1 for b in bets if b["actual"] > b["line"])
    return p/len(bets), len(bets), w

def onepos(rows):
    best = {}
    for r in rows:
        k = (r["pl"], r["date"])
        if k not in best or r["mk"] < best[k]["mk"]: best[k] = r
    return list(best.values())

for lab, prickey, linekey in (("LATE(t-1h)", "over", "line"), ("OPEN", "oover", "oline")):
    cand = [r for r in R if any(s in SIGS for s in r["srcs"]) and r["mk"] in BM]
    print(lab, "candidates", len(cand))
    ms = [r for r in cand if r["prev"] is not None and r[linekey] - r["prev"] < 0.5]
    ms = onepos(ms)
    bb = [dict(over=r[prickey], actual=r["actual"], line=r[linekey], **{k: r[k] for k in ("pl","date","gt","mk","tm")}) for r in ms]
    v, n, w = roi(bb)
    print("  MODEL_S  n=%d  W=%d (%.1f%%)  ROI %+.1f%%  games=%d" % (n, w, 100*w/max(n,1), 100*v, len(set(b["gt"] for b in bb))))
    rej = [r for r in cand if r["prev"] is not None and r[linekey] - r["prev"] >= 0.5]
    rej = onepos(rej)
    bb2 = [dict(over=r[prickey], actual=r["actual"], line=r[linekey]) for r in rej]
    v2, n2, w2 = roi(bb2)
    print("  REJECT   n=%d  W=%d  ROI %+.1f%%" % (n2, w2, 100*v2))
    npv = onepos([r for r in cand if r["prev"] is None])
    bb3 = [dict(over=r[prickey], actual=r["actual"], line=r[linekey]) for r in npv]
    v3, n3, w3 = roi(bb3)
    print("  NOPREV   n=%d  ROI %+.1f%%" % (n3, 100*v3))
    # by month
    for m in ("202606", "202607", "202608"):
        sub = [b for b in bb if b["date"][:6] == m]
        v4, n4, w4 = roi(sub)
        print("     %s n=%-3d ROI %+.1f%%" % (m, n4, 100*v4))
    print("")

# board-wide base rates
allb = [dict(over=r["over"], actual=r["actual"], line=r["line"]) for r in R]
v, n, w = roi(allb)
print("FULL BOARD over: n=%d win%% %.1f  ROI %+.1f%%" % (n, 100*w/n, 100*v))
u = sum((r["under"]-1) if r["actual"] < r["line"] else (0.0 if r["actual"] == r["line"] else -1.0) for r in R)/len(R)
print("FULL BOARD under ROI %+.1f%%" % (100*u))
print("mean over odds %.3f  mean under odds %.3f  implied margin %.2f%%" % (
    statistics.mean(r["over"] for r in R), statistics.mean(r["under"] for r in R),
    100*(statistics.mean(1/r["over"] for r in R) + statistics.mean(1/r["under"] for r in R) - 1)))
print("push rate %.2f%%" % (100*sum(1 for r in R if r["actual"] == r["line"])/len(R)))
