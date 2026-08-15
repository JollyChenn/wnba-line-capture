# audit_hybrid.py - two questions, checked carefully.
#   1. Has the model actually degraded recently, or is the late slump ordinary variance?
#   2. Does the parlay arithmetic hold up under inspection - including the failure modes that
#      have already caught me four times today (double counting, mismatched lines, stale odds)?
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260820)
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

MKTS = ("pra", "pr", "pts"); SIGS = ("flip", "hotover", "overshoot")
gm = {g.get("game_id"): (g.get("date", ""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); team = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(tip=tp, pra=p_+rb+a, pr=p_+rb, pts=p_))
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
    BETS.append(dict(pl=pl, name=(b.get("player") or "").split()[-1], mk=mk, tip=gt,
                     day=gt.strftime("%Y%m%d"), odds=seq[-1][2], won=rec[mk] > line,
                     line=line, actual=rec[mk], nquote=len(seq)))
byday = collections.defaultdict(list)
for r in BETS: byday[r["day"]].append(r)
for d in list(byday):
    best = {}
    for r in sorted(byday[d], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[d] = sorted(best.values(), key=lambda r: r["tip"])
days = sorted(byday)
flat = [r for d in days for r in byday[d]]
P = sum(1 for r in flat if r["won"])/len(flat)

print("="*106)
print("  1. IS THE RECENT SLUMP REAL, OR IS IT WHAT A GOOD MODEL LOOKS LIKE SOMETIMES?")
print("="*106)
print("  rolling 20-bet ROI through the sample:")
for i in range(0, len(flat)-19, 10):
    w = flat[i:i+20]
    u = sum((r["odds"]-1) if r["won"] else -1.0 for r in w)
    hit = sum(1 for r in w if r["won"])/20
    bar = "#" * max(0, int(20*u/10)) if u > 0 else "." * max(0, int(-20*u/10))
    print(f"    bets {i+1:>3}-{i+20:<3} {w[0]['day']}..{w[-1]['day']}  {100*hit:5.1f}%  {u:+6.2f}u  {bar}")
print("")
half = len(flat)//2
for lbl, g in (("first half ", flat[:half]), ("second half", flat[half:])):
    w = sum(1 for r in g if r["won"]); u = sum((r["odds"]-1) if r["won"] else -1.0 for r in g)
    print(f"  {lbl}  n={len(g)}  {100*w/len(g):5.1f}%  {u:+7.2f}u  ROI {100*u/len(g):+6.1f}%")
last = flat[-20:]
lw = sum(1 for r in last if r["won"]); lu = sum((r["odds"]-1) if r["won"] else -1.0 for r in last)
print(f"  LAST 20 BETS  {100*lw/len(last):5.1f}%  {lu:+7.2f}u  ROI {100*lu/len(last):+6.1f}%")
print("")
print("  MONTE CARLO: if the true hit rate really is %.1f%%, how often does a random 20-bet" % (100*P))
print("  stretch come out at or below what the last 20 did?")
odds = [r["odds"] for r in flat]
worse = 0; T = 20000
for _ in range(T):
    s = random.sample(odds, 20)
    u = sum((o-1) if random.random() < P else -1.0 for o in s)
    if u <= lu: worse += 1
print(f"    {worse}/{T} = {100*worse/T:.1f}% of random 20-bet stretches are this bad or worse")
print(f"    -> {'ORDINARY VARIANCE' if worse/T > 0.05 else 'unusual, worth watching'}")
print("")
print("="*106)
print("  2. PARLAY AUDIT - checking the arithmetic and the traps")
print("="*106)
pairs = []
for d in days:
    v = byday[d]
    for i in range(0, len(v)-1, 2):
        pairs.append((v[i], v[i+1]))
print(f"  pairs formed: {len(pairs)}   legs consumed: {2*len(pairs)}   bets available: {len(flat)}")
used = collections.Counter()
for a, b2 in pairs: used[(a['day'], a['pl'])] += 1; used[(b2['day'], b2['pl'])] += 1
reuse = [k for k, c in used.items() if c > 1]
print(f"  CHECK any leg reused across parlays: {len(reuse)} {'FAIL' if reuse else 'OK'}")
samegame = sum(1 for a, b2 in pairs if a["tip"] == b2["tip"])
print(f"  CHECK legs from the SAME GAME (correlated): {samegame} of {len(pairs)} "
      f"({100*samegame/len(pairs):.0f}%)")
mism = sum(1 for a, b2 in pairs if a["nquote"] < 1 or b2["nquote"] < 1)
print(f"  CHECK any leg priced off an empty quote series: {mism} {'FAIL' if mism else 'OK'}")
manual = pairs[0]
a, b2 = manual
print(f"  SPOT CHECK  {a['name']} @{a['odds']} x {b2['name']} @{b2['odds']} = "
      f"{a['odds']*b2['odds']:.4f}  (payout on 1u if both land)")
print(f"              legs won? {a['won']} / {b2['won']}  -> parlay "
      f"{'WIN' if a['won'] and b2['won'] else 'loss'}")
pu = sum((a['odds']*b2['odds']-1) if (a['won'] and b2['won']) else -1.0 for a, b2 in pairs)
legs_u = sum((r['odds']-1) if r['won'] else -1.0 for a, b2 in pairs for r in (a, b2))
print(f"  RECONCILE   parlay P&L {pu:+.2f}u on {len(pairs)}u risked")
print(f"              the same legs as singles: {legs_u:+.2f}u on {2*len(pairs)}u risked")
print("")
print("  same-game pairs are the one real correlation risk - two players in one game share pace.")
sg = [(a, b2) for a, b2 in pairs if a["tip"] == b2["tip"]]
dg = [(a, b2) for a, b2 in pairs if a["tip"] != b2["tip"]]
for lbl, g in (("same game ", sg), ("diff games", dg)):
    if len(g) < 5:
        print(f"    {lbl}  n={len(g)} too few"); continue
    w = sum(1 for a, b2 in g if a["won"] and b2["won"])
    u = sum((a['odds']*b2['odds']-1) if (a['won'] and b2['won']) else -1.0 for a, b2 in g)
    print(f"    {lbl}  n={len(g):<3} hit {100*w/len(g):5.1f}%  {u:+6.2f}u  ROI {100*u/len(g):+6.1f}%")
