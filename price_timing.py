# price_timing.py - two operational questions:
#   A) the book hangs a line ABOVE recent form. Betting the UNDER there loses. So what about
#      FADING that - taking the OVER anyway, at the board's real over price?
#   B) WHEN IS THE PRICE HIGHEST? Higher odds = better for us. If the board is systematically
#      more generous at some hour, that is free money with no model at all - you just place the
#      same bet at a better time.
# ---------------------------------------------------------------------------------------------
# On (A): careful. Overs beat unders on this board no matter what (53.4% vs 46.7%), so a cell
# that says "bet the over" will look good for reasons that have nothing to do with the gap. It
# is only interesting if it beats the OVER baseline, not zero. That is how newunder fooled us.
#
# On (B): a price series has to be normalised before averaging. A prop at 2.30 and a prop at 1.70
# are not comparable in raw terms, so every capture is divided by that night's own mean price for
# that selection. A value of 1.02 means "2% better odds than this prop's typical price".
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

games = {}
for g in load("data/games_2026.csv"):
    games[g.get("game_id")] = dict(date=g.get("date",""), tip=ts(g.get("tip")))
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
        if pre: pergame[(pl, mk, dt)].setdefault(ln, {})[side] = (pre, rec["tip"])

P = []
for (pl, mk, dt), lines in pergame.items():
    ln, sides = max(lines.items(), key=lambda kv: sum(len(x[0]) for x in kv[1].values()))
    if "Over" not in sides or "Under" not in sides: continue
    a = ANCH.get((pl, mk, dt))
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if a is None or rec is None or rec[mk] == ln: continue
    ov, tip = sides["Over"]; un, _ = sides["Under"]
    P.append(dict(pl=pl, mk=mk, date=dt, tip=tip, line=ln, gap=ln - a,
                  over_series=ov, under_series=un,
                  over_odds=ov[-1][1], under_odds=un[-1][1], over_won=rec[mk] > ln))
P.sort(key=lambda r: r["date"])
print(f"{len(P)} player-market-games with a two-sided series and a causal anchor\n")

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
print("  A. BOOK IS HIGH -> FADE IT AND TAKE THE OVER ANYWAY (at the real over price)")
print("="*88)
print("    graded against the 53.4% OVER baseline, so this only counts if it beats other overs")
for lo, hi, nm in ((0,1,"gap 0 to +1"), (1,2,"gap +1 to +2"), (2,3,"gap +2 to +3"),
                   (3,4,"gap +3 to +4"), (4,6,"gap +4 to +6"), (6,8,"gap +6 to +8"),
                   (8,99,"gap >= +8")):
    cell([r for r in P if lo <= r["gap"] < hi], "Over", f"      {nm}", minn=20)
HI = [r for r in P if r["gap"] >= 4]
cell(HI, "Over", "      ALL gap >= +4, take the OVER", minn=25)
if len(HI) >= 50:
    h = len(HI)//2
    cell(HI[:h], "Over", "        first half", minn=20)
    cell(HI[h:], "Over", "        second half", minn=20)
print("\n    NOTE the trap: 'bet the over' is a winning-looking instruction on a board where overs")
print("    hit 53.4% and unders 46.7%. Only the LIFT column tells you if the gap added anything.")

print("\n" + "="*88)
print("  B. WHEN IS THE PRICE HIGHEST? (higher odds = better for us, same bet, better payout)")
print("="*88)
# normalise each capture against its own night's mean price for that selection
BUCK = [(24, 12, "12-24h before"), (12, 8, "8-12h"), (8, 6, "6-8h"), (6, 4, "4-6h"),
        (4, 3, "3-4h"), (3, 2, "2-3h"), (2, 1.5, "90m-2h"), (1.5, 1, "1-90m"),
        (1, 0.5, "30-60m"), (0.5, 0, "under 30m")]
rel = collections.defaultdict(list)
best_at = collections.Counter(); tot_series = 0
for r in P:
    s = r["over_series"]
    if len(s) < 4: continue
    tot_series += 1
    mean_o = sum(o for _, o in s)/len(s)
    if mean_o <= 0: continue
    hrs = [( (r["tip"]-t).total_seconds()/3600, o) for t, o in s]
    for h_, o in hrs:
        for hi, lo, nm in BUCK:
            if lo <= h_ < hi: rel[nm].append(o/mean_o); break
    bh, bo = max(hrs, key=lambda x: x[1])
    for hi, lo, nm in BUCK:
        if lo <= bh < hi: best_at[nm] += 1; break
print(f"    {tot_series} prop series with 4+ captures\n")
print(f"    {'window before tip':<20}{'captures':>10}{'avg price vs own mean':>24}{'best price here':>18}")
for hi, lo, nm in BUCK:
    v = rel.get(nm, [])
    if len(v) < 30:
        print(f"    {nm:<20}{len(v):>10}      too few"); continue
    m = sum(v)/len(v)
    print(f"    {nm:<20}{len(v):>10}{100*(m-1):>+22.2f}%{100*best_at[nm]/max(1,tot_series):>17.0f}%")
print("\n    'avg price vs own mean' above 0 = the board is MORE generous in that window.")
print("    'best price here' = share of props whose single best price of the night landed there.")

print("\n" + "="*88)
print("  B2. SAME QUESTION BY CLOCK TIME (your local time, WIB = UTC+7)")
print("="*88)
byhour = collections.defaultdict(list)
for r in P:
    s = r["over_series"]
    if len(s) < 4: continue
    mean_o = sum(o for _, o in s)/len(s)
    if mean_o <= 0: continue
    for t, o in s:
        byhour[(t + datetime.timedelta(hours=7)).hour].append(o/mean_o)
print(f"    {'WIB hour':<12}{'captures':>10}{'avg price vs own mean':>26}")
for hh in range(24):
    v = byhour.get(hh, [])
    if len(v) < 100: continue
    print(f"    {hh:02d}:00{'':<7}{len(v):>10}{100*(sum(v)/len(v)-1):>+24.2f}%")

print("\n" + "="*88)
print("  B3. AND FOR THE BAND THAT PASSED THE GATE (gap -6..-3): when to place THOSE")
print("="*88)
BAND = [r for r in P if -6 <= r["gap"] < -3 and len(r["over_series"]) >= 4]
print(f"    {len(BAND)} qualifying props with enough captures")
relb = collections.defaultdict(list)
for r in BAND:
    s = r["over_series"]; mean_o = sum(o for _, o in s)/len(s)
    if mean_o <= 0: continue
    for t, o in s:
        h_ = (r["tip"]-t).total_seconds()/3600
        for hi, lo, nm in BUCK:
            if lo <= h_ < hi: relb[nm].append(o/mean_o); break
for hi, lo, nm in BUCK:
    v = relb.get(nm, [])
    if len(v) < 20: continue
    print(f"    {nm:<20}{len(v):>8} captures   avg price {100*(sum(v)/len(v)-1):+.2f}% vs own mean")
print("\n    if the good window differs for this band, that is where the alert should fire.")

print("\n" + "="*88)
print("  B4. WHAT IS PERFECT TIMING EVEN WORTH? and is any window genuinely over-represented?")
print("="*88)
# the 'best price here' column above is CONFOUNDED: windows we sample more often win the maximum
# more often just by having more chances. Normalise by each window's share of all captures.
capshare = collections.Counter(); bestshare = collections.Counter(); spans = []
for r in P:
    s = r["over_series"]
    if len(s) < 4: continue
    mean_o = sum(o for _, o in s)/len(s)
    mx = max(o for _, o in s); mn = min(o for _, o in s)
    if mean_o <= 0 or mn <= 0: continue
    spans.append((mx/mean_o - 1, mx/mn - 1, mx/s[-1][1] - 1))
    for t, o in s:
        h_ = (r["tip"]-t).total_seconds()/3600
        for hi, lo, nm in BUCK:
            if lo <= h_ < hi: capshare[nm] += 1; break
    bt = max(s, key=lambda x: x[1])[0]
    bh = (r["tip"]-bt).total_seconds()/3600
    for hi, lo, nm in BUCK:
        if lo <= bh < hi: bestshare[nm] += 1; break
tc = sum(capshare.values()); tb = sum(bestshare.values())
print(f"    {'window':<20}{'% of captures':>15}{'% of peaks':>13}{'ratio':>9}")
for hi, lo, nm in BUCK:
    if capshare[nm] < 50: continue
    cs, bs = capshare[nm]/tc, bestshare[nm]/tb
    print(f"    {nm:<20}{100*cs:>14.1f}%{100*bs:>12.1f}%{bs/cs if cs else 0:>9.2f}")
print("    ratio 1.00 = that window produces peaks exactly as often as we look at it.")
print("    Nothing meaningfully above 1.00 means there is no hour when the board is generous.")
if spans:
    a = sum(x[0] for x in spans)/len(spans)
    b = sum(x[1] for x in spans)/len(spans)
    c = sum(x[2] for x in spans)/len(spans)
    print(f"\n    THE PRIZE for perfect timing, {len(spans)} props:")
    print(f"      best price vs that prop's average price   {100*a:+.2f}%")
    print(f"      best price vs that prop's WORST price      {100*b:+.2f}%")
    print(f"      best price vs the CLOSING price            {100*c:+.2f}%")
    print(f"    -> perfect hindsight timing is worth about {100*a:.1f}% per bet. Real, but it")
    print(f"       requires knowing the peak in advance, and the table above says no window")
    print(f"       predicts it. Against a 7.0% pricing disadvantage it is not the lever.")
