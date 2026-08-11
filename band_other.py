# band_other.py - the band on markets it was never fitted to, and on anchors it was never fitted with
# ---------------------------------------------------------------------------------------------
# The signal was found on pts / pra / pr / pa. The board also carries REB (5515 rows), AST (3296)
# and RA (5914) which have never been touched by any test this season. That makes them a real
# holdout: if "the book hangs a stale low number and the over is cheap" is a true statement about
# how this book works, it should show up there too. If it only exists on the four markets it was
# discovered on, it is a property of the search, not of the book.
#
# ONE THING MUST BE FIXED FIRST. The band is "3 to 6 points below the trailing median". On a
# points line of 14 that is a 21-43% discount. On a REBOUNDS line of 6 the same 3-6 points is
# physically impossible - the line would have to be negative. So the band has to be expressed in
# RELATIVE terms and translated across:
#
#     gap_pct = (book_line - anchor) / anchor
#
# SECOND TEST - ANCHOR ROBUSTNESS. "trailing-10 MEDIAN" was never justified, it is just what the
# model always used. A real effect should survive swapping it for a mean, or a 5-game window. If
# the edge only exists at one exact anchor definition, it is a knife-edge and therefore luck.
import csv, os, sys, math, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
FIT  = ("pts", "pra", "pr", "pa")          # where the band was found
HOLD = ("reb", "ast", "ra")                # never used by any test this season
ALL  = FIT + HOLD

games = {g.get("game_id"): dict(date=g.get("date",""), tip=ts(g.get("tip")))
         for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    g = games.get(r.get("game_id"))
    if not g or not g["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=g["date"], tip=g["tip"],
        pts=pts, reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast))
for v in plog.values(): v.sort(key=lambda x: x["date"])

def build_anchor(kind, win):
    A = {}
    for pl, v in plog.items():
        for i, g in enumerate(v):
            prev = v[:i][-win:]
            if len(prev) < min(5, win): continue   # a 5-game window can never have 6 priors
            for mk in ALL:
                vals = [x[mk] for x in prev]
                A[(pl, mk, g["date"])] = statistics.median(vals) if kind == "median" else sum(vals)/len(vals)
    return A
ANCH = build_anchor("median", 10)

byplayer = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v:
        if g["tip"]: byplayer[pl].append((g["tip"], g["date"], g))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in ALL:
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

def universe(anchors):
    out = []
    for (pl, mk, dt), lines in pergame.items():
        ln, sides = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
        if "Over" not in sides: continue
        a = anchors.get((pl, mk, dt))
        rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
        if a is None or a <= 0 or rec is None or rec[mk] == ln: continue
        out.append(dict(pl=pl, mk=mk, date=dt, line=ln, anchor=a, gap=ln-a, gap_pct=(ln-a)/a,
                        odds=sides["Over"][-1][1], over_won=rec[mk] > ln))
    return sorted(out, key=lambda r: r["date"])
U = universe(ANCH)
print(f"{len(U)} over-props with a causal anchor across all 7 markets\n")

# per-market OVER baseline - these are NOT the same across markets and using one number for all
# would repeat exactly the mistake that made newunder look like a signal
BASE = {}
print(f"    {'market':<8}{'props':>8}{'over baseline':>16}{'median line':>14}")
for mk in ALL:
    rows = [r for r in U if r["mk"] == mk]
    if len(rows) < 50: continue
    BASE[mk] = sum(1 for r in rows if r["over_won"])/len(rows)
    lns = sorted(r["line"] for r in rows)
    print(f"    {mk:<8}{len(rows):>8}{100*BASE[mk]:>15.1f}%{lns[len(lns)//2]:>14.1f}")

def cell(rows, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"    {label:<52} n={n} too few"); return None
    w = sum(1 for r in rows if r["over_won"])/n
    base = sum(BASE.get(r["mk"], 0.534) for r in rows)/n     # blended baseline of the rows present
    rr = [(r["odds"]-1) if r["over_won"] else -1.0 for r in rows]
    m = sum(rr)/n; z = (w-base)/math.sqrt(base*(1-base)/n)
    print(f"    {label:<52} n={n:<5} win {100*w:5.1f}%  ROI {100*m:+6.1f}%  "
          f"lift {100*(w-base):+5.1f}pp  z={z:+5.2f}")
    return w, m, n, z

print("\n" + "="*92)
print("  1. TRANSLATE THE BAND. What is '3 to 6 points below' as a PERCENTAGE?")
print("="*92)
fit_band = [r for r in U if r["mk"] in FIT and -6 <= r["gap"] < -3]
pcts = sorted(r["gap_pct"] for r in fit_band)
LO, HI = pcts[int(len(pcts)*0.1)], pcts[int(len(pcts)*0.9)]
print(f"    the fitted band in relative terms: median {100*pcts[len(pcts)//2]:+.0f}%, "
      f"10th {100*pcts[0]:+.0f}%, 90th {100*pcts[-1]:+.0f}%")
PLO, PHI = -0.45, -0.18
print(f"    -> using gap_pct between {100*PLO:+.0f}% and {100*PHI:+.0f}% as the portable rule")
cell([r for r in U if r["mk"] in FIT and PLO <= r["gap_pct"] < PHI],
     "    the FITTED markets, restated as a percentage band")
cell(fit_band, "    the FITTED markets, original absolute band (-6..-3)")

print("\n" + "="*92)
print("  2. THE HOLDOUT: reb / ast / ra - never used to find anything")
print("="*92)
for mk in HOLD:
    rows = [r for r in U if r["mk"] == mk]
    cell([r for r in rows if PLO <= r["gap_pct"] < PHI], f"    {mk}: gap {100*PLO:.0f}%..{100*PHI:.0f}%", minn=20)
cell([r for r in U if r["mk"] in HOLD and PLO <= r["gap_pct"] < PHI],
     "    ALL THREE HOLDOUT MARKETS COMBINED")
print()
cell([r for r in U if r["mk"] in HOLD], "    holdout markets, no filter (the control)")
print("\n    the comparison that matters is the filtered holdout vs the unfiltered holdout.")

print("\n" + "="*92)
print("  3. THE LADDER ON THE HOLDOUT - shape matters more than one cell")
print("="*92)
for lo, hi in ((-0.90,-0.45), (-0.45,-0.30), (-0.30,-0.18), (-0.18,-0.08), (-0.08,0.08), (0.08,0.90)):
    cell([r for r in U if r["mk"] in HOLD and lo <= r["gap_pct"] < hi],
         f"    gap {100*lo:+.0f}% to {100*hi:+.0f}%", minn=20)

print("\n" + "="*92)
print("  4. ANCHOR ROBUSTNESS - does the edge survive a different definition of 'recent form'?")
print("="*92)
print(f"    {'anchor':<28}{'n':>6}{'win%':>9}{'lift':>9}{'z':>8}")
for kind, win in (("median", 10), ("mean", 10), ("median", 5), ("mean", 5), ("median", 15)):
    A = build_anchor(kind, win)
    UU = universe(A)
    rows = [r for r in UU if r["mk"] in FIT and PLO <= r["gap_pct"] < PHI]
    if len(rows) < 30:
        print(f"    trailing-{win} {kind:<18}{len(rows):>6}   too few"); continue
    w = sum(1 for r in rows if r["over_won"])/len(rows)
    base = sum(BASE.get(r["mk"], 0.534) for r in rows)/len(rows)
    z = (w-base)/math.sqrt(base*(1-base)/len(rows))
    print(f"    trailing-{win} {kind:<18}{len(rows):>6}{100*w:>8.1f}%{100*(w-base):>+8.1f}{z:>8.2f}")
print("\n    a real effect should be visible under every reasonable definition. If it only exists")
print("    at trailing-10-median, it is a knife-edge and therefore an artefact of the search.")
