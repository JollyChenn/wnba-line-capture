# fade_raised.py - the book RAISED her number since last game. We skip the over. Should we take
#                  the UNDER instead?
# ---------------------------------------------------------------------------------------------
# WHY THIS IS NOT AUTOMATIC. "The over has no edge here" and "the under has an edge here" are
# different statements. On a two-sided market the win rates are complementary by construction, so
# if the over runs +2.1pp above its baseline then the under runs 2.1pp BELOW its own baseline.
# Skipping a bet and fading it are not the same decision, and the arithmetic actually points the
# wrong way before we start.
#
# But two things could still rescue it, and only data settles them:
#   PRICE   the under is priced separately. A -2pp win rate at a much better price can still beat
#           a +2pp win rate at a worse one. The mirror holds for win RATE, not for ROI.
#   TAIL    "raised 0.5-2" and "raised 5+" may behave very differently. A big raise is the book
#           reacting hard to something; that is where an overreaction would live if one exists.
#
# THE BAR IS HIGH AND WORTH STATING UP FRONT. Blind unders on this board return about -13%. So a
# fade needs roughly +7pp of win-rate lift just to reach break-even, before it makes a penny.
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
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")

gm = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not (dt and tp): continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=dt, tip=tp, pts=pts, reb=reb, ast=ast,
        pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast))
for v in plog.values(): v.sort(key=lambda x: x["date"])
byp = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v: byp[pl].append((g["tip"], g["date"], g))
for v in byp.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byp.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
pergame = collections.defaultdict(dict)
for (pl, mk, side, ln), v in raw.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
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
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or rec[mk] == ln: continue
    P.append(dict(pl=pl, mk=mk, date=dt, line=ln, over_won=rec[mk] > ln,
                  oo=sides["Over"][-1][1], uo=sides["Under"][-1][1]))
P.sort(key=lambda r: r["date"])
lh = collections.defaultdict(list)
for r in P: lh[(r["pl"], r["mk"])].append((r["date"], r["line"]))
for v in lh.values(): v.sort()
def prev_line(pl, mk, dt):
    v = lh[(pl, mk)]
    i = next((k for k, x in enumerate(v) if x[0] == dt), None)
    return v[i-1][1] if i is not None and i >= 1 else None
for r in P:
    pv = prev_line(r["pl"], r["mk"], r["date"])
    r["dline"] = (r["line"] - pv) if pv is not None else None
BASE = {}
tmp = collections.defaultdict(list)
for r in P:
    tmp[(r["mk"], "Over")].append(1.0 if r["over_won"] else 0.0)
    tmp[(r["mk"], "Under")].append(0.0 if r["over_won"] else 1.0)
for k, v in tmp.items():
    if len(v) >= 80: BASE[k] = sum(v)/len(v)
P = [r for r in P if (r["mk"], "Over") in BASE and r["dline"] is not None]
print(f"{len(P)} board props with both sides priced AND a previous-game line\n")

def cell(rows, side, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"    {label:<44} n={n} too few"); return
    if side == "Over":
        w = sum(1 for r in rows if r["over_won"])/n
        roi = sum((r["oo"]-1) if r["over_won"] else -1.0 for r in rows)/n
    else:
        w = sum(1 for r in rows if not r["over_won"])/n
        roi = sum((r["uo"]-1) if not r["over_won"] else -1.0 for r in rows)/n
    base = sum(BASE[(r["mk"], side)] for r in rows)/n
    z = (w-base)/math.sqrt(base*(1-base)/n)
    print(f"    {label:<44} n={n:<5} win {100*w:5.1f}%  ROI {100*roi:+6.1f}%  "
          f"lift {100*(w-base):+5.1f}pp  z={z:+5.2f}")

print("="*94)
print("  1. THE LADDER, BOTH SIDES. Over shown for reference, UNDER is the fade.")
print("="*94)
LAD = ((0.5,1.5,"book raised 0.5-1.5"), (1.5,3,"raised 1.5-3"), (3,5,"raised 3-5"),
       (5,99,"raised 5+"))
for lo, hi, nm in LAD:
    sel = [r for r in P if lo <= r["dline"] < hi]
    cell(sel, "Over",  f"  {nm}  -> OVER  (what we skip)")
    cell(sel, "Under", f"  {nm}  -> UNDER (the fade)")
    print()
allr = [r for r in P if r["dline"] >= 0.5]
cell(allr, "Over",  "  ALL raised 0.5+  -> OVER")
cell(allr, "Under", "  ALL raised 0.5+  -> UNDER (the fade)")
print()
cell(P, "Under", "  CONTROL: every under, no filter")

print("\n" + "="*94)
print("  2. WHY THE MIRROR MAKES THIS HARD")
print("="*94)
ov = sum(1 for r in allr if r["over_won"])/len(allr)
ob = sum(BASE[(r["mk"], "Over")] for r in allr)/len(allr)
ub = sum(BASE[(r["mk"], "Under")] for r in allr)/len(allr)
print(f"    on raised props the OVER wins {100*ov:.1f}% against an over baseline of {100*ob:.1f}%")
print(f"    -> the UNDER therefore wins {100*(1-ov):.1f}% against an under baseline of {100*ub:.1f}%")
print(f"    the two lifts are equal and opposite BY CONSTRUCTION. Skipping a bet and fading it")
print(f"    are different decisions, and there is no free lunch in flipping the side.")
uo = sum(r["uo"] for r in allr)/len(allr)
be = 100/uo
print(f"\n    average under price on these {uo:.2f} -> break-even needs {be:.1f}%")
print(f"    the fade delivers {100*(1-ov):.1f}%. Gap to break-even: {(1-ov)*100-be:+.1f}pp")

print("\n" + "="*94)
print("  3. THE SAME QUESTION ON OUR OWN SKIPPED BETS")
print("="*94)
seen, M = set(), []
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    pl, mk, ln = (b.get("player") or "").lower(), b.get("market"), f(b.get("line"))
    if mk not in MKTS or ln is None: continue
    dt, rec = game_after(pl, ts(b.get("captured_utc")) or datetime.datetime.now(datetime.timezone.utc))
    if not rec: continue
    k = (dt, pl, mk)
    if k in seen: continue
    seen.add(k)
    m = next((r for r in P if r["pl"] == pl and r["mk"] == mk and r["date"] == dt), None)
    if m: M.append(m)
sk = [r for r in M if r["dline"] >= 0.5]
print(f"    {len(M)} of our over candidates matched to a board row with a previous line")
cell(sk, "Over",  "  our SKIPPED bets, taken as overs anyway")
cell(sk, "Under", "  our SKIPPED bets, FADED to the under")
print("\n    if fading our own skips loses, the filter is doing the right thing by simply")
print("    dropping them rather than reversing them.")
