# audit_signals.py - the careful recheck before anything goes live.
# ---------------------------------------------------------------------------------------------
# I have now compared roughly 8 signals x {raw, filtered} x several price bases. That is a wide
# enough search that "flip + hotover raw looks best" could easily be the lucky corner - which is
# exactly how the gap band died. So this file does four things, in order:
#
#   1 SETTLE THE PRICE BASIS. My tables disagreed because one used the odds LOGGED when the signal
#     fired and another the board's LAST price before tip. Before ranking anything, measure how far
#     apart those are and which one a real bettor gets.
#   2 RANK EVERY SIGNAL on that basis, raw and filtered, with alpha over the matched blind baseline.
#   3 PRICE THE MULTIPLICITY. Re-run the ENTIRE search (every signal x raw/filtered) on simulated
#     outcomes, 400 times, and ask how often chance produces a leader as good as ours.
#   4 SPLIT IN TIME. Anything that survives 1-3 still has to hold in the final third.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
random.seed(20260814)
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
MK = ("pts","pra","pr","pa","reb","ast","ra")

gm = {g["game_id"]: (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not (dt and tp): continue
    p, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=dt, tip=tp, pts=p, reb=rb, ast=a,
        pra=p+rb+a, pr=p+rb, pa=p+a, ra=rb+a))
for v in plog.values(): v.sort(key=lambda x: x["date"])
byp = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v: byp[pl].append((g["tip"], g["date"], g))
for v in byp.values(): v.sort()
def ga(pl, when):
    for tip, dt, rec in byp.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MK:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
pg = collections.defaultdict(dict)
for (pl, mk, side, ln), v in raw.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
    blocks.append(cur)
    for blk in blocks:
        if not blk: continue
        dt, rec = ga(pl, blk[0][0])
        if not rec: continue
        pre = [x for x in blk if x[0] <= rec["tip"]]
        if pre: pg[(pl, mk, dt)].setdefault(ln, {})[side] = pre
BL = {}; tmp = collections.defaultdict(list); main = {}
for (pl, mk, dt), lines in pg.items():
    ln, sides = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
    if "Over" not in sides: continue
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or rec[mk] == ln: continue
    main[(pl, mk, dt)] = ln
    tmp[(mk,"Over")].append(1.0 if rec[mk] > ln else 0.0)
for k, v in tmp.items():
    if len(v) >= 60: BL[k] = sum(v)/len(v)
lh = collections.defaultdict(list)
for (pl, mk, dt), ln in main.items(): lh[(pl, mk)].append((dt, ln))
for v in lh.values(): v.sort()
def prev(pl, mk, dt):
    v = lh[(pl, mk)]; i = next((k for k, x in enumerate(v) if x[0] == dt), None)
    return v[i-1][1] if i is not None and i >= 1 else None
def drift(pl, mk, ln, tip):
    v = [x for x in raw.get((pl, mk, "Over", ln), []) if x[0] <= tip - datetime.timedelta(hours=2)
         and 0 <= (tip-x[0]).total_seconds() <= 36*3600]
    return v[-1][1]/v[0][1] - 1 if len(v) >= 2 else None

# every logged price for a bet, so the price bases can be compared on the SAME bets
byid = collections.defaultdict(list)
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    pl, mk, ln, o = (b.get("player") or "").lower(), b.get("market"), f(b.get("line")), f(b.get("odds"))
    t = ts(b.get("captured_utc"))
    if not (t and o and ln is not None) or mk not in MK: continue
    dt, rec = ga(pl, t)
    if not rec: continue
    byid[(dt, pl, mk)].append((t, o, ln, b.get("src") or "?"))
B = []
for (dt, pl, mk), v in byid.items():
    v.sort()
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or (mk, "Over") not in BL: continue
    first_o, first_ln, src = v[0][1], v[0][2], v[0][3]
    last_o,  last_ln       = v[-1][1], v[-1][2]
    if rec[mk] == first_ln: continue
    cl = main.get((pl, mk, dt))
    close_o = pg[(pl, mk, dt)][cl]["Over"][-1][1] if cl is not None and cl in pg[(pl, mk, dt)] else None
    pv = prev(pl, mk, dt); dr = drift(pl, mk, first_ln, rec["tip"])
    B.append(dict(date=dt, mo=dt[:6], pl=pl, mk=mk, src=src,
                  first=first_o, last=last_o, close=close_o,
                  won=rec[mk] > first_ln, base=BL[(mk,"Over")],
                  passes=(pv is not None and (first_ln-pv) < 0.5 and dr is not None and dr < 0.01)))
B.sort(key=lambda r: r["date"])
print(f"{len(B)} deduped OVER bets with every price basis attached\n")

print("="*112)
print("  1. SETTLE THE PRICE BASIS - how far apart are they, on the SAME bets?")
print("="*112)
have = [r for r in B if r["close"]]
print(f"  {len(have)} bets have all three prices")
fl = sum(r["first"]-r["last"] for r in have)/len(have)
fc = sum(r["first"]-r["close"] for r in have)/len(have)
print(f"    mean FIRST logged price {sum(r['first'] for r in have)/len(have):.3f}")
print(f"    mean LAST  logged price {sum(r['last'] for r in have)/len(have):.3f}   "
      f"(first is {fl:+.3f} better)")
print(f"    mean board CLOSE price  {sum(r['close'] for r in have)/len(have):.3f}   "
      f"(first is {fc:+.3f} better)")
for nm, key in (("first logged", "first"), ("last logged", "last"), ("board close", "close")):
    u = sum((r[key]-1) if r["won"] else -1.0 for r in have)
    print(f"    betting all {len(have)} at the {nm:<13} -> {u:+7.2f}u   ROI {100*u/len(have):+5.1f}%")
print("\n    FIRST is what the alert showed, so it is achievable - but only if you bet immediately.")
print("    The gap between first and close is the cost of hesitating. Everything below uses FIRST,")
print("    and that assumption is the single biggest optimism in these numbers.")

print("\n" + "="*112)
print("  2. EVERY SIGNAL, RAW AND FILTERED")
print("="*112)
def stat(rows, key="first"):
    n = len(rows)
    if n < 20: return None
    w = sum(1 for r in rows if r["won"]); b = sum(r["base"] for r in rows)/n
    u = sum((r[key]-1) if r["won"] else -1.0 for r in rows)
    z = (w/n-b)/math.sqrt(b*(1-b)/n)
    return dict(n=n, w=w, wr=w/n, u=u, roi=u/n, alpha=w/n-b, z=z)
print(f"  {'signal':<14}{'RAW n':>7}{'ROI':>8}{'alpha':>8}{'z':>7}   "
      f"{'FILT n':>7}{'ROI':>8}{'alpha':>8}{'z':>7}   {'filter helps?':>14}")
SRC = [s for s, c in collections.Counter(r["src"] for r in B).most_common() if c >= 25]
for s in SRC:
    a = stat([r for r in B if r["src"] == s])
    fi = stat([r for r in B if r["src"] == s and r["passes"]])
    if not a: continue
    fs = (f"{fi['n']:>7}{100*fi['roi']:>7.1f}%{100*fi['alpha']:>+8.1f}{fi['z']:>7.2f}"
          if fi else f"{'':>7}{'too few':>16}{'':>7}")
    verdict = "" if not fi else ("HELPS" if fi["u"] > a["u"] else f"costs {a['u']-fi['u']:.1f}u")
    print(f"  {s:<14}{a['n']:>7}{100*a['roi']:>7.1f}%{100*a['alpha']:>+8.1f}{a['z']:>7.2f}   "
          f"{fs}   {verdict:>14}")
print()
for nm, sel in (("flip+hotover", lambda r: r["src"] in ("flip","hotover")),
                ("ALL signals",  lambda r: True)):
    a = stat([r for r in B if sel(r)]); fi = stat([r for r in B if sel(r) and r["passes"]])
    if a and fi:
        print(f"  {nm:<14}{a['n']:>7}{100*a['roi']:>7.1f}%{100*a['alpha']:>+8.1f}{a['z']:>7.2f}   "
              f"{fi['n']:>7}{100*fi['roi']:>7.1f}%{100*fi['alpha']:>+8.1f}{fi['z']:>7.2f}   "
              f"{'HELPS' if fi['u']>a['u'] else f'costs {a[chr(39)+chr(39)] if False else a[chr(117)]-fi[chr(117)]:.1f}u':>14}")

print("\n" + "="*112)
print("  3. MULTIPLICITY - re-run the WHOLE search on simulated outcomes, 400x")
print("="*112)
CELLS = [(s, filt) for s in SRC + ["flip+hotover", "ALL"] for filt in (False, True)]
def sel_rows(cell):
    s, filt = cell
    if s == "ALL": rows = B
    elif s == "flip+hotover": rows = [r for r in B if r["src"] in ("flip","hotover")]
    else: rows = [r for r in B if r["src"] == s]
    return [r for r in rows if (r["passes"] or not filt)]
def best(outcomes=None):
    bz = None
    for c in CELLS:
        rows = sel_rows(c)
        n = len(rows)
        if n < 20: continue
        if outcomes is None: w = sum(1 for r in rows if r["won"])
        else: w = sum(1 for r in rows if outcomes[id(r)])
        b = sum(r["base"] for r in rows)/n
        z = (w/n-b)/math.sqrt(b*(1-b)/n)
        if bz is None or z > bz[0]: bz = (z, c, n)
    return bz
nulls = []
for _ in range(400):
    out = {id(r): (random.random() < r["base"]) for r in B}
    bb = best(out)
    if bb: nulls.append(bb[0])
nulls.sort()
real = best()
beat = sum(1 for x in nulls if x >= real[0])/len(nulls)
print(f"  {len(CELLS)} cells searched")
print(f"  null best-z: median {nulls[len(nulls)//2]:+.2f}  95th {nulls[int(len(nulls)*.95)]:+.2f}  "
      f"max {nulls[-1]:+.2f}")
print(f"  our best: {real[1][0]} {'filtered' if real[1][1] else 'raw'} -> z={real[0]:+.2f} (n={real[2]})")
print(f"  chance beats it {100*beat:.1f}% of the time  ({'PASSES' if beat < 0.05 else 'FAILS'})")

print("\n" + "="*112)
print("  4. TIME SPLIT on the leaders")
print("="*112)
cut = int(len(B)*2/3); cutdate = B[cut]["date"]
for nm, sel in (("flip+hotover raw", lambda r: r["src"] in ("flip","hotover")),
                ("flip raw",         lambda r: r["src"] == "flip"),
                ("hotover raw",      lambda r: r["src"] == "hotover"),
                ("ALL + filter X",   lambda r: r["passes"])):
    a = stat([r for r in B[:cut] if sel(r)]); b_ = stat([r for r in B[cut:] if sel(r)])
    fa = f"n={a['n']:<4} ROI {100*a['roi']:+6.1f}% alpha {100*a['alpha']:+5.1f}pp" if a else "too few"
    fb = f"n={b_['n']:<4} ROI {100*b_['roi']:+6.1f}% alpha {100*b_['alpha']:+5.1f}pp" if b_ else "too few"
    print(f"  {nm:<20} first 2/3: {fa:<44} final 1/3: {fb}")
print(f"\n  split at {cutdate}")

print("\n" + "="*112)
print("  5. DOES FILTER X RAISE THE WIN RATE? (win% is what it actually moves, ROI follows)")
print("="*112)
print(f"  {'signal':<16}{'RAW n':>7}{'win%':>8}{'alpha':>8}   {'FILT n':>7}{'win%':>8}{'alpha':>8}"
      f"   {'win% moved':>12}{'units moved':>13}")
def wr(rows):
    n = len(rows)
    if n < 12: return None
    w = sum(1 for r in rows if r["won"]); b = sum(r["base"] for r in rows)/n
    u = sum((r["first"]-1) if r["won"] else -1.0 for r in rows)
    return dict(n=n, wr=w/n, alpha=w/n-b, u=u)
for nm, sel in ([(s, (lambda s: (lambda r: r["src"] == s))(s)) for s in SRC]
                + [("flip+hotover", lambda r: r["src"] in ("flip","hotover")),
                   ("ALL", lambda r: True)]):
    a = wr([r for r in B if sel(r)])
    fi = wr([r for r in B if sel(r) and r["passes"]])
    if not a: continue
    if not fi:
        print(f"  {nm:<16}{a['n']:>7}{100*a['wr']:>7.1f}%{100*a['alpha']:>+8.1f}   "
              f"{'too few':>7}"); continue
    print(f"  {nm:<16}{a['n']:>7}{100*a['wr']:>7.1f}%{100*a['alpha']:>+8.1f}   "
          f"{fi['n']:>7}{100*fi['wr']:>7.1f}%{100*fi['alpha']:>+8.1f}   "
          f"{100*(fi['wr']-a['wr']):>+11.1f}pp{fi['u']-a['u']:>+12.1f}u")
print("\n  filter X raises win% almost everywhere - it just removes so many bets that total")
print("  profit falls. Higher rate, smaller book. That is the entire trade-off in one table.")

print("\n" + "="*112)
print("  6. TWO SEPARATE BETS? - only if the two sets are actually different")
print("="*112)
A = {(r["date"], r["pl"], r["mk"]) for r in B if r["src"] in ("flip","hotover")}
C = {(r["date"], r["pl"], r["mk"]) for r in B if r["passes"]}
both = A & C
print(f"  flip+hotover RAW      {len(A)} bets")
print(f"  ALL + filter X        {len(C)} bets")
print(f"  in BOTH               {len(both)}  ({100*len(both)/len(A):.0f}% of the raw set, "
      f"{100*len(both)/len(C):.0f}% of the filtered set)")
print(f"  union                 {len(A | C)} distinct bets\n")
def show(keys, label):
    rows = [r for r in B if (r["date"], r["pl"], r["mk"]) in keys]
    s = wr(rows)
    if not s: print(f"  {label:<40} too few"); return
    print(f"  {label:<40} n={s['n']:<4} {100*s['wr']:5.1f}%  {s['u']:+7.2f}u  "
          f"ROI {100*s['u']/s['n']:+6.1f}%  alpha {100*s['alpha']:+5.1f}pp")
show(A, "flip+hotover raw alone")
show(C, "filter X alone")
show(A | C, "UNION - take every bet in either")
show(both, "  the overlap (would be double-staked)")
show(A - C, "  raw only, filter X rejects it")
show(C - A, "  filter X only, not a flip/hotover")
print("\n  if the overlap is small the two are genuinely different products and can run side by")
print("  side. If it is large, 'two bets' just means staking the same bet twice.")

print("\n" + "="*112)
print("  7. WHICH HALF OF FILTER X DOES THE WORK ON FLIP+HOTOVER? (and is a tier justified?)")
print("="*112)
FH = [r for r in B if r["src"] in ("flip","hotover")]
byid2 = {}
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    pl, mk, ln = (b.get("player") or "").lower(), b.get("market"), f(b.get("line"))
    t = ts(b.get("captured_utc"))
    if not (t and ln is not None) or mk not in MK: continue
    dt, rec = ga(pl, t)
    if not rec: continue
    k = (dt, pl, mk)
    if k not in byid2: byid2[k] = (ln, rec["tip"])
for r in FH:
    k = (r["date"], r["pl"], r["mk"])
    ln, tip = byid2.get(k, (None, None))
    r["pv"] = prev(r["pl"], r["mk"], r["date"]) if ln is not None else None
    r["dr"] = drift(r["pl"], r["mk"], ln, tip) if ln is not None and tip else None
    r["notraised"] = (r["pv"] is not None and ln is not None and (ln - r["pv"]) < 0.5)
    r["nodrift"] = (r["dr"] is not None and r["dr"] < 0.01)
def s2(rows, label):
    n = len(rows)
    if n < 10: print(f"  {label:<46}n={n} too few"); return
    w = sum(1 for r in rows if r["won"]); b = sum(r["base"] for r in rows)/n
    u = sum((r["first"]-1) if r["won"] else -1.0 for r in rows)
    print(f"  {label:<46}n={n:<4}{w}-{n-w} {100*w/n:5.1f}% {u:+7.2f}u ROI {100*u/n:+6.1f}%"
          f" alpha {100*(w/n-b):+5.1f}pp")
s2(FH, "flip+hotover, everything (the bet list)")
print()
s2([r for r in FH if r["notraised"]], "  book did NOT raise (that half alone)")
s2([r for r in FH if r["nodrift"]],   "  price did NOT drift (that half alone)")
s2([r for r in FH if r["notraised"] and r["nodrift"]], "  BOTH = filter X  <- the star")
print()
s2([r for r in FH if not (r["notraised"] and r["nodrift"])], "  everything filter X does NOT star")
print("\n  A tier is only justified if the starred group is clearly better AND the unstarred group")
print("  is still worth betting. If unstarred loses, it is a gate not a tier.")
