# mega_sweep.py - THE definitive sweep. Every feature family, both sides, one global correction.
# ---------------------------------------------------------------------------------------------
# Today taught two things that shape this:
#   1 slicing ~100 Model S bets cannot resolve anything - a coin flip on them produced +24.7%
#   2 the full board (6000+ two-sided quotes) CAN - its noise ceiling is a few percent, not 40%
# So this runs on the full board, prices both sides from the board's own quotes at the same
# line, and applies ONE global permutation across the entire grid rather than a p-value per cell.
#
# FEATURE FAMILIES, all computed strictly from games BEFORE the one being predicted:
#   BOX      usage share, usage trend, minutes trend, rest days, scoring rank
#   MOMENTUM her last-3 vs season, her OVER/UNDER streak (the zig-zag folklore), team win streak
#   LINE     the star, line move vs her last game, gap to her trailing median, price level
#   GAME     total, spread and moneyline, where Pinnacle coverage exists
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260914)
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

ALL_MK = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
        "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
        "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
        "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
        "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

gmeta = {}; result = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if not t: continue
    gmeta[g.get("game_id")] = (g.get("date", ""), t, g.get("home"), g.get("away"))
    hs, a_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is not None and a_ is not None:
        result[(g.get("date"), g.get("home"))] = hs > a_
        result[(g.get("date"), g.get("away"))] = a_ > hs

pgrow = {}; roster = collections.defaultdict(set); teamof = {}; teamuse = collections.defaultdict(float)
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp, hm, aw = gmeta[gid]
    pl, tm = (r.get("player") or "").lower(), r.get("team")
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    use = (f(r.get("fga")) or 0) + 0.44*(f(r.get("fta")) or 0) + (f(r.get("to")) or 0)
    pgrow[(pl, tp)] = dict(tm=tm, tip=tp, date=dt, min=f(r.get("min")) or 0, use=use,
                           pts=p_, reb=rb, ast=a, pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)
    roster[(tm, tp)].add(pl); teamof[pl] = tm; teamuse[(tm, tp)] += use
hist = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): hist[pl].append(row)
for v in hist.values(): v.sort(key=lambda x: x["tip"])

tips_of = collections.defaultdict(list)
for gid, (dt, tp, hm, aw) in gmeta.items():
    tips_of[hm].append(tp); tips_of[aw].append(tp)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None

# game markets, closing
GM = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2: continue
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tm))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if not cap: continue
    s = GM[(st, ab)]
    # MAIN LINE, NOT AN ALTERNATE (fixed 2026-08-26). Pinnacle posts a ladder - the median
    # snapshot carries SEVEN total rows (e.g. 172.0 ... 175.0) sharing one capture timestamp.
    # The old test "cap > stored cap" is false for every tie, so it kept whichever rung landed
    # last in the file: an arbitrary alternate differing from the main line by a median 1.5
    # points, and by more than a point on 71% of snapshots. Everything built on GM inherited it,
    # including the retracted "higher total -> better player overs" gradient.
    # The main line is the rung priced closest to even; validated against 1xbet's own posted
    # total to mean +0.04 / sd 0.66.
    _pr = (r.get("prices") or "").split(",")
    _skew = 9.0
    if len(_pr) == 2:
        _a, _b = am(_pr[0]), am(_pr[1])
        if _a is not None and _b is not None: _skew = abs(_a - _b)
    if r.get("type") == "total" and pts is not None:
        if "tot" not in s or (cap, -_skew) > (s["tot"][0], -s["tot"][2]):
            s["tot"] = (cap, pts, _skew)
    if r.get("type") == "spread" and pts is not None:
        if "spr" not in s or (cap, -_skew) > (s["spr"][0], -s["spr"][2]):
            s["spr"] = (cap, abs(pts), _skew)
    if r.get("type") == "moneyline":
        pr = (r.get("prices") or "").split(",")
        h = am(pr[0]) if pr and pr[0] else None
        if h is not None and ("ml" not in s or cap > s["ml"][0]): s["ml"] = (cap, h)

# BOARD NAME RESOLUTION (added 2026-08-26). The join used to be an exact lowercase string match
# and failed on 8 real players covering 3,201 board rows - 3.9% of the prop book - led by
# A'ja Wilson at 1,530 rows. Those players were silently absent from every study built on this
# preamble, so any conclusion about "stars" or usage rank was drawn from a population with the
# league's highest-usage name deleted. namefix.resolve() maps board spellings onto box spellings
# and returns None only for a genuinely unknown name, which we count and report rather than drop.
import namefix as _nf
_resolve = _nf.build(os.path.join(D, "data", "box_2026.csv"))
_NAMEMAP, _UNRESOLVED = {}, collections.Counter()
def _pl(raw_name):
    k = (raw_name or "").strip()
    if k in _NAMEMAP: return _NAMEMAP[k]
    hit = _resolve(k)
    if hit is None:
        _UNRESOLVED[k] += 1
        _NAMEMAP[k] = k.lower()
    else:
        _NAMEMAP[k] = hit.strip().lower()
    return _NAMEMAP[k]

raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in ALL_MK:
        raw[(_pl(b.get("player")), b.get("market"), b.get("side"), ln)].append((t, o))
side = collections.defaultdict(dict)
lines_seen = collections.defaultdict(list)
for (pl, mk, sd, ln), v in raw.items():
    tm = teamof.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if not g2: continue
        cur = side[(pl, mk, g2)].get(sd)
        if cur is None or t > cur[0]: side[(pl, mk, g2)][sd] = (t, ln, o)
        if sd == "Over": lines_seen[(pl, mk)].append((g2, ln))
# her line in her PREVIOUS game - one line per game (the last posted), then step back one game.
# sorting the raw (game, line) pairs instead would order by LINE inside a game and hand back a
# number she was never actually facing - the same class of mistake that faked the timing result.
prevline = {}
for (pl, mk), v in lines_seen.items():
    lastof = {}
    for g2, ln in v: lastof[g2] = ln
    gs = sorted(lastof)
    for i in range(1, len(gs)):
        prevline[(pl, mk, gs[i])] = lastof[gs[i-1]]

# opponent lookup, built once
OPP = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    OPP[(hm, t2)] = (d2, aw); OPP[(aw, t2)] = (d2, hm)

B = []
for (pl, mk, gt), sd in side.items():
    if "Over" not in sd or "Under" not in sd: continue
    if sd["Over"][1] != sd["Under"][1]: continue
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    line = sd["Over"][1]
    if now[mk] == line: continue
    prior = [x for x in hist.get(pl, []) if x["tip"] < gt]
    if len(prior) < 6: continue
    p3, p5, p10 = prior[-3:], prior[-5:], prior[-10:]
    tm = now["tm"]
    mates = {}
    for m in roster.get((tm, gt), ()):
        pv = [x for x in hist.get(m, []) if x["tip"] < gt][-6:]
        if pv: mates[m] = statistics.mean(x["pts"] for x in pv)
    rank = (sorted(mates, key=lambda m: -mates[m]).index(pl) + 1) if pl in mates else 99
    def sh(rows):
        vals = [r["use"]/teamuse[(r["tm"], r["tip"])] for r in rows if teamuse.get((r["tm"], r["tip"]), 0) > 0]
        return statistics.mean(vals) if vals else None
    us3, us10 = sh(p3), sh(p10)
    med10 = statistics.median(x[mk] for x in p10)
    # momentum: did she beat her own line in the previous 2 games we have lines for?
    streak = 0
    for x in reversed(prior[-3:]):
        pl_ = prevline.get((pl, mk, x["tip"]))
        if pl_ is None: break
        if x[mk] > pl_: streak += 1
        else: break
    rest = (gt - prior[-1]["tip"]).total_seconds()/86400
    pv = prevline.get((pl, mk, gt))
    dt = now["date"]
    od = OPP.get((tm, gt))
    g_ = GM.get((od[0], tuple(sorted((tm, od[1])))), {}) if od else {}
    B.append(dict(pl=pl, mk=mk, gt=gt, date=dt, tm=tm, rank=rank, line=line,
                  over_od=sd["Over"][2], under_od=sd["Under"][2], over_won=now[mk] > line,
                  use3=us3, use_tr=(None if (us3 is None or us10 is None) else us3-us10),
                  min_tr=statistics.mean(x["min"] for x in p3) - statistics.mean(x["min"] for x in p10),
                  form=statistics.mean(x[mk] for x in p5) - line,
                  medgap=med10 - line, streak=streak, rest=rest,
                  starred=(None if pv is None else line - pv < 0.5),
                  linemv=(None if pv is None else line - pv),
                  price=sd["Over"][2],
                  tot=g_.get("tot", (None, None))[1], spr=g_.get("spr", (None, None))[1],
                  ml=g_.get("ml", (None, None))[1],
                  won_last=result.get((prior[-1]["date"], prior[-1]["tm"]))))
print(f"{len(B)} two-sided board quotes with full box history")
for k in ("use_tr", "min_tr", "form", "medgap", "starred", "tot", "spr", "ml", "won_last"):
    print(f"    {k:<10} present on {sum(1 for r in B if r.get(k) is not None):>5}")
print("")

def med_of(key):
    v = sorted(r[key] for r in B if r.get(key) is not None)
    return v[len(v)//2] if v else None

CELLS = []
def add(name, sel):
    for w in ("over", "under"):
        CELLS.append((f"{name} [{w}]", sel, w))
# BOX
for k, lbl in (("use_tr", "usage trend"), ("min_tr", "minutes trend"),
               ("form", "form vs line"), ("medgap", "median gap"), ("price", "price")):
    m = med_of(k)
    if m is None: continue
    add(f"{lbl} HIGH", lambda r, k=k, m=m: r.get(k) is not None and r[k] >= m)
    add(f"{lbl} LOW",  lambda r, k=k, m=m: r.get(k) is not None and r[k] < m)
# RANK
for k in range(1, 6):
    add(f"rank {k}", lambda r, k=k: r["rank"] == k)
# MOMENTUM
for s in (0, 1, 2):
    add(f"over-streak {s}", lambda r, s=s: r["streak"] == s)
add("rested 2+ days", lambda r: r["rest"] >= 2)
add("back-to-back-ish (<2d)", lambda r: r["rest"] < 2)
add("team won last", lambda r: r.get("won_last") is True)
add("team lost last", lambda r: r.get("won_last") is False)
# LINE
add("STARRED", lambda r: r.get("starred") is True)
add("raised", lambda r: r.get("starred") is False)
# GAME MARKETS
for k, lbl in (("tot", "game total"), ("spr", "spread"), ("ml", "win prob")):
    m = med_of(k)
    if m is None: continue
    add(f"{lbl} HIGH", lambda r, k=k, m=m: r.get(k) is not None and r[k] >= m)
    add(f"{lbl} LOW",  lambda r, k=k, m=m: r.get(k) is not None and r[k] < m)
# MARKET
for mk in ALL_MK:
    add(f"market {mk}", lambda r, mk=mk: r["mk"] == mk)

MINN = 120
def score(sel, w, lab):
    g = [r for r in B if sel(r)]
    if len(g) < MINN: return None
    if w == "over":
        return sum((r["over_od"]-1) if lab[id(r)] else -1.0 for r in g)/len(g), len(g)
    return sum((r["under_od"]-1) if not lab[id(r)] else -1.0 for r in g)/len(g), len(g)

real_lab = {id(r): r["over_won"] for r in B}
res = []
for nm, sel, w in CELLS:
    s = score(sel, w, real_lab)
    if s: res.append((s[0], nm, s[1]))
res.sort(reverse=True)
print("="*100)
print(f"  {len(res)} cells with n>={MINN}.  TOP 12 AND BOTTOM 6")
print("="*100)
for v, nm, n in res[:12]:
    print(f"  {nm:<34} n={n:<5} ROI {100*v:+6.1f}%")
print("  ...")
for v, nm, n in res[-6:]:
    print(f"  {nm:<34} n={n:<5} ROI {100*v:+6.1f}%")
print("")
print("="*100)
print("  GLOBAL PERMUTATION OVER THE WHOLE GRID")
print("="*100)
best_real = res[0][0]
outs = [r["over_won"] for r in B]
T = 1500; beat = 0; sims = []
for _ in range(T):
    random.shuffle(outs)
    lab = {id(r): w for r, w in zip(B, outs)}
    b = max((score(sel, w, lab) or (-9,))[0] for nm, sel, w in CELLS)
    sims.append(b)
    if b >= best_real: beat += 1
sims.sort()
print(f"  best real cell: {res[0][1]}  ROI {100*best_real:+.1f}%")
print(f"  shuffled best-of-grid: median {100*sims[T//2]:+.1f}%  p95 {100*sims[int(T*0.95)]:+.1f}%  "
      f"max {100*sims[-1]:+.1f}%")
print(f"  GLOBAL p = {beat/T:.4f}")
print("")
print(f"  the noise ceiling on a {len(res)}-cell grid at n>={MINN} is p95 = "
      f"{100*sims[int(T*0.95)]:+.1f}%. Anything below that is indistinguishable from luck.")
print(f"  cells that clear it: " +
      str([nm for v, nm, n in res if v >= sims[int(T*0.95)]]) or "none")
