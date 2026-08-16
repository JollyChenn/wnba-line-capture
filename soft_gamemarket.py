# soft_gamemarket.py - is ANY 1xbet game market soft, or only the player props?
# ---------------------------------------------------------------------------------------------
# The moneyline check said 1xbet == Pinnacle to within 0.8pp, which closes moneyline betting.
# But I only compared moneylines. The same feed carries the game TOTAL and SPREAD, and those are
# less-watched numbers than the moneyline. If either is soft the way the props are (1xbet sits
# 7.0% below fair on props, t=-42.9), a rating would have somewhere to work.
#
# This is the question that decides whether building a better Elo is worth doing at all: a rating
# only pays if there is a lazy price to aim it at.
import csv, os, sys, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def am(p):
    v = f(p)
    if v is None: return None
    return (-v)/((-v)+100) if v < 0 else 100/(v+100)

FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
        "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
        "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
        "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
        "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

def key_of(teams, start):
    tm = (teams or "").split("|")
    if len(tm) != 2: return None
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tm))
    if "" in ab: return None
    return ((start or "")[:10], ab)

P = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    k = key_of(r.get("teams"), r.get("start"))
    cap = ts(r.get("captured_utc"))
    if not k or not cap: continue
    typ, pts = r.get("type"), f(r.get("points"))
    pr = (r.get("prices") or "").split(",")
    if typ in ("total", "spread") and pts is not None and len(pr) >= 2:
        cur = P[k].get(typ)
        if cur is None or cap > cur[0]:
            P[k][typ] = (cap, pts, am(pr[0]), am(pr[1]))

X = collections.defaultdict(dict)
for r in load("xbet_gamelines.csv"):
    k = key_of(r.get("teams"), r.get("start"))
    cap = ts(r.get("captured_utc"))
    if not k or not cap: continue
    cur = X[k].get(r.get("type"))
    if cur is None or cap > cur[0]:
        X[k][r.get("type")] = (cap, f(r.get("points")), f(r.get("p1")), f(r.get("p2")))

both = sorted(set(X) & set(P))
print(f"{len(both)} games with BOTH books captured")
print("")
print("=" * 96)
print("  1XBET vs PINNACLE on the GAME markets")
print("=" * 96)
print(f"  {'game':<12}{'xb total':>10}{'pinn':>8}{'diff':>7}   {'xb spr':>8}{'pinn':>8}{'diff':>7}   {'xb vig':>8}")
dt_, ds_ = [], []
for k in both:
    g = "/".join(k[1])
    xt, pt = X[k].get("total"), P[k].get("total")
    xs, ps = X[k].get("spread"), P[k].get("spread")
    tcol = scol = vcol = ""
    if xt and pt and xt[1] is not None:
        d = xt[1] - pt[1]; dt_.append(d)
        tcol = f"{xt[1]:>10.1f}{pt[1]:>8.1f}{d:>+7.1f}"
        if xt[2] and xt[3]: vcol = f"{100*(1/xt[2] + 1/xt[3] - 1):>7.1f}%"
    if xs and ps and xs[1] is not None:
        d = abs(xs[1]) - abs(ps[1]); ds_.append(d)
        scol = f"{xs[1]:>8.1f}{ps[1]:>8.1f}{d:>+7.1f}"
    print(f"  {g:<12}{tcol}   {scol}   {vcol}")
print("")
if dt_:
    print(f"  TOTAL   mean |diff| {sum(abs(x) for x in dt_)/len(dt_):.2f} points   "
          f"mean signed {sum(dt_)/len(dt_):+.2f}   n={len(dt_)}")
if ds_:
    print(f"  SPREAD  mean |diff| {sum(abs(x) for x in ds_)/len(ds_):.2f} points   "
          f"mean signed {sum(ds_)/len(ds_):+.2f}   n={len(ds_)}")
print("")
print("  For scale: on player props 1xbet sits 7.0% below Pinnacle fair (t=-42.9). A game total")
print("  agreeing to well under a point is the same story as the moneyline - no lazy price here.")
