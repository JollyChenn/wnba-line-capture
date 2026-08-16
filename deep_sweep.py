# deep_sweep.py - one PRE-REGISTERED sweep over game-market features, with a GLOBAL
# multiplicity correction. Not a series of hopeful slices.
# ---------------------------------------------------------------------------------------------
# Every feature below is declared up front, each is split at its own median (no threshold
# hunting), and the BEST result across the whole sweep is then compared against the best result
# from the same sweep run on shuffled labels. That is the only way a wide search stays honest:
# if you look at 14 features you will find one at p<0.05 roughly half the time by chance.
#
# Features: the game's closing total, spread and moneyline; the MOVEMENT of each between our
# first and last capture; the prop's own price; and the market.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260823)
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
    """american price -> implied probability"""
    v = f(p)
    if v is None: return None
    return (-v)/((-v)+100) if v < 0 else 100/(v+100)

FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

# ---- game markets: FIRST and LAST capture, so movement is available ---------------------------
gl = collections.defaultdict(lambda: collections.defaultdict(list))
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2 or not st: continue
    ab = tuple(sorted(FULL2AB.get(t.strip(), "") for t in tm))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if cap is None: continue
    typ = r.get("type")
    if typ == "total" and pts is not None:
        gl[(st, ab)]["total"].append((cap, pts))
    elif typ == "spread" and pts is not None:
        gl[(st, ab)]["spread"].append((cap, abs(pts)))
    elif typ == "moneyline":
        pr = (r.get("prices") or "").split(",")
        h = am(pr[0]) if pr and pr[0] else None
        if h is not None: gl[(st, ab)]["ml"].append((cap, h))
for k in gl:
    for t in gl[k]: gl[k][t].sort()

# ---- Model S bets ------------------------------------------------------------------------------
MKTS = ("pra","pr","pts"); SIGS = ("flip","hotover","overshoot")
gm = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, date=dt, pra=p_+rb+a, pr=p_+rb, pts=p_))
    team[pl] = r.get("team")
tips_of = collections.defaultdict(list); opp = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t:
        tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
        opp[(g.get("date"), g["home"])] = g["away"]; opp[(g.get("date"), g["away"])] = g["home"]
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = team.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

seen, BETS = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in MKTS: continue
    t0, tm = ts(b.get("captured_utc")), team.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    seq = bygame.get((pl, mk, gt), [])
    rec = next((g for g in plog.get(pl, []) if g["tip"] == gt), None)
    if not seq or not rec: continue
    seen.add((pl, mk, gt))
    line = seq[-1][1]
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    if pv is None or line - pv >= 0.5: continue
    dt = rec["date"]; o_ = opp.get((dt, tm)); ab = tuple(sorted((tm, o_))) if o_ else None
    G = gl.get((dt, ab), {})
    def first_last(t):
        v = G.get(t, [])
        return (v[0][1], v[-1][1]) if len(v) >= 1 else (None, None)
    t0v, t1v = first_last("total"); s0, s1 = first_last("spread"); m0, m1 = first_last("ml")
    BETS.append(dict(pl=pl, mk=mk, date=dt, tm=tm, odds=seq[-1][2], won=rec[mk] > line,
                     total=t1v, total_mv=(None if t0v is None else t1v - t0v),
                     spread=s1,  spread_mv=(None if s0 is None else s1 - s0),
                     ml=m1,      ml_mv=(None if m0 is None else m1 - m0),
                     price=seq[-1][2]))
byday = collections.defaultdict(list)
for r in BETS: byday[r["date"]].append(r)
for d in list(byday):
    best = {}
    for r in sorted(byday[d], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[d] = list(best.values())
K = [r for v in byday.values() for r in v]
print(f"{len(K)} Model S bets. Coverage of each game-market feature:")
FEATS = ["total","total_mv","spread","spread_mv","ml","ml_mv","price"]
for ft in FEATS:
    print(f"    {ft:<12} {sum(1 for r in K if r.get(ft) is not None):>4} of {len(K)}")
print("")

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0

def sweep(labels, verbose=False):
    """every feature, split at its own median. returns the best |ROI| cell found."""
    best = -9e9; bestlbl = ""
    for ft in FEATS:
        have = [(r, labels[id(r)]) for r in K if r.get(ft) is not None]
        if len(have) < 30: continue
        vals = sorted(r[ft] for r, _ in have); med = vals[len(vals)//2]
        for side, sel in (("high", lambda r: r[ft] >= med), ("low", lambda r: r[ft] < med)):
            g = [(r, w) for r, w in have if sel(r)]
            if len(g) < 15: continue
            v = sum((r["odds"]-1) if w else -1.0 for r, w in g)/len(g)
            if verbose:
                hit = sum(1 for _, w in g if w)/len(g)
                print(f"    {ft:<12} {side:<5} (med {med:+.2f})  n={len(g):<4} {100*hit:5.1f}%  ROI {100*v:+6.1f}%")
            if v > best: best, bestlbl = v, f"{ft} {side}"
    # market is categorical, not a median split
    for mk in ("pra","pr","pts"):
        g = [(r, labels[id(r)]) for r in K if r["mk"] == mk]
        if len(g) < 15: continue
        v = sum((r["odds"]-1) if w else -1.0 for r, w in g)/len(g)
        if verbose:
            hit = sum(1 for _, w in g if w)/len(g)
            print(f"    market {mk:<6}          n={len(g):<4} {100*hit:5.1f}%  ROI {100*v:+6.1f}%")
        if v > best: best, bestlbl = v, f"market {mk}"
    return best, bestlbl

print("="*100)
print("  THE SWEEP - every feature split at its own median, plus market")
print("="*100)
real_labels = {id(r): r["won"] for r in K}
best, lbl = sweep(real_labels, verbose=True)
print("")
print(f"  BEST CELL: {lbl}  at ROI {100*best:+.1f}%   (baseline for all {len(K)} bets: {100*roi(K):+.1f}%)")
print("")
print("="*100)
print("  GLOBAL MULTIPLICITY - rerun the WHOLE sweep on shuffled outcomes, 2000 times.")
print("  If the features carry nothing, how often does the best-of-sweep match ours?")
print("="*100)
outs = [r["won"] for r in K]
beat = 0; T = 2000; sims = []
for _ in range(T):
    sh = outs[:]; random.shuffle(sh)
    lab = {id(r): w for r, w in zip(K, sh)}
    b, _ = sweep(lab)
    sims.append(b)
    if b >= best: beat += 1
sims.sort()
print(f"    shuffled best-of-sweep: median {100*sims[T//2]:+.1f}%   p95 {100*sims[int(T*0.95)]:+.1f}%"
      f"   max {100*sims[-1]:+.1f}%")
print(f"    beat or matched ours {beat}/{T}  ->  GLOBAL p = {beat/T:.4f}")
print("")
print("  Reading: a wide sweep on pure noise still produces a best cell well above baseline.")
print("  Only a global p below ~0.05 would mean these features carry anything at all.")
