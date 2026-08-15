# parlay_full.py - 2-leg parlays, now that the pricing question is settled.
# ---------------------------------------------------------------------------------------------
# CONFIRMED AT THE BOOK BY THE USER: 1.87 x 1.73 = 3.2351 and 1xbet quoted 3.235. It pays the
# STRAIGHT PRODUCT on a 2-leg accumulator, no extra margin. That was the single unknown that
# decided whether any of this matters, and it lands in favour of parlays.
#
# METHOD. Pairs are drawn RANDOMLY and WITHOUT REUSE inside a slate, 2 legs maximum, over many
# shuffles. Enumerating every possible pair is what I did first and it was wrong: a 7-bet night
# makes 21 overlapping pairs that all win together, which inflated ROI to +81.6% and manufactured
# most of an apparent leg correlation.
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260818)
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
plog = collections.defaultdict(list)
team = {}
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
    if t:
        tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()

def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t - when).total_seconds() <= 60 * 3600:
            return t
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
    if pv is None or line - pv >= 0.5: continue                  # MODEL S only
    BETS.append(dict(pl=pl, tm=tm, day=gt.strftime("%Y%m%d"), odds=seq[-1][2], won=rec[mk] > line))

byday = collections.defaultdict(list)
for r in BETS: byday[r["day"]].append(r)
for d in list(byday):                                            # one position per player
    best = {}
    for r in sorted(byday[d], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[d] = list(best.values())

allb = [r for v in byday.values() for r in v]
n_s = len(allb)
w_s = sum(1 for r in allb if r["won"])
u_s = sum((r["odds"] - 1) if r["won"] else -1.0 for r in allb)
print(f"SINGLES  {n_s} bets  {100*w_s/n_s:.1f}%  {u_s:+.2f}u  ROI {100*u_s/n_s:+.1f}%  risk {n_s}u")
print("")

def run(days, trials=2000):
    out = []
    for _ in range(trials):
        n = w = 0; u = 0.0; left = 0
        for d in days:
            pool = byday[d][:]
            random.shuffle(pool)
            for i in range(0, len(pool) - 1, 2):
                a, b_ = pool[i], pool[i + 1]
                od = a["odds"] * b_["odds"]
                won = a["won"] and b_["won"]
                n += 1; w += won; u += (od - 1) if won else -1.0
            left += len(pool) % 2
        if n: out.append((w / n, u / n, n, u, left))
    return sorted(out, key=lambda x: x[1])

days = sorted(byday)
res = run(days)
mid = res[len(res) // 2]
print("=" * 98)
print("  2-LEG PARLAYS, random non-overlapping pairing, 1u per ticket, 2000 shuffles")
print("=" * 98)
print(f"  tickets per pass   ~{mid[2]}   (plus ~{mid[4]} odd bets left unpaired)")
print(f"  hit rate   median {100*mid[0]:5.1f}%    p5 {100*res[len(res)//20][0]:.1f}%   p95 {100*res[-len(res)//20][0]:.1f}%")
print(f"  ROI        median {100*mid[1]:+5.1f}%    p5 {100*res[len(res)//20][1]:+.1f}%   p95 {100*res[-len(res)//20][1]:+.1f}%")
print(f"  units      median {mid[3]:+.2f}u on {mid[2]}u risked")
print(f"  independence would predict {100*(w_s/n_s)**2:.1f}% - actual {100*mid[0]:.1f}%")
losers = sum(1 for x in res if x[1] < 0)
print(f"  shuffles with a NEGATIVE ROI: {losers}/{len(res)} = {100*losers/len(res):.1f}%")
print("")
print("=" * 98)
print("  EQUAL RISK - singles stake 1u; parlays stake enough to deploy the same capital")
print("=" * 98)
stake = n_s / mid[2]
print(f"  singles        {n_s} x 1.00u = {n_s:5.1f}u risked   profit {u_s:+7.2f}u   ROI {100*u_s/n_s:+6.1f}%")
print(f"  2-leg parlays  {mid[2]} x {stake:.2f}u = {mid[2]*stake:5.1f}u risked   profit {mid[3]*stake:+7.2f}u   ROI {100*mid[1]:+6.1f}%")
print("")
print("=" * 98)
print("  OUT OF SAMPLE")
print("=" * 98)
cut = days[int(len(days) * 0.6)]
for lbl, dd in (("IN ", [d for d in days if d < cut]), ("OUT", [d for d in days if d >= cut])):
    sub = [r for d in dd for r in byday[d]]
    ws = sum(1 for r in sub if r["won"])
    us = sum((r["odds"] - 1) if r["won"] else -1.0 for r in sub)
    rr = run(dd, 800)
    m = rr[len(rr) // 2]
    print(f"  {lbl}  singles {len(sub):>3} bets ROI {100*us/len(sub):+6.1f}%   |   "
          f"parlays ~{m[2]} tickets hit {100*m[0]:5.1f}% ROI {100*m[1]:+6.1f}%")
print("")
print("=" * 98)
print("  DRAWDOWN - the real cost of parlaying")
print("=" * 98)
eq = peak = dd_ = 0.0; run_ = 0; worst = 0
for d in days:
    for r in byday[d]:
        eq += (r["odds"] - 1) if r["won"] else -1.0
        peak = max(peak, eq); dd_ = min(dd_, eq - peak)
        run_ = 0 if r["won"] else run_ + 1; worst = max(worst, run_)
print(f"  {'singles 1u':<20} worst drawdown {dd_:+7.2f}u   longest losing run {worst}")
dds, runs = [], []
for _ in range(400):
    eq = peak = d2 = 0.0; run2 = 0; w2 = 0
    for d in days:
        pool = byday[d][:]
        random.shuffle(pool)
        for i in range(0, len(pool) - 1, 2):
            o = pool[i]["odds"] * pool[i + 1]["odds"]
            won = pool[i]["won"] and pool[i + 1]["won"]
            eq += (o - 1) if won else -1.0
            peak = max(peak, eq); d2 = min(d2, eq - peak)
            run2 = 0 if won else run2 + 1; w2 = max(w2, run2)
    dds.append(d2); runs.append(w2)
dds.sort(); runs.sort()
print(f"  {'2-leg parlay 1u':<20} worst drawdown {dds[len(dds)//2]:+7.2f}u (p5 {dds[len(dds)//20]:+.2f}u)"
      f"   longest losing run {runs[len(runs)//2]} (p95 {runs[-len(runs)//20]})")
