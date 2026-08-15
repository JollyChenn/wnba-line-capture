# grade_shadow.py - settle the shadow log and print the head-to-head scoreboard.
# ---------------------------------------------------------------------------------------------
# shadow_log.py records what each competing rule would have bet, at decision time. This fills in
# the outcomes and shows all of them side by side, so that in six weeks the choice between
# MODEL_S and its rejected alternatives is made by forward data.
#
# Reads the box score fresh for recent slates (a cached box can be a game behind - that is how a
# Wheeler assist went missing once and graded a win as a loss).
import csv, os, sys, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
FWD = os.path.join(D, "shadow_forward.csv")
if not os.path.exists(FWD):
    print("  no shadow_forward.csv yet"); raise SystemExit

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

gm = {g.get("game_id"): g.get("date", "") for g in load("data/games_2026.csv")}
box = {}
for r in load("data/box_2026.csv"):
    d = gm.get(r.get("game_id"))
    if not d: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    box[(d, (r.get("player") or "").strip().lower())] = dict(
        pts=p_, reb=rb, ast=a, pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)

rows = load("shadow_forward.csv")
graded = 0
for r in rows:
    if (r.get("result") or ""): continue
    day = (r.get("slate") or "").replace("-", "")
    act = box.get((day, (r.get("player") or "").strip().lower()))
    ln = f(r.get("line"))
    if not act or ln is None: continue
    v = act.get(r.get("market"))
    if v is None: continue
    r["result"] = "push" if v == ln else ("WIN" if v > ln else "loss")
    r["actual"] = v
    graded += 1

# MUST match shadow_log.py exactly. It writes `mv`; omitting it here would silently
# drop the column on every rewrite - the file is rewritten in full each run.
COLS = ["slate", "config", "player", "market", "line", "odds", "src",
        "prev_line", "mv", "drift", "logged_utc", "result", "actual"]
tmp = FWD + ".tmp"
with open(tmp, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for r in rows: w.writerow({c: r.get(c, "") for c in COLS})
os.replace(tmp, FWD)                                   # atomic
print(f"  shadow: graded {graded} new, {len(rows)} rows total")

done = [r for r in rows if (r.get("result") or "").upper() in ("WIN", "LOSS", "PUSH")]
if not done:
    print("  shadow: nothing settled yet"); raise SystemExit

def pnl(r):
    res = (r.get("result") or "").upper()
    if res == "PUSH": return 0.0
    o = f(r.get("odds")) or 1.85
    return (o - 1) if res == "WIN" else -1.0

ORDER = ["MODEL_S", "S_prev", "S_loose", "S_drift", "S_filterx", "S_nostar",
         "S_raised", "S_noprev", "OLD_MENU"]
slates = sorted({r["slate"] for r in done})
print("")
print("=" * 96)
print(f"  SHADOW SCOREBOARD - {len(slates)} settled slate(s), {slates[0]} to {slates[-1]}")
print("  MODEL_S is live. The rest are filters that were rejected on backtest and are being")
print("  tracked forward so the decision is eventually made by real data.")
print("=" * 96)
print(f"  {'config':<11} {'record':>8} {'win%':>7} {'units':>9} {'ROI':>8} {'bets/slate':>11}")
for cfg in ORDER:
    g = [r for r in done if r["config"] == cfg]
    if not g:
        print(f"  {cfg:<11} {'-':>8}"); continue
    w = sum(1 for r in g if (r["result"] or "").upper() == "WIN")
    l = sum(1 for r in g if (r["result"] or "").upper() == "LOSS")
    u = sum(pnl(r) for r in g)
    tag = "  <- LIVE" if cfg == "MODEL_S" else ""
    print(f"  {cfg:<11} {f'{w}-{l}':>8} {100*w/len(g):6.1f}% {u:+8.2f}u {100*u/len(g):+7.1f}%"
          f" {len(g)/len(slates):10.1f}{tag}")
print("")
print("  n is tiny. This table is not evidence yet - it is a record being built. The point at")
print("  which it starts to mean anything is ~50 bets on MODEL_S.")

# ---- STAKING OVERLAYS -----------------------------------------------------------------------
# The tier question is NOT a selection question - the picks are identical. It is purely how much
# to put on each one. Because shadow_forward.csv records `src`, every staking scheme can be
# scored on the SAME bets with no re-logging and no second live experiment. That is deliberate:
# running tiered staking live would confound "is the tier right" with "is the model right".
#
# Backtest said flip 2u / rest 1u returns +29.4% vs +23.5% flat, and holds out of sample
# (IN +37.6% -> OUT +24.8%). But that is fitted to flip's +54.8% on n=25, which WILL regress.
# So the tier stays on paper until the forward record says the same thing independently.
S = [r for r in done if r["config"] == "MODEL_S"]
if S:
    print("")
    print("=" * 96)
    print("  STAKING OVERLAYS on the SAME Model S picks - selection identical, only size differs")
    print("=" * 96)
    SCHEMES = [
        ("flat 1u                    <- LIVE", lambda r: 1.0),
        ("flip 2u / rest 1u",                  lambda r: 2.0 if r.get("src") == "flip" else 1.0),
        ("flip 2u / rest 0.5u",                lambda r: 2.0 if r.get("src") == "flip" else 0.5),
        ("flip 3u / rest 1u",                  lambda r: 3.0 if r.get("src") == "flip" else 1.0),
    ]
    print(f"  {'scheme':<36} {'risked':>9} {'profit':>9} {'ROI':>8} {'worst DD':>10}")
    for lbl, stake in SCHEMES:
        risk = sum(stake(r) for r in S)
        prof = sum(stake(r) * pnl(r) for r in S)
        eq = peak = dd = 0.0
        for r in S:
            eq += stake(r) * pnl(r)
            peak = max(peak, eq); dd = min(dd, eq - peak)
        print(f"  {lbl:<36} {risk:8.1f}u {prof:+8.2f}u {100*prof/risk if risk else 0:+7.1f}% {dd:+9.2f}u")
    bysrc = collections.Counter(r.get("src") for r in S)
    print("")
    print("  forward mix so far: " + ", ".join(f"{k} {v}" for k, v in sorted(bysrc.items())))
    fl = [r for r in S if r.get("src") == "flip"]
    ot = [r for r in S if r.get("src") != "flip"]
    for lbl, g in (("flip", fl), ("hotover+overshoot", ot)):
        if len(g) >= 5:
            w = sum(1 for r in g if (r["result"] or "").upper() == "WIN")
            u = sum(pnl(r) for r in g)
            print(f"    {lbl:<20} {w}-{len(g)-w}  {u:+6.2f}u  ROI {100*u/len(g):+6.1f}%")
        else:
            print(f"    {lbl:<20} n={len(g)} - too few to compare tiers yet")
    print("")
    print("  SWITCH RULE: only move off flat 1u when flip has >=25 forward bets AND beats")
    print("  hotover+overshoot by >=15pp of ROI. Anything less is the n=25 backtest talking.")

    # ---- PARLAYS ------------------------------------------------------------------------------
    # Scored on the SAME Model S picks, so this is purely "how to combine them", not a new
    # selection. Pairing is DETERMINISTIC (alphabetical, consecutive, no reuse) because the
    # obvious version - every possible pair - double counts badly: a 7-bet night yields 21
    # overlapping pairs that all win together, which inflated my first backtest to +81.6% ROI
    # and manufactured an apparent leg correlation that was mostly the overlap.
    #
    # PRICING SETTLED 2026-08-15: the user checked at the book. 1.87 x 1.73 = 3.2351 and 1xbet
    # quoted 3.235 - it pays the STRAIGHT PRODUCT, no accumulator margin. So the figures below
    # are real, not an upper bound.
    #
    # AND A CORRECTION TO MY OWN EARLIER OBJECTION. I said a parlay "squares the edge and the
    # error together". That is true of ROI magnitude but NOT of the break-even point, which is
    # identical: a single breaks even at p = 1/o, a pair at p^2 = 1/o^2, i.e. the same p. A
    # parlay is pure leverage - it does not move the threshold at which you start losing.
    # Observed leg clustering (+3.5pp over independence) actually pushes the parlay's break-even
    # BELOW the single's, but that is measured on 21 nights and is the weakest input here.
    byslate = collections.defaultdict(list)
    for r in S: byslate[r["slate"]].append(r)
    p2 = []; pall = []
    for sl, v in byslate.items():
        v = sorted(v, key=lambda r: (r.get("player") or ""))
        for i in range(0, len(v)-1, 2):
            a, b = v[i], v[i+1]
            od = (f(a.get("odds")) or 1.85) * (f(b.get("odds")) or 1.85)
            won = all((x.get("result") or "").upper() == "WIN" for x in (a, b))
            p2.append((od, won))
        if len(v) >= 2:
            od = 1.0
            for x in v: od *= (f(x.get("odds")) or 1.85)
            pall.append((od, all((x.get("result") or "").upper() == "WIN" for x in v), len(v)))
    print("")
    print("=" * 96)
    print("  PARLAYS on the same Model S picks (1u per ticket, assumes the book pays the product)")
    print("=" * 96)
    sw = sum(1 for r in S if (r["result"] or "").upper() == "WIN")
    su = sum(pnl(r) for r in S)
    print(f"  {'singles, flat 1u':<30} {len(S):>4} tickets  {100*sw/len(S):5.1f}%  {su:+8.2f}u"
          f"  ROI {100*su/len(S):+6.1f}%")
    for lbl, g in (("2-leg parlays", [(o, w) for o, w in p2]),
                   ("full-night accumulator", [(o, w) for o, w, _ in pall])):
        if not g:
            print(f"  {lbl:<30} none yet (needs 2+ bets on a slate)"); continue
        w = sum(1 for _, x in g if x)
        u = sum((o-1) if x else -1.0 for o, x in g)
        print(f"  {lbl:<30} {len(g):>4} tickets  {100*w/len(g):5.1f}%  {u:+8.2f}u"
              f"  ROI {100*u/len(g):+6.1f}%  avg odds {sum(o for o, _ in g)/len(g):.2f}")
    if p2:
        exp = (sw/len(S))**2
        act = sum(1 for _, x in p2 if x)/len(p2)
        print(f"  independence check: singles {100*sw/len(S):.1f}% -> pairs should hit "
              f"{100*exp:.1f}%, actual {100*act:.1f}%")
    print("  NOT LIVE - but not because the maths is against it. Book pricing is confirmed fair")
    print("  (straight product), break-even is IDENTICAL to singles, and at equal risk the")
    print("  backtest gives ~3x the profit for ~2x the drawdown. The reason to wait is that both")
    print("  rest on the SAME unproven single-leg edge: leverage applied before the edge is")
    print("  established just makes being wrong more expensive. Revisit at 50 single-leg bets.")
