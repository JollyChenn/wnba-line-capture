# config_compare.py - what would EACH version of the model have bet, on the same recent nights?
# ---------------------------------------------------------------------------------------------
# Three configurations, graded side by side on the live signal log:
#   OLD MENU  every over signal, any market, no star   (what the bot alerted before this week)
#   PREV      flip + hotover, pra/pr/pts, starred      (the model as of yesterday morning)
#   LIVE      flip + hotover + overshoot, same, starred
# One bet per player-market-night in all three, so the comparison is like for like.
import csv, os, sys, datetime, collections, statistics
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

SINCE = sys.argv[1] if len(sys.argv) > 1 else "20260808"
MKTS  = ("pts","pra","pr","pa","reb","ast","ra")

gm = {g.get("game_id"): g.get("date","") for g in load("data/games_2026.csv")}
box = {}
for r in load("data/box_2026.csv"):
    d = gm.get(r.get("game_id"))
    if not d: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    box[(d, (r.get("player") or "").strip().lower())] = dict(
        pts=p_, reb=rb, ast=a, pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)

# the board, split into nights, so we can find her PREVIOUS line (for the star)
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
nights = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a_, b_ in zip(v, v[1:]):
        if (b_[0]-a_[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
    blocks.append(cur)
    for blk in blocks:
        if blk: nights[(pl, mk)].append((blk[0][0], ln, blk))
for v in nights.values(): v.sort()

def prev_line(pl, mk, day):
    """her line the LAST time this market was quoted before today - the star's reference point"""
    dd = datetime.datetime.strptime(day, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    before = [x for x in nights.get((pl, mk), []) if (dd - x[0]).total_seconds() > 18*3600]
    return before[-1][1] if before else None

# every signal since SINCE, deduped to one per player-market-night
seen, C = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over": continue
    day = (b.get("date") or "").replace("-", "")[:8]
    if not day or day < SINCE: continue
    pl, mk, ln, od = (b.get("player") or "").lower(), b.get("market"), f(b.get("line")), f(b.get("odds"))
    if mk not in MKTS or ln is None or od is None: continue
    if (day, pl, mk) in seen: continue
    act = box.get((day, pl))
    if not act: continue                       # game not played / not captured yet
    seen.add((day, pl, mk))
    pv = prev_line(pl, mk, day)
    # intraday price drift on THIS night's series for this line - the old drift gate
    dd = datetime.datetime.strptime(day, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    tonight_blk = [x for x in nights.get((pl, mk), []) if abs((x[0]-dd).total_seconds()) < 30*3600]
    dr = None
    if tonight_blk:
        blk = max(tonight_blk, key=lambda x: len(x[2]))[2]
        if len(blk) >= 2: dr = blk[-1][1]/blk[0][1] - 1
    C.append(dict(day=day, pl=pl, name=b.get("player"), mk=mk, line=ln, odds=od,
                  dr=dr, nodrift=(dr is not None and dr < 0.01),
                  src=b.get("src") or "?", actual=act[mk], won=act[mk] > ln,
                  push=act[mk] == ln, prev=pv,
                  raised=(pv is not None and ln - pv >= 0.5)))
C.sort(key=lambda r: (r["day"], r["name"]))

CONFIGS = [
    ("OLD MENU  any over signal, any market, no star", lambda r: True),
    ("PREV      flip+hotover, pra/pr/pts, STARRED",
     lambda r: r["src"] in ("flip","hotover") and r["mk"] in ("pra","pr","pts") and not r["raised"]),
    ("LIVE      +overshoot, pra/pr/pts, STARRED",
     lambda r: r["src"] in ("flip","hotover","overshoot") and r["mk"] in ("pra","pr","pts") and not r["raised"]),
    ("DRIFT     same signals, drift gate INSTEAD of star",
     lambda r: r["src"] in ("flip","hotover","overshoot") and r["mk"] in ("pra","pr","pts") and r["nodrift"]),
    ("FILTER X  same signals, star AND drift stacked",
     lambda r: r["src"] in ("flip","hotover","overshoot") and r["mk"] in ("pra","pr","pts")
               and not r["raised"] and r["nodrift"]),
]

def one_position(rows):
    """THE LIVE RULE: same player on two markets is ONE position, not two. Keep her best-priced
       leg and drop the rest, otherwise a single bad night for one player is counted twice."""
    best = {}
    for r in sorted(rows, key=lambda x: -x["odds"]):
        best.setdefault((x_ := (r["day"], r["pl"])), r)
    return sorted(best.values(), key=lambda r: (r["day"], r["name"]))

def score(rows):
    n = len(rows)
    if not n: return 0, 0, 0.0
    w = sum(1 for r in rows if r["won"] and not r["push"])
    u = sum(0.0 if r["push"] else ((r["odds"]-1) if r["won"] else -1.0) for r in rows)
    return w, n, u

days = sorted({r["day"] for r in C})
print(f"{len(C)} graded over-signals since {SINCE}, on {len(days)} slates: {', '.join(days)}")
print("")
print("="*104)
print("  NIGHT BY NIGHT")
print("="*104)
for d in days:
    print(f"  --- {d} ---")
    for label, fn in CONFIGS:
        rows = [r for r in C if r["day"] == d and fn(r)]
        if not label.startswith("OLD"): rows = one_position(rows)
        w, n, u = score(rows)
        if not n:
            print(f"    {label:<48} no bet"); continue
        print(f"    {label:<48} {w}-{n-w}  {u:+6.2f}u")
        for r in rows:
            mark = "WIN " if r["won"] else "loss"
            print(f"        {mark} {r['name']:<20} {r['mk'].upper():<4} Over {r['line']:<6} @{r['odds']:<6} "
                  f"got {r['actual']:<5} _{r['src']}_")
    print("")
print("="*104)
print("  TOTAL OVER THE WHOLE WINDOW")
print("="*104)
for label, fn in CONFIGS:
    rows = [r for r in C if fn(r)]
    if not label.startswith("OLD"): rows = one_position(rows)
    w, n, u = score(rows)
    if not n:
        print(f"  {label:<48} no bets"); continue
    print(f"  {label:<48} {w}-{n-w}  {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%  ({n/len(days):.1f}/night)")
