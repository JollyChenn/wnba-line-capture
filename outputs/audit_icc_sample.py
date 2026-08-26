# Hostile audit of the ICC / design-effect claim on the pre-game prop board.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = (open(os.path.join(REPO, "mega_sweep.py"), encoding="utf-8").read()
        .split('print(f"{len(B)} two-sided board quotes')[0]
        .replace('D = os.path.dirname(os.path.abspath(__file__))', 'D = REPO'))
exec(_src)
assert D == REPO, D

# ---------- 0. raw tick count ----------
ALLROWS = load("xbet_board.csv")
print("raw board rows            %d" % len(ALLROWS))
print("raw rows in the 7 markets %d" % sum(1 for r in ALLROWS if r.get("market") in ALL_MK))

# ---------- 1. build gradable closing two-sided quotes, two variants ----------
def build(require_hist):
    out = []
    for (pl, mk, gt), sd in side.items():
        if "Over" not in sd or "Under" not in sd: continue
        if sd["Over"][1] != sd["Under"][1]: continue
        now = pgrow.get((pl, gt))
        if not now: continue
        line = sd["Over"][1]
        if now[mk] == line: continue                    # push
        if require_hist:
            if now["min"] < 8: continue
            if len([x for x in hist.get(pl, []) if x["tip"] < gt]) < 6: continue
        out.append(dict(pl=pl, mk=mk, gt=gt, tm=now["tm"], date=now["date"],
                        over=1 if now[mk] > line else 0,
                        oo=sd["Over"][2], uo=sd["Under"][2]))
    return out

LOOSE = build(False)
STRICT = build(True)
for nm, Q in (("loose (all gradable)", LOOSE), ("strict (mega_sweep B)", STRICT)):
    g = len(set(q["gt"] for q in Q))
    print("%-24s quotes=%6d  games=%4d  players=%4d  over_rate=%.4f" % (
        nm, len(Q), g, len(set(q["pl"] for q in Q)), statistics.mean(q["over"] for q in Q)))

Q = LOOSE if abs(len(LOOSE) - 7259) <= abs(len(STRICT) - 7259) else STRICT
print("\n>>> auditing variant with n=%d, games=%d\n" % (len(Q), len(set(q["gt"] for q in Q))))

# ---------- 2. cluster structure ----------
def clusters(Q, keyf):
    d = collections.defaultdict(list)
    for q in Q: d[keyf(q)].append(q["over"])
    return d

KEYS = collections.OrderedDict([
 ("game",        lambda q: q["gt"]),
 ("date/slate",  lambda q: q["date"]),
 ("team-night",  lambda q: (q["tm"], q["gt"])),
 ("player",      lambda q: q["pl"]),
 ("player-game", lambda q: (q["pl"], q["gt"])),
 ("market",      lambda q: q["mk"]),
])

def icc_anova(d):
    ks = [k for k in d if len(d[k]) >= 1]
    N = sum(len(d[k]) for k in ks); k = len(ks)
    if k < 2 or N <= k: return None, None
    gm = sum(sum(d[c]) for c in ks) / N
    MSB = sum(len(d[c]) * (statistics.mean(d[c]) - gm) ** 2 for c in ks) / (k - 1)
    MSW = sum(sum((x - statistics.mean(d[c])) ** 2 for x in d[c]) for c in ks) / (N - k)
    sizes = [len(d[c]) for c in ks]
    m0 = (N - sum(s * s for s in sizes) / N) / (k - 1)
    if MSW <= 0: return None, m0
    return (MSB - MSW) / (MSB + (m0 - 1) * MSW), m0

def deff_from(d):
    icc, m0 = icc_anova(d)
    sizes = [len(v) for v in d.values()]
    mbar = statistics.mean(sizes)
    mA = mbar + statistics.pvariance(sizes) / mbar if mbar else mbar
    dm = 1 + (mbar - 1) * icc if icc is not None else None
    dk = 1 + (mA - 1) * icc if icc is not None else None
    d0 = 1 + (m0 - 1) * icc if icc is not None else None
    return icc, mbar, mA, m0, dm, dk, d0

print("cluster        k     mean_m   m_A(Kish)  ICC       deff(mean)  deff(Kish)")
for nm, kf in KEYS.items():
    icc, mbar, mA, m0, dm, dk, d0 = deff_from(clusters(Q, kf))
    print("%-13s %5d %9.2f %10.2f  %8s  %9s  %9s" % (
        nm, len(clusters(Q, kf)), mbar, mA,
        ("%.4f" % icc) if icc is not None else "n/a",
        ("%.2f" % dm) if dm else "n/a", ("%.2f" % dk) if dk else "n/a"))

# ---------- 3. block bootstrap SE ----------
def block_boot(Q, keyf, iters=4000):
    d = collections.defaultdict(list)
    for q in Q: d[keyf(q)].append(q["over"])
    keys = list(d); K = len(keys); rates = []
    for _ in range(iters):
        s = 0; n = 0
        for _ in range(K):
            v = d[keys[random.randrange(K)]]
            s += sum(v); n += len(v)
        if n: rates.append(s / n)
    rates.sort()
    return statistics.pstdev(rates), rates[int(.025 * len(rates))], rates[int(.975 * len(rates))]

p = statistics.mean(q["over"] for q in Q); n = len(Q)
se_iid = math.sqrt(p * (1 - p) / n)
print("\nbase over rate %.4f   naive iid SE %.5f   (n=%d)" % (p, se_iid, n))
print("block          bootSE    95% CI                deff(SE^2 ratio)  SE inflation")
BOOT = {}
for nm, kf in KEYS.items():
    se, lo, hi = block_boot(Q, kf)
    BOOT[nm] = (se, lo, hi)
    print("%-13s %.5f  [%.4f, %.4f]       %6.2f        %5.2fx" % (
        nm, se, lo, hi, (se / se_iid) ** 2, se / se_iid))

# ---------- 4. sensitivity ----------
def deff_game(Qs):
    icc, mbar, mA, m0, dm, dk, d0 = deff_from(clusters(Qs, KEYS["game"]))
    return icc, dm
base_icc, base_deff = deff_game(Q)
print("\nfull sample: ICC(game)=%.4f  deff=%.2f" % (base_icc, base_deff))

d = clusters(Q, KEYS["game"])
contrib = sorted(d, key=lambda c: -len(d[c]) * (statistics.mean(d[c]) - p) ** 2)
for j in (1, 2, 3, 5, 10):
    drop = set(contrib[:j])
    Qd = [q for q in Q if q["gt"] not in drop]
    i2, d2 = deff_game(Qd)
    print("  drop top-%2d contributing games (n=%d): ICC=%.4f deff=%.2f" % (j, len(Qd), i2, d2))
pc = collections.Counter(q["pl"] for q in Q)
for j in (1, 2, 5):
    drop = set(x for x, _ in pc.most_common(j))
    Qd = [q for q in Q if q["pl"] not in drop]
    i2, d2 = deff_game(Qd)
    print("  drop top-%2d players by volume (n=%d): ICC=%.4f deff=%.2f" % (j, len(Qd), i2, d2))

gk = list(d)
jk = []
for c in gk:
    Qd = [q for q in Q if q["gt"] != c]
    i2, _ = deff_game(Qd)
    if i2 is not None: jk.append(i2)
G = len(jk); mj = statistics.mean(jk)
se_jk = math.sqrt((G - 1) / G * sum((x - mj) ** 2 for x in jk))
mbar = statistics.mean(len(v) for v in d.values())
print("\njackknife-over-games: ICC=%.4f +/- %.4f  => ICC 95%% CI [%.4f, %.4f]" % (
    base_icc, se_jk, base_icc - 1.96 * se_jk, base_icc + 1.96 * se_jk))
print("   => deff 95%% CI [%.2f, %.2f]" % (
    1 + (mbar - 1) * (base_icc - 1.96 * se_jk), 1 + (mbar - 1) * (base_icc + 1.96 * se_jk)))

bi = []
for _ in range(2000):
    dd = {}
    for idx in range(len(gk)):
        c = gk[random.randrange(len(gk))]
        dd[(c, idx)] = d[c]
    i2, _ = icc_anova(dd)
    if i2 is not None: bi.append(i2)
bi.sort()
print("   game-block bootstrap of ICC: median %.4f 95%% CI [%.4f, %.4f]" % (
    bi[len(bi) // 2], bi[int(.025 * len(bi))], bi[int(.975 * len(bi))]))
bd = sorted(1 + (mbar - 1) * x for x in bi)
print("   game-block bootstrap of deff: median %.2f 95%% CI [%.2f, %.2f]" % (
    bd[len(bd) // 2], bd[int(.025 * len(bd))], bd[int(.975 * len(bd))]))

# ---------- 5. MDE ----------
se_g = BOOT["game"][0]
print("\nMDE with the game-block SE (%.5f):" % se_g)
print("   power 80%% two-sided: %.2f pp in win rate" % (2.80 * se_g * 100))
print("   a +3.5pp lift over breakeven is %.2f game-block SEs" % (3.5 / (se_g * 100)))
print("   claim's deff 2.91 implies SE %.5f ; measured game-block SE %.5f" % (
    se_iid * math.sqrt(2.91), se_g))

gsz = sorted((len(v) for v in d.values()), reverse=True)
tot = sum(gsz)
print("\ngames=%d  top-5 games hold %.1f%% of quotes; top-20 hold %.1f%%" % (
    len(d), sum(gsz[:5]) / tot * 100, sum(gsz[:20]) / tot * 100))
print("  cluster sizes: min %d med %d max %d  CV=%.2f" % (
    min(gsz), gsz[len(gsz) // 2], max(gsz), statistics.pstdev(gsz) / statistics.mean(gsz)))

# ---------- 6. how many independent games actually carry it ----------
print("\nquotes per game distribution deciles:")
print("  " + " ".join("%d" % gsz[int(q * (len(gsz) - 1))] for q in [i / 10 for i in range(11)]))
