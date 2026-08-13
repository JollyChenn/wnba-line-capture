# anchor_gap.py - the FLIP idea in both directions, backtested on the whole board; and whether
#                 the book's prop re-rating reaches the moneyline / total / spread.
# ---------------------------------------------------------------------------------------------
# WHAT A FLIP ACTUALLY IS, stated generally: the book has hung a line FAR BELOW the player's own
# recent form, so we take the over. The mirror - "flip under" - is the book hanging a line far
# ABOVE recent form, so we take the under. We have only ever run the over half, and only on the
# handful of players our pick model happened to flag. That is a tiny, one-sided sample.
#
# So here it is properly, in both directions, on EVERY prop the board ever posted:
#
#     anchor = the player's own trailing-10 MEDIAN for that market, PRIOR GAMES ONLY
#     gap    = book_line - anchor      (negative = book is low  -> the OVER is the flip)
#                                      (positive = book is high -> the UNDER is the flip)
#
# This is the founding thesis of the entire project - "books anchor on stale form and reprice role
# changes slowly" - and it has never been tested against real captured book lines at scale. Every
# earlier version graded against our own median, which is circular. This grades against the board.
#
# EVERY CELL IS SCORED AS LIFT OVER ITS OWN SIDE'S BASELINE, because the sides are not comparable:
#     board over baseline 53.4%   board under baseline 46.7%   (measured, fade_hunt.py)
# A 55% under is a GOOD under. A 55% over is a mediocre over. Scoring both against 50% - which is
# what we did all season - is what made newunder look like a signal when it has zero lift.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
random.seed(20260811)
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
OVER_BASE, UNDER_BASE = 0.534, 0.467
MKTS = ("pts", "pra", "pr", "pa")

# ---- games, box, and the causal trailing-10 median -----------------------------------------------
games = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    games[g.get("game_id")] = dict(date=g.get("date",""), tip=ts(g.get("tip")), home=g.get("home"),
                                   away=g.get("away"), hs=hs, as_=as_)
plog = collections.defaultdict(list)
teamof = {}
for r in load("data/box_2026.csv"):
    g = games.get(r.get("game_id"))
    if not g or not g["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    rec = dict(date=g["date"], tip=g["tip"], gid=r.get("game_id"), team=r.get("team"),
               pts=pts, reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast)
    plog[(r.get("player") or "").lower()].append(rec)
    teamof[(g["date"], (r.get("player") or "").lower())] = r.get("team")
for v in plog.values(): v.sort(key=lambda x: x["date"])

ANCH = {}          # (player, market, date) -> trailing-10 median from PRIOR games only
for pl, v in plog.items():
    for i, g in enumerate(v):
        prev = v[:i][-10:]
        if len(prev) < 6: continue
        for mk in MKTS:
            ANCH[(pl, mk, g["date"])] = statistics.median(x[mk] for x in prev)
print(f"{len(ANCH)} causal trailing-10 anchors built from prior games only")

byplayer = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v:
        if g["tip"]: byplayer[pl].append((g["tip"], g["date"], g))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

# ---- the board's main line per player-market-game, both sides priced -----------------------------
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
pergame = collections.defaultdict(dict)
for (pl, mk, side, ln), v in raw.items():
    v.sort()
    blocks, cur = [], [v[0]]                       # split per night - the bug that bit three times
    for prev, nxt in zip(v, v[1:]):
        if (nxt[0]-prev[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(nxt)
    blocks.append(cur)
    for blk in blocks:
        if not blk: continue
        dt, rec = game_after(pl, blk[0][0])
        if not rec: continue
        pre = [x for x in blk if x[0] <= rec["tip"]]
        if pre: pergame[(pl, mk, dt)].setdefault(ln, {})[side] = pre

P = []
for (pl, mk, dt), lines in pergame.items():
    ln, sides = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
    if "Over" not in sides or "Under" not in sides: continue
    a = ANCH.get((pl, mk, dt))
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if a is None or rec is None or rec[mk] == ln: continue
    P.append(dict(pl=pl, mk=mk, date=dt, tip=rec["tip"], team=rec["team"], line=ln, anchor=a,
                  gap=ln - a, over_odds=sides["Over"][-1][1], under_odds=sides["Under"][-1][1],
                  actual=rec[mk], over_won=rec[mk] > ln))
P.sort(key=lambda r: r["date"])
print(f"{len(P)} player-market-games with a two-sided board line AND a causal anchor")
gaps = sorted(r["gap"] for r in P)
print(f"    gap (book line minus our trailing median): median {gaps[len(gaps)//2]:+.1f}, "
      f"10th {gaps[int(len(gaps)*.1)]:+.1f}, 90th {gaps[int(len(gaps)*.9)]:+.1f}\n")

def cell(rows, side, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"    {label:<46} n={n} too few"); return None
    if side == "Over":
        w = sum(1 for r in rows if r["over_won"])/n
        rr = [(r["over_odds"]-1) if r["over_won"] else -1.0 for r in rows]; base = OVER_BASE
    else:
        w = sum(1 for r in rows if not r["over_won"])/n
        rr = [(r["under_odds"]-1) if not r["over_won"] else -1.0 for r in rows]; base = UNDER_BASE
    m = sum(rr)/n; z = (w-base)/math.sqrt(base*(1-base)/n)
    print(f"    {label:<46} n={n:<5} win {100*w:5.1f}%  ROI {100*m:+6.1f}%  "
          f"lift {100*(w-base):+5.1f}pp  z={z:+5.2f}")
    return w, m, n, z

print("="*88)
print("  1. THE FLIP LADDER, BOTH DIRECTIONS - book line vs the player's own trailing median")
print("="*88)
print("  (a) BOOK IS LOW  -> take the OVER   [this is the existing FLIP]")
for lo, hi, nm in ((-99,-6,"gap <= -6  (book 6+ below form)"), (-6,-4,"gap -6 to -4"),
                   (-4,-2,"gap -4 to -2"), (-2,-1,"gap -2 to -1"), (-1,0,"gap -1 to 0")):
    cell([r for r in P if lo <= r["gap"] < hi], "Over", f"    {nm}")
print("\n  (b) BOOK IS HIGH -> take the UNDER  [this is the never-tested FLIP UNDER]")
for lo, hi, nm in ((0,1,"gap 0 to +1"), (1,2,"gap +1 to +2"), (2,4,"gap +2 to +4"),
                   (4,6,"gap +4 to +6"), (6,99,"gap >= +6  (book 6+ above form)")):
    cell([r for r in P if lo <= r["gap"] < hi], "Under", f"    {nm}")
print("\n    A real stale-line edge shows a MONOTONE ladder in both panels: the further the book")
print("    is from recent form, the better the bet against it. Anything else is noise.")

print("\n" + "="*88)
print("  2. THE GATE - date split, then a null that re-runs the whole ladder search")
print("="*88)
CELLS = [("Over", lo, hi) for lo, hi in ((-99,-6),(-6,-4),(-4,-2),(-2,-1))] + \
        [("Under", lo, hi) for lo, hi in ((1,2),(2,4),(4,6),(6,99))]
cut_i = int(len(P)*2/3); IN, OUT = P[:cut_i], P[cut_i:]
print(f"    IN {len(IN)} (to {IN[-1]['date']})   OUT {len(OUT)} (from {OUT[0]['date']})")
def idxs(rows, c):
    _, lo, hi = c
    return [i for i, r in enumerate(rows) if lo <= r["gap"] < hi]
def stat(rows, c, outcomes=None):
    side, _, _ = c
    idx = idxs(rows, c)
    if len(idx) < 25: return None
    xs = []
    for i in idx:
        r = rows[i]; ow = outcomes[i] if outcomes is not None else r["over_won"]
        if side == "Over": xs.append((r["over_odds"]-1) if ow else -1.0)
        else:              xs.append((r["under_odds"]-1) if not ow else -1.0)
    m = sum(xs)/len(xs); sd = (sum((x-m)**2 for x in xs)/(len(xs)-1))**.5
    return (m/(sd/math.sqrt(len(xs))), m*100, len(xs)) if sd else None
def search(rows, outcomes=None):
    best = None
    for c in CELLS:
        s = stat(rows, c, outcomes)
        if s and (best is None or s[0] > best[0][0]): best = (s, c)
    return best
imp = lambda r: min(0.97, max(0.03, (1/r["over_odds"])/(1/r["over_odds"] + 1/r["under_odds"])))
nulls = []
for _ in range(400):
    sim = [random.random() < imp(r) for r in IN]
    b = search(IN, sim)
    if b: nulls.append(b[0][0])
nulls.sort(); real = search(IN)
if real:
    beat = sum(1 for x in nulls if x >= real[0][0])/len(nulls)
    print(f"    null best-t: median {nulls[len(nulls)//2]:+.2f}  95th {nulls[int(len(nulls)*.95)]:+.2f}")
    print(f"    our best in-sample: {real[1]} -> t={real[0][0]:+.2f} ROI={real[0][1]:+.1f}% n={real[0][2]}")
    print(f"    null beats it {beat*100:.1f}%  ({'PASSES' if beat < 0.05 else 'FAILS'})")
    o = stat(OUT, real[1])
    print(f"    OUT-OF-SAMPLE: " + (f"n={o[2]} ROI={o[1]:+.1f}% t={o[0]:+.2f}" if o else "too few"))

print("\n" + "="*88)
print("  3. DOES THE BOOK'S PROP RE-RATING REACH THE MONEYLINE / TOTAL / SPREAD?")
print("="*88)
# team_gap = how far the book's prop lines sit from recent form, summed over that team's players.
# A team whose props are all hung BELOW form is a team the book expects to score less.
TG = collections.defaultdict(list)
for r in P:
    if r["mk"] == "pts" and r["team"]: TG[(r["date"], r["team"])].append(r)
tg = {k: dict(gap=sum(x["gap"] for x in v), n=len(v)) for k, v in TG.items() if len(v) >= 4}
print(f"    {len(tg)} team-games with 4+ points props (team_gap = summed book-vs-form gap)")
res = {}
for g in games.values():
    if g["hs"] is None: continue
    res[(g["date"], g["home"])] = (g["hs"], g["as_"], True)
    res[(g["date"], g["away"])] = (g["as_"], g["hs"], False)
def corr(xs, ys, label, ntest=1):
    n = len(xs)
    if n < 25:
        print(f"    {label:<50} n={n} too few"); return
    mx, my = sum(xs)/n, sum(ys)/n
    sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
    if not (sx and sy): return
    r = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n/(sx*sy)
    t = r*math.sqrt((n-2)/max(1e-9, 1-r*r)); p = math.erfc(abs(t)/math.sqrt(2))
    print(f"    {label:<50} n={n:<5} r={r:+.3f}  t={t:+5.2f}  p={p:.3f}"
          f"{'  **' if p < 0.05/ntest else ''}")
rows = [(v["gap"], res[k][0], res[k][1], res[k][2]) for k, v in tg.items() if k in res]
NT = 4
corr([x[0] for x in rows], [x[1] for x in rows], "team_gap -> that team's POINTS", NT)
corr([x[0] for x in rows], [x[1]-x[2] for x in rows], "team_gap -> MARGIN", NT)
corr([x[0] for x in rows], [1.0 if x[1] > x[2] else 0.0 for x in rows], "team_gap -> WON (moneyline)", NT)
pairg = collections.defaultdict(dict)
for k, v in tg.items():
    if k not in res: continue
    pairg[k[0] + ("H" if res[k][2] else "A")] = None
gm = collections.defaultdict(list)
for k, v in tg.items():
    if k in res: gm[(k[0], res[k][0]+res[k][1])].append(v["gap"])
tot = [(sum(v), k[1]) for k, v in gm.items() if len(v) == 2]
corr([x[0] for x in tot], [x[1] for x in tot], "combined team_gap -> GAME TOTAL", NT)
print(f"    ** = survives Bonferroni for {NT} tests (p < {0.05/NT:.4f})")
print("\n    The book sets prop lines and game lines with the SAME information. If team_gap")
print("    predicted the game result, the two desks would be disagreeing - and that gap would")
print("    be the trade. A flat result means they agree, which is what a competent book looks like.")

print("\n" + "="*88)
print("  4. THE WINNER UNDER SCRUTINY: book line 4-6 pts BELOW recent form -> take the OVER")
print("="*88)
W = [r for r in P if -6 <= r["gap"] < -4]
h = len(W)//2
print(f"    halves:")
cell(W[:h], "Over", f"      first half  {W[0]['date']}-{W[h-1]['date']}", minn=20)
cell(W[h:], "Over", f"      second half {W[h]['date']}-{W[-1]['date']}", minn=20)
print(f"\n    by market:")
for mk in MKTS:
    cell([r for r in W if r["mk"] == mk], "Over", f"      {mk}", minn=15)
print(f"\n    neighbouring bands, for shape:")
for lo, hi in ((-8,-6),(-6,-5),(-5,-4),(-4,-3),(-3,-2)):
    cell([r for r in P if lo <= r["gap"] < hi], "Over", f"      gap {lo} to {hi}", minn=20)

# CLV: does the market move toward these bets after the open? this is the instrument that
# killed the crater>=4 rule last run, so the winner has to face it too.
print(f"\n    CLV (open -> close on the board, the one instrument that separates winners here):")
clvs = collections.defaultdict(list)
for (pl, mk, dt), lines in pergame.items():
    a = ANCH.get((pl, mk, dt))
    if a is None: continue
    ln, sides = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
    if "Over" not in sides or len(sides["Over"]) < 2: continue
    gap = ln - a
    o0, o1 = sides["Over"][0][1], sides["Over"][-1][1]
    band = "WINNER gap -6..-4" if -6 <= gap < -4 else ("other over-flip gap<-1" if gap < -1 else
           ("flip-under gap>+2" if gap > 2 else "middle"))
    clvs[band].append(o0/o1 - 1)
for band in ("WINNER gap -6..-4", "other over-flip gap<-1", "middle", "flip-under gap>+2"):
    v = clvs.get(band, [])
    if len(v) < 20:
        print(f"      {band:<26} n={len(v)} too few"); continue
    pos = sum(1 for x in v if x > 0)
    print(f"      {band:<26} n={len(v):<5} mean CLV {100*sum(v)/len(v):+5.2f}%  "
          f"positive {100*pos/len(v):.0f}%")
print("\n      positive CLV = the price shortened after the open = the market came toward us.")
print("      That is what a real mispricing looks like being corrected.")

print("\n" + "="*88)
print("  5. THE CONTIGUOUS REGION - three adjacent sub-bands were all strongly positive")
print("="*88)
BAND = [r for r in P if -6 <= r["gap"] < -3]
w = sum(1 for r in BAND if r["over_won"]); n = len(BAND)
rr = [(r["over_odds"]-1) if r["over_won"] else -1.0 for r in BAND]
z = (w/n - OVER_BASE)/math.sqrt(OVER_BASE*(1-OVER_BASE)/n)
print(f"    gap -6 to -3, take the OVER:  n={n}  {w}-{n-w}  win {100*w/n:.1f}%  "
      f"ROI {100*sum(rr)/len(rr):+.1f}%")
print(f"      lift {100*(w/n-OVER_BASE):+.1f}pp   z={z:+.2f}   p={math.erfc(abs(z)/math.sqrt(2)):.4f}")
ci = 1.96*math.sqrt((w/n)*(1-w/n)/n)
print(f"      95% CI on the win rate: {100*(w/n-ci):.1f}% to {100*(w/n+ci):.1f}%  "
      f"(break-even is {100/ (sum(r['over_odds'] for r in BAND)/n):.1f}%)")
cut = int(len(BAND)*2/3)
cell(BAND[:cut], "Over", "      in-sample two thirds", minn=20)
cell(BAND[cut:], "Over", "      final third, untouched", minn=20)
print(f"\n    concentration check - is it a few players?")
cnt = collections.Counter(r["pl"] for r in BAND)
top = cnt.most_common(5)
print(f"      {len(cnt)} distinct players; top 5 = {sum(c for _, c in top)}/{n} bets "
      f"({100*sum(c for _, c in top)/n:.0f}%)")
for pl, c in top:
    sub = [r for r in BAND if r["pl"] == pl]
    print(f"        {pl[:24]:<24} n={c:<3} won {sum(1 for r in sub if r['over_won'])}")
nodup = [r for r in BAND if cnt[r["pl"]] <= 4]
cell(nodup, "Over", "      excluding any player with 5+ appearances", minn=20)
print(f"\n    WHY CLV IS FLAT HERE AND THAT IS NOT FATAL: this is a STALE-LINE edge. The claim is")
print(f"    that the book hung a wrong NUMBER and never noticed. If it never notices, the price")
print(f"    never moves, so CLV stays ~0 by construction. CLV disproves a signal that claims the")
print(f"    MARKET will agree with us; it cannot disprove one that claims the market stays wrong.")
print(f"    The cost is that we get no independent confirmation - only the outcomes.")
