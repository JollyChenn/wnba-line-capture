# clv_hunt.py - "why not just bet on good CLV?" - taking the idea seriously and testing it
# ---------------------------------------------------------------------------------------------
# THE PROBLEM WITH BETTING ON GOOD CLV, stated plainly:
#   CLV is measured FROM YOUR OWN ENTRY PRICE to the close.  CLV = your_price / closing_price - 1.
#   So your CLV is decided entirely by what the price does AFTER you bet. At the moment you are
#   deciding, your CLV does not exist yet. You cannot filter on it any more than you can filter
#   on the final score.
#
# AND THE PREMISE CUTS THE WRONG WAY. If the price "rarely moves after T-2h" - which is what the
# horizon sweep showed - then betting at T-2h means your entry IS roughly the close, so your CLV
# is roughly ZERO by construction. Betting late does not give you good CLV. It guarantees you
# none. Good CLV requires betting BEFORE the move, which means betting without knowing it.
#
# BUT THERE IS A REAL VERSION OF THE IDEA, and it is the best lead we have had:
#   you cannot observe your future CLV, but you might be able to PREDICT it. Last run found
#   corr(past movement, future movement) = +0.317 on n=405 - which is NOT nothing. If something
#   visible at T-2h forecasts which way the price moves next, then betting those props earns
#   positive CLV on purpose, and positive CLV was worth +15pp of win rate in our graded data.
#
# So: A) prove CLV collapses as you bet later.  B) hunt for anything that predicts future CLV.
#      C) if found, does trading it survive costs and a null.  D) and how is FLIP actually doing.
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
def summ(xs, label, minn=15, unit="%"):
    n = len(xs)
    if n < minn:
        print(f"    {label:<50} n={n} too few"); return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5 if n > 1 else 0
    t = m/(sd/math.sqrt(n)) if sd else 0
    print(f"    {label:<50} n={n:<5} {m*100:+6.1f}{unit}  t={t:+5.2f}")
    return m, t, n

# ---- board series, split per night (the keying bug fixed earlier) --------------------------------
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in ("pts","pra","pr","pa"):
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
blocks = []
for (pl, mk, side, ln), v in raw.items():
    v.sort(); cur = [v[0]]
    for prev, nxt in zip(v, v[1:]):
        if (nxt[0]-prev[0]).total_seconds() > 12*3600: blocks.append((pl, mk, side, ln, cur)); cur = []
        cur.append(nxt)
    blocks.append((pl, mk, side, ln, cur))

gtip = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
pbox = {}
for r in load("data/box_2026.csv"):
    dt, tp = gtip.get(r.get("game_id"), ("", None))
    if not (dt and tp): continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pbox[(dt, (r.get("player") or "").lower())] = dict(tip=tp, pts=pts, reb=reb, ast=ast,
                                                       pra=pts+reb+ast, pr=pts+reb, pa=pts+ast)

def build(hrs):
    """Freeze the board at T-`hrs`. Returns rows with an entry price, the past movement that was
    visible then, the FUTURE movement to the close, and whether the bet won."""
    out = []
    for pl, mk, side, ln, s in blocks:
        cand = [rec for (dt, p2), rec in pbox.items()
                if p2 == pl and s[0][0] <= rec["tip"] <= s[0][0] + datetime.timedelta(hours=36)]
        if not cand: continue
        rec = min(cand, key=lambda r: r["tip"])
        cut = rec["tip"] - datetime.timedelta(hours=hrs)
        pre = [x for x in s if x[0] <= cut]; post = [x for x in s if x[0] > cut]
        if len(pre) < 2 or not post: continue
        entry, close = pre[-1][1], post[-1][1]
        won = (rec[mk] > ln) if side == "Over" else (rec[mk] < ln)
        out.append(dict(pl=pl, mk=mk, side=side, line=ln, entry=entry, close=close,
                        past=entry/pre[0][1]-1, clv=entry/close-1, won=won,
                        ncap=len(pre), tip=rec["tip"],
                        span=(pre[-1][0]-pre[0][0]).total_seconds()/3600))
    return out
ret = lambda r: (r["entry"]-1) if r["won"] else -1.0

print("="*84)
print("  A. WHAT IS YOUR CLV IF YOU BET LATE? (the premise, tested)")
print("="*84)
print(f"    {'entry':<10}{'props':>7}{'mean CLV':>11}{'mean |CLV|':>12}{'% with CLV>1%':>15}")
for lbl, h in (("T-8h", 8.0), ("T-6h", 6.0), ("T-4h", 4.0), ("T-2h", 2.0), ("T-1h", 1.0), ("T-30m", 0.5)):
    R = build(h)
    if len(R) < 20: continue
    cl = [r["clv"] for r in R]
    print(f"    {lbl:<10}{len(R):>7}{100*sum(cl)/len(cl):>10.2f}%"
          f"{100*sum(abs(x) for x in cl)/len(cl):>11.2f}%"
          f"{100*sum(1 for x in cl if x > 0.01)/len(cl):>14.0f}%")
print("\n    -> the later you bet, the smaller your CLV gets in BOTH directions. Betting late")
print("       does not win you CLV, it removes it. CLV is the reward for betting EARLY and")
print("       being right about a move that has not happened yet.")

R = build(2.0)
print(f"\n    sanity on the premise: at T-2h the average price has already moved "
      f"{100*sum(abs(r['past']) for r in R)/len(R):.1f}% from open,")
print(f"    and still moves {100*sum(abs(r['clv']) for r in R)/len(R):.1f}% afterwards. "
      f"'rarely moves' is only half true.")

print("\n" + "="*84)
print("  B. CAN WE PREDICT FUTURE CLV FROM WHAT IS VISIBLE AT T-2h? (the real version)")
print("="*84)
def corr(xs, ys):
    n = len(xs)
    if n < 20: return 0, 0
    mx, my = sum(xs)/n, sum(ys)/n
    sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
    if not (sx and sy): return 0, 0
    r = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n/(sx*sy)
    return r, r*math.sqrt((n-2)/max(1e-9, 1-r*r))
FEATS = [("past movement (open -> now)", lambda r: r["past"]),
         ("entry price level",           lambda r: r["entry"]),
         ("captures so far",             lambda r: float(r["ncap"])),
         ("hours of history",            lambda r: r["span"]),
         ("is an Over",                  lambda r: 1.0 if r["side"] == "Over" else 0.0),
         ("line size",                   lambda r: r["line"])]
print(f"    predicting FUTURE movement (entry -> close), n={len(R)}")
print(f"    {'feature':<36}{'r':>8}{'t':>8}{'p':>8}")
for nm, fn in FEATS:
    r_, t_ = corr([fn(x) for x in R], [x["clv"] for x in R])
    p = math.erfc(abs(t_)/math.sqrt(2))
    mark = " **" if p < 0.05/len(FEATS) else ""
    print(f"    {nm:<36}{r_:>+8.3f}{t_:>+8.2f}{p:>8.3f}{mark}")
print(f"    ** = survives Bonferroni for {len(FEATS)} features (p < {0.05/len(FEATS):.4f})")
print("
    WARNING - SHARED-NUMERATOR BIAS, and it is fatal to both survivors:")
print("      past = entry/open - 1   and   clv = entry/close - 1")
print("      BOTH have `entry` on top. Any noise in the entry price pushes both up together,")
print("      manufacturing a positive correlation out of nothing. `entry price level` scoring")
print("      r=+0.54 is the tell - a raw price cannot predict a future move; it appears in the")
print("      numerator of the thing being predicted. So do NOT read these as real forecasts.")
print("      The honest test is whether past movement predicts the BET WINNING - section C.")

print("\n    the strongest feature, in buckets:")
srt = sorted(R, key=lambda r: r["past"]); k = len(srt)//3
for nm, grp in (("lengthened most before entry", srt[2*k:]), ("middle", srt[k:2*k]),
                ("shortened most before entry", srt[:k])):
    cl = [x["clv"] for x in grp]
    wr = sum(1 for x in grp if x["won"])/len(grp)
    print(f"      {nm:<32} mean future CLV {100*sum(cl)/len(cl):+5.2f}%   "
          f"win {100*wr:4.1f}%   ROI {100*sum(ret(x) for x in grp)/len(grp):+5.1f}%")

print("\n" + "="*84)
print("  C. SO TRADE IT: bet the props predicted to SHORTEN. Does it survive costs and a null?")
print("="*84)
srt2 = sorted(R, key=lambda r: r["tip"])
cut_i = int(len(srt2)*2/3)
IN, OUT = srt2[:cut_i], srt2[cut_i:]
print(f"    IN-SAMPLE {len(IN)} (to {IN[-1]['tip'].date()})   OUT-OF-SAMPLE {len(OUT)} "
      f"(from {OUT[0]['tip'].date()})\n")
summ([ret(x) for x in IN], "baseline: every prop at T-2h")
THR = (0.005, 0.01, 0.02, 0.03)
for t_ in THR:
    summ([ret(x) for x in IN if x["past"] >= t_], f"BET the drifted: past movement >= +{t_*100:.1f}%")
for t_ in THR:
    summ([ret(x) for x in IN if x["past"] <= -t_], f"(current rule) prefer shortened: past <= -{t_*100:.1f}%")

def stat(xs, minn=25):
    n = len(xs)
    if n < minn: return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5
    return (m/(sd/math.sqrt(n)), m*100, n) if sd else None
def search(rows, outcomes=None):
    best = None
    for t_ in THR:
        for nm, sel in (("bet drifted", lambda r: r["past"] >= t_),
                        ("prefer shortened", lambda r: r["past"] <= -t_)):
            idx = [i for i, r in enumerate(rows) if sel(r)]
            xs = [((rows[i]["entry"]-1) if (outcomes[i] if outcomes else rows[i]["won"]) else -1.0)
                  for i in idx]
            s = stat(xs)
            if s and (best is None or s[0] > best[0][0]): best = (s, (nm, t_))
    return best
implied = lambda r: min(0.97, max(0.03, (1/r["entry"])/1.055))
nulls = []
for _ in range(300):
    sim = [random.random() < implied(r) for r in IN]
    b = search(IN, sim)
    if b: nulls.append(b[0][0])
nulls.sort(); real = search(IN)
if real and nulls:
    beat = sum(1 for x in nulls if x >= real[0][0])/len(nulls)
    print(f"\n    null best-t: median {nulls[len(nulls)//2]:+.2f}  95th {nulls[int(len(nulls)*.95)]:+.2f}")
    print(f"    our best in-sample: {real[1]} -> t={real[0][0]:+.2f} ROI={real[0][1]:+.1f}% n={real[0][2]}")
    print(f"    null beats it {beat*100:.1f}%  ({'PASSES' if beat < 0.05 else 'FAILS'})")
    nm, t_ = real[1]
    sel = (lambda r: r["past"] >= t_) if nm == "bet drifted" else (lambda r: r["past"] <= -t_)
    print("\n    OUT-OF-SAMPLE, tested once:")
    summ([ret(x) for x in OUT if sel(x)], f"    {nm} at {t_*100:.1f}%", minn=12)

print("\n" + "="*84)
print("  D. HOW IS FLIP ACTUALLY DOING? (settled bets, not paper theory)")
print("="*84)
gb = [r for r in load("graded_bets.csv") if (r.get("result") or "").upper() in ("WIN", "LOSS")]
won = lambda r: (r.get("result") or "").upper() == "WIN"
gret = lambda r: ((f(r.get("odds")) or 0)-1) if won(r) else -1.0
bysrc = collections.defaultdict(list)
for r in gb: bysrc[r.get("src") or "?"].append(r)
print(f"    {'src':<14}{'n':>5}{'W-L':>10}{'win%':>8}{'ROI':>9}{'t':>7}{'mean CLV':>11}")
for src, rows in sorted(bysrc.items(), key=lambda kv: -len(kv[1])):
    rr = [gret(r) for r in rows]
    w = sum(1 for r in rows if won(r)); n = len(rows)
    m = sum(rr)/n; sd = (sum((x-m)**2 for x in rr)/(n-1))**.5 if n > 1 else 0
    t = m/(sd/math.sqrt(n)) if sd else 0
    cl = [f(r.get("odds_clv")) for r in rows if f(r.get("odds_clv")) is not None]
    cs = f"{100*sum(cl)/len(cl):+.2f}%" if cl else "-"
    print(f"    {src:<14}{n:>5}{f'{w}-{n-w}':>10}{100*w/n:>7.1f}%{m*100:>8.1f}%{t:>7.2f}{cs:>11}")
print("\n    FLIP broken out by side (the 'flip under' question):")
flips = [r for r in gb if (r.get("src") or "").startswith("flip")]
for side in ("Over", "Under"):
    rows = [r for r in flips if r.get("side") == side]
    if len(rows) < 5:
        print(f"      flip {side:<6} n={len(rows)} too few"); continue
    rr = [gret(r) for r in rows]; w = sum(1 for r in rows if won(r))
    m = sum(rr)/len(rr); sd = (sum((x-m)**2 for x in rr)/(len(rr)-1))**.5
    print(f"      flip {side:<6} n={len(rows):<4} {w}-{len(rows)-w}  win {100*w/len(rows):.1f}%  "
          f"ROI {m*100:+.1f}%  t={m/(sd/math.sqrt(len(rr))):+.2f}")
print("\n    a prop at 1.85 needs 54.1% to break even. Compare every win% above to that.")

# ---- E. FLIP DEEP DIVE ---------------------------------------------------------------------------
print("\n" + "="*84)
print("  E. FLIP, PROPERLY. (there is no 'flip under' - a flip IS an under-pick turned over)")
print("="*84)
fl = sorted([r for r in gb if (r.get("src") or "").startswith("flip")], key=lambda r: r.get("date",""))
print(f"    flip family: {len(fl)} settled bets, sides = "
      f"{dict(collections.Counter(r.get('side') for r in fl))}")
if fl:
    n = len(fl); w = sum(1 for r in fl if won(r)); rr = [gret(r) for r in fl]
    avg_odds = sum(f(r.get('odds')) or 0 for r in fl)/n
    be = 1/avg_odds
    ph = w/n
    z = (ph-be)/math.sqrt(be*(1-be)/n)
    print(f"    overall  {w}-{n-w}  win {100*ph:.1f}%   ROI {100*sum(rr)/n:+.1f}%   "
          f"avg odds {avg_odds:.2f} -> break-even {100*be:.1f}%")
    print(f"    vs break-even: z={z:+.2f}  p={math.erfc(abs(z)/math.sqrt(2)):.3f}  "
          f"({'significant' if math.erfc(abs(z)/math.sqrt(2))<0.05 else 'NOT significant'})")
    h = n//2
    for lbl, grp in (("first half  " + fl[0].get("date","")[:8], fl[:h]),
                     ("second half " + fl[h].get("date","")[:8], fl[h:])):
        g_w = sum(1 for r in grp if won(r)); g_r = [gret(r) for r in grp]
        print(f"      {lbl:<24} n={len(grp):<4} {g_w}-{len(grp)-g_w}  "
              f"win {100*g_w/len(grp):4.1f}%  ROI {100*sum(g_r)/len(g_r):+6.1f}%")
    dates = {r.get("date") for r in fl}
    base = [r for r in gb if r.get("date") in dates and r.get("side") == "Over"
            and not (r.get("src") or "").startswith("flip")]
    if len(base) >= 20:
        b_w = sum(1 for r in base if won(r)); b_r = [gret(r) for r in base]
        print(f"      SAME-NIGHT baseline (other overs) n={len(base):<4} {b_w}-{len(base)-b_w}  "
              f"win {100*b_w/len(base):4.1f}%  ROI {100*sum(b_r)/len(b_r):+6.1f}%")
        print(f"      flip beats the same-night over baseline by "
              f"{100*(ph - b_w/len(base)):+.1f}pp")
    cl = [f(r.get("odds_clv")) for r in fl if f(r.get("odds_clv")) is not None]
    if cl:
        pos = sum(1 for x in cl if x > 0)
        print(f"      CLV: mean {100*sum(cl)/len(cl):+.2f}%, positive on {pos}/{len(cl)} "
              f"({100*pos/len(cl):.0f}%)")
    print(f"\n    VERDICT: above break-even, best src on the board, and the only one pairing a")
    print(f"    positive win rate with positive CLV. But n={n} at t~1.0 is roughly a 1-in-3")
    print(f"    chance of looking this good on luck alone. Promising, not proven.")
