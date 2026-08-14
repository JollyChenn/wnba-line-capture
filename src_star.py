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
print(f"{len(M)} eligible over candidates (one per player-market-night)")
print("")

def rep(rows, label, minn=15):
    n = len(rows)
    if n < minn:
        print(f"  {label:<40} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["over_won"]); b = sum(r["obase"] for r in rows)/n
    u = sum((r["oo"]-1) if r["over_won"] else -1.0 for r in rows)
    z = (w/n-b)/math.sqrt(b*(1-b)/n)
    print(f"  {label:<40} n={n:<4} {w}-{n-w} {100*w/n:5.1f}%  {u:+7.2f}u  ROI {100*u/n:+6.1f}%"
          f"  alpha {100*(w/n-b):+5.1f}pp  z={z:+5.2f}")

srcs = sorted({r["src"] for r in M}, key=lambda s: -len([r for r in M if r["src"]==s]))
print("="*108)
print("  EVERY OVER SOURCE, RAW vs STARRED (star = book did NOT raise her number 0.5+)")
print("="*108)
for s in srcs:
    rows = [r for r in M if r["src"] == s]
    rep(rows,                                     f"{s}  RAW")
    rep([r for r in rows if r["dline"] < 0.5],    f"{s}  STARRED")
    rep([r for r in rows if r["dline"] >= 0.5],   f"{s}  raised (unstarred)")
    print("")
print("="*108)
print("  THE LIVE MODEL, AND WHAT ADDING EACH OTHER SOURCE WOULD DO")
print("="*108)
live = [r for r in M if r["src"] in ("flip","hotover") and r["dline"] < 0.5]
rep(live, "flip + hotover, STARRED  <- LIVE")
for s in srcs:
    if s in ("flip","hotover"): continue
    plus = [r for r in M if r["src"] in ("flip","hotover",s) and r["dline"] < 0.5]
    rep(plus, f"  + {s}")
