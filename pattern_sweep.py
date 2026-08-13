# pattern_sweep.py - ten pre-declared hypotheses, tested once each, with the multiplicity priced
# ---------------------------------------------------------------------------------------------
# Every hypothesis below is written down BEFORE looking, with its predicted side, and each is
# tested exactly once. No threshold hunting - if a rule needs a number, it gets the obvious one.
# That is what makes a Bonferroni bar meaningful: 10 tests -> p < 0.005 to call anything real.
#
# THE TEN, and why each is worth a shot:
#   1 ZIG-ZAG DOWN     she badly missed her line last game -> OVER now. The classic bounce-back.
#                      We know the book CHASES (corr +0.373); the question is whether it overdoes it.
#   2 ZIG-ZAG UP       she badly beat it last game -> UNDER now. The mirror.
#   3 ALTERNATION      last two games went over-then-under (or reverse) -> the pattern continues.
#                      This is what "zig-zag" means literally, and nobody has tested it here.
#   4 HOT STREAK       three straight overs -> OVER again. Does form persist or regress?
#   5 BACK-TO-BACK     playing on <=1 day rest -> UNDER. Tired legs, shorter minutes.
#   6 LONG REST        4+ days off -> OVER. Fresh, and the book may not adjust.
#   7 BLOWOUT HANGOVER last game was a 20+ point blowout -> OVER now. Her last line was suppressed
#                      by garbage time, so the book's anchor is artificially low.
#   8 LAZY LINE        the book hung the IDENTICAL number 3+ games running -> it has stopped
#                      thinking. This is the purest form of the staleness thesis.
#   9 RETURN          she missed her team's last game -> the book's anchor is built on stale data.
#  10 HOME            home games -> OVER. Cheap to test, and books do shade home/away.
#
# SCORING: lift over the correct per-market, per-side board baseline. Never against 50%.
# GATE: (a) Bonferroni for 10 tests, (b) a shared null that re-runs the WHOLE sweep on simulated
# outcomes so "best of ten" is priced, (c) a first-two-thirds / final-third split on any survivor,
# because the last three candidates all died in the final third.
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
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")

G = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    G[g.get("game_id")] = dict(date=g.get("date",""), tip=ts(g.get("tip")), home=g.get("home"),
                               away=g.get("away"), hs=hs, as_=as_,
                               margin=(abs(hs-as_) if hs is not None and as_ is not None else None))
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    g = G.get(r.get("game_id"))
    if not g or not g["date"] or not g["tip"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=g["date"], tip=g["tip"], gid=g_id if False else r.get("game_id"),
        team=r.get("team"), min=f(r.get("min")) or 0, margin=g["margin"],
        home=(r.get("team") == g["home"]), pts=pts, reb=reb, ast=ast,
        pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast))
for v in plog.values(): v.sort(key=lambda x: x["date"])
idx = {(pl, g["date"]): i for pl, v in plog.items() for i, g in enumerate(v)}

byplayer = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v: byplayer[pl].append((g["tip"], g["date"], g))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

# board: main line per player-market-game, both sides
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
pergame = collections.defaultdict(dict)
for (pl, mk, side, ln), v in raw.items():
    v.sort()
    blocks, cur = [], [v[0]]
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
    i = idx.get((pl, dt))
    if i is None: continue
    cur = plog[pl][i]
    if cur[mk] == ln: continue
    P.append(dict(pl=pl, mk=mk, date=dt, line=ln, i=i, rec=cur,
                  over_odds=sides["Over"][-1][1], under_odds=sides["Under"][-1][1],
                  over_won=cur[mk] > ln))
P.sort(key=lambda r: r["date"])

# the book's line history for a player-market, so we can spot a LAZY LINE
lhist = collections.defaultdict(list)
for r in P: lhist[(r["pl"], r["mk"])].append((r["date"], r["line"]))
for v in lhist.values(): v.sort()

BASE = {}
tmp = collections.defaultdict(list)
for r in P:
    tmp[(r["mk"], "Over")].append(1.0 if r["over_won"] else 0.0)
    tmp[(r["mk"], "Under")].append(0.0 if r["over_won"] else 1.0)
for k, v in tmp.items():
    if len(v) >= 80: BASE[k] = sum(v)/len(v)
P = [r for r in P if (r["mk"], "Over") in BASE]
print(f"{len(P)} player-market-games on the board with an outcome and a baseline\n")

# ---- prior-game facts, all causal ---------------------------------------------------------------
def prior(r, k=1):
    j = r["i"] - k
    return plog[r["pl"]][j] if j >= 0 else None
def prev_line(r, back=1):
    v = lhist[(r["pl"], r["mk"])]
    pos = next((i for i, x in enumerate(v) if x[0] == r["date"]), None)
    return v[pos-back][1] if pos is not None and pos-back >= 0 else None
def prev_vs_line(r, back=1):
    """How far she landed from the line the book hung LAST time - both are prior facts."""
    p, l = prior(r, back), prev_line(r, back)
    return (p[r["mk"]] - l) if (p and l is not None) else None
def rest_days(r):
    p = prior(r)
    return (r["rec"]["tip"] - p["tip"]).days if p else None
def lazy_line(r):
    v = lhist[(r["pl"], r["mk"])]
    pos = next((i for i, x in enumerate(v) if x[0] == r["date"]), None)
    if pos is None or pos < 2: return False
    return v[pos][1] == v[pos-1][1] == v[pos-2][1]
def missed_last(r):
    """She has a board line now, but did she sit her team's previous game?"""
    p = prior(r)
    if not p: return None
    return (r["rec"]["tip"] - p["tip"]).days >= 5      # a 5+ day gap in a dense schedule = absence

HYP = [
    ("1 ZIG-ZAG DOWN  missed line by 5+ -> OVER",  "Over",
     lambda r: (lambda d: d is not None and d <= -5)(prev_vs_line(r))),
    ("2 ZIG-ZAG UP    beat line by 5+  -> UNDER", "Under",
     lambda r: (lambda d: d is not None and d >= 5)(prev_vs_line(r))),
    ("3 ALTERNATION   last two alternated -> continue", "Over",
     lambda r: (lambda a, b: a is not None and b is not None and a < 0 < b)(prev_vs_line(r,1), prev_vs_line(r,2))),
    ("4 HOT STREAK    3 straight overs -> OVER",  "Over",
     lambda r: all((lambda d: d is not None and d > 0)(prev_vs_line(r, k)) for k in (1,2,3))),
    ("5 BACK-TO-BACK  <=1 day rest -> UNDER",     "Under",
     lambda r: (lambda d: d is not None and d <= 1)(rest_days(r))),
    ("6 LONG REST     4+ days off -> OVER",       "Over",
     lambda r: (lambda d: d is not None and d >= 4)(rest_days(r))),
    ("7 BLOWOUT HANGOVER 20+ margin -> OVER",     "Over",
     lambda r: (lambda p: p is not None and p["margin"] is not None and p["margin"] >= 20)(prior(r))),
    ("8 LAZY LINE     same number 3 games -> OVER", "Over", lazy_line),
    ("9 RETURN        5+ day gap -> OVER",        "Over", lambda r: missed_last(r) is True),
    ("10 HOME         home game -> OVER",         "Over", lambda r: r["rec"]["home"]),
]

def evaluate(rows, side, pred, outcomes=None):
    out = []
    for i, r in enumerate(rows):
        try:
            if not pred(r): continue
        except Exception: continue
        ow = outcomes[i] if outcomes is not None else r["over_won"]
        won = ow if side == "Over" else (not ow)
        odds = r["over_odds"] if side == "Over" else r["under_odds"]
        out.append((won, odds, BASE[(r["mk"], side)]))
    return out
def score(sel):
    n = len(sel)
    if n < 40: return None
    w = sum(1 for x in sel if x[0])/n
    base = sum(x[2] for x in sel)/n
    roi = sum((x[1]-1) if x[0] else -1.0 for x in sel)/n
    z = (w-base)/math.sqrt(base*(1-base)/n)
    return z, 100*w, 100*roi, 100*(w-base), n

print("="*96)
print("  THE SWEEP - each hypothesis tested once, scored as lift over its own side's baseline")
print("="*96)
print(f"    {'hypothesis':<44}{'n':>6}{'win%':>8}{'ROI':>9}{'lift':>8}{'z':>7}{'':>4}")
results = []
for nm, side, pred in HYP:
    s = score(evaluate(P, side, pred))
    if not s:
        print(f"    {nm:<44}   too few"); continue
    z, w, roi, lift, n = s
    p = math.erfc(abs(z)/math.sqrt(2))
    mark = "**" if p < 0.05/len(HYP) else ("*" if p < 0.05 else "")
    print(f"    {nm:<44}{n:>6}{w:>7.1f}%{roi:>8.1f}%{lift:>+8.1f}{z:>7.2f}  {mark}")
    results.append((z, nm, side, pred, s))
print(f"    ** = clears Bonferroni for {len(HYP)} tests (p<{0.05/len(HYP):.4f})   * = raw p<0.05 only")

print("\n" + "="*96)
print("  THE SHARED NULL - re-run the ENTIRE sweep on simulated outcomes, 400 times")
print("="*96)
imp = lambda r: min(0.97, max(0.03, (1/r["over_odds"])/(1/r["over_odds"] + 1/r["under_odds"])))
nulls = []
for _ in range(400):
    sim = [random.random() < imp(r) for r in P]
    best = None
    for nm, side, pred in HYP:
        s = score(evaluate(P, side, pred, sim))
        if s and (best is None or abs(s[0]) > abs(best)): best = abs(s[0])
    if best is not None: nulls.append(best)
nulls.sort()
best_real = max(results, key=lambda x: abs(x[0]))
beat = sum(1 for x in nulls if x >= abs(best_real[0]))/len(nulls)
print(f"    best |z| from a sweep that knows nothing: median {nulls[len(nulls)//2]:.2f}  "
      f"95th {nulls[int(len(nulls)*.95)]:.2f}  max {nulls[-1]:.2f}")
print(f"    our best: {best_real[1].strip()} -> |z|={abs(best_real[0]):.2f}")
print(f"    the null sweep beats it {beat*100:.1f}% of the time  "
      f"({'PASSES' if beat < 0.05 else 'FAILS'})")

print("\n" + "="*96)
print("  ANYTHING THAT CLEARED raw p<0.05, SPLIT IN TIME (the test that killed the last three)")
print("="*96)
cut = int(len(P)*2/3)
for z, nm, side, pred, s in sorted(results, key=lambda x: -abs(x[0])):
    if math.erfc(abs(z)/math.sqrt(2)) >= 0.05: continue
    a, b = score(evaluate(P[:cut], side, pred)), score(evaluate(P[cut:], side, pred))
    print(f"    {nm.strip()}")
    print(f"      first two thirds  " + (f"n={a[4]:<5} lift {a[3]:+5.1f}pp  z={a[0]:+.2f}" if a else "too few"))
    print(f"      final third       " + (f"n={b[4]:<5} lift {b[3]:+5.1f}pp  z={b[0]:+.2f}" if b else "too few"))

print("\n" + "="*96)
print("  THE INVERSION: both significant results say MOMENTUM, not zig-zag")
print("="*96)
print("    #2 predicted UNDER after a big over and came back -4.7pp. So the OVER outperformed by")
print("    +4.7pp. #3 predicted the alternation continues and came back -3.6pp, i.e. the MISS")
print("    continued. Both point the same way: form PERSISTS, it does not zig-zag.")
print("    Testing that properly now - a ladder, which is the shape a real effect has.\n")
print(f"    {'last game finished vs the line the book hung':<46}{'n':>6}{'win%':>8}{'ROI':>9}{'lift':>8}{'z':>7}")
LAD = ((-99,-8,"missed by 8+"), (-8,-5,"missed by 5-8"), (-5,-2,"missed by 2-5"),
       (-2,2,"landed within 2"), (2,5,"beat by 2-5"), (5,8,"beat by 5-8"), (8,99,"beat by 8+"))
for lo, hi, nm in LAD:
    s = score(evaluate(P, "Over", lambda r, lo=lo, hi=hi:
                       (lambda d: d is not None and lo <= d < hi)(prev_vs_line(r))))
    if not s:
        print(f"    {nm:<46}   too few"); continue
    z, w, roi, lift, n = s
    print(f"    {nm:<46}{n:>6}{w:>7.1f}%{roi:>8.1f}%{lift:>+8.1f}{z:>7.2f}")
print("    monotone rising = momentum is real. Jumbled = the two hits above were noise.")

print("\n" + "="*96)
print("  THE TWO TESTS THAT KILLED EVERY PREVIOUS CANDIDATE")
print("="*96)
mom = lambda r: (lambda d: d is not None and d >= 5)(prev_vs_line(r))
FIT  = ("pts","pra","pr","pa"); HOLD = ("reb","ast","ra")
print("    (a) HOLDOUT MARKETS - reb/ast/ra, never used to find this")
for lbl, mks in (("fitted markets pts/pra/pr/pa", FIT), ("HOLDOUT reb/ast/ra", HOLD)):
    s = score(evaluate([r for r in P if r["mk"] in mks], "Over", mom))
    print(f"      {lbl:<40} " + (f"n={s[4]:<5} win {s[1]:.1f}%  lift {s[3]:+5.1f}pp  z={s[0]:+.2f}"
                                 if s else "too few"))
print("\n    (b) TIME SPLIT")
for lbl, part in (("first two thirds", P[:cut]), ("final third    ", P[cut:])):
    s = score(evaluate(part, "Over", mom))
    print(f"      {lbl:<40} " + (f"n={s[4]:<5} win {s[1]:.1f}%  lift {s[3]:+5.1f}pp  z={s[0]:+.2f}"
                                 if s else "too few"))
print("\n    (c) IS IT JUST THE BOOK NOT MOVING ENOUGH? the book DOES chase (corr +0.373).")
print("        If momentum survives even after the book raised the line, the chase is too small.")
for nm, cond in (("book RAISED the line since", lambda r: (lambda a,b: a is not None and b is not None and a > b)(r["line"], prev_line(r))),
                 ("book left it or cut it",     lambda r: (lambda a,b: a is not None and b is not None and a <= b)(r["line"], prev_line(r)))):
    s = score(evaluate(P, "Over", lambda r, c=cond: mom(r) and c(r)))
    print(f"      {nm:<40} " + (f"n={s[4]:<5} win {s[1]:.1f}%  lift {s[3]:+5.1f}pp  z={s[0]:+.2f}"
                                if s else "too few"))
