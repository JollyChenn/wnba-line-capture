# hybrid_test.py - the user's proposal, tested exactly as specified.
# ---------------------------------------------------------------------------------------------
#   "parlay those 2, then bet single with them too, and if there are 3 pairs we only choose 2
#    pairs. each pair 1 unit"
#
# So per slate:
#   * every Model S pick as a SINGLE, 1u each
#   * PLUS 2-leg parlays built from those same picks, 1u each, capped at 2 tickets a night
#   * pairs are random and non-overlapping (a bet appears in at most one parlay)
#
# The legs are therefore double-exposed: a player who loses costs you her single AND the parlay
# she is in. That is the thing to measure - it is not the same as doing one or the other.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
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

MKTS = ("pra", "pr", "pts")
SIGS = ("flip", "hotover", "overshoot")
gm = {g.get("game_id"): (g.get("date", ""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, pra=p_ + rb + a, pr=p_ + rb, pts=p_))
    team[pl] = r.get("team")
tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t - when).total_seconds() <= 60 * 3600: return t
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
        gt = game_for(tm, t)
        if gt: bygame[(pl, mk, gt)].append((t, ln, o))
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
    BETS.append(dict(pl=pl, day=gt.strftime("%Y%m%d"), odds=seq[-1][2], won=rec[mk] > line))
byday = collections.defaultdict(list)
for r in BETS: byday[r["day"]].append(r)
for d in list(byday):
    best = {}
    for r in sorted(byday[d], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[d] = list(best.values())
days = sorted(byday)

def trial(max_pairs, do_singles, do_parlays, stake_par=1.0):
    risk = prof = 0.0; tickets = 0; parw = parn = 0
    eq = peak = dd = 0.0
    for d in days:
        pool = byday[d][:]; random.shuffle(pool)
        if do_singles:
            for r in pool:
                risk += 1.0; g = (r["odds"] - 1) if r["won"] else -1.0
                prof += g; eq += g; peak = max(peak, eq); dd = min(dd, eq - peak); tickets += 1
        if do_parlays:
            made = 0
            for i in range(0, len(pool) - 1, 2):
                if made >= max_pairs: break
                a, b_ = pool[i], pool[i + 1]
                od = a["odds"] * b_["odds"]; won = a["won"] and b_["won"]
                risk += stake_par; g = stake_par * ((od - 1) if won else -1.0)
                prof += g; eq += g; peak = max(peak, eq); dd = min(dd, eq - peak)
                tickets += 1; made += 1; parn += 1; parw += won
    return risk, prof, dd, tickets, parw, parn

def summarise(label, **kw):
    R = [trial(**kw) for _ in range(1500)]
    R.sort(key=lambda x: x[1] / x[0])
    m = R[len(R) // 2]
    neg = sum(1 for x in R if x[1] < 0)
    lo = R[len(R) // 20]; hi = R[-len(R) // 20]
    print(f"  {label:<40} risk {m[0]:6.1f}u  profit {m[1]:+7.2f}u  ROI {100*m[1]/m[0]:+6.1f}%"
          f"  (p5 {100*lo[1]/lo[0]:+.1f}% p95 {100*hi[1]/hi[0]:+.1f}%)  DD {m[2]:+6.2f}u"
          f"  neg {100*neg/len(R):.0f}%")
    return m

print(f"{sum(len(v) for v in byday.values())} Model S bets over {len(days)} slates")
sizes = collections.Counter(len(v) for v in byday.values())
print("  slate sizes: " + ", ".join(f"{k}-bet x{v}" for k, v in sorted(sizes.items())))
print("")
print("=" * 118)
print("  THE PROPOSAL vs THE ALTERNATIVES  (1500 random pairings each)")
print("=" * 118)
summarise("SINGLES only, 1u",                 max_pairs=0,  do_singles=True,  do_parlays=False)
summarise("PARLAYS only, max 2/night, 1u",    max_pairs=2,  do_singles=False, do_parlays=True)
summarise("BOTH - singles 1u + max 2 pairs 1u  <- YOURS", max_pairs=2, do_singles=True, do_parlays=True)
summarise("BOTH - singles 1u + UNCAPPED pairs", max_pairs=99, do_singles=True, do_parlays=True)
summarise("BOTH - singles 1u + max 2 pairs 0.5u", max_pairs=2, do_singles=True, do_parlays=True, stake_par=0.5)
print("")
print("=" * 118)
print("  SAME TOTAL RISK - scale each scheme so it deploys the capital singles-only would")
print("=" * 118)
base = trial(max_pairs=0, do_singles=True, do_parlays=False)
target = base[0]
for lbl, kw in (("SINGLES only", dict(max_pairs=0, do_singles=True, do_parlays=False)),
                ("PARLAYS only, max 2/night", dict(max_pairs=2, do_singles=False, do_parlays=True)),
                ("BOTH, max 2 pairs   <- YOURS", dict(max_pairs=2, do_singles=True, do_parlays=True))):
    R = [trial(**kw) for _ in range(1500)]
    R.sort(key=lambda x: x[1] / x[0])
    m = R[len(R) // 2]
    sc = target / m[0]
    print(f"  {lbl:<34} stake x{sc:.2f}  risk {m[0]*sc:6.1f}u  profit {m[1]*sc:+7.2f}u"
          f"  ROI {100*m[1]/m[0]:+6.1f}%  DD {m[2]*sc:+6.2f}u")
