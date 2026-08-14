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
    M.append(dict(src=b.get("src"), date=dt, pl=pl, mk=mk, line=cl, oo=sides["Over"][-1][1],
                  uo=sides["Under"][-1][1], over_won=rec[mk] > cl,
                  obase=BL[(mk,"Over")], ubase=BL[(mk,"Under")],
                  dline=cl-pv, drift=dr, team=tm, wp=mlp.get((dt, tm)),
                  gres=res.get((dt, tm))))


M.sort(key=lambda r: r["date"])
import random
random.seed(20260814)

# de-vig each line's own two-sided price -> the book's honest probability for THIS over
for r in M:
    io, iu = 1.0/r["oo"], 1.0/r["uo"]
    r["p"] = io/(io+iu)
print(f"{len(M)} two-sided starred-or-not candidates, each with a de-vigged fair probability")
print(f"mean book fair prob for our overs: {sum(r['p'] for r in M)/len(M):.3f}")
print("")

SRCS  = sorted({r["src"] for r in M})
MKSET = [("pra","pr","pts"), ("pra","pr"), ("pra",), ("pr",), ("pts",), ("pra","pr","pts","pa")]
def combos():
    out = []
    for k in range(1, len(SRCS)+1):
        import itertools
        for c in itertools.combinations(SRCS, k):
            for mks in MKSET:
                for star in (True, False, None):
                    out.append((c, mks, star))
    return out
CELLS = combos()

def best_roi(outcome):
    best = -9e9; bestn = 0
    for srcs, mks, star in CELLS:
        rows = [r for r in M if r["src"] in srcs and r["mk"] in mks
                and (star is None or (r["dline"] < 0.5) == star)]
        if len(rows) < 25: continue
        u = sum((r["oo"]-1) if outcome(r) else -1.0 for r in rows)
        roi = u/len(rows)
        if roi > best: best, bestn = roi, len(rows)
    return best, bestn

real, realn = best_roi(lambda r: r["over_won"])
print("="*96)
print("  MULTIPLICITY NULL. I searched a lot of cells to land on this model. So: simulate every")
print("  outcome from that line's OWN de-vigged book probability - a world with no edge, but the")
print("  same lines, prices and sample sizes - then re-run the WHOLE search and take its best cell.")
print(f"  {len(CELLS)} cells searched per trial, min n=25.")
print("="*96)
print(f"  REAL best cell:  ROI {100*real:+6.1f}%  (n={realn})")
print("")
TRIALS = 400
beat = 0; sims = []
for t in range(TRIALS):
    draw = {id(r): (random.random() < r["p"]) for r in M}
    b, _ = best_roi(lambda r: draw[id(r)])
    sims.append(b)
    if b >= real: beat += 1
sims.sort()
print(f"  {TRIALS} no-edge worlds, each searched the same way:")
print(f"    median best-cell ROI  {100*sims[TRIALS//2]:+6.1f}%")
print(f"    p90                   {100*sims[int(TRIALS*0.90)]:+6.1f}%")
print(f"    p95                   {100*sims[int(TRIALS*0.95)]:+6.1f}%")
print(f"    p99                   {100*sims[int(TRIALS*0.99)]:+6.1f}%")
print(f"    max                   {100*sims[-1]:+6.1f}%")
print("")
print(f"  no-edge worlds that matched or beat our real best cell: {beat}/{TRIALS}"
      f"  -> multiplicity-priced p = {beat/TRIALS:.3f}")
print("")
print("  READ THIS AS: even with NO edge, cherry-picking the best of many cells produces a")
print("  positive ROI. The question is whether ours is bigger than that cherry-picking floor.")
