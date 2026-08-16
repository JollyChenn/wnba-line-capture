# ml_power.py - can a power rating built from results/box scores beat the moneyline?
# ---------------------------------------------------------------------------------------------
# THE BAR IS HIGH AND WORTH STATING FIRST. wnba_odds_history.csv carries de-vigged probabilities
# at roughly 3.7% vig, i.e. a competent book. To profit we do not need to predict games well - we
# need to predict them BETTER THAN THAT LINE, which already contains every box score we have.
# Our prop edge exists because 1xbet is slow on obscure player numbers; a moneyline is the most
# liquid, most-watched number on the board and has no equivalent blind spot.
#
# WALK-FORWARD THROUGHOUT. Every rating used to predict a game is built only from games that
# finished BEFORE it. That is the one thing that makes or breaks a study like this - a rating
# fitted on the full season would "predict" beautifully and mean nothing.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260827)
D = os.path.dirname(os.path.abspath(__file__))
ODDS = r"C:\Users\Axioo\Downloads\wnba_odds_history.csv"

def load(p, absolute=False):
    fp = p if absolute else os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
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

# ---- results, in order -------------------------------------------------------------------------
GAMES = []
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None or as_ is None: continue
    GAMES.append(dict(date=g.get("date"), home=g.get("home"), away=g.get("away"),
                      hs=hs, as_=as_, margin=hs-as_, hw=hs > as_))
GAMES.sort(key=lambda x: x["date"])
print(f"{len(GAMES)} completed games, {GAMES[0]['date']} to {GAMES[-1]['date']}")

# ---- closing moneyline, per (date, home, away) --------------------------------------------------
mk = {}
for r in load(ODDS, absolute=True):
    c, t = ts(r.get("commence")), f(r.get("ts"))
    hp, hd, ad = f(r.get("home_novig")), f(r.get("home_dec")), f(r.get("away_dec"))
    if not (c and t and hp and hd and ad): continue
    h, a = FULL2AB.get(r.get("home"), ""), FULL2AB.get(r.get("away"), "")
    if not h or not a: continue
    for key in (c.strftime("%Y%m%d"), (c - datetime.timedelta(hours=6)).strftime("%Y%m%d")):
        prev = mk.get((key, h, a))
        if prev is None or t > prev[0]: mk[(key, h, a)] = (t, hp, hd, ad)
print(f"{len(mk)} games with a closing moneyline")

# ---- walk-forward Elo ---------------------------------------------------------------------------
# margin-aware update, home edge estimated from completed games only, nothing peeks forward.
def run(K=20.0, HFA=None):
    R = collections.defaultdict(lambda: 1500.0)
    out = []
    played = 0; hwins = 0
    for g in GAMES:
        # home advantage from games ALREADY played, defaulting to a neutral 0 until we have some
        hfa = HFA if HFA is not None else (60.0 if played < 20 else 400*math.log10(max(hwins/played, .01)/max(1-hwins/played, .01))/2)
        eh = 1/(1+10**(-((R[g["home"]]+hfa)-R[g["away"]])/400))
        row = mk.get((g["date"], g["home"], g["away"]))
        if row and played >= 30:                       # need a burn-in before trusting the rating
            out.append(dict(date=g["date"], home=g["home"], away=g["away"],
                            p_model=eh, p_mkt=row[1], hd=row[2], ad=row[3], hw=g["hw"]))
        mov = math.log(abs(g["margin"]) + 1) * (2.2/((abs(R[g["home"]]-R[g["away"]])*0.001)+2.2))
        s = 1.0 if g["hw"] else 0.0
        delta = K * mov * (s - eh)
        R[g["home"]] += delta; R[g["away"]] -= delta
        played += 1; hwins += 1 if g["hw"] else 0
    return out, R

BETS, R = run()
print(f"{len(BETS)} games predictable walk-forward (after burn-in, with a line)")
print("")

def brier(rows, key): return sum((r[key]-(1.0 if r["hw"] else 0.0))**2 for r in rows)/len(rows)
print("="*100)
print("  1. IS THE RATING ANY GOOD AT ALL? Brier score, lower is better")
print("="*100)
print(f"  market   {brier(BETS,'p_mkt'):.4f}")
print(f"  our Elo  {brier(BETS,'p_model'):.4f}")
print(f"  coin flip 0.2500")
print(f"  -> {'the market is better' if brier(BETS,'p_mkt') < brier(BETS,'p_model') else 'WE ARE BETTER'}")
print("")
print("="*100)
print("  2. BETTING THE DISAGREEMENT - back whichever side our rating likes more than the market")
print("="*100)
def bet(rows, edge_min):
    n = w = 0; u = 0.0
    for r in rows:
        eh, ph = r["p_model"], r["p_mkt"]
        if eh - ph >= edge_min:                       # we like the HOME side
            n += 1; won = r["hw"]; u += (r["hd"]-1) if won else -1.0; w += won
        elif (1-eh) - (1-ph) >= edge_min:             # we like the AWAY side
            n += 1; won = not r["hw"]; u += (r["ad"]-1) if won else -1.0; w += won
    return n, w, u
print(f"  {'edge threshold':<18}{'bets':>6}{'win%':>8}{'units':>10}{'ROI':>9}")
for e in (0.02, 0.04, 0.06, 0.08, 0.10, 0.15):
    n, w, u = bet(BETS, e)
    if n < 20:
        print(f"  {e:<18.2f}{n:>6}   too few"); continue
    print(f"  {e:<18.2f}{n:>6}{100*w/n:>7.1f}%{u:>+9.2f}u{100*u/n:>+8.1f}%")
print("")
print("="*100)
print("  3. THE FAIR CONTROL - the same staking on RANDOM sides, same games")
print("="*100)
for e in (0.02, 0.06, 0.10):
    n, _, _ = bet(BETS, e)
    if n < 20: continue
    sims = []
    for _ in range(2000):
        u = 0.0
        for r in random.sample(BETS, min(n, len(BETS))):
            if random.random() < 0.5: u += (r["hd"]-1) if r["hw"] else -1.0
            else: u += (r["ad"]-1) if not r["hw"] else -1.0
        sims.append(u/n)
    sims.sort()
    real = bet(BETS, e)[2]/n
    beat = sum(1 for x in sims if x >= real)
    print(f"  edge>={e:.2f}  real ROI {100*real:+6.1f}%   random median {100*sims[1000]:+6.1f}%"
          f"   p95 {100*sims[1900]:+6.1f}%   p={beat/2000:.3f}")
print("")
print("="*100)
print("  4. WHERE THE RATING ENDED UP (sanity check that it learned anything)")
print("="*100)
for t, v in sorted(R.items(), key=lambda kv: -kv[1])[:6]:
    print(f"    {t:<5} {v:7.1f}")
print("    ...")
for t, v in sorted(R.items(), key=lambda kv: -kv[1])[-4:]:
    print(f"    {t:<5} {v:7.1f}")
