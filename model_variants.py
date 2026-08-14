# model_variants.py - three questions about the current model:
#   1 LOOSEN FILTER 5. We currently take one bet per player-market and treat a player who
#     qualifies on two markets as ONE position. What if we let both run?
#   2 FADE THE CUT. The model BETS the over when the book cuts her number. What if the cut is
#     actually the book knowing something, and the under is the play?
#   3 THE MONEYLINE, on the model's own bets rather than the whole board. Does whether her team
#     is favourite or underdog change anything, and does the model firing predict the game?
#
# All three are scored as ALPHA over the matched per-market/side blind baseline, because a subset
# made of pa bets and a subset made of ast bets are not comparable on raw win rate.
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
MK = ("pts","pra","pr","pa","reb","ast","ra"); BET = ("pra","pr","pts")
FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

gm = {g["game_id"]: (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
res = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None: continue
    res[(g["date"], g["home"])] = dict(won=hs > as_, total=hs+as_)
    res[(g["date"], g["away"])] = dict(won=as_ > hs, total=hs+as_)
plog = collections.defaultdict(list); teamon = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not (dt and tp): continue
    p, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(date=dt, tip=tp, pts=p, reb=rb, ast=a, pra=p+rb+a, pr=p+rb, pa=p+a, ra=rb+a))
    teamon[(dt, pl)] = r.get("team")
for v in plog.values(): v.sort(key=lambda x: x["date"])
byp = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v: byp[pl].append((g["tip"], g["date"], g))
for v in byp.values(): v.sort()
def ga(pl, when):
    for tip, dt, rec in byp.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None
mlp = {}
ser = collections.defaultdict(list)
for r in load(ODDS, absolute=True):
    t, c = f(r.get("ts")), ts(r.get("commence"))
    hp, ap = f(r.get("home_novig")), f(r.get("away_novig"))
    if t and c and hp and ap:
        ser[(c, r.get("home"), r.get("away"))].append((datetime.datetime.fromtimestamp(t, datetime.timezone.utc), hp, ap))
for (c, home, away), v in ser.items():
    v.sort(); hab, aab = FULL2AB.get(home), FULL2AB.get(away)
    if not (hab and aab): continue
    for k in (c.strftime("%Y%m%d"), (c - datetime.timedelta(hours=6)).strftime("%Y%m%d")):
        mlp[(k, hab)] = v[-1][1]; mlp[(k, aab)] = v[-1][2]

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
    if "Over" not in sides or "Under" not in sides: continue
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or rec[mk] == ln: continue
    main[(pl, mk, dt)] = ln
    tmp[(mk,"Over")].append(1.0 if rec[mk] > ln else 0.0)
    tmp[(mk,"Under")].append(0.0 if rec[mk] > ln else 1.0)
for k, v in tmp.items():
    if len(v) >= 80: BL[k] = sum(v)/len(v)
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

seen, M = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in BET: continue
    dt, rec = ga(pl, ts(b.get("captured_utc")))
    if not rec or (mk, "Over") not in BL: continue
    k = (dt, pl, mk)
    if k in seen: continue
    seen.add(k)
    cl = main.get((pl, mk, dt))
    if cl is None or rec[mk] == cl: continue
    pv = prev(pl, mk, dt); dr = drift(pl, mk, cl, rec["tip"])
    if pv is None or dr is None: continue
    sides = pg[(pl, mk, dt)][cl]
    tm = teamon.get((dt, pl))
    M.append(dict(date=dt, pl=pl, mk=mk, line=cl, oo=sides["Over"][-1][1],
                  uo=sides["Under"][-1][1], over_won=rec[mk] > cl,
                  obase=BL[(mk,"Over")], ubase=BL[(mk,"Under")],
                  dline=cl-pv, drift=dr, team=tm, wp=mlp.get((dt, tm)),
                  gres=res.get((dt, tm))))
M.sort(key=lambda r: r["date"])
MODEL = [r for r in M if r["dline"] < 0.5 and r["drift"] < 0.01]
print(f"{len(M)} eligible over candidates | {len(MODEL)} pass the full model\n")

def rep(rows, label, side="Over", minn=20):
    n = len(rows)
    if n < minn:
        print(f"  {label:<48} n={n} too few"); return
    if side == "Over":
        w = sum(1 for r in rows if r["over_won"]); b = sum(r["obase"] for r in rows)/n
        u = sum((r["oo"]-1) if r["over_won"] else -1.0 for r in rows)
    else:
        w = sum(1 for r in rows if not r["over_won"]); b = sum(r["ubase"] for r in rows)/n
        u = sum((r["uo"]-1) if not r["over_won"] else -1.0 for r in rows)
    z = (w/n-b)/math.sqrt(b*(1-b)/n)
    print(f"  {label:<48} n={n:<4} {w}-{n-w} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%"
          f"  alpha {100*(w/n-b):+5.1f}pp  z={z:+5.2f}")

print("="*110)
print("  1. LOOSEN FILTER 5 - let a player who qualifies on two markets run as two bets")
print("="*110)
cnt = collections.Counter((r["date"], r["pl"]) for r in MODEL)
solo = [r for r in MODEL if cnt[(r["date"], r["pl"])] == 1]
multi = [r for r in MODEL if cnt[(r["date"], r["pl"])] > 1]
rep(MODEL, "  the model as it stands (all qualifying rows)")
rep(solo,  "  players who qualified on ONE market only")
rep(multi, "  players who qualified on TWO+ markets")
pairs = collections.defaultdict(list)
for r in multi: pairs[(r["date"], r["pl"])].append(r)
both = sum(1 for v in pairs.values() if all(x["over_won"] for x in v))
none = sum(1 for v in pairs.values() if not any(x["over_won"] for x in v))
split = len(pairs) - both - none
print(f"\n    of {len(pairs)} multi-market players: {both} won BOTH, {none} lost BOTH, "
      f"{split} split")
print(f"    -> {100*(both+none)/max(1,len(pairs)):.0f}% moved together. That is the correlation:")
print(f"       doubling up is not two independent bets, it is one bet at 2u with extra variance.")

print("\n" + "="*110)
print("  2. THE BOOK CUT HER NUMBER - we bet the over. What if we fade it instead?")
print("="*110)
for lo, hi, nm in ((-99,-2,"cut 2+"), (-2,-0.5,"cut 0.5-2"), (-0.5,0.5,"held")):
    sel = [r for r in M if lo <= r["dline"] < hi and r["drift"] < 0.01]
    rep(sel, f"  book {nm}  -> OVER (what we do)", "Over")
    rep(sel, f"  book {nm}  -> UNDER (the fade)", "Under")
    print()
cut = [r for r in M if r["dline"] < -0.5 and r["drift"] < 0.01]
rep(cut, "  ALL cuts -> OVER", "Over")
rep(cut, "  ALL cuts -> UNDER (fade)", "Under")

print("\n" + "="*110)
print("  3. THE MONEYLINE, on the model's own bets")
print("="*110)
WP = [r for r in MODEL if r["wp"] is not None]
print(f"  {len(WP)} of {len(MODEL)} model bets have a closing moneyline\n")
for lo, hi, nm in ((0,0.40,"her team a clear underdog <40%"), (0.40,0.60,"close game 40-60%"),
                   (0.60,1.01,"her team favoured >60%")):
    rep([r for r in WP if lo <= r["wp"] < hi], f"  {nm}")
print()
gr = [r for r in MODEL if r["gres"]]
if len(gr) >= 30:
    tw = sum(1 for r in gr if r["gres"]["won"])
    exp = sum(r["wp"] for r in gr if r["wp"] is not None)
    nn = sum(1 for r in gr if r["wp"] is not None)
    print(f"  does the model firing predict her TEAM winning?")
    print(f"    teams with a model bet won {tw}/{len(gr)} = {100*tw/len(gr):.1f}%")
    if nn >= 30:
        sd = math.sqrt(sum(r["wp"]*(1-r["wp"]) for r in gr if r["wp"] is not None))
        got = sum(1 for r in gr if r["wp"] is not None and r["gres"]["won"])
        z = (got-exp)/sd
        print(f"    market expected {exp:.1f} of {nn}, got {got}  ->  z={z:+.2f}, "
              f"p={math.erfc(abs(z)/math.sqrt(2)):.3f}")
        print(f"    -> if this is ~0 the moneyline carries nothing our prop signal does not.")

print("\n" + "="*110)
print("  4. THE FULL INVERSION - flip EVERY switch and see if the mirror model works")
print("="*110)
print("  If the model has real edge its exact opposite should lose. If the opposite also loses,")
print("  the vig is eating both and neither side has information. If the opposite WINS, the model")
print("  is pointed backwards. This is the cheapest way to find out which of the three it is.\n")
print(f"  {'side':<7}{'line filter':<22}{'drift filter':<18}{'n':>5}{'W-L':>10}{'win%':>8}"
      f"{'units':>9}{'ROI':>9}{'alpha':>8}")
def cellrow(side, lname, lsel, dname, dsel):
    rows = [r for r in M if lsel(r) and dsel(r)]
    n = len(rows)
    if n < 20:
        print(f"  {side:<7}{lname:<22}{dname:<18}{n:>5}  too few"); return
    if side == "Over":
        w = sum(1 for r in rows if r["over_won"]); b = sum(r["obase"] for r in rows)/n
        u = sum((r["oo"]-1) if r["over_won"] else -1.0 for r in rows)
    else:
        w = sum(1 for r in rows if not r["over_won"]); b = sum(r["ubase"] for r in rows)/n
        u = sum((r["uo"]-1) if not r["over_won"] else -1.0 for r in rows)
    print(f"  {side:<7}{lname:<22}{dname:<18}{n:>5}{f'{w}-{n-w}':>10}{100*w/n:>7.1f}%"
          f"{u:>+9.2f}{100*u/n:>+8.1f}%{100*(w/n-b):>+7.1f}")
LF = [("book did NOT raise", lambda r: r["dline"] < 0.5),
      ("book RAISED (inverted)", lambda r: r["dline"] >= 0.5)]
DF = [("skip-drift", lambda r: r["drift"] < 0.01),
      ("drifted (inverted)", lambda r: r["drift"] >= 0.01)]
for side in ("Over", "Under"):
    for lname, lsel in LF:
        for dname, dsel in DF:
            cellrow(side, lname, lsel, dname, dsel)
    print()
print("  READ THE FOUR CORNERS:")
print("    Over  + not-raised + skip-drift  = THE MODEL")
print("    Under + raised     + drifted     = its exact mirror")
print("  If the mirror is merely bad rather than symmetrically good, the edge is real but small")
print("  and the under side's structural -13% is doing most of the damage.")

print("\n" + "="*110)
print("  5. DOES THE GAME'S TOTAL LINE OR SPREAD SAY ANYTHING ABOUT THE MODEL?")
print("="*110)
print("  Two different questions again:")
print("    SORTING   is the model better in high-total or lopsided games? (a filter)")
print("    PREDICTING does the model firing forecast the total or the cover? (a bet)")
print("  Coverage caveat: gamelines.csv only starts 2026-07-11, so this is the thin end.\n")
def dec(am):
    a = f(am)
    return None if a is None or a == 0 else (1 + a/100 if a > 0 else 1 + 100/abs(a))
snap = collections.defaultdict(list)
for r in load("gamelines.csv"):
    t = ts(r.get("captured_utc")); st = ts((r.get("start") or "") + "Z" if r.get("start") else None)
    if not (t and st) or t > st or r.get("type") not in ("total", "spread"): continue
    pr = (r.get("prices") or "").split(",")
    if len(pr) != 2: continue
    d1, d2 = dec(pr[0]), dec(pr[1])
    if d1 and d2 and f(r.get("points")) is not None:
        snap[(r.get("teams"), st, r.get("type"))].append((t, f(r.get("points")), d1, d2))
close = {}
for k, v in snap.items():
    last = max(x[0] for x in v)
    same = [x for x in v if x[0] == last]
    if same: close[k] = min(same, key=lambda x: abs(x[2]-x[3]))
GI = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    tp = ts(g.get("tip"))
    if hs is None or not tp: continue
    hn = next((k for k, ab in FULL2AB.items() if ab == g["home"]), None)
    an = next((k for k, ab in FULL2AB.items() if ab == g["away"]), None)
    if not (hn and an): continue
    kt = next((k for k in close if k[0] == f"{hn}|{an}" and k[2] == "total"
               and abs((k[1]-tp).total_seconds()) < 6*3600), None)
    ks = next((k for k in close if k[0] == f"{hn}|{an}" and k[2] == "spread"
               and abs((k[1]-tp).total_seconds()) < 6*3600), None)
    for tm, own, opp_ in ((g["home"], hs, as_), (g["away"], as_, hs)):
        GI[(g["date"], tm)] = dict(
            total_line=close[kt][1] if kt else None, actual_total=hs+as_,
            spread=(close[ks][1] if ks else None), is_home=(tm == g["home"]),
            margin=own-opp_)
for r in M:
    gi = GI.get((r["date"], r["team"]))
    r["tl"] = gi["total_line"] if gi else None
    r["at"] = gi["actual_total"] if gi else None
    # spread in gamelines is the HOME handicap; flip it for an away player
    r["sp"] = (gi["spread"] if gi["is_home"] else -gi["spread"]) if (gi and gi["spread"] is not None) else None
    r["marg"] = gi["margin"] if gi else None
MODEL = [r for r in M if r["dline"] < 0.5 and r["drift"] < 0.01]
TL = [r for r in MODEL if r["tl"] is not None]
SP = [r for r in MODEL if r["sp"] is not None]
print(f"  {len(TL)} of {len(MODEL)} model bets have a closing TOTAL, {len(SP)} have a SPREAD\n")
print("  (a) SORTING - does the model perform differently by game environment?")
for lo, hi, nm in ((0,168,"total line under 168"), (168,176,"total 168-176"), (176,999,"total 176+")):
    rep([r for r in TL if lo <= r["tl"] < hi], f"    {nm}", "Over", minn=15)
print()
for lo, hi, nm in ((-99,-6,"her team fav by 6+"), (-6,-1.5,"fav by 1.5-6"),
                   (-1.5,1.5,"pick'em"), (1.5,6,"dog by 1.5-6"), (6,99,"dog by 6+")):
    rep([r for r in SP if lo <= r["sp"] < hi], f"    {nm}", "Over", minn=15)
print("\n  (b) PREDICTING - does a model bet forecast the GAME total going over?")
gt = {}
for r in TL: gt[(r["date"], r["team"])] = r
games_ = {}
for r in TL: games_[(r["date"], tuple(sorted((r["team"],))))] = r
uniq = {}
for r in TL: uniq[(r["date"], r["at"], r["tl"])] = r
rows = list(uniq.values())
if len(rows) >= 20:
    ov = sum(1 for r in rows if r["at"] > r["tl"])
    n = len(rows)
    z = (ov/n - 0.5)/math.sqrt(0.25/n)
    print(f"    {n} distinct games carrying a model bet: {ov} went OVER the closing total "
          f"({100*ov/n:.0f}%)")
    print(f"    vs a 50% coin flip: z={z:+.2f}, p={math.erfc(abs(z)/math.sqrt(2)):.3f}")
    print(f"    mean closing total {sum(r['tl'] for r in rows)/n:.1f}, "
          f"mean actual {sum(r['at'] for r in rows)/n:.1f}  "
          f"(diff {sum(r['at']-r['tl'] for r in rows)/n:+.1f})")
else:
    print(f"    only {len(rows)} distinct games - cannot test")

print("\n" + "="*110)
print("  5c. THE CONTROL THAT DECIDES IT - what did games WITHOUT a model bet do?")
print("="*110)
print("  66% sounds strong until you check the baseline. Earlier work found overs ran ~66% across")
print("  this whole window, so the honest comparison is model-games vs NON-model-games, not vs 50%.\n")
allg = {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    tp = ts(g.get("tip"))
    if hs is None or not tp: continue
    hn = next((k for k, ab in FULL2AB.items() if ab == g["home"]), None)
    an = next((k for k, ab in FULL2AB.items() if ab == g["away"]), None)
    if not (hn and an): continue
    kt = next((k for k in close if k[0] == f"{hn}|{an}" and k[2] == "total"
               and abs((k[1]-tp).total_seconds()) < 6*3600), None)
    if not kt: continue
    tl = close[kt][1]
    if hs+as_ == tl: continue
    allg[(g["date"], g["home"], g["away"])] = dict(tl=tl, at=hs+as_, over=(hs+as_) > tl,
                                                   dov=close[kt][2], dun=close[kt][3])
modelteams = {(r["date"], r["team"]) for r in MODEL}
withm, without = [], []
for (dt, h, a), v in allg.items():
    (withm if ((dt, h) in modelteams or (dt, a) in modelteams) else without).append(v)
def tot(rows, label):
    n = len(rows)
    if n < 12:
        print(f"    {label:<40} n={n} too few"); return None
    ov = sum(1 for r in rows if r["over"])
    roi = sum((r["dov"]-1) if r["over"] else -1.0 for r in rows)/n
    print(f"    {label:<40} n={n:<4} {ov}-{n-ov}  over {100*ov/n:5.1f}%  "
          f"bet-the-over ROI {100*roi:+6.1f}%  mean actual-line {sum(r['at']-r['tl'] for r in rows)/n:+.1f}")
    return ov/n, n
a = tot(withm,   "games WITH a model bet")
b = tot(without, "games with NO model bet (control)")
tot(list(allg.values()), "every game in the window")
if a and b:
    pa_, na = a; pb, nb = b
    p = (pa_*na + pb*nb)/(na+nb)
    z = (pa_-pb)/math.sqrt(p*(1-p)*(1/na+1/nb))
    print(f"\n    difference {100*(pa_-pb):+.1f}pp   z={z:+.2f}   "
          f"p={math.erfc(abs(z)/math.sqrt(2)):.3f}")
    print(f"    -> this, not the 66%, is whether the model tells you anything about the total.")

print("\n" + "="*110)
print("  6. TEAM TOTALS - the sharpest version of the question")
print("="*110)
print("  A player prop is a SHARE of her team's expected points. So the book gives us two numbers")
print("  that have to be consistent with each other: her line, and her team's total. Three tests:")
print("    LEVEL   is the model better when the book expects her team to score a lot?")
print("    vs FORM is the book's team total above or below what that team has actually been")
print("            scoring? (the same staleness question, one level up)")
print("    SHARE   her line as a fraction of the team total, against her historical share of")
print("            team points. If the book says 88 team points and prices her at 14 while she")
print("            normally takes 20% of her team's scoring, the two desks disagree - and the")
print("            team total is the one with real money behind it.\n")
tt = collections.defaultdict(list)
for r in load("gamelines.csv"):
    t = ts(r.get("captured_utc")); st = ts((r.get("start") or "") + "Z" if r.get("start") else None)
    if not (t and st) or t > st or r.get("type") != "team_total": continue
    p = f(r.get("points"))
    if p is not None and r.get("side") in ("home", "away"):
        tt[(r.get("teams"), st, r.get("side"))].append((t, p))
ttclose = {k: max(v)[1] for k, v in tt.items()}
TT = {}
for g in load("data/games_2026.csv"):
    tp = ts(g.get("tip"))
    if not tp: continue
    hn = next((k for k, ab in FULL2AB.items() if ab == g["home"]), None)
    an = next((k for k, ab in FULL2AB.items() if ab == g["away"]), None)
    if not (hn and an): continue
    for side, tm in (("home", g["home"]), ("away", g["away"])):
        k = next((k for k in ttclose if k[0] == f"{hn}|{an}" and k[2] == side
                  and abs((k[1]-tp).total_seconds()) < 6*3600), None)
        if k: TT[(g["date"], tm)] = ttclose[k]
print(f"  {len(TT)} (date, team) closing team totals parsed")
# that team's own recent scoring, prior games only
tpts = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None: continue
    tpts[g["home"]].append((g["date"], hs)); tpts[g["away"]].append((g["date"], as_))
for v in tpts.values(): v.sort()
def team_norm(tm, dt, n=10):
    prev = [p for d, p in tpts.get(tm, []) if d < dt][-n:]
    return sum(prev)/len(prev) if len(prev) >= 5 else None
# her historical share of team points, prior games only
def share(pl, tm, dt, n=10):
    ps = [g["pts"] for g in plog.get(pl, []) if g["date"] < dt][-n:]
    tn = team_norm(tm, dt, n)
    if len(ps) < 5 or not tn: return None
    return (sum(ps)/len(ps))/tn
for r in M:
    r["tt"] = TT.get((r["date"], r["team"]))
    r["tnorm"] = team_norm(r["team"], r["date"])
    r["shr"] = share(r["pl"], r["team"], r["date"])
MODEL = [r for r in M if r["dline"] < 0.5 and r["drift"] < 0.01]
A = [r for r in MODEL if r["tt"] is not None]
print(f"  {len(A)} of {len(MODEL)} model bets have a closing team total\n")
print("  (a) LEVEL - the book's expected points for her team")
for lo, hi, nm in ((0,82,"team total under 82"), (82,88,"82-88"), (88,999,"88+")):
    rep([r for r in A if lo <= r["tt"] < hi], f"    {nm}", "Over", minn=15)
print("\n  (b) vs FORM - team total minus that team's own trailing-10 points")
B = [r for r in A if r["tnorm"] is not None]
for lo, hi, nm in ((-99,-3,"book expects team 3+ BELOW its norm"), (-3,3,"about normal"),
                   (3,99,"book expects team 3+ ABOVE its norm")):
    rep([r for r in B if lo <= r["tt"]-r["tnorm"] < hi], f"    {nm}", "Over", minn=15)
print("\n  (c) SHARE - her line as a fraction of the team total, vs her historical share")
C = [r for r in A if r["shr"] and r["mk"] == "pts"]
print(f"    {len(C)} model bets are POINTS props (share only makes sense there)")
for lo, hi, nm in ((-99,-0.02,"line implies a SMALLER share than usual"),
                   (-0.02,0.02,"in line with her usual share"),
                   (0.02,99,"line implies a BIGGER share than usual")):
    sel = [r for r in C if lo <= (r["line"]/r["tt"] - r["shr"]) < hi]
    rep(sel, f"    {nm}", "Over", minn=12)
