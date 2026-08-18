# mate_by_stat.py - the teammate effect, split by STAT, using box scores for power.
# ---------------------------------------------------------------------------------------------
# The pooled test said teammates do BETTER when our pick hits (52.8% vs 45.9%), i.e. pace beats
# usage competition. But pooling hides that the three stats have OPPOSITE mechanisms:
#
#   POINTS    finite shots. If our pick takes 20 of them, a teammate's scoring should suffer.
#   ASSISTS   COMPLEMENTARY. Somebody passed her the ball on a big scoring night, so a teammate's
#             assists should RISE when our pick goes over. This is the one with a clean prediction.
#   REBOUNDS  driven by misses and pace, largely independent of who is scoring. Should follow pace.
#
# Measured against each teammate's OWN trailing average rather than a quoted line, because the
# board only prices a fraction of players and the box score prices all of them - roughly ten
# times the sample, which is the whole reason the last few tests could not resolve anything.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260909)
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

BET_MK = ("pra", "pr", "pts"); SIGS = ("flip", "hotover", "overshoot")
gmeta = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: gmeta[g.get("game_id")] = (g.get("date", ""), t)
pgrow = {}; roster = collections.defaultdict(set); teamof = {}
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp = gmeta[gid]
    pl, tm = (r.get("player") or "").lower(), r.get("team")
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    mn = f(r.get("min")) or 0
    pgrow[(pl, tp)] = dict(tm=tm, tip=tp, date=dt, min=mn, pts=p_, reb=rb, ast=a,
                           pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)
    roster[(tm, tp)].add(pl); teamof[pl] = tm
hist = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): hist[pl].append(row)
for v in hist.values(): v.sort(key=lambda x: x["tip"])

tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in BET_MK and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = teamof.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

seen, OURS = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in BET_MK: continue
    t0, tm = ts(b.get("captured_utc")), teamof.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    seq = bygame.get((pl, mk, gt), []); now = pgrow.get((pl, gt))
    if not seq or not now: continue
    line = seq[-1][1]
    if now[mk] == line: continue
    e = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, e[-1])][-1][1] if e else None
    if pv is None or line - pv >= 0.5: continue
    seen.add((pl, mk, gt))
    OURS.append(dict(pl=pl, tm=tm, gt=gt, hit=now[mk] > line))
print(f"{len(OURS)} starred Model S bets ({sum(1 for o in OURS if o['hit'])} hit)")

# every teammate on those games, measured against her OWN trailing-5 average
ROWS = []
for o in OURS:
    for m in roster.get((o["tm"], o["gt"]), ()):
        if m == o["pl"]: continue
        now = pgrow.get((m, o["gt"]))
        if not now or now["min"] < 8: continue          # garbage-time bodies add only noise
        prior = [x for x in hist.get(m, []) if x["tip"] < o["gt"]][-5:]
        if len(prior) < 4: continue
        rec = dict(mate=m, ourhit=o["hit"], min=now["min"])
        for st in ("pts", "reb", "ast"):
            base = statistics.mean(x[st] for x in prior)
            rec[st + "_d"] = now[st] - base
            rec[st + "_up"] = now[st] > base
        rec["min_d"] = now["min"] - statistics.mean(x["min"] for x in prior)
        ROWS.append(rec)
print(f"{len(ROWS)} teammate performances measured against their own trailing-5 average")
print("")
print("="*100)
print("  DOES THE TEAMMATE EFFECT DIFFER BY STAT? (vs her own recent average)")
print("="*100)
won = [r for r in ROWS if r["ourhit"]]; lost = [r for r in ROWS if not r["ourhit"]]
print(f"  our pick HIT on {len(won)} teammate-games, MISSED on {len(lost)}")
print("")
print(f"  {'stat':<10}{'when ours HIT':>22}{'when ours MISSED':>22}{'gap':>12}")
for st, lbl in (("pts", "POINTS"), ("reb", "REBOUNDS"), ("ast", "ASSISTS"), ("min", "MINUTES")):
    a = statistics.mean(r[st + "_d"] for r in won)
    b = statistics.mean(r[st + "_d"] for r in lost)
    print(f"  {lbl:<10}{a:>+21.2f}{b:>+21.2f}{a-b:>+11.2f}")
print("")
print("  (numbers are the teammate's stat MINUS her own trailing-5 average, so 0 = normal)")
print("")
print("  and as a rate - share of teammates who BEAT their own average:")
print(f"  {'stat':<10}{'ours HIT':>14}{'ours MISSED':>14}{'gap':>10}")
for st, lbl in (("pts", "POINTS"), ("reb", "REBOUNDS"), ("ast", "ASSISTS")):
    a = 100*sum(1 for r in won if r[st + "_up"])/len(won)
    b = 100*sum(1 for r in lost if r[st + "_up"])/len(lost)
    print(f"  {lbl:<10}{a:>13.1f}%{b:>13.1f}%{a-b:>+9.1f}pp")
print("")
print("="*100)
print("  PERMUTATION - shuffle which nights our pick 'hit', keep everything else")
print("="*100)
flags = [r["ourhit"] for r in ROWS]
for st, lbl in (("pts", "POINTS"), ("reb", "REBOUNDS"), ("ast", "ASSISTS")):
    real = (statistics.mean(r[st+"_d"] for r in won) - statistics.mean(r[st+"_d"] for r in lost))
    beat = 0; T = 4000
    vals = [r[st+"_d"] for r in ROWS]
    for _ in range(T):
        random.shuffle(flags)
        a = [v for v, fl in zip(vals, flags) if fl]; b = [v for v, fl in zip(vals, flags) if not fl]
        if abs(statistics.mean(a) - statistics.mean(b)) >= abs(real): beat += 1
    print(f"  {lbl:<10} real gap {real:+.2f}   two-sided p = {beat/T:.4f}")
print("")
print("  MINUTES is the control that matters: if teammates simply play longer on the nights our")
print("  pick hits, every stat rises mechanically and there is no per-stat story at all.")
