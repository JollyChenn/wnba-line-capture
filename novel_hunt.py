# novel_hunt.py - four mechanisms never tested here, sharing nothing with the old filters.
# ---------------------------------------------------------------------------------------------
#  A  MILESTONE LINES. Players fight for round numbers - 10 points, 20 points, 10 rebounds
#     (the double-double). A line at 9.5 or 19.5 sits directly UNDER a milestone: the player has
#     a private incentive to clear it that a stat model does not price. Documented in the NBA
#     (the 10-assist hunt). Cells: lines X9.5/X.5-under-milestone vs lines just OVER a milestone
#     (10.5, 20.5) where the incentive works against the over.
#  B  TRADER ATTENTION. A 6-game slate has 3x the lines of a 2-game slate but not 3x the traders.
#     Errors should concentrate on big slates. Cell: overs/unders by slate size; if attention is
#     real, EXTREME lines (very deep or very high vs her norm) misprice more on big nights.
#  C  FORGOTTEN LINES. Between open and ping the book moves lines as news arrives. If most of her
#     TEAMMATES' lines moved tonight but HERS did not, the book updated the game and skipped her.
#     Bet her in the direction of the team's aggregate move. Propagation family, internal to the
#     book itself - not tested anywhere in 40+ scripts.
#  D  STAR-RETURN FADE. When a 25+ minute player returns from a 3+ game absence, her teammates'
#     recent stats are inflated by the feast games without her - and a trailing-window line keeps
#     that inflation for several games. Fade (UNDER) teammates whose lines sit above their
#     WITH-star baseline on the return night. The mirror of cascade, which only handles the OUT.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260823)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
gof, oppof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid; oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm
# board walks for the forgotten-line feature
walk = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, t)
    if gt: walk[(pl, mk, gt)].append((t, ln, o))
for v in walk.values(): v.sort()
# star absences/returns from the box: 25+ min players, gaps of 3+ team games
absret = []                                   # (team, return_gt, star)
for pl, g in hist.items():
    if len(g) < 8: continue
    mins = statistics.median(r["min"] for r in g[-12:])
    if mins < 25: continue
    tm = g[-1]["tm"]
    played = {r["tip"] for r in g if r["tm"] == tm}
    sched = tips_of.get(tm, [])
    for i, t in enumerate(sched):
        if t not in played: continue
        j = i - 1; missed = 0
        while j >= 0 and sched[j] not in played: missed += 1; j -= 1
        if missed >= 3 and j >= 0: absret.append((tm, t, pl))
ret_nights = collections.defaultdict(set)
for tm, t, star in absret: ret_nights[(tm, t)].add(star)

Q = []
for (pl, mk, gt), sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    # forgotten-line: did her line move tonight? did her teammates'?
    q = walk.get((pl, mk, gt), [])
    mymove = (q[-1][1] - q[0][1]) if len(q) >= 2 else None
    mates = []
    for (p2, m2, g2), qq in walk.items():
        if g2 != gt or p2 == pl or teamof.get(p2) != tm or m2 != mk: continue
        if len(qq) >= 2 and abs(qq[-1][1] - qq[0][1]) > 0.01:
            mates.append(qq[-1][1] - qq[0][1])
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, ln=ln,
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  mymove=mymove, nmoved=len(mates),
                  matedir=(statistics.mean(mates) if len(mates) >= 2 else None),
                  ret=(gt in {t for (tm2, t) in ret_nights if tm2 == tm}
                       and pl not in ret_nights.get((tm, gt), set()))))
slsize = collections.Counter()
for r in Q: slsize[r["gt"].date()] = len({x["gid"] for x in Q if x["gt"].date() == r["gt"].date()})
for r in Q: r["slate_n"] = slsize[r["gt"].date()]
print(f"{len(Q)} quotes; {len(absret)} star-return nights detected; "
      f"slate sizes seen: {sorted(set(slsize.values()))}")
def ret_(r, s): return ((r[s+"_od"]-1) if r[s+"_won"] else -1.0)
def roi(rows, s): return 100*sum(ret_(r, s) for r in rows)/len(rows) if rows else 0.0
def hitr(rows, s): return 100*sum(1 for r in rows if r[s+"_won"])/len(rows) if rows else 0.0
def pboot(rows, s, T=2000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bp[p]], s))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
CELLS = [
    ("A line 9.5/19.5/29.5 pts-ish (chase UP) OVER",
     lambda r: r["mk"] in ("pts", "pr", "pra") and (r["ln"] % 10) == 9.5, "o"),
    ("A line 10.5/20.5/30.5 (milestone passed) UNDER",
     lambda r: r["mk"] in ("pts", "pr", "pra") and (r["ln"] % 10) == 0.5 and r["ln"] > 5, "u"),
    ("A reb/ra line at 9.5 (double-double chase) OVER",
     lambda r: r["mk"] in ("reb", "ra") and r["ln"] == 9.5, "o"),
    ("A control: mid-decade lines (4.5/5.5/14.5...) OVER",
     lambda r: r["mk"] in ("pts", "pr", "pra") and (r["ln"] % 10) in (4.5, 5.5), "o"),
    ("B small slate (1-2 games): OVER", lambda r: r["slate_n"] <= 2, "o"),
    ("B big slate (4+ games): OVER", lambda r: r["slate_n"] >= 4, "o"),
    ("B big slate: UNDER", lambda r: r["slate_n"] >= 4, "u"),
    ("C team moved UP, she did not: OVER (stale low)",
     lambda r: r["matedir"] is not None and r["matedir"] >= 0.75
               and r["mymove"] is not None and abs(r["mymove"]) < 0.01, "o"),
    ("C team moved DOWN, she did not: UNDER (stale high)",
     lambda r: r["matedir"] is not None and r["matedir"] <= -0.75
               and r["mymove"] is not None and abs(r["mymove"]) < 0.01, "u"),
    ("C control: she moved WITH the team: OVER",
     lambda r: r["matedir"] is not None and r["matedir"] >= 0.75
               and r["mymove"] is not None and r["mymove"] >= 0.5, "o"),
    ("D star-return night, teammates: UNDER", lambda r: r["ret"], "u"),
    ("D star-return night, teammates: OVER (control)", lambda r: r["ret"], "o"),
]
peaks = []
for _ in range(1000):
    pool = [(r["o_won"], r["u_won"]) for r in Q]; random.shuffle(pool)
    for r, x in zip(Q, pool): r["_o"], r["_u"] = x
    best = -99
    for lbl, sel, s in CELLS:
        g = [r for r in Q if sel(r)]
        if len(g) < 50: continue
        best = max(best, 100*sum((r[s+"_od"]-1) if r["_"+s] else -1.0 for r in g)/len(g))
    if best > -99: peaks.append(best)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("")
print("="*104)
print(f"  NOISE CEILING FIRST: {len(CELLS)} declared cells -> p95 best {CEIL:+.1f}%  (min n=50)")
print("="*104)
res = []
for lbl, sel, s in CELLS:
    g = [r for r in Q if sel(r)]
    if len(g) < 50:
        print(f"    {lbl:<52} n={len(g)} too few"); continue
    lo, hi = pboot(g, s)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<52} n={len(g):<5}{hitr(g,s):>6.1f}%{roi(g,s):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
    res.append((roi(g, s), lbl))
print("")
win = [x for x in res if x[0] > CEIL]
print("  ABOVE THE CEILING: " + (", ".join(f"{l} ({v:+.1f}%)" for v, l in sorted(win, reverse=True)) if win else "none"))
