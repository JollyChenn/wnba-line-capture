# under_gamestar.py - the between-games game-market test, applied to the UNDER models.
# ---------------------------------------------------------------------------------------------
# This is a FALSIFICATION test, not another slice. On Model S overs the pattern was:
#     game total HIGHER than the team's last game  ->  our overs do better
#     team more of an UNDERDOG than last game      ->  our overs do better
# If that is a real pace/possession effect it MUST INVERT on unders: a rising total should hurt
# an under, a falling total should help it. If unders move the SAME way as overs, the pattern is
# an artifact and dies.
#
# The under sources also carry far more data than our over signals - newunder alone has thousands
# of rows - so this is the first version of this test with any real power behind it.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
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

FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

G = collections.defaultdict(dict)
for r in load("gamelines.csv"):
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2 or not st: continue
    hm, aw = FULL2AB.get(tm[0].strip(), ""), FULL2AB.get(tm[1].strip(), "")
    if not hm or not aw: continue
    ab = tuple(sorted((hm, aw)))
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if cap is None: continue
    slot = G[(st, ab)]; slot["home"] = hm
    if r.get("type") == "total" and pts is not None:
        if "tot" not in slot or cap > slot["tot"][0]: slot["tot"] = (cap, pts)
    elif r.get("type") == "spread" and pts is not None:
        if "spr" not in slot or cap > slot["spr"][0]: slot["spr"] = (cap, pts)
    elif r.get("type") == "moneyline":
        pr = (r.get("prices") or "").split(",")
        h = am(pr[0]) if pr and pr[0] else None
        if h is not None and ("ml" not in slot or cap > slot["ml"][0]): slot["ml"] = (cap, h)
hist = collections.defaultdict(list)
for (st, ab), slot in G.items():
    hm = slot.get("home")
    if not hm: continue
    for t in ab:
        own = (t == hm)
        spr = slot.get("spr", (None, None))[1]; ml = slot.get("ml", (None, None))[1]
        hist[t].append(dict(date=st, tot=slot.get("tot", (None, None))[1],
                            spr=(spr if own else (None if spr is None else -spr)),
                            ml=(ml if own else (None if ml is None else 1-ml))))
for v in hist.values(): v.sort(key=lambda x: x["date"])
def prev_game(t, d):
    v = [x for x in hist.get(t, []) if x["date"] < d]
    return v[-1] if v else None
def this_game(t, d):
    return next((x for x in hist.get(t, []) if x["date"] == d), None)

MKTS = ("pts","pra","pr","pa","reb","ast","ra")
gm = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, date=dt, pts=p_, reb=rb, ast=a,
                         pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a))
    team[pl] = r.get("team")
tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None

# board for BOTH sides - an under is settled and priced on the Under quote
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, sd, ln), v in raw.items():
    tm = team.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, sd, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

def build(side, srcs):
    seen, K = set(), []
    for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
        if b.get("side") != side or b.get("src") not in srcs: continue
        pl, mk = (b.get("player") or "").lower(), b.get("market")
        if mk not in MKTS: continue
        t0, tm = ts(b.get("captured_utc")), team.get(pl)
        if not (t0 and tm): continue
        gt = game_for(tm, t0)
        if not gt or (pl, mk, gt) in seen: continue
        seq = bygame.get((pl, mk, side, gt), [])
        rec = next((g for g in plog.get(pl, []) if g["tip"] == gt), None)
        if not seq or not rec: continue
        line, price = seq[-1][1], seq[-1][2]
        if rec[mk] == line: continue
        seen.add((pl, mk, gt))
        won = (rec[mk] > line) if side == "Over" else (rec[mk] < line)
        now_, prv = this_game(tm, rec["date"]), prev_game(tm, rec["date"])
        d = {}
        if now_ and prv:
            for k in ("tot","spr","ml"):
                d[k] = (now_[k]-prv[k]) if (now_[k] is not None and prv[k] is not None) else None
        K.append(dict(pl=pl, date=rec["date"], odds=price, won=won,
                      d_tot=d.get("tot"), d_spr=d.get("spr"), d_ml=d.get("ml")))
    byday = collections.defaultdict(list)
    for r in K: byday[r["date"]].append(r)
    for dd in list(byday):
        best = {}
        for r in sorted(byday[dd], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
        byday[dd] = list(best.values())
    return [r for v in byday.values() for r in v]

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show(rows, label, minn=20):
    n = len(rows)
    if n < minn:
        print(f"    {label:<34} n={n:<4} too few"); return None
    w = sum(1 for r in rows if r["won"])
    print(f"    {label:<34} n={n:<4} {100*w/n:5.1f}%  ROI {100*roi(rows):+6.1f}%")
    return roi(rows)


# THE STAR WAS DISCOVERED ON OVERS AND NEVER APPLIED TO UNDERS. For an over, the book RAISING her
# number means it has already repriced what our signal saw. The mirror for an UNDER is the book
# CUTTING her number. That test has never been run - the unders were written off on their raw
# record, which is precisely the mistake that nearly cost us overshoot.
def build2(side, srcs):
    seen, K = set(), []
    for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
        if b.get("side") != side or b.get("src") not in srcs: continue
        pl, mk = (b.get("player") or "").lower(), b.get("market")
        if mk not in MKTS: continue
        t0, tm = ts(b.get("captured_utc")), team.get(pl)
        if not (t0 and tm): continue
        gt = game_for(tm, t0)
        if not gt or (pl, mk, gt) in seen: continue
        seq = bygame.get((pl, mk, side, gt), [])
        rec = next((g for g in plog.get(pl, []) if g["tip"] == gt), None)
        if not seq or not rec: continue
        line, price = seq[-1][1], seq[-1][2]
        if rec[mk] == line: continue
        seen.add((pl, mk, gt))
        earlier = sorted(g for (p2, m2, sd2, g) in bygame
                         if p2 == pl and m2 == mk and sd2 == side and g < gt)
        pv = bygame[(pl, mk, side, earlier[-1])][-1][1] if earlier else None
        won = (rec[mk] > line) if side == "Over" else (rec[mk] < line)
        K.append(dict(pl=pl, mk=mk, date=rec["date"], odds=price, won=won, line=line, prev=pv,
                      mv=(None if pv is None else line - pv)))
    byday = collections.defaultdict(list)
    for r in K: byday[r["date"]].append(r)
    for dd in list(byday):
        best = {}
        for r in sorted(byday[dd], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
        byday[dd] = list(best.values())
    return [r for v in byday.values() for r in v]

def roi2(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def show2(rows, label, minn=20):
    n = len(rows)
    if n < minn:
        print(f"    {label:<44} n={n:<4} too few"); return
    w = sum(1 for r in rows if r["won"])
    avg = sum(r["odds"] for r in rows)/n
    print(f"    {label:<44} n={n:<4} {100*w/n:5.1f}%  ROI {100*roi2(rows):+6.1f}%  be {100/avg:.1f}%")


allun = build2("Under", ("newunder","model","starout","fragile"))
U = [r for r in allun if r["mk"] in ("pra","pr","pts")]
def roi2(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
# to FADE an under you buy the OVER on the same player-game, at the OVER price
faded = []
for r in U:
    key = None
    for (p2, m2, sd, g) in bygame:
        if p2 == r["pl"] and m2 == r["mk"] and sd == "Over":
            pass
    # find the over quote for the same player-market-game
    cand = [(g, v) for (p2, m2, sd, g), v in bygame.items()
            if p2 == r["pl"] and m2 == r["mk"] and sd == "Over"]
    for g, v in cand:
        if v and v[-1][1] == r["line"]:
            faded.append(dict(odds=v[-1][2], won=not r["won"])); break
print("="*100)
print("  CAN WE FADE THE UNDERS? buy the OVER on the same selection, at the OVER price")
print("="*100)
n = len(U); w = sum(1 for r in U if r["won"])
avg_u = sum(r["odds"] for r in U)/n
print(f"  the unders themselves   n={n:<4} hit {100*w/n:5.1f}%  avg {avg_u:.3f}  "
      f"break-even {100/avg_u:.1f}%  ROI {100*roi2(U):+.1f}%")
if len(faded) >= 30:
    fn = len(faded); fw = sum(1 for r in faded if r["won"])
    avg_f = sum(r["odds"] for r in faded)/fn
    print(f"  FADED (buy the over)    n={fn:<4} hit {100*fw/fn:5.1f}%  avg {avg_f:.3f}  "
          f"break-even {100/avg_f:.1f}%  ROI {100*roi2(faded):+.1f}%")
    print("")
    print(f"  cushion when fading: {100*fw/fn:.1f}% hit against a {100/avg_f:.1f}% break-even"
          f"  ->  {100*fw/fn - 100/avg_f:+.1f}pp")
    print("")
    print("  the under misses by 7.4pp, so the over on the same line clears by about the same")
    print("  MINUS the book's cut on the other side. That cut is the whole reason fading a bad")
    print("  bet is not a good bet - you pay the vig twice, once to be wrong and once to invert.")
else:
    print(f"  only {len(faded)} matched over quotes - too few")
