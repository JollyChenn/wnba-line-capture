# minutes_spillover.py - minutes ARE predictable. So what does that actually move?
# ---------------------------------------------------------------------------------------------
# Established earlier and not in dispute: a player's minutes next game are forecastable from her own
# recent minutes (prev_min_vs_norm r=+0.257, min_trend r=+0.239, both t>14 on n=3420). What is NOT
# established is that anyone MISPRICES it. This file asks where that forecast could possibly show up.
#
# THE KEY STRUCTURAL FACT: minutes are ZERO-SUM inside a team. Every team plays exactly 200 player-
# minutes. If Player A is forecast +5 minutes, someone else is forecast -5. So a team's TOTAL
# minutes cannot move, and a naive "this team's minutes are up" signal is meaningless by construction.
#
# What CAN move is WHO gets them. If the extra minutes go to a high-scoring-rate player and come off
# a low-rate player, the team should score more at the same pace. That is the only channel through
# which a minutes forecast can reach a team total, a game total, or a spread:
#
#     quality_shift = SUM over players of  (forecast minutes deviation) x (her scoring rate
#                                            MINUS the team's minute-weighted average rate)
#
# Units are POINTS. A quality_shift of +2.0 means the predicted rotation change is worth about two
# extra team points relative to that team playing its normal rotation.
#
# TWO SEPARATE QUESTIONS, tested separately, because they are not the same question:
#   STAGE A  does quality_shift predict the raw outcome at all?   (whole season, ~254 games)
#   STAGE B  does it beat the CLOSING LINE?                        (only where we have lines)
# A can be YES while B is NO - that is what "already priced in" looks like, and it is the single
# most common way a real predictive signal turns out to be worth nothing.
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))

def load(p):
    fp = p if os.path.isabs(p) else os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

# ---- games -----------------------------------------------------------------------------------
games = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None or as_ is None: continue
    games[g.get("game_id")] = dict(gid=g.get("game_id"), date=g.get("date",""), tip=ts(g.get("tip")),
                                   home=g.get("home"), away=g.get("away"), hs=hs, as_=as_)
print(f"{len(games)} finished games")

# ---- player logs, in date order ----------------------------------------------------------------
plog = collections.defaultdict(list)
teamgame = collections.defaultdict(list)          # (gid, team) -> player rows
for r in load("data/box_2026.csv"):
    g = games.get(r.get("game_id"))
    if not g: continue
    rec = dict(gid=g["gid"], date=g["date"], team=r.get("team"), pl=(r.get("player") or "").lower(),
               min=f(r.get("min")) or 0.0, pts=f(r.get("pts")) or 0.0)
    plog[rec["pl"]].append(rec); teamgame[(rec["gid"], rec["team"])].append(rec)
for v in plog.values(): v.sort(key=lambda x: x["date"])

# ---- the causal forecast: minutes and scoring rate from PRIOR GAMES ONLY ------------------------
FC = {}
for pl, v in plog.items():
    for i, g in enumerate(v):
        prev = v[:i]
        if len(prev) < 6: continue
        l10, l3 = prev[-10:], prev[-3:]
        m10 = sum(x["min"] for x in l10)/len(l10)
        if m10 <= 6: continue                              # deep bench: noise, and never in a rotation read
        min_trend = sum(x["min"] for x in l3)/3 - m10      # is she trending up or down?
        prev_dev  = prev[-1]["min"] - m10                  # what did she do last game?
        pred_dev  = 0.5*(min_trend + prev_dev)             # same forecast as minutes_hunt.py
        tot = sum(x["min"] for x in l10)
        if tot <= 0: continue
        FC[(g["gid"], pl)] = dict(min_norm=m10, pred_dev=pred_dev,
                                  rate=sum(x["pts"] for x in l10)/tot)   # points per minute

# ---- team-game aggregation ---------------------------------------------------------------------
def team_norm(team, date, n=10):
    """That team's own trailing points-scored average BEFORE this date - the baseline to beat."""
    hist = []
    for g in games.values():
        if g["date"] >= date: continue
        if g["home"] == team: hist.append((g["date"], g["hs"]))
        elif g["away"] == team: hist.append((g["date"], g["as_"]))
    hist.sort()
    return sum(x[1] for x in hist[-n:])/len(hist[-n:]) if len(hist) >= 5 else None

TG = {}
for (gid, team), rows in teamgame.items():
    g = games.get(gid)
    if not g: continue
    cov = [(r, FC[(gid, r["pl"])]) for r in rows if (gid, r["pl"]) in FC]
    if len(cov) < 6: continue                              # need most of the rotation forecast
    base = sum(fc["min_norm"] for _, fc in cov)
    if base < 120: continue                                # covering under 60% of 200 minutes: skip
    trate = sum(fc["rate"]*fc["min_norm"] for _, fc in cov)/base      # team's normal scoring rate
    TG[(gid, team)] = dict(
        gid=gid, team=team, date=g["date"], is_home=(g["home"] == team),
        pts=(g["hs"] if g["home"] == team else g["as_"]),
        cover=base,
        net_dev=sum(fc["pred_dev"] for _, fc in cov),                 # should be ~0: minutes are zero-sum
        quality_shift=sum(fc["pred_dev"]*(fc["rate"] - trate) for _, fc in cov),
        norm=team_norm(team, g["date"]))
TG = {k: v for k, v in TG.items() if v["norm"] is not None}
print(f"{len(TG)} team-games with a full causal rotation forecast\n")

print("="*84)
print("  SANITY: is the signal even coherent? (minutes are zero-sum; the forecast should know it)")
print("="*84)
nd = sorted(v["net_dev"] for v in TG.values())
qs = sorted(v["quality_shift"] for v in TG.values())
print(f"    net forecast minute change per team  median {nd[len(nd)//2]:+.1f} min   "
      f"(zero-sum says this should sit near 0)")
print(f"    quality_shift (predicted points swing from WHO plays)")
print(f"      median {qs[len(qs)//2]:+.2f}   10th {qs[int(len(qs)*.1)]:+.2f}   "
      f"90th {qs[int(len(qs)*.9)]:+.2f}   range {qs[0]:+.1f} to {qs[-1]:+.1f}")
print(f"    minutes covered by the forecast: median "
      f"{sorted(v['cover'] for v in TG.values())[len(TG)//2]:.0f} of 200")
print("    -> if the 10th-90th spread is under a point, there is nothing here big enough to bet.")

def corr(xs, ys, label, ntest=1):
    n = len(xs)
    if n < 20:
        print(f"    {label:<52} n={n} too few"); return None
    mx, my = sum(xs)/n, sum(ys)/n
    sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
    if not (sx and sy): return None
    r = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n/(sx*sy)
    t = r*math.sqrt((n-2)/max(1e-9, 1-r*r))
    p = math.erfc(abs(t)/math.sqrt(2))
    mark = "**" if p < 0.05/ntest else ("(raw p<.05)" if p < 0.05 else "")
    print(f"    {label:<52} n={n:<5} r={r:+.3f}  t={t:+5.2f}  p={p:.3f} {mark}")
    return r, t, p

print("\n" + "="*84)
print("  STAGE A. DOES IT PREDICT THE RAW OUTCOME? (whole season, no lines involved)")
print("="*84)
NT = 6      # six tests in this block -> Bonferroni threshold p < 0.0083
rows = list(TG.values())
corr([v["quality_shift"] for v in rows], [v["pts"] - v["norm"] for v in rows],
     "quality_shift  ->  team points vs own 10-game norm", NT)
corr([v["net_dev"] for v in rows], [v["pts"] - v["norm"] for v in rows],
     "net_dev (should be dead)  ->  team points vs norm", NT)

pair = collections.defaultdict(dict)
for (gid, team), v in TG.items(): pair[gid]["h" if v["is_home"] else "a"] = v
both = [p for p in pair.values() if "h" in p and "a" in p]
print(f"\n    {len(both)} games where BOTH teams have a forecast (needed for totals and spreads)")
corr([p["h"]["quality_shift"] + p["a"]["quality_shift"] for p in both],
     [(p["h"]["pts"] + p["a"]["pts"]) - (p["h"]["norm"] + p["a"]["norm"]) for p in both],
     "combined quality_shift  ->  GAME TOTAL vs both norms", NT)
corr([p["h"]["quality_shift"] - p["a"]["quality_shift"] for p in both],
     [(p["h"]["pts"] - p["a"]["pts"]) - (p["h"]["norm"] - p["a"]["norm"]) for p in both],
     "quality_shift EDGE (home-away)  ->  MARGIN vs norms", NT)
corr([p["h"]["quality_shift"] - p["a"]["quality_shift"] for p in both],
     [1.0 if p["h"]["pts"] > p["a"]["pts"] else 0.0 for p in both],
     "quality_shift EDGE  ->  home WON (the moneyline)", NT)
corr([abs(p["h"]["quality_shift"]) + abs(p["a"]["quality_shift"]) for p in both],
     [abs((p["h"]["pts"] + p["a"]["pts"]) - (p["h"]["norm"] + p["a"]["norm"])) for p in both],
     "total rotation churn  ->  size of the total surprise", NT)

# ---- STAGE B: the closing line ------------------------------------------------------------------
print("\n" + "="*84)
print("  STAGE B. DOES IT BEAT THE CLOSING LINE? (the only question that pays)")
print("="*84)
FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}
def dec(am):
    a = f(am)
    if a is None or a == 0: return None
    return 1 + a/100 if a > 0 else 1 + 100/abs(a)

# closing snapshot per (game, type): the last capture before tip; among alternate lines pick the
# most balanced one, which is the main market rather than a hook
snap = collections.defaultdict(list)
for r in load("gamelines.csv"):
    t, st = ts(r.get("captured_utc")), ts((r.get("start") or "") + "Z" if r.get("start") else None)
    if not (t and st) or t > st: continue
    pr = (r.get("prices") or "").split(",")
    if len(pr) != 2: continue
    d1, d2 = dec(pr[0]), dec(pr[1])
    if not (d1 and d2): continue
    snap[(r.get("teams"), st, r.get("type"), r.get("side"))].append(
        (t, f(r.get("points")), d1, d2))
close = {}
for k, v in snap.items():
    last_t = max(x[0] for x in v)
    same = [x for x in v if x[0] == last_t and x[1] is not None]
    if same: close[k] = min(same, key=lambda x: abs(x[2]-x[3]))     # most balanced = the main line
print(f"    {len(close)} closing lines parsed from gamelines.csv")

linked = []
for p in both:
    h, a = p["h"], p["a"]
    g = games[h["gid"]]
    hn = next((k for k, ab in FULL2AB.items() if ab == g["home"]), None)
    an = next((k for k, ab in FULL2AB.items() if ab == g["away"]), None)
    if not (hn and an) or not g["tip"]: continue
    key_t = [k for k in close if k[0] == f"{hn}|{an}" and abs((k[1]-g["tip"]).total_seconds()) < 6*3600]
    if not key_t: continue
    st = key_t[0][1]
    tot = close.get((f"{hn}|{an}", st, "total", ""))
    spr = close.get((f"{hn}|{an}", st, "spread", ""))
    linked.append(dict(h=h, a=a, g=g, tot=tot, spr=spr))
print(f"    {len(linked)} games matched to a closing total/spread\n")

def flat(rets, label):
    n = len(rets)
    if n < 20:
        print(f"    {label:<52} n={n} too few to test"); return
    m = sum(rets)/n; sd = (sum((x-m)**2 for x in rets)/(n-1))**.5
    t = m/(sd/math.sqrt(n)) if sd else 0
    print(f"    {label:<52} n={n:<5} ROI={m*100:+6.1f}%  t={t:+5.2f}")

# THE BASELINE FIRST. If overs simply hit in this window, then "bet OVER" cells look good and
# "bet UNDER" cells look terrible for reasons that have nothing to do with our signal. Any cell
# has to be read against this line, not against zero.
b_over, b_under, nov = [], [], 0
for L in linked:
    if not L["tot"]: continue
    _, pts, dov, dun = L["tot"]
    actual = L["h"]["pts"] + L["a"]["pts"]
    if actual == pts: continue
    nov += 1 if actual > pts else 0
    b_over.append((dov-1) if actual > pts else -1.0)
    b_under.append((dun-1) if actual < pts else -1.0)
flat(b_over,  "BASELINE: bet EVERY over, no signal")
flat(b_under, "BASELINE: bet EVERY under, no signal")
print(f"    overs went {nov}/{len(b_over)} = {100*nov/max(1,len(b_over)):.0f}% in this window\n")

for thr in (0.5, 1.0, 2.0):
    r_over, r_under = [], []
    for L in linked:
        if not L["tot"]: continue
        _, pts, dov, dun = L["tot"]
        q = L["h"]["quality_shift"] + L["a"]["quality_shift"]
        actual = L["h"]["pts"] + L["a"]["pts"]
        if actual == pts: continue
        if q >= thr:   r_over.append((dov-1) if actual > pts else -1.0)
        elif q <= -thr: r_under.append((dun-1) if actual < pts else -1.0)
    flat(r_over,  f"rotation says MORE points (shift>=+{thr}) -> bet OVER")
    flat(r_under, f"rotation says FEWER points (shift<=-{thr}) -> bet UNDER")

for thr in (0.5, 1.0, 2.0):
    rets = []
    for L in linked:
        if not L["spr"]: continue
        _, hcap, dh, da = L["spr"]
        q = L["h"]["quality_shift"] - L["a"]["quality_shift"]
        marg = L["g"]["hs"] - L["g"]["as_"]
        if marg + hcap == 0: continue
        if q >= thr:    rets.append((dh-1) if marg + hcap > 0 else -1.0)
        elif q <= -thr: rets.append((da-1) if marg + hcap < 0 else -1.0)
    flat(rets, f"rotation edge >= {thr} pts -> bet that side's SPREAD")

print("\n" + "="*84)
print("  HOW TO READ THIS")
print("="*84)
print("    STAGE A significant + STAGE B flat  =  real signal, already in the price. Unbettable.")
print("    STAGE A flat                        =  the channel does not exist at all.")
print("    Both positive                       =  worth a forward paper tracker, nothing more,")
print("                                           because Stage B here has well under 100 games.")
