# august_check.py - why is August bad, and what does FLIP alone look like?
# ---------------------------------------------------------------------------------------------
# FIRST QUESTION TO ASK, AND ALMOST NOBODY ASKS IT: is August actually bad, or is it a normal bad
# run? 96 bets is not many. Before inventing a story about the book getting sharper or the roster
# changing, work out how often a genuine 56% bettor has a stretch this poor. If the answer is
# "about a third of the time", then there is nothing to explain and every explanation is a
# just-so story.
#
# Only if it survives that do the real candidates matter:
#   COMPOSITION   are we betting different signals / markets / sides in August?
#   ENVIRONMENT   did the whole BOARD get harder, not just us? (check the board baseline by month)
#   PRICE         are we getting worse odds for the same bets?
#   CONCENTRATION is it one signal or one player bleeding?
import csv, os, sys, math, random, datetime, collections
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

bidx = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS:
        bidx[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
for v in bidx.values(): v.sort()
def drift_at(pl, mk, side, ln, cut, tip):
    v = [x for x in bidx.get((pl, mk, side, ln), [])
         if x[0] <= cut and 0 <= (tip - x[0]).total_seconds() <= 36*3600]
    return v[-1][1]/v[0][1] - 1 if len(v) >= 2 else None

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
    dr = drift_at(pl, mk, side, ln, rec["tip"] - datetime.timedelta(hours=2), rec["tip"])
    M.append(dict(date=dt, mo=dt[:6], pl=pl, mk=mk, side=side, src=src, odds=o, drift=dr,
                  won=(rec[mk] > ln) if side == "Over" else (rec[mk] < ln)))
M.sort(key=lambda r: r["date"])
KEEP = [r for r in M if r["drift"] is not None and r["drift"] < 0.01]   # the live rule
print(f"{len(M)} deduped menu bets; {len(KEEP)} pass skip-drift with a causal read\n")

def u(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)
def wr(rows): return sum(1 for r in rows if r["won"])/len(rows) if rows else 0

print("="*88)
print("  1. IS AUGUST EVEN BAD? - a 56% bettor's normal worst months, simulated")
print("="*88)
pre = [r for r in KEEP if r["mo"] < "202608"]
aug = [r for r in KEEP if r["mo"] == "202608"]
p_true = wr(pre)
print(f"    Jun-Jul: {len(pre)} bets at {100*p_true:.1f}%   |   Aug: {len(aug)} bets at "
      f"{100*wr(aug):.1f}%  ({u(aug):+.2f}u)")
w_aug = sum(1 for r in aug if r["won"])
exp = len(aug)*p_true
sd = math.sqrt(len(aug)*p_true*(1-p_true))
z = (w_aug - exp)/sd
print(f"    if the true rate were still {100*p_true:.1f}%, August should have won "
      f"{exp:.1f} of {len(aug)}; it won {w_aug}")
print(f"    that is z={z:+.2f}, p={math.erfc(abs(z)/math.sqrt(2)):.3f}")
worse = 0
for _ in range(20000):
    s = sum(1 for _ in range(len(aug)) if random.random() < p_true)
    if s <= w_aug: worse += 1
print(f"    simulating 20,000 Augusts at the Jun-Jul rate: {100*worse/20000:.1f}% of them are "
      f"this bad or worse")
units_worse = 0
for _ in range(20000):
    tot = sum((random.choice([r['odds'] for r in aug])-1) if random.random() < p_true else -1.0
              for _ in range(len(aug)))
    if tot <= u(aug): units_worse += 1
print(f"    in UNITS: {100*units_worse/20000:.1f}% of simulated Augusts lose at least this much")

print("\n" + "="*88)
print("  2. DID THE BOARD ITSELF GET HARDER? (environment, not us)")
print("="*88)
bm = collections.defaultdict(list)
for (pl, mk, side, ln), v in bidx.items():
    dt, rec = game_after(pl, v[0][0])
    if not rec or rec[mk] == ln: continue
    bm[(dt[:6], side)].append(1.0 if ((rec[mk] > ln) if side == "Over" else (rec[mk] < ln)) else 0.0)
print(f"    {'month':<10}{'board OVER hit%':>18}{'board UNDER hit%':>19}{'n':>8}")
for mo in sorted({k[0] for k in bm}):
    o_, u_ = bm.get((mo, "Over"), []), bm.get((mo, "Under"), [])
    if len(o_) < 100: continue
    print(f"    {mo:<10}{100*sum(o_)/len(o_):>17.1f}%{100*sum(u_)/len(u_):>18.1f}%{len(o_):>8}")
print("    a big swing here means the whole board moved, and our month says nothing about us.")

print("\n" + "="*88)
print("  3. COMPOSITION - are we betting different things in August?")
print("="*88)
for mo in sorted({r["mo"] for r in KEEP}):
    rows = [r for r in KEEP if r["mo"] == mo]
    srcs = collections.Counter(r["src"] for r in rows).most_common(4)
    ov = sum(1 for r in rows if r["side"] == "Over")/len(rows)
    print(f"    {mo}  n={len(rows):<4} overs {100*ov:3.0f}%  avg odds "
          f"{sum(r['odds'] for r in rows)/len(rows):.2f}  "
          f"srcs {', '.join(f'{s}:{c}' for s, c in srcs)}")

print("\n" + "="*88)
print("  4. WHERE DID AUGUST'S LOSSES ACTUALLY COME FROM?")
print("="*88)
print(f"    {'src':<14}{'n':>5}{'W-L':>10}{'win%':>8}{'units':>9}")
for src, c in collections.Counter(r["src"] for r in aug).most_common():
    rows = [r for r in aug if r["src"] == src]
    w = sum(1 for r in rows if r["won"])
    print(f"    {src:<14}{len(rows):>5}{f'{w}-{len(rows)-w}':>10}{100*w/len(rows):>7.0f}%{u(rows):>+9.2f}")
print(f"\n    by side:")
for sd_ in ("Over", "Under"):
    rows = [r for r in aug if r["side"] == sd_]
    if rows:
        w = sum(1 for r in rows if r["won"])
        print(f"      {sd_:<7} n={len(rows):<4} {w}-{len(rows)-w}  {100*w/len(rows):.0f}%  {u(rows):+.2f}u")

print("\n" + "="*88)
print("  5. WHAT IF WE ONLY RAN FLIP? (and the under-side question, settled)")
print("="*88)
fl = [r for r in M if r["src"].startswith("flip")]
print(f"    flip family sides: {dict(collections.Counter(r['side'] for r in fl))}")
print(f"    -> a flip IS an under-pick whose line collapsed, so the bet is always the OVER.")
print(f"       There is no 'flip under' to run. Here is flip on its own:\n")
print(f"    {'month':<10}{'n':>5}{'W-L':>10}{'win%':>8}{'units':>9}{'ROI':>9}")
for scope, rows_all in (("ALL flip bets", fl),
                        ("flip + skip-drift", [r for r in fl if r["drift"] is not None and r["drift"] < 0.01])):
    print(f"    --- {scope} ---")
    for mo in sorted({r["mo"] for r in rows_all}):
        rows = [r for r in rows_all if r["mo"] == mo]
        if len(rows) < 5: continue
        w = sum(1 for r in rows if r["won"])
        print(f"    {mo:<10}{len(rows):>5}{f'{w}-{len(rows)-w}':>10}{100*w/len(rows):>7.0f}%"
              f"{u(rows):>+9.2f}{100*u(rows)/len(rows):>8.1f}%")
    w = sum(1 for r in rows_all if r["won"])
    print(f"    {'TOTAL':<10}{len(rows_all):>5}{f'{w}-{len(rows_all)-w}':>10}"
          f"{100*w/len(rows_all):>7.0f}%{u(rows_all):>+9.2f}{100*u(rows_all)/len(rows_all):>8.1f}%\n")
print("    and for completeness, EVERY under bet we have ever logged:")
un = [r for r in M if r["side"] == "Under"]
w = sum(1 for r in un if r["won"])
print(f"      n={len(un)}  {w}-{len(un)-w}  {100*w/len(un):.1f}%  {u(un):+.2f}u  "
      f"ROI {100*u(un)/len(un):+.1f}%")

print("\n" + "="*88)
print("  6. THE ELEPHANT: split the whole menu by SIDE")
print("="*88)
print(f"    {'scope':<28}{'n':>6}{'W-L':>11}{'win%':>8}{'units':>10}{'ROI':>9}")
for lbl, rows in (("EVERY bet we ever logged", M),
                  ("  all OVER bets", [r for r in M if r["side"] == "Over"]),
                  ("  all UNDER bets", [r for r in M if r["side"] == "Under"])):
    w = sum(1 for r in rows if r["won"])
    print(f"    {lbl:<28}{len(rows):>6}{f'{w}-{len(rows)-w}':>11}{100*w/len(rows):>7.1f}%"
          f"{u(rows):>+10.2f}{100*u(rows)/len(rows):>8.1f}%")
print("\n    overs by month:")
ov = [r for r in M if r["side"] == "Over"]
for mo in sorted({r["mo"] for r in ov}):
    rows = [r for r in ov if r["mo"] == mo]
    if len(rows) < 20: continue
    w = sum(1 for r in rows if r["won"])
    print(f"      {mo}  n={len(rows):<4} {w}-{len(rows)-w}  {100*w/len(rows):5.1f}%  "
          f"{u(rows):+8.2f}u  ROI {100*u(rows)/len(rows):+6.1f}%")
print("\n    unders by month:")
un2 = [r for r in M if r["side"] == "Under"]
for mo in sorted({r["mo"] for r in un2}):
    rows = [r for r in un2 if r["mo"] == mo]
    if len(rows) < 20: continue
    w = sum(1 for r in rows if r["won"])
    print(f"      {mo}  n={len(rows):<4} {w}-{len(rows)-w}  {100*w/len(rows):5.1f}%  "
          f"{u(rows):+8.2f}u  ROI {100*u(rows)/len(rows):+6.1f}%")
w = sum(1 for r in un2 if r["won"]); n = len(un2)
z = (w/n - 0.467)/math.sqrt(0.467*0.533/n)
print(f"\n    unders vs the board's own 46.7% under baseline: we hit {100*w/n:.1f}%, z={z:+.2f}")
print(f"    -> we are not even picking unders BADLY. The under side of this board simply does")
print(f"       not pay: the board prices it {100*(0.467*1.85-1):+.1f}% and we are getting exactly that.")
