# xm_cross6.py - the two staking numbers that actually matter out of all this.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
L = load("bets_log.csv"); FIRE = {}
for r in L:
    pl = (r.get("player") or "").lower(); mk = r.get("market"); sd = r.get("side")
    src = r.get("src") or ""; ln = f(r.get("line")); od = f(r.get("odds")); cap = ts(r.get("captured_utc"))
    if not (pl and mk and sd and cap and ln is not None and od): continue
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, cap)
    if not gt: continue
    k = (src, pl, mk, gt); cur = FIRE.get(k)
    if cur is None or cap < cur["cap"]:
        FIRE[k] = dict(src=src, pl=pl, mk=mk, gt=gt, side=sd, line=ln, odds=od, cap=cap, date=r.get("date"), tm=tm)
ROWS = []
for k, v in FIRE.items():
    row = pgrow.get((v["pl"], v["gt"]))
    if not row: continue
    act = row.get(v["mk"])
    if act is None or act == v["line"]: continue
    won = (act > v["line"]) if v["side"] == "Over" else (act < v["line"])
    ROWS.append(dict(v, act=act, won=won, pnl=(v["odds"] - 1) if won else -1.0))
OVERF = {"cascade", "overshoot", "flip_paper", "flip", "hotover", "usgshock"}

# (1) two bets, same player, same game, DIFFERENT family. how often do they co-resolve?
pg = collections.defaultdict(list)
for r in ROWS: pg[(r["pl"], r["gt"])].append(r)
buck = collections.defaultdict(lambda: [0, 0])
for k, rs in pg.items():
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b_ = rs[i], rs[j]
            if a["src"] == b_["src"]: continue
            same_side = a["side"] == b_["side"]
            same_mk = a["mk"] == b_["mk"]
            lab = ("SAME side, " + ("same market" if same_mk else "different market")
                   if same_side else "OPPOSITE side, " + ("same market" if same_mk else "different market"))
            buck[lab][0] += 1
            if a["won"] == b_["won"]: buck[lab][1] += 1
print("CO-RESOLUTION of two bets from DIFFERENT families on the SAME player-game")
print("%-40s%7s%14s" % ("relationship", "pairs", "same result"))
for lab, (n, s) in sorted(buck.items(), key=lambda x: -x[1][0]):
    print("%-40s%7d%13.0f%%" % (lab, n, 100 * s / n))
# baseline: two bets, same side, DIFFERENT players, same slate
bydate = collections.defaultdict(list)
for r in ROWS: bydate[r["date"]].append(r)
n0 = s0 = 0
for d, rs in bydate.items():
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b_ = rs[i], rs[j]
            if a["pl"] == b_["pl"] or a["side"] != b_["side"] or a["src"] == b_["src"]: continue
            n0 += 1
            if a["won"] == b_["won"]: s0 += 1
print("%-40s%7d%13.0f%%" % ("baseline: same side, DIFFERENT players", n0, 100 * s0 / n0))

# (2) the self-hedge: player-games where the bot fired BOTH an over and an under
print("\nSELF-HEDGE: player-games where the bot fired an OVER and an UNDER on the same player")
hedge = []
for k, rs in pg.items():
    o = [r for r in rs if r["side"] == "Over"]; u = [r for r in rs if r["side"] == "Under"]
    if o and u:
        hedge.append((k, o, u))
allp = [r["pnl"] for k, o, u in hedge for r in o + u]
print("  %d player-games, %d bets, combined ROI %+.1f%%   (board margin is ~7%%, so a hedge burns it)"
      % (len(hedge), len(allp), 100 * statistics.mean(allp)))
same_mk = [(k, o, u) for k, o, u in hedge if set(x["mk"] for x in o) & set(x["mk"] for x in u)]
print("  of those, %d are OVER and UNDER on the SAME market = a literal middle/hedge" % len(same_mk))
for k, o, u in same_mk[:8]:
    print("    %-22s %s  O%.1f@%.2f (%s) vs U%.1f@%.2f (%s)  actual %.0f"
          % (k[0][:22], o[0]["mk"], o[0]["line"], o[0]["odds"], o[0]["src"],
             u[0]["line"], u[0]["odds"], u[0]["src"], o[0]["act"]))
# which side wins when the SAME market is contradicted?
if same_mk:
    ov = [r["pnl"] for k, o, u in same_mk for r in o]; un = [r["pnl"] for k, o, u in same_mk for r in u]
    print("  same-market contradictions: OVER side n=%d ROI %+.1f%% | UNDER side n=%d ROI %+.1f%%"
          % (len(ov), 100 * statistics.mean(ov), len(un), 100 * statistics.mean(un)))

# phi for the same-player pairs
def phi(v):
    xs=[a for a,b in v]; ys=[b for a,b in v]
    mx,my=statistics.mean(xs),statistics.mean(ys)
    n=sum((a-mx)*(b-my) for a,b in v)
    dx=math.sqrt(sum((a-mx)**2 for a in xs)); dy=math.sqrt(sum((b-my)**2 for b in ys))
    return n/(dx*dy) if dx and dy else 0.0
pairs=collections.defaultdict(list)
for k,rs in pg.items():
    for i in range(len(rs)):
        for j in range(i+1,len(rs)):
            a,b_=rs[i],rs[j]
            if a["src"]==b_["src"]: continue
            lab=("SAME side" if a["side"]==b_["side"] else "OPP side")+", "+("same mkt" if a["mk"]==b_["mk"] else "diff mkt")
            pairs[lab].append((1.0 if a["won"] else 0.0,1.0 if b_["won"] else 0.0))
print("\nphi (correlation of win indicators) for same-player-game cross-family pairs:")
for lab,v in sorted(pairs.items(), key=lambda x:-len(x[1])):
    print("  %-24s n=%4d  phi=%+.3f" % (lab,len(v),phi(v)))
