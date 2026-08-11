# band_drift.py - does DRIFT add anything to the one signal that passed the gate?
# ---------------------------------------------------------------------------------------------
# Skip-drift is dead as a general filter: on the whole board it moves ROI by roughly nothing, and
# the bucket the live menu prefers (price shortened) is the WORST one. But that was measured
# across every prop indiscriminately. The question now is narrower and fairer:
#
#     within the ONE band that passed the null gate - book line 3 to 6 points BELOW the player's
#     own trailing-10 median, take the over - does what the price does before tip tell us which
#     of those stale lines are real and which are the book knowing something we do not?
#
# There is a genuine reason it might. The band's claim is "the book hung a wrong number and has
# not noticed". Two things could happen before tip:
#     THE BOOK NOTICES  -> it moves the LINE up, or shortens the over price. Our edge evaporates
#                          because the mistake is being corrected while we watch.
#     THE BOOK STAYS PUT -> the number is still wrong at tip. That is the bet we want.
# So the interesting filter here is not "skip drift" but "skip the ones being CORRECTED".
#
# Everything is read causally: only captures at or before the decision point are used.
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
OVER_BASE = 0.534
MKTS = ("pts", "pra", "pr", "pa")

games = {g.get("game_id"): dict(date=g.get("date",""), tip=ts(g.get("tip")))
         for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    g = games.get(r.get("game_id"))
    if not g or not g["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=g["date"], tip=g["tip"], pts=pts,
        reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast))
for v in plog.values(): v.sort(key=lambda x: x["date"])
ANCH = {}
for pl, v in plog.items():
    for i, g in enumerate(v):
        prev = v[:i][-10:]
        if len(prev) < 6: continue
        for mk in MKTS: ANCH[(pl, mk, g["date"])] = statistics.median(x[mk] for x in prev)
byplayer = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v:
        if g["tip"]: byplayer[pl].append((g["tip"], g["date"], g))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

# board, split per night, keeping EVERY line offered so we can see the book move its number
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
pergame = collections.defaultdict(dict)
for (pl, mk, ln), v in raw.items():
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
        if pre: pergame[(pl, mk, dt)][ln] = pre

B = []
for (pl, mk, dt), lines in pergame.items():
    a = ANCH.get((pl, mk, dt))
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if a is None or rec is None: continue
    ln, s = max(lines.items(), key=lambda kv: len(kv[1]))
    if rec[mk] == ln or len(s) < 2: continue
    # the book moving its NUMBER during the night, which is the correction we care about
    first_line = min(lines.items(), key=lambda kv: kv[1][0][0])[0]
    last_line  = max(lines.items(), key=lambda kv: kv[1][-1][0])[0]
    B.append(dict(pl=pl, mk=mk, date=dt, tip=rec["tip"], line=ln, gap=ln - a, series=s,
                  line_move=last_line - first_line, odds=s[-1][1], over_won=rec[mk] > ln))
B.sort(key=lambda r: r["date"])
BAND = [r for r in B if -6 <= r["gap"] < -3]
print(f"{len(B)} over-series with a causal anchor;  {len(BAND)} in the gate-passing band "
      f"(gap -6..-3)\n")

def cell(rows, label, minn=20, use="odds"):
    n = len(rows)
    if n < minn:
        print(f"    {label:<50} n={n} too few"); return None
    w = sum(1 for r in rows if r["over_won"])/n
    rr = [(r[use]-1) if r["over_won"] else -1.0 for r in rows]
    m = sum(rr)/n; z = (w-OVER_BASE)/math.sqrt(OVER_BASE*(1-OVER_BASE)/n)
    print(f"    {label:<50} n={n:<5} win {100*w:5.1f}%  ROI {100*m:+6.1f}%  "
          f"lift {100*(w-OVER_BASE):+5.1f}pp  z={z:+5.2f}")
    return w, m, n, z

def with_drift(rows, hrs):
    """Attach the price movement visible at T-hrs, and the price we could actually take then."""
    out = []
    for r in rows:
        cut = r["tip"] - datetime.timedelta(hours=hrs)
        pre = [x for x in r["series"] if x[0] <= cut]
        if len(pre) < 2: continue
        out.append(dict(r, drift=pre[-1][1]/pre[0][1]-1, entry=pre[-1][1]))
    return out

print("="*88)
print("  1. DOES DRIFT SPLIT THE BAND? (decision at T-6h, bet at the price available then)")
print("="*88)
for hrs in (6.0, 2.0):
    W = with_drift(BAND, hrs)
    print(f"\n    --- decision point T-{hrs:.0f}h,  {len(W)} of {len(BAND)} band props have a "
          f"causal read ---")
    cell(W, f"      whole band at T-{hrs:.0f}h", minn=20, use="entry")
    cell([r for r in W if r["drift"] <= -0.01], "      price SHORTENED >=1% (money agrees)",
         minn=15, use="entry")
    cell([r for r in W if -0.01 < r["drift"] < 0.01], "      price FLAT", minn=15, use="entry")
    cell([r for r in W if r["drift"] >= 0.01], "      price DRIFTED >=1% (we currently skip)",
         minn=15, use="entry")

print("\n" + "="*88)
print("  2. THE BETTER QUESTION: is the book CORRECTING the number before tip?")
print("="*88)
print("    the band's claim is 'the book hung a wrong line and has not noticed'. If it moves the")
print("    LINE up during the night, it has noticed - and our reason for betting is gone.")
moved = [r for r in BAND if r["line_move"] >= 0.5]
still = [r for r in BAND if abs(r["line_move"]) < 0.5]
down  = [r for r in BAND if r["line_move"] <= -0.5]
cell(still, "      book NEVER moved its number (still stale at tip)")
cell(moved, "      book RAISED the line during the night (correcting)")
cell(down,  "      book CUT the line further")
print(f"\n    share of the band the book never corrected: "
      f"{100*len(still)/len(BAND):.0f}%  ({len(still)}/{len(BAND)})")

print("\n" + "="*88)
print("  3. IS THE BAND EVEN DRIFTY? (compare its price behaviour to the rest of the board)")
print("="*88)
def dstats(rows, label):
    W = with_drift(rows, 2.0)
    if len(W) < 30:
        print(f"    {label:<40} n={len(W)} too few"); return
    d = [r["drift"] for r in W]
    sh = sum(1 for x in d if x <= -0.01)/len(d); dr = sum(1 for x in d if x >= 0.01)/len(d)
    print(f"    {label:<40} n={len(W):<5} mean move {100*sum(d)/len(d):+5.2f}%   "
          f"shortened {100*sh:.0f}%  drifted {100*dr:.0f}%")
dstats(BAND, "the gate-passing band (gap -6..-3)")
dstats([r for r in B if r["gap"] > -1], "the rest of the board (gap > -1)")
dstats(B, "everything")
print("\n    if the band drifts like everything else, drift carries no extra information here -")
print("    it is a property of the board, not of the mistake we are trying to exploit.")
