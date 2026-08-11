# ml_prop_link.py - is there a tradeable link between PLAYER-PROP drift and the MONEYLINE?
# ---------------------------------------------------------------------------------------------
# New data: wnba_odds_history.csv, a no-vig moneyline time series over ~216 games since 2026-05-31.
# That is far more history than our own 40 slates of prop captures, and it lets us ask three things
# our own data could not:
#   1 Does the MONEYLINE itself move informatively? (the same drift question, on a market that is
#     100x more liquid than a WNBA player prop - if drift works anywhere it should work here)
#   2 Do prop drift and ML drift move TOGETHER? If a team's props are being marked down while its
#     ML is not, one of the two is stale - and the stale one is where an edge would live.
#   3 Does prop drift predict the ML move, early enough to trade the ML?
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
ODDS = r"C:\Users\Axioo\Downloads\wnba_odds_history.csv"
def load(p):
    return list(csv.DictReader(open(p, encoding="utf-8", errors="replace"))) if os.path.exists(p) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def stat(xs, label, show=True):
    n = len(xs)
    if n < 10:
        if show: print(f"    {label:<48} n={n} (too few)")
        return None
    m = sum(xs)/n; sd = (sum((x-m)**2 for x in xs)/(n-1))**.5
    t = m/(sd/math.sqrt(n)) if sd else 0
    if show: print(f"    {label:<48} n={n:<4} mean={m*100:+6.1f}%  t={t:+5.2f}")
    return n, m*100, t

FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

# ---- results ------------------------------------------------------------------------------------
res = {}
for g in load(os.path.join(D, "data", "games_2026.csv")):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None or as_ is None: continue
    res[(g.get("date", ""), g.get("home"), g.get("away"))] = (hs, as_)

# ---- moneyline series, one per game --------------------------------------------------------------
rows = load(ODDS)
print(f"loaded {len(rows)} moneyline snapshots")
ml = collections.defaultdict(list)
for r in rows:
    t, c = f(r.get("ts")), ts(r.get("commence"))
    hp, ap = f(r.get("home_novig")), f(r.get("away_novig"))
    if not (t and c and hp and ap): continue
    ml[(c, r.get("home"), r.get("away"))].append((datetime.datetime.fromtimestamp(t, datetime.timezone.utc), hp, ap))

games = []
for (c, home, away), s in ml.items():
    s.sort()
    if len(s) < 3: continue
    hab, aab = FULL2AB.get(home), FULL2AB.get(away)
    key = (c.strftime("%Y%m%d"), hab, aab)
    sc = res.get(key)
    if not sc:                                   # tips can straddle midnight UTC
        key2 = ((c - datetime.timedelta(hours=6)).strftime("%Y%m%d"), hab, aab)
        sc = res.get(key2)
    if not sc: continue
    open_h, close_h = s[0][1], s[-1][1]
    # the price 2h out, for the causal version
    pre = [x for x in s if x[0] <= c - datetime.timedelta(hours=2)]
    h2 = pre[-1][1] if pre else None
    games.append(dict(commence=c, home=hab, away=aab, hs=sc[0], as_=sc[1],
                      open_h=open_h, close_h=close_h, h2=h2,
                      home_won=sc[0] > sc[1], span_h=(s[-1][0]-s[0][0]).total_seconds()/3600,
                      nobs=len(s)))
print(f"matched {len(games)} games to results  "
      f"(median {sorted(g['nobs'] for g in games)[len(games)//2]} snapshots, "
      f"median span {sorted(g['span_h'] for g in games)[len(games)//2]:.1f}h)")

print("\n" + "="*78)
print("  1. DOES THE MONEYLINE MOVE INFORMATIVELY? (steam-chasing test)")
print("="*78)
# if the market is efficient, a team whose win prob ROSE should NOT be a profitable bet at the close
mv = sorted(games, key=lambda g: g["close_h"] - g["open_h"])
k = len(mv)//3
for nm, grp in (("home prob FELL most", mv[:k]), ("middle", mv[k:2*k]), ("home prob ROSE most", mv[2*k:])):
    d = sum(g["close_h"]-g["open_h"] for g in grp)/len(grp)
    w = sum(g["home_won"] for g in grp)/len(grp)
    exp = sum(g["close_h"] for g in grp)/len(grp)
    print(f"    {nm:<24} move={d*100:+5.1f}pp   home won {w*100:4.0f}%   "
          f"closing line implied {exp*100:4.0f}%   edge {100*(w-exp):+5.1f}pp")
print("    -> if 'edge' is ~0 the closing line is efficient and the MOVE carries no extra info")

print("\n" + "="*78)
print("  2. BET THE STEAM: back the side the money moved toward, at the CLOSING price")
print("="*78)
for thr in (0.02, 0.04, 0.06):
    rets = []
    for g in games:
        d = g["close_h"] - g["open_h"]
        if abs(d) < thr: continue
        back_home = d > 0
        p = g["close_h"] if back_home else 1 - g["close_h"]
        if p <= 0.01 or p >= 0.99: continue
        won = g["home_won"] if back_home else not g["home_won"]
        rets.append((1/p - 1) if won else -1.0)   # no-vig price = fair, so this is the pure test
    stat(rets, f"back the steam when |move| >= {thr*100:.0f}pp (fair price)")
print("    NOTE: paid at the NO-VIG price. A real book charges ~4-5% vig, so anything under")
print("    +5% here is a loser in practice.")

print("\n" + "="*78)
print("  3. FADE THE STEAM: back the side the money moved AWAY from")
print("="*78)
for thr in (0.02, 0.04, 0.06):
    rets = []
    for g in games:
        d = g["close_h"] - g["open_h"]
        if abs(d) < thr: continue
        back_home = d < 0                          # opposite of the move
        p = g["close_h"] if back_home else 1 - g["close_h"]
        if p <= 0.01 or p >= 0.99: continue
        won = g["home_won"] if back_home else not g["home_won"]
        rets.append((1/p - 1) if won else -1.0)
    stat(rets, f"fade the steam when |move| >= {thr*100:.0f}pp (fair price)")

print("\n" + "="*78)
print("  1b. IS THAT +11.1pp CELL REAL? (it is the only interesting number above)")
print("="*78)
grp = mv[2*k:]
w = sum(g["home_won"] for g in grp); n = len(grp)
exp = sum(g["close_h"] for g in grp)
# binomial test against the SUM of closing probabilities, which is the fair expectation
sd = math.sqrt(sum(p*(1-p) for p in (g["close_h"] for g in grp)))
z = (w - exp)/sd
print(f"    home won {w}/{n}, closing line expected {exp:.1f}")
print(f"    z={z:+.2f}  p={math.erfc(abs(z)/math.sqrt(2)):.3f}")
rets = [(1/g["close_h"] - 1) if g["home_won"] else -1.0 for g in grp if 0.02 < g["close_h"] < 0.98]
stat(rets, "backing HOME in that tercile, at the fair price")
print("    multiplicity: this is 1 cell of ~20 tests run today. At p=0.05 you expect 1 false hit.")

print("\n" + "="*78)
print("  4. THE LINK: do a team's PROP drifts and its MONEYLINE move together?")
print("="*78)
gdate = {g.get("game_id"): g.get("date", "") for g in load(os.path.join(D, "data", "games_2026.csv"))}
pteam = {}
for r in load(os.path.join(D, "data", "box_2026.csv")):
    d, pl, tm = gdate.get(r.get("game_id"), ""), (r.get("player") or "").lower(), r.get("team") or ""
    if d and pl and tm: pteam[(d, pl)] = tm
ser = collections.defaultdict(list)
for r in load(os.path.join(D, "xbet_board.csv")):
    t, o, ln = ts(r.get("captured_utc")), f(r.get("odds")), f(r.get("line"))
    if t and o and ln is not None and r.get("side") == "Over" and r.get("market") in ("pts","pra","pr","pa"):
        ser[(t.strftime("%Y%m%d"), (r.get("player") or "").lower(), r.get("market"), ln)].append((t, o))
pairs = []
for g in games:
    d8 = g["commence"].strftime("%Y%m%d")
    for team, is_home in ((g["home"], True), (g["away"], False)):
        dr = []
        for (dd, pl, mk, ln), s in ser.items():
            if abs(int(dd) - int(d8)) > 1: continue
            if pteam.get((d8, pl)) != team: continue
            s = sorted(s)
            if len(s) >= 2: dr.append(s[-1][1]/s[0][1] - 1)
        if len(dr) >= 3:
            mlmove = (g["close_h"] - g["open_h"]) * (1 if is_home else -1)
            pairs.append((sum(dr)/len(dr), mlmove, len(dr)))
if len(pairs) >= 20:
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
    n = len(xs); mx, my = sum(xs)/n, sum(ys)/n
    cov = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n
    sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
    r = cov/(sx*sy) if sx and sy else 0
    tt = r*math.sqrt((n-2)/max(1e-9, 1-r*r))
    print(f"    correlation(team mean PROP drift, that team's ML move) = {r:+.3f}   n={n}")
    print(f"    t={tt:+.2f}  p={math.erfc(abs(tt)/math.sqrt(2)):.3f}")
    print("    expected sign: NEGATIVE (props marked down -> ML win prob falls)")
else:
    print(f"    only {len(pairs)} team-games overlap between the prop board and the ML history")
