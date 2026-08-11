# menu_filters.py - invert skip-drift, add the line-move filter, and apply both to the REAL menu
# ---------------------------------------------------------------------------------------------
# Two findings survived the band retraction, and both are about how to FILTER rather than what to
# bet, so they can be tested on the menu we already run:
#
#   1 SKIP-DRIFT IS INVERTED. Board-wide at T-2h the bucket we prefer ("price shortened, money
#     agrees") is the worst one. So the proposal is to flip it: prefer FLAT and DRIFTED, drop
#     SHORTENED. Note the honest starting point - board-wide, flipping it improved ROI but did
#     not make it positive. Expect improvement, not profit.
#
#   2 THE BOOK MOVING ITS LINE AGAINST US IS REAL INFORMATION. Stated generally, not just for
#     overs: skip when the book moves the number in the direction that hurts our side.
#         our bet is an OVER  and the book CUTS the line   -> it knows something, skip
#         our bet is an UNDER and the book RAISES the line -> same, skip
#
# EVERYTHING IS SCORED AS LIFT OVER THE CORRECT PER-MARKET, PER-SIDE BASELINE. That is the rule
# that exposed newunder as no signal at all, and it is not optional.
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
def d8(s):
    s = (s or "").replace("-", "")
    return s[:8] if len(s) >= 8 else ""
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")

games = {g.get("game_id"): dict(date=g.get("date",""), tip=ts(g.get("tip")))
         for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    g = games.get(r.get("game_id"))
    if not g or not g["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=g["date"], tip=g["tip"], pts=pts,
        reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast))
for v in plog.values(): v.sort(key=lambda x: x["date"])
byplayer = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v:
        if g["tip"]: byplayer[pl].append((g["tip"], g["date"], g))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

# ---- board: price series per selection, and the set of lines offered that night ------------------
bidx = collections.defaultdict(list)
lines_night = collections.defaultdict(list)          # (player, market, gamedate) -> [(t, line)]
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("market") not in MKTS: continue
    bidx[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
    if b.get("side") == "Over":
        lines_night[((b.get("player") or "").lower(), b.get("market"))].append((t, ln))
for v in bidx.values(): v.sort()
for v in lines_night.values(): v.sort()

def line_move(pl, mk, tip):
    """How the book moved its NUMBER during the 36h before this tip. + = raised, - = cut."""
    v = [x for x in lines_night.get((pl, mk), []) if 0 <= (tip - x[0]).total_seconds() <= 36*3600]
    return (v[-1][1] - v[0][1]) if len(v) >= 2 else None
def drift_at(pl, mk, side, ln, cut, tip):
    v = [x for x in bidx.get((pl, mk, side, ln), [])
         if x[0] <= cut and 0 <= (tip - x[0]).total_seconds() <= 36*3600]
    return (v[-1][1]/v[0][1] - 1, v[-1][1]) if len(v) >= 2 else (None, None)

# ---- per market+side baseline, from the whole board ----------------------------------------------
BASE = {}
tmp = collections.defaultdict(list)
for (pl, mk, side, ln), v in bidx.items():
    dt, rec = game_after(pl, v[0][0])
    if not rec or rec[mk] == ln: continue
    tmp[(mk, side)].append(1.0 if ((rec[mk] > ln) if side == "Over" else (rec[mk] < ln)) else 0.0)
for k, v in tmp.items():
    if len(v) >= 80: BASE[k] = sum(v)/len(v)
print("board baselines (market, side) -> win rate")
for k in sorted(BASE): print(f"    {k[0]:<5}{k[1]:<7}{100*BASE[k]:5.1f}%   n={len(tmp[k])}")

# ---- our real menu -------------------------------------------------------------------------------
seen, M = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    t, ln, o = ts(b.get("captured_utc")), f(b.get("line")), f(b.get("odds"))
    mk, side, src = b.get("market"), b.get("side"), (b.get("src") or "?")
    pl = (b.get("player") or "").lower()
    if not (t and ln is not None and o and mk in MKTS and side in ("Over", "Under")): continue
    k = (d8(b.get("date")), pl, mk, side, ln, src)
    if k in seen: continue
    seen.add(k)
    dt, rec = game_after(pl, t)
    if not rec or rec[mk] == ln: continue
    cut = rec["tip"] - datetime.timedelta(hours=2)
    dr, entry = drift_at(pl, mk, side, ln, cut, rec["tip"])
    lm = line_move(pl, mk, rec["tip"])
    won = (rec[mk] > ln) if side == "Over" else (rec[mk] < ln)
    M.append(dict(date=dt, pl=pl, mk=mk, side=side, src=src, line=ln, odds=o, entry=entry or o,
                  won=won, drift=dr, line_move=lm,
                  base=BASE.get((mk, side), 0.50)))
M.sort(key=lambda r: r["date"])
print(f"\n{len(M)} deduped menu bets with an outcome; "
      f"{sum(1 for r in M if r['drift'] is not None)} have a causal T-2h drift read, "
      f"{sum(1 for r in M if r['line_move'] is not None)} have a line-move read")

def rep(rows, label, minn=25, use="odds"):
    n = len(rows)
    if n < minn:
        print(f"    {label:<52} n={n} too few"); return None
    w = sum(1 for r in rows if r["won"])/n
    base = sum(r["base"] for r in rows)/n
    rr = [(r[use]-1) if r["won"] else -1.0 for r in rows]
    m = sum(rr)/n; z = (w-base)/math.sqrt(base*(1-base)/n)
    print(f"    {label:<52} n={n:<5} win {100*w:5.1f}%  ROI {100*m:+6.1f}%  "
          f"lift {100*(w-base):+5.1f}pp  z={z:+5.2f}")
    return w, m, n, z

print("\n" + "="*94)
print("  1. THE INVERSION, ON THE WHOLE BOARD FIRST (not inside the retracted band)")
print("="*94)
BOARD = []
for (pl, mk, side, ln), v in bidx.items():
    dt, rec = game_after(pl, v[0][0])
    if not rec or rec[mk] == ln or (mk, side) not in BASE: continue
    cut = rec["tip"] - datetime.timedelta(hours=2)
    dr, entry = drift_at(pl, mk, side, ln, cut, rec["tip"])
    if dr is None: continue
    BOARD.append(dict(won=(rec[mk] > ln) if side == "Over" else (rec[mk] < ln),
                      odds=entry, entry=entry, drift=dr, base=BASE[(mk, side)],
                      line_move=line_move(pl, mk, rec["tip"]), side=side, date=dt))
BOARD.sort(key=lambda r: r["date"])
print(f"    {len(BOARD)} board selections with a causal T-2h read")
rep(BOARD, "      everything (the control)")
rep([r for r in BOARD if r["drift"] <= -0.01], "      price SHORTENED  <- what we currently keep")
rep([r for r in BOARD if -0.01 < r["drift"] < 0.01], "      price FLAT")
rep([r for r in BOARD if r["drift"] >= 0.01], "      price DRIFTED   <- what we currently skip")
rep([r for r in BOARD if r["drift"] > -0.01], "      INVERTED RULE: flat + drifted")

print("\n  the line-move filter, also board-wide:")
def against(r):
    """Did the book move its number AGAINST our side during the night?"""
    if r["line_move"] is None: return None
    return (r["line_move"] <= -0.5) if r["side"] == "Over" else (r["line_move"] >= 0.5)
rep([r for r in BOARD if against(r) is False], "      book did NOT move against us")
rep([r for r in BOARD if against(r) is True], "      book MOVED AGAINST us  <- skip these")
rep([r for r in BOARD if r["drift"] > -0.01 and against(r) is False],
    "      BOTH filters: flat/drifted AND book not against us")

print("\n" + "="*94)
print("  2. NOW ON OUR ACTUAL MENU - what each filter would have done to the real bets")
print("="*94)
D2 = [r for r in M if r["drift"] is not None]
rep(M,  "      the menu as it stands, everything")
rep(D2, "      menu subset that has a causal drift read")
rep([r for r in D2 if r["drift"] < 0.01], "      CURRENT RULE: skip-drift (keep non-drifted)")
rep([r for r in D2 if r["drift"] > -0.01], "      INVERTED: keep flat + drifted")
rep([r for r in D2 if r["drift"] >= 0.01], "      FULLY INVERTED: keep only drifted")
mv = [r for r in D2 if r["line_move"] is not None]
def against_m(r):
    return (r["line_move"] <= -0.5) if r["side"] == "Over" else (r["line_move"] >= 0.5)
rep([r for r in mv if not against_m(r)], "      LINE FILTER only: book not moving against us")
STACK = [r for r in mv if r["drift"] > -0.01 and not against_m(r)]
rep(STACK, "      BOTH FILTERS STACKED")

print("\n" + "="*94)
print("  3. THE STACK, BROKEN OUT BY SIGNAL - does it rescue anything or just cut volume?")
print("="*94)
for src in sorted({r["src"] for r in M}, key=lambda s: -len([r for r in M if r["src"] == s])):
    allr = [r for r in M if r["src"] == src]
    st = [r for r in STACK if r["src"] == src]
    if len(allr) < 30: continue
    a = rep(allr, f"      {src} - unfiltered", minn=25)
    if len(st) >= 20: rep(st, f"      {src} - with both filters", minn=20)
    else: print(f"      {src} - with both filters                    n={len(st)} too few")

print("\n" + "="*94)
print("  4. HOLDOUT IN TIME - the stack on the last third of the menu, untouched")
print("="*94)
cut_i = int(len(STACK)*2/3)
if len(STACK) >= 45:
    rep(STACK[:cut_i], "      first two thirds", minn=20)
    rep(STACK[cut_i:], "      final third", minn=15)
print("\n    HOW TO READ ALL OF THIS: the filters are only worth applying if the stacked row beats")
print("    the unfiltered row by more than it costs in volume - and if it still holds in the final")
print("    third. A lift that only exists in-sample is the same mistake as the retracted band.")

print("\n" + "="*94)
print("  5. CORRECTION TO SECTION 1 - IT WAS DOUBLE-COUNTING. Read this instead.")
print("="*94)
print("    Section 1 pooled Over and Under selections. Those are THE SAME EVENT TWICE: one wins")
print("    exactly when the other loses, and when the over price shortens the under price")
print("    lengthens. So one real outcome gets written down as both 'shortened won' AND")
print("    'drifted lost', manufacturing the correlation out of pure bookkeeping.")
print("    Each side has to be read on its own.\n")
for SIDE in ("Over", "Under"):
    S = [r for r in BOARD if r["side"] == SIDE]
    print(f"    --- {SIDE} selections only, n={len(S)} ---")
    rep(S, f"      every {SIDE} (control)")
    rep([r for r in S if r["drift"] <= -0.01], "      SHORTENED  <- current rule keeps")
    rep([r for r in S if -0.01 < r["drift"] < 0.01], "      FLAT")
    rep([r for r in S if r["drift"] >= 0.01], "      DRIFTED    <- current rule skips")
    rep([r for r in S if against(r) is True], "      book MOVED AGAINST us")
    rep([r for r in S if against(r) is False], "      book did NOT move against us")
    print()
print("    If SHORTENED beats DRIFTED on BOTH sides independently, the original skip-drift rule")
print("    is right and my earlier 'the filter is backwards' claim was an artefact of comparing")
print("    an overs-only slice against a single wrong baseline.")

print("\n" + "="*94)
print("  6. THE CORRECT STACK ON THE MENU: keep skip-drift, ADD the line filter")
print("="*94)
MV = [r for r in M if r["drift"] is not None and r["line_move"] is not None]
print(f"    {len(MV)} menu bets with BOTH a causal drift read and a line-move read\n")
rep(MV, "      that subset, unfiltered")
rep([r for r in MV if r["drift"] < 0.01], "      skip-drift only (the current rule)")
rep([r for r in MV if not against_m(r)], "      line filter only")
GOOD = [r for r in MV if r["drift"] < 0.01 and not against_m(r)]
rep(GOOD, "      BOTH: skip-drift AND book not moving against us")
print("\n    by signal, under the correct stack:")
for src in sorted({r["src"] for r in MV}, key=lambda s: -len([r for r in MV if r["src"] == s])):
    g = [r for r in GOOD if r["src"] == src]
    a = [r for r in MV if r["src"] == src]
    if len(a) < 40: continue
    rep(a, f"      {src} - unfiltered", minn=25)
    rep(g, f"      {src} - correct stack", minn=20)
print("\n    holdout in time, the correct stack:")
if len(GOOD) >= 45:
    c = int(len(GOOD)*2/3)
    rep(GOOD[:c], "      first two thirds", minn=20)
    rep(GOOD[c:], "      final third, untouched", minn=15)
