# ml_pattern_hunt.py - hunt the moneyline history for a real pattern, with the gates that stop
# a search from manufacturing one.
# ---------------------------------------------------------------------------------------------
# THE PROBLEM WITH "FIND A SIGNIFICANT PATTERN": search hard enough over 173 games and something
# will hit p<0.05 by chance. ~20 tests were already run on this data today. So the protocol is:
#
#   1 SPLIT   first 2/3 of games by date = IN-SAMPLE (search here only)
#             last  1/3                  = OUT-OF-SAMPLE (touched once, at the end)
#   2 GRID    a pre-declared hypothesis space, enumerated exhaustively - no hand-picked cells
#   3 SHUFFLE permute the outcomes and re-run the ENTIRE search 400 times. The best t-stat found
#             on shuffled data is what "best of N tests" produces under the null. A real pattern
#             must beat that distribution, not the textbook t=2.
#   4 OOS     the single best in-sample rule is then tested once out-of-sample. No re-picking.
#   5 COST    everything is priced at NO-VIG. A real book takes ~4.5%, so the OOS edge must clear
#             that to be worth anything.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
ODDS = r"C:\Users\Axioo\Downloads\wnba_odds_history.csv"
random.seed(20260811)          # fixed: the shuffle control must be reproducible
MIN_N = 20                     # a cell must have this many bets to be considered at all

def load(p):
    return list(csv.DictReader(open(p, encoding="utf-8", errors="replace"))) if os.path.exists(p) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

res = {}
for g in load(os.path.join(D, "data", "games_2026.csv")):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is not None and as_ is not None:
        res[(g.get("date", ""), g.get("home"), g.get("away"))] = (hs, as_)

ml = collections.defaultdict(list)
for r in load(ODDS):
    t, c = f(r.get("ts")), ts(r.get("commence"))
    hp = f(r.get("home_novig"))
    if t and c and hp: ml[(c, r.get("home"), r.get("away"))].append((datetime.datetime.fromtimestamp(t, datetime.timezone.utc), hp))

G = []
for (c, home, away), s in ml.items():
    s.sort()
    if len(s) < 3: continue
    hab, aab = FULL2AB.get(home), FULL2AB.get(away)
    sc = res.get((c.strftime("%Y%m%d"), hab, aab)) or \
         res.get(((c - datetime.timedelta(hours=6)).strftime("%Y%m%d"), hab, aab))
    if not sc: continue
    pre = [x for x in s if x[0] <= c - datetime.timedelta(hours=2)]
    G.append(dict(c=c, open_h=s[0][1], close_h=s[-1][1],
                  h2=(pre[-1][1] if pre else s[0][1]),
                  home_won=sc[0] > sc[1]))
G.sort(key=lambda g: g["c"])
cut = int(len(G) * 2/3)
IN, OUT = G[:cut], G[cut:]
print(f"{len(G)} games  ->  IN-SAMPLE {len(IN)} (to {IN[-1]['c'].date()})  |  "
      f"OUT-OF-SAMPLE {len(OUT)} (from {OUT[0]['c'].date()})")

# ---- the pre-declared grid ----------------------------------------------------------------------
# Every rule is: pick a SIDE, under a condition on the price and on how it moved. Priced at the
# T-2h no-vig line, which is what you could actually take.
SIDES = ("home", "away")
MOVES = (("any", lambda d: True),
         ("rose>1pp", lambda d: d > 0.01), ("rose>3pp", lambda d: d > 0.03),
         ("fell>1pp", lambda d: d < -0.01), ("fell>3pp", lambda d: d < -0.03),
         ("flat<1pp", lambda d: abs(d) <= 0.01))
BANDS = (("any", 0.0, 1.0), ("dog <40%", 0.0, 0.40), ("even 40-60%", 0.40, 0.60),
         ("fav >60%", 0.60, 1.0), ("big fav >70%", 0.70, 1.0))

def evaluate(games, side, mv, band, outcomes=None):
    """Returns the flat-stake returns of this rule. `outcomes` lets the shuffle control swap in
    permuted results while keeping every price and move identical."""
    _, mvf = mv; _, lo, hi = band
    out = []
    for i, g in enumerate(games):
        d = g["h2"] - g["open_h"]                       # move visible at T-2h
        p = g["h2"] if side == "home" else 1 - g["h2"]  # our side's price at T-2h
        if not (lo <= p < hi): continue
        if not mvf(d if side == "home" else -d): continue
        if p <= 0.02 or p >= 0.98: continue
        hw = outcomes[i] if outcomes is not None else g["home_won"]
        won = hw if side == "home" else not hw
        out.append((1/p - 1) if won else -1.0)
    return out

def tstat(xs):
    n = len(xs)
    if n < MIN_N: return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5
    return (m/(sd/math.sqrt(n)), m*100, n) if sd else None

def search(games, outcomes=None):
    best = None
    for side in SIDES:
        for mv in MOVES:
            for band in BANDS:
                r = tstat(evaluate(games, side, mv, band, outcomes))
                if r and (best is None or r[0] > best[0][0]):
                    best = (r, (side, mv[0], band[0]))
    return best

print("\n=== 2. exhaustive grid on IN-SAMPLE only ===")
ncells = len(SIDES)*len(MOVES)*len(BANDS)
allres = []
for side in SIDES:
    for mv in MOVES:
        for band in BANDS:
            r = tstat(evaluate(IN, side, mv, band))
            if r: allres.append((r, (side, mv[0], band[0])))
allres.sort(key=lambda x: -x[0][0])
print(f"    {ncells} cells declared, {len(allres)} had n>=15")
print(f"    {'rule':<44}{'n':>5}{'ROI':>9}{'t':>7}")
for (t, roi, n), (s, m, b) in allres[:5]:
    print(f"    {s+' | '+m+' | '+b:<44}{n:>5}{roi:>8.1f}%{t:>7.2f}")
best_in, best_rule = allres[0]

print("\n=== 3. SHUFFLE CONTROL - what does the best-of-search produce under the null? ===")
# THE NULL MUST PRESERVE CALIBRATION. A plain permutation of home_won breaks the link between
# price and outcome, so a 20% longshot "wins" 50% of the time and the search finds +150% edges -
# the null then looks STRONGER than reality (median best-t +3.23 vs our +1.01), which is nonsense.
# The right null is "the closing line is correct and the MOVE adds nothing": simulate each game's
# result from its own closing probability. Prices and moves stay exactly as they were.
nulls = []
for _ in range(400):
    sim = [random.random() < g["close_h"] for g in IN]
    b = search(IN, sim)
    if b: nulls.append(b[0][0])
nulls.sort()
p95, p99 = nulls[int(len(nulls)*0.95)], nulls[int(len(nulls)*0.99)]
beat = sum(1 for x in nulls if x >= best_in[0]) / len(nulls)
print(f"    best t on 400 SHUFFLED searches: median {nulls[len(nulls)//2]:+.2f}  "
      f"95th {p95:+.2f}  99th {p99:+.2f}  max {nulls[-1]:+.2f}")
print(f"    our best in-sample t = {best_in[0]:+.2f}")
print(f"    -> shuffled search beats it {beat*100:.1f}% of the time  "
      f"({'PASSES' if beat < 0.05 else 'FAILS'} the multiplicity gate)")

print("\n=== 4. OUT-OF-SAMPLE - the winning rule, tested once ===")
side, mvn, bn = best_rule
mv = next(m for m in MOVES if m[0] == mvn); band = next(b for b in BANDS if b[0] == bn)
o = tstat(evaluate(OUT, side, mv, band))
print(f"    rule: {side} | {mv[0]} | {band[0]}")
print(f"    in-sample      n={best_in[2]:<4} ROI={best_in[1]:+6.1f}%  t={best_in[0]:+5.2f}")
if o: print(f"    OUT-OF-SAMPLE  n={o[2]:<4} ROI={o[1]:+6.1f}%  t={o[0]:+5.2f}")
else: print(f"    OUT-OF-SAMPLE  too few games to test")

print("\n=== 5. COST - no-vig is not a real price ===")
if o:
    print(f"    OOS edge at fair prices        {o[1]:+.1f}%")
    print(f"    a real book takes ~4.5% vig -> {o[1]-4.5:+.1f}% after cost")
    print(f"    {'TRADEABLE' if o[1]-4.5 > 0 and beat < 0.05 else 'NOT TRADEABLE'}")
