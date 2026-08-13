# pinn_yardstick.py - now that we can price anything against Pinnacle, point it at OUR OWN strategy.
# ---------------------------------------------------------------------------------------------
# clv_timing.py established that the average 1xbet prop sits 7.0% below Pinnacle's no-vig fair
# price (n=551 time-aligned, t=-42.9). That is a statement about the BOARD. It says nothing yet
# about OUR MENU. Four questions follow directly, and all four are answerable from data we hold:
#
#   1 DOES OUR SIGNAL FIND BETTER-PRICED PROPS? If flip/overshoot/model bets sit at -2% vs fair
#     while the board sits at -7%, the signal is worth something even if its win rate looks flat -
#     it is steering us toward the cheap corner of a expensive board. If our bets are ALSO at -7%,
#     the signal adds nothing on price and every edge has to come from prediction alone.
#
#   2 SHOULD WE JUST BET AT PINNACLE? Pinnacle's WNBA prop hold is ~6-7% two-way, so its posted
#     price is ~3-3.5% below its own fair. 1xbet is 7.0% below. On price alone Pinnacle is about
#     3.5% per bet cheaper. But price is only half of it - see 3.
#
#   3 WHERE DOES A SOFT BOOK ACTUALLY PAY? Not in the price - in the LINE. A book that hangs
#     14.5 when the sharp number is 16.5 has made an error worth far more than 7%. We have never
#     tested this directly. It is the one soft-book play the season has not ruled out.
#
#   4 DOES CLV TELL US ANYTHING? We have 754 graded bets carrying odds_clv. CLV is only a proof
#     instrument if it actually separates winners from losers IN OUR DATA. Test it, do not assume.
import csv, os, sys, math, datetime, collections
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

def summ(xs, label, unit="%", minn=10):
    n = len(xs)
    if n < minn:
        print(f"    {label:<44} n={n} too few"); return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5 if n > 1 else 0
    t = m/(sd/math.sqrt(n)) if sd else 0
    print(f"    {label:<44} n={n:<5} {m*100:+6.1f}{unit}   t={t:+5.2f}")
    return m, t, n

# ---- Pinnacle reference: (date, player, market, side) -> [(t, line, fair)] ----------------------
pinn = collections.defaultdict(list)
for r in load("pinn_snapshots.csv"):
    t, ln, fair = ts(r.get("captured_utc")), f(r.get("pinn_line")), f(r.get("pinn_fair"))
    if t and ln is not None and fair:
        pinn[(d8(r.get("date")), (r.get("player") or "").lower(), r.get("market"), r.get("side"))].append((t, ln, fair))
for v in pinn.values(): v.sort()
mk_cov = collections.Counter(k[2] for k in pinn)
print(f"Pinnacle reference: {sum(len(v) for v in pinn.values())} snapshots, markets {dict(mk_cov)}")
print("NOTE: Pinnacle coverage is overwhelmingly PTS. Anything below is a points-market answer.\n")

# ---- 1. our own menu, priced against fair ------------------------------------------------------
print("="*84)
print("  1. DOES OUR SIGNAL STEER US TO BETTER-PRICED PROPS? (board average is -7.0%)")
print("="*84)
bysrc = collections.defaultdict(list)
matched_bets = []
for b in load("bets_log.csv"):
    ln, o = f(b.get("line")), f(b.get("odds"))
    if ln is None or not o: continue
    key = (d8(b.get("date")), (b.get("player") or "").lower(), b.get("market"), b.get("side"))
    pv = pinn.get(key)
    if not pv: continue
    same = [x for x in pv if abs(x[1] - ln) < 0.01]        # identical line only
    if not same: continue
    bt = ts(b.get("captured_utc"))
    near = min(same, key=lambda x: abs((x[0]-bt).total_seconds())) if bt else same[-1]
    vs_fair = o/near[2] - 1
    bysrc[b.get("src") or "?"].append(vs_fair)
    matched_bets.append(dict(src=b.get("src"), vs_fair=vs_fair, key=key, line=ln, odds=o))
allv = [x for v in bysrc.values() for x in v]
if allv:
    summ(allv, "EVERY logged bet, vs Pinnacle fair")
    for src, v in sorted(bysrc.items(), key=lambda kv: -len(kv[1])):
        summ(v, f"  src = {src}", minn=8)
    print("\n    A src closer to 0% is finding cheaper props. A src at -7% is just taking the board.")
else:
    print("    no overlap between bets_log and Pinnacle on an identical line")

# ---- 2 + 3. the LINE, not the price ------------------------------------------------------------
print("\n" + "="*84)
print("  2. WHERE A SOFT BOOK ACTUALLY PAYS: does 1xbet HANG A DIFFERENT LINE than Pinnacle?")
print("="*84)
games = {}
for g in load("data/games_2026.csv"):
    games[g.get("game_id")] = g.get("date", "")
box = {}
for r in load("data/box_2026.csv"):
    dt = games.get(r.get("game_id"))
    if not dt: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    box[(dt, (r.get("player") or "").lower())] = dict(pts=pts, reb=reb, ast=ast,
                                                      pra=pts+reb+ast, pr=pts+reb, pa=pts+ast)

# best 1xbet price per (date, player, market, side, line) - take the LAST capture of that night
xb = {}
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None): continue
    k = (t.strftime("%Y%m%d"), (b.get("player") or "").lower(), b.get("market"), b.get("side"))
    cur = xb.get(k)
    if cur is None or t > cur[0]: xb[k] = (t, ln, o)

pairs = []
for (dt, pl, mk, side), pv in pinn.items():
    for cand_d in (dt, (datetime.datetime.strptime(dt, "%Y%m%d") - datetime.timedelta(days=1)).strftime("%Y%m%d")) if dt else ():
        x = xb.get((cand_d, pl, mk, side))
        if not x: continue
        pl_line, pl_fair = pv[-1][1], pv[-1][2]
        act = box.get((dt, pl))
        if not act or mk not in act: continue
        gap = x[1] - pl_line                       # 1xbet line MINUS Pinnacle line
        if abs(gap) > 6.0: break                   # a 15-point gap is a bad join, not a soft line
        pairs.append(dict(pl=pl, mk=mk, side=side, date=dt, xline=x[1], xodds=x[2],
                          pline=pl_line, pfair=pl_fair, gap=gap, actual=act[mk]))
        break
print(f"    {len(pairs)} (player, market, side, night) rows where BOTH books posted a line")
if pairs:
    gaps = sorted(p["gap"] for p in pairs)
    same = sum(1 for g in gaps if abs(g) < 0.01)
    print(f"    identical line: {same}/{len(gaps)} ({100*same/len(gaps):.0f}%)   "
          f"|gap|>=1.0: {sum(1 for g in gaps if abs(g)>=1.0)}   "
          f"|gap|>=2.0: {sum(1 for g in gaps if abs(g)>=2.0)}")
    print(f"    gap range {gaps[0]:+.1f} to {gaps[-1]:+.1f}, median {gaps[len(gaps)//2]:+.1f}")
    print("\n    THE PLAY: when 1xbet hangs a LOWER line than the sharp book, take its OVER;")
    print("    when it hangs a HIGHER line, take its UNDER. Graded at 1xbet's own price.")
    for thr in (0.5, 1.0, 1.5, 2.0):
        rets = []
        for p in pairs:
            if p["side"] != "Over": continue
            if p["gap"] <= -thr:                    # 1xbet line is BELOW sharp -> over is cheap
                rets.append((p["xodds"]-1) if p["actual"] > p["xline"] else -1.0)
        summ(rets, f"1xbet line >= {thr} BELOW Pinnacle -> bet its OVER", minn=10)
    for thr in (0.5, 1.0, 1.5, 2.0):
        rets = []
        for p in pairs:
            if p["side"] != "Under": continue
            if p["gap"] >= thr:                     # 1xbet line is ABOVE sharp -> under is cheap
                rets.append((p["xodds"]-1) if p["actual"] < p["xline"] else -1.0)
        summ(rets, f"1xbet line >= {thr} ABOVE Pinnacle -> bet its UNDER", minn=10)
    base_o = [(p["xodds"]-1) if p["actual"] > p["xline"] else -1.0
              for p in pairs if p["side"] == "Over"]
    base_u = [(p["xodds"]-1) if p["actual"] < p["xline"] else -1.0
              for p in pairs if p["side"] == "Under"]
    print()
    summ(base_o, "BASELINE: every 1xbet over, no line filter")
    summ(base_u, "BASELINE: every 1xbet under, no line filter")

# ---- 3. venue math ------------------------------------------------------------------------------
print("\n" + "="*84)
print("  3. SO SHOULD WE BET AT PINNACLE INSTEAD?")
print("="*84)
print("    1xbet posted price      = fair x 0.930   (measured: -7.0%, n=551, t=-42.9)")
print("    Pinnacle posted price   = fair x ~0.966  (~6-7% two-way hold on WNBA props)")
print("    -> on PRICE alone Pinnacle is about 3.6% per bet cheaper. That is the entire")
print("       difference between a -6% strategy and a -2.4% one, and it costs nothing to switch.")
print("    BUT: you cannot measure yourself against the book you are betting into. Betting at")
print("    Pinnacle means the yardstick is gone and every cent has to come from being genuinely")
print("    more accurate than the sharpest WNBA price in the market. That is a much harder game")
print("    than finding 1xbet's mistakes - it is just a cheaper one to lose at.")

# ---- 4. does CLV tell us anything? --------------------------------------------------------------
print("\n" + "="*84)
print("  4. DOES CLV ACTUALLY TELL US ANYTHING? (754 graded bets, tested not assumed)")
print("="*84)
# the result column is written 'WIN' but 'loss' - case matters, and getting it wrong silently
# keeps only the winners and reports a 100% hit rate
gb = [r for r in load("graded_bets.csv") if (r.get("result") or "").upper() in ("WIN", "LOSS")]
print(f"    {len(gb)} settled bets with a result "
      f"({sum(1 for r in gb if (r.get('result') or '').upper()=='WIN')} won)")
def ret(r):
    o = f(r.get("odds")) or 0
    return (o-1) if (r.get("result") or "").upper() == "WIN" else -1.0
def won(r): return (r.get("result") or "").upper() == "WIN"
for name, col in (("odds CLV (price moved our way)", "odds_clv"),
                  ("sharp CLV (vs Pinnacle)", "sharp_odds_clv")):
    have = [r for r in gb if f(r.get(col)) is not None]
    if len(have) < 20:
        print(f"\n    {name}: only {len(have)} bets carry this column"); continue
    pos = [ret(r) for r in have if f(r.get(col)) > 0]
    neg = [ret(r) for r in have if f(r.get(col)) < 0]
    print(f"\n    {name}  -  n={len(have)}")
    summ(pos, "  bets that GOT positive CLV -> ROI")
    summ(neg, "  bets that got negative CLV -> ROI")
    wp = sum(1 for r in have if f(r.get(col)) > 0 and won(r))
    np_ = sum(1 for r in have if f(r.get(col)) > 0)
    wn = sum(1 for r in have if f(r.get(col)) < 0 and won(r))
    nn = sum(1 for r in have if f(r.get(col)) < 0)
    if np_ and nn:
        print(f"      win rate  positive-CLV {100*wp/np_:.1f}% (n={np_})   "
              f"negative-CLV {100*wn/nn:.1f}% (n={nn})   gap {100*(wp/np_-wn/nn):+.1f}pp")
    mean_clv = sum(f(r.get(col)) for r in have)/len(have)
    print(f"      our mean {name.split(' (')[0]}: {mean_clv*100:+.2f}%")

print("\n    HOW TO READ IT: if positive-CLV bets win materially more than negative-CLV ones,")
print("    CLV is a working instrument and our mean CLV is a verdict on the strategy. If the")
print("    two buckets look the same, CLV is measuring noise here and cannot referee anything.")

# ---- 5. reconciling the two results --------------------------------------------------------------
print("\n" + "="*84)
print("  5. IF CLV SEPARATES 15pp, WHY DOESN'T THE DRIFT FILTER EARN ANYTHING?")
print("="*84)
# CLV and drift are the SAME NUMBER with the sign flipped: positive CLV = the price shortened
# after we bet = money agreed with us. So the 15pp gap above and the skip-drift filter are two
# views of one effect. The difference is WHEN you know it and HOW MUCH of the board it touches.
# Section 4 compares the two TAILS and silently drops every flat bet. A live filter cannot do
# that - it has to act on the whole board. So: the same three-way split, causally, at T-2h.
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("side") == "Over" and b.get("market") in ("pts","pra","pr","pa"):
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
blocks = []
for (pl, mk, ln), v in raw.items():
    v.sort(); cur = [v[0]]
    for prev, nxt in zip(v, v[1:]):
        if (nxt[0]-prev[0]).total_seconds() > 12*3600: blocks.append((pl, mk, ln, cur)); cur = []
        cur.append(nxt)
    blocks.append((pl, mk, ln, cur))
gtip = {}
for g in load("data/games_2026.csv"):
    gtip[g.get("game_id")] = (g.get("date",""), ts(g.get("tip")))
pbox = {}
for r in load("data/box_2026.csv"):
    dt, tp = gtip.get(r.get("game_id"), ("", None))
    if not (dt and tp): continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pbox[(dt, (r.get("player") or "").lower())] = dict(tip=tp, pts=pts, reb=reb, ast=ast,
                                                       pra=pts+reb+ast, pr=pts+reb, pa=pts+ast)
rows = []
for pl, mk, ln, s in blocks:
    if len(s) < 2: continue
    cand = [rec for (dt, p2), rec in pbox.items()
            if p2 == pl and s[0][0] <= rec["tip"] <= s[0][0] + datetime.timedelta(hours=36)]
    if not cand: continue
    rec = min(cand, key=lambda r: r["tip"])
    pre = [x for x in s if x[0] <= rec["tip"] - datetime.timedelta(hours=2)]
    if len(pre) < 2: continue
    rows.append(dict(move=pre[-1][1]/pre[0][1]-1, odds=pre[-1][1], won=rec[mk] > ln))
r_ = lambda x: (x["odds"]-1) if x["won"] else -1.0
print(f"    {len(rows)} board props with a causal read at T-2h\n")
summ([r_(x) for x in rows if x["move"] <= -0.01], "SHORTENED >=1% by T-2h (positive CLV so far)")
summ([r_(x) for x in rows if -0.01 < x["move"] < 0.01], "FLAT - the big middle")
summ([r_(x) for x in rows if x["move"] >= 0.01], "DRIFTED >=1% by T-2h (negative CLV so far)")
print(f"\n    share of the board in each bucket: "
      f"shortened {100*sum(1 for x in rows if x['move']<=-0.01)/len(rows):.0f}%  "
      f"flat {100*sum(1 for x in rows if -0.01<x['move']<0.01)/len(rows):.0f}%  "
      f"drifted {100*sum(1 for x in rows if x['move']>=0.01)/len(rows):.0f}%")
print("    -> skip-drift only removes the last bucket. If the board is mostly FLAT, removing")
print("       a small tail cannot move the average much, however right the tail is.")

# ---- 6. THE DECISIVE SPLIT: movement BEFORE the bet vs movement AFTER it ------------------------
print("\n" + "="*84)
print("  6. PAST MOVEMENT vs FUTURE MOVEMENT - these are not the same thing and we mixed them")
print("="*84)
# graded_bets' odds_clv is measured from OUR ENTRY PRICE to the CLOSE - that is the movement
# AFTER we bet. Our skip-drift filter uses movement from the OPEN to NOW - the movement BEFORE
# we bet. They correlate only because they share a segment. Test them separately on the same props.
rows2 = []
for pl, mk, ln, s in blocks:
    if len(s) < 3: continue
    cand = [rec for (dt, p2), rec in pbox.items()
            if p2 == pl and s[0][0] <= rec["tip"] <= s[0][0] + datetime.timedelta(hours=36)]
    if not cand: continue
    rec = min(cand, key=lambda r: r["tip"])
    cut = rec["tip"] - datetime.timedelta(hours=2)
    pre = [x for x in s if x[0] <= cut]; post = [x for x in s if x[0] > cut]
    if len(pre) < 2 or not post: continue
    entry = pre[-1][1]
    rows2.append(dict(past=entry/pre[0][1]-1,          # open -> our entry   (KNOWN when betting)
                      future=entry/post[-1][1]-1,       # our entry -> close  (UNKNOWABLE)
                      odds=entry, won=rec[mk] > ln))
print(f"    {len(rows2)} props that have both a T-2h entry AND later movement\n")
print("    (a) PAST movement - what skip-drift actually uses, and what you CAN see:")
summ([r_(x) for x in rows2 if x["past"] <= -0.01], "  shortened before our bet")
summ([r_(x) for x in rows2 if x["past"] >= 0.01],  "  drifted before our bet  <- we skip these")
print("\n    (b) FUTURE movement - what CLV measures, and what you CANNOT see when betting:")
summ([r_(x) for x in rows2 if x["future"] > 0.005],  "  price SHORTENED after our bet (+CLV)")
summ([r_(x) for x in rows2 if x["future"] < -0.005], "  price LENGTHENED after our bet (-CLV)")
wp = [x for x in rows2 if x["future"] > 0.005]; wn = [x for x in rows2 if x["future"] < -0.005]
if wp and wn:
    a = sum(1 for x in wp if x["won"])/len(wp); b = sum(1 for x in wn if x["won"])/len(wn)
    print(f"      win rate  +CLV {100*a:.1f}% (n={len(wp)})   -CLV {100*b:.1f}% (n={len(wn)})   "
          f"gap {100*(a-b):+.1f}pp")
xs = [x["past"] for x in rows2]; ys = [x["future"] for x in rows2]
n = len(xs); mx, my = sum(xs)/n, sum(ys)/n
sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
rr = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n/(sx*sy) if sx and sy else 0
print(f"\n    correlation(PAST movement, FUTURE movement) = {rr:+.3f}")
print("    -> if this is near zero, knowing the past movement tells you nothing about the")
print("       future movement, and CLV can never be turned into a pre-bet filter.")
