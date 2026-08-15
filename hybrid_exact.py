# hybrid_exact.py - backtest the rule EXACTLY as model_card.py now implements it.
# ---------------------------------------------------------------------------------------------
# My earlier hybrid test used RANDOM pairing across 1500 shuffles, which answers "does the idea
# work on average". The card does something specific: it sorts the night's bets by TIP TIME and
# pairs them consecutively. That is one particular pairing out of many, so it deserves its own
# number rather than inheriting the average.
#
#   * every starred pick as a 1u single
#   * bets sorted by tip, paired consecutively, each pair 1u
#   * odd bet out stays a single only
import csv, os, sys, math, datetime, collections
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
    BETS.append(dict(pl=pl, name=(b.get("player") or "").split()[-1], mk=mk, tip=gt,
                     day=gt.strftime("%Y%m%d"), odds=seq[-1][2], won=rec[mk] > line, line=line))

byday = collections.defaultdict(list)
for r in BETS: byday[r["day"]].append(r)
for d in list(byday):
    best = {}
    for r in sorted(byday[d], key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
    byday[d] = sorted(best.values(), key=lambda r: r["tip"])       # THE CARD'S ORDER
days = sorted(byday)

print("=" * 112)
print("  NIGHT BY NIGHT - the exact card rule (sorted by tip, paired consecutively)")
print("=" * 112)
tot_s = tot_p = 0.0; ns = npar = 0; wins = parw = 0
eq = peak = ddh = 0.0
eqs = peaks = dds = 0.0
for d in days:
    v = byday[d]
    su = sum((r["odds"] - 1) if r["won"] else -1.0 for r in v)
    ns += len(v); wins += sum(1 for r in v if r["won"]); tot_s += su
    pu = 0.0; pl_txt = []
    for i in range(0, len(v) - 1, 2):
        a, b2 = v[i], v[i + 1]
        od = a["odds"] * b2["odds"]; won = a["won"] and b2["won"]
        g = (od - 1) if won else -1.0
        pu += g; npar += 1; parw += won
        pl_txt.append(f"{a['name']}+{b2['name']} @{od:.2f} {'WIN' if won else 'loss'}")
    tot_p += pu
    for r in v:
        eqs += (r["odds"] - 1) if r["won"] else -1.0
        peaks = max(peaks, eqs); dds = min(dds, eqs - peaks)
    eq += su + pu; peak = max(peak, eq); ddh = min(ddh, eq - peak)
    if len(v) >= 2 or su != 0:
        w = sum(1 for r in v if r["won"])
        print(f"  {d}  {len(v)} bet(s) {w}-{len(v)-w}  singles {su:+6.2f}u  "
              f"parlay {pu:+6.2f}u  night {su+pu:+6.2f}u  running {eq:+7.2f}u")
        for t in pl_txt: print(f"             {t}")
print("")
print("=" * 112)
print("  TOTALS")
print("=" * 112)
print(f"  {'':<26} {'tickets':>8} {'hit%':>7} {'risk':>8} {'profit':>9} {'ROI':>8} {'worst DD':>10}")
print(f"  {'SINGLES only, 1u':<26} {ns:>8} {100*wins/ns:6.1f}% {ns:7.1f}u {tot_s:+8.2f}u"
      f" {100*tot_s/ns:+7.1f}% {dds:+9.2f}u")
print(f"  {'PARLAYS only, 1u':<26} {npar:>8} {100*parw/npar:6.1f}% {npar:7.1f}u {tot_p:+8.2f}u"
      f" {100*tot_p/npar:+7.1f}%")
print(f"  {'BOTH  <- THE CARD RULE':<26} {ns+npar:>8} {'':>7} {ns+npar:7.1f}u {tot_s+tot_p:+8.2f}u"
      f" {100*(tot_s+tot_p)/(ns+npar):+7.1f}% {ddh:+9.2f}u")
print("")
cut = days[int(len(days) * 0.6)]
print("  out of sample, split " + cut + ":")
for lbl, dd in (("IN ", [d for d in days if d < cut]), ("OUT", [d for d in days if d >= cut])):
    s_ = p_ = 0.0; n_ = q_ = 0
    for d in dd:
        v = byday[d]
        s_ += sum((r["odds"] - 1) if r["won"] else -1.0 for r in v); n_ += len(v)
        for i in range(0, len(v) - 1, 2):
            a, b2 = v[i], v[i + 1]
            od = a["odds"] * b2["odds"]; won = a["won"] and b2["won"]
            p_ += (od - 1) if won else -1.0; q_ += 1
    print(f"    {lbl}  singles {n_:>3} ROI {100*s_/n_:+6.1f}%  |  parlays {q_:>3} ROI "
          f"{(100*p_/q_ if q_ else 0):+6.1f}%  |  BOTH ROI {100*(s_+p_)/(n_+q_):+6.1f}%")
print("")
print("  how the tip-time pairing compares with the 1500-shuffle average: random pairing gave")
print("  the hybrid ROI +23.2%. Any large gap here is pairing luck, not a better rule.")
