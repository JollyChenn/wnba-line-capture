# winner_profile.py - what does a WINNING over bet look like? price, movement, cross-match, and the
#                     game's own moneyline.
# ---------------------------------------------------------------------------------------------
# We now know the over side plus our signals adds +11.4% over blind selection, and flip adds
# +13.7%. The question is whether anything OBSERVABLE separates the winners from the losers, so
# the alert can rank rather than just fire.
#
# THE CONTROL THAT MAKES THIS HONEST: every cell is scored against the BLIND ROI of the same
# market/side combinations it contains. A subset that happens to be all "pa" bets will look great
# against a flat benchmark, because blind pa overs lose only 0.2% while blind ast overs lose 12.6%.
# Comparing to the matched blind baseline removes that entirely, so what is left is the signal.
#
# FEATURES, all knowable before tip:
#   PRICE            the entry odds - are we better on short favourites or long shots?
#   MOVEMENT         drift at T-2h on our own side
#   CROSS-MATCH      how the book's number moved since her PREVIOUS game (the re-rating)
#   THE GAME'S ML    is her team favourite or underdog, and by how much? Never tested on props.
#                    Real mechanism either way: favourites blow teams out and rest starters, but
#                    underdogs get garbage time. Worth knowing which dominates.
#   GAME TOTAL       is it expected to be a shootout?
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
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
def d8(s):
    s = (s or "").replace("-", "")
    return s[:8] if len(s) >= 8 else ""
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

games = {}
for g in load("data/games_2026.csv"):
    games[g.get("game_id")] = dict(date=g.get("date",""), tip=ts(g.get("tip")),
                                   home=g.get("home"), away=g.get("away"))
plog = collections.defaultdict(list)
teamof = {}
for r in load("data/box_2026.csv"):
    g = games.get(r.get("game_id"))
    if not g or not g["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    rec = dict(date=g["date"], tip=g["tip"], team=r.get("team"), gid=r.get("game_id"),
               pts=pts, reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast)
    plog[(r.get("player") or "").lower()].append(rec)
    teamof[(g["date"], (r.get("player") or "").lower())] = r.get("team")
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

# ---- the game's own moneyline, closing no-vig, keyed by (date, team) ------------------------------
mlrow = {}
ml = collections.defaultdict(list)
for r in load(ODDS, absolute=True):
    t, c = f(r.get("ts")), ts(r.get("commence"))
    hp, ap = f(r.get("home_novig")), f(r.get("away_novig"))
    if t and c and hp and ap:
        ml[(c, r.get("home"), r.get("away"))].append((datetime.datetime.fromtimestamp(t, datetime.timezone.utc), hp, ap))
for (c, home, away), v in ml.items():
    v.sort()
    hab, aab = FULL2AB.get(home), FULL2AB.get(away)
    if not (hab and aab): continue
    for key in (c.strftime("%Y%m%d"), (c - datetime.timedelta(hours=6)).strftime("%Y%m%d")):
        mlrow[(key, hab)] = v[-1][1]           # closing win probability for that team
        mlrow[(key, aab)] = v[-1][2]
print(f"moneyline reference: {len(mlrow)} (date, team) closing win probabilities")

# ---- board, main line per player-market-night, both sides ------------------------------------------
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
        if pre: pergame[(pl, mk, dt)].setdefault(ln, {})[side] = pre

# blind baseline per market+side, and the book's line for a player-market by night
BLIND = {}
tmpB = collections.defaultdict(list)
mainline = {}
for (pl, mk, dt), lines in pergame.items():
    ln, sides = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
    if "Over" not in sides or "Under" not in sides: continue
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or rec[mk] == ln: continue
    mainline[(pl, mk, dt)] = ln
    tmpB[(mk, "Over")].append(1.0 if rec[mk] > ln else 0.0)
    tmpB[(mk, "Under")].append(0.0 if rec[mk] > ln else 1.0)
for k, v in tmpB.items():
    if len(v) >= 80: BLIND[k] = sum(v)/len(v)
lhist = collections.defaultdict(list)
for (pl, mk, dt), ln in mainline.items(): lhist[(pl, mk)].append((dt, ln))
for v in lhist.values(): v.sort()
def prev_book_line(pl, mk, dt):
    v = lhist[(pl, mk)]
    pos = next((i for i, x in enumerate(v) if x[0] == dt), None)
    return v[pos-1][1] if pos is not None and pos >= 1 else None
def drift_at(pl, mk, side, ln, tip):
    v = [x for x in raw.get((pl, mk, side, ln), [])
         if x[0] <= tip - datetime.timedelta(hours=2) and 0 <= (tip-x[0]).total_seconds() <= 36*3600]
    return v[-1][1]/v[0][1] - 1 if len(v) >= 2 else None

# ---- our bets ------------------------------------------------------------------------------------
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
    if not rec or rec[mk] == ln or (mk, side) not in BLIND: continue
    tm = teamof.get((dt, pl))
    pv = prev_book_line(pl, mk, dt)
    M.append(dict(date=dt, mo=dt[:6], pl=pl, mk=mk, side=side, src=src, line=ln, odds=o,
                  won=(rec[mk] > ln) if side == "Over" else (rec[mk] < ln),
                  blind=BLIND[(mk, side)], drift=drift_at(pl, mk, side, ln, rec["tip"]),
                  dline=(ln - pv) if pv is not None else None,
                  winprob=mlrow.get((dt, tm))))
M.sort(key=lambda r: r["date"])
OV = [r for r in M if r["side"] == "Over"]
FL = [r for r in M if r["src"].startswith("flip")]
print(f"{len(M)} deduped bets | {len(OV)} overs | {len(FL)} flip | "
      f"{sum(1 for r in OV if r['winprob'] is not None)} overs have a moneyline\n")

def cell(rows, label, minn=30):
    n = len(rows)
    if n < minn:
        print(f"    {label:<40} n={n} too few"); return
    w = sum(1 for r in rows if r["won"])/n
    b = sum(r["blind"] for r in rows)/n
    roi = sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/n
    z = (w-b)/math.sqrt(b*(1-b)/n)
    print(f"    {label:<40} n={n:<5} win {100*w:5.1f}%  ROI {100*roi:+6.1f}%  "
          f"vs blind {100*b:5.1f}%  alpha {100*(w-b):+5.1f}pp  z={z:+5.2f}")

print("="*102)
print("  0. THE STARTING POINT")
print("="*102)
cell(M,  "everything")
cell(OV, "all OVER bets")
cell(FL, "flip family (all overs)")

print("\n" + "="*102)
print("  1. PRICE - does the entry odds level separate winners?")
print("="*102)
for lo, hi, nm in ((0,1.75,"under 1.75 (short)"), (1.75,1.85,"1.75-1.85"), (1.85,1.95,"1.85-1.95"),
                   (1.95,2.10,"1.95-2.10"), (2.10,99,"2.10+ (longshot)")):
    cell([r for r in OV if lo <= r["odds"] < hi], f"    overs @ {nm}")

print("\n" + "="*102)
print("  2. ODDS MOVEMENT - drift on our own side by T-2h")
print("="*102)
DR = [r for r in OV if r["drift"] is not None]
cell([r for r in DR if r["drift"] <= -0.02], "    shortened 2%+")
cell([r for r in DR if -0.02 < r["drift"] <= -0.005], "    shortened slightly")
cell([r for r in DR if -0.005 < r["drift"] < 0.005], "    flat")
cell([r for r in DR if 0.005 <= r["drift"] < 0.02], "    drifted slightly")
cell([r for r in DR if r["drift"] >= 0.02], "    drifted 2%+")

print("\n" + "="*102)
print("  3. CROSS-MATCH - how the book moved her number since her LAST game")
print("="*102)
CM = [r for r in OV if r["dline"] is not None]
for lo, hi, nm in ((-99,-2,"cut 2+ since last game"), (-2,-0.5,"cut 0.5-2"),
                   (-0.5,0.5,"same number"), (0.5,2,"raised 0.5-2"), (2,99,"raised 2+")):
    cell([r for r in CM if lo <= r["dline"] < hi], f"    book {nm}")

print("\n" + "="*102)
print("  4. THE GAME'S MONEYLINE - never tested on props before")
print("="*102)
WP = [r for r in OV if r["winprob"] is not None]
for lo, hi, nm in ((0,0.30,"heavy underdog <30%"), (0.30,0.45,"underdog 30-45%"),
                   (0.45,0.55,"coin flip"), (0.55,0.70,"favourite 55-70%"),
                   (0.70,1.01,"heavy favourite 70%+")):
    cell([r for r in WP if lo <= r["winprob"] < hi], f"    her team {nm}")
print()
cell([r for r in WP if r["winprob"] >= 0.55], "    ALL favourites")
cell([r for r in WP if r["winprob"] < 0.45],  "    ALL underdogs")

print("\n" + "="*102)
print("  5. THE SAME FOUR, ON FLIP ONLY")
print("="*102)
cell([r for r in FL if r["odds"] >= 1.90], "    flip @ 1.90+")
cell([r for r in FL if r["odds"] < 1.90],  "    flip @ under 1.90")
FD = [r for r in FL if r["drift"] is not None]
cell([r for r in FD if r["drift"] < 0.01], "    flip + skip-drift")
cell([r for r in FD if r["drift"] >= 0.01], "    flip + drifted")
FW = [r for r in FL if r["winprob"] is not None]
cell([r for r in FW if r["winprob"] >= 0.55], "    flip, team favoured")
cell([r for r in FW if r["winprob"] < 0.45],  "    flip, team underdog")

print("\n" + "="*102)
print("  MULTIPLICITY: ~24 cells were inspected above. At p<0.05 you expect roughly one false")
print("  hit by chance, and the Bonferroni bar is p<0.002 (|z|>3.1). Read the z column with that")
print("  in mind, and treat anything that is not ALSO monotone across its ladder as noise.")
print("="*102)

print("\n" + "="*102)
print("  6. WHAT SURVIVES, STACKED - and does it hold in the final third?")
print("="*102)
print("    Of the four features only ONE has a clean monotone ladder: the cross-match line move.")
print("    Price is jumbled (short good, 1.85-1.95 good, 1.95+ dead) and the moneyline peaks in")
print("    the middle with both tails lower - that shape is what a false positive looks like when")
print("    you inspect 24 cells. So the stack is built on cross-match + drift, not on all four.\n")
base = [r for r in OV if r["dline"] is not None and r["drift"] is not None]
cell(base, "  overs with both reads (fair basis)")
cell([r for r in base if r["dline"] < 0.5], "  + book did NOT raise her number")
cell([r for r in base if r["dline"] < 0.5 and r["drift"] < 0.01], "  + skip-drift as well")
cell([r for r in base if r["dline"] < 0.5 and r["drift"] < 0.01 and r["odds"] < 1.95],
     "  + and price under 1.95")
STACK = [r for r in base if r["dline"] < 0.5 and r["drift"] < 0.01]
print("\n    holdout in time on 'overs + book did not raise + skip-drift':")
c = int(len(STACK)*2/3)
cell(STACK[:c], "      first two thirds", minn=25)
cell(STACK[c:], "      final third, untouched", minn=20)
print("\n    per month:")
for mo in sorted({r["mo"] for r in STACK}):
    cell([r for r in STACK if r["mo"] == mo], f"      {mo}", minn=20)
def units(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)
print(f"\n    UNITS at flat 1u:")
for lbl, rows in (("all 1492 logged bets", M), ("overs only", OV),
                  ("overs + both reads", base), ("the stack", STACK)):
    w = sum(1 for r in rows if r["won"])
    print(f"      {lbl:<28}{len(rows):>5} bets  {w}-{len(rows)-w}  {units(rows):+8.2f}u  "
          f"ROI {100*units(rows)/len(rows):+6.1f}%")
print("\n" + "="*102)
print("  7. IS IT PROFIT OVER TIME, OR ONE GOOD MONTH? - the actual series, in units")
print("="*102)
def U(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)
CFG = [("current menu (everything)", M),
       ("OVERS ONLY", OV),
       ("overs + book did not raise", [r for r in OV if r["dline"] is not None and r["dline"] < 0.5]),
       ("overs + not-raised + skip-drift", STACK)]
import datetime as _dt
def wk(d):
    y, m, dd = int(d[:4]), int(d[4:6]), int(d[6:8])
    return _dt.date(y, m, dd).isocalendar()[:2]
print(f"    {'config':<34}{'month':>9}{'n':>6}{'W-L':>10}{'win%':>8}{'units':>10}{'ROI':>9}")
for nm, rows in CFG:
    for mo in sorted({r["mo"] for r in rows}):
        s = [r for r in rows if r["mo"] == mo]
        if len(s) < 10: continue
        w = sum(1 for r in s if r["won"])
        print(f"    {nm:<34}{mo:>9}{len(s):>6}{f'{w}-{len(s)-w}':>10}{100*w/len(s):>7.1f}%"
              f"{U(s):>+10.2f}{100*U(s)/len(s):>8.1f}%")
    w = sum(1 for r in rows if r["won"])
    print(f"    {'  TOTAL':<34}{'':>9}{len(rows):>6}{f'{w}-{len(rows)-w}':>10}"
          f"{100*w/len(rows):>7.1f}%{U(rows):>+10.2f}{100*U(rows)/len(rows):>8.1f}%\n")

print("    WEEK BY WEEK - 3 months is only ~7 weeks, so this is the honest resolution:")
for nm, rows in (("OVERS ONLY", OV), ("the stack", STACK)):
    weeks = sorted({wk(r["date"]) for r in rows})
    line, pos, run = [], 0, 0.0
    for w_ in weeks:
        s = [r for r in rows if wk(r["date"]) == w_]
        if len(s) < 5: continue
        uu = U(s); run += uu
        if uu > 0: pos += 1
        line.append(f"{uu:+.1f}")
    print(f"      {nm:<14} {' '.join(line)}")
    tot = len([w_ for w_ in weeks if len([r for r in rows if wk(r['date']) == w_]) >= 5])
    print(f"      {'':<14} {pos}/{tot} winning weeks, running total {run:+.2f}u")

print("\n    CONCENTRATION - how much of the profit is one month?")
for nm, rows in CFG:
    tot = U(rows)
    if abs(tot) < 1: continue
    best = max(({r["mo"] for r in rows}), key=lambda m_: U([r for r in rows if r["mo"] == m_]))
    bu = U([r for r in rows if r["mo"] == best])
    print(f"      {nm:<34} total {tot:+7.2f}u   best month {best} {bu:+7.2f}u "
          f"= {100*bu/tot if tot else 0:.0f}% of it")
