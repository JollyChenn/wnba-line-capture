# TRACK 4 - the four claims put through walk-forward, permutation, robustness, execution, bankroll.
import platform; platform._wmi = None
import os, sys, json, math, random, statistics, collections
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
from t4_lib import base, boot_ci_by_game, drawdown, longest_losing
R = base()
SIGS = ("flip", "hotover", "overshoot"); BM = ("pra", "pr", "pts")
rng = np.random.default_rng(20260826)
LOG = []
def P(s=""):
    print(s); LOG.append(s)

# ---------------------------------------------------------------- helpers
def mkbets(rows, side="over", pricekey="over", linekey="line"):
    out = []
    for r in rows:
        ln = r[linekey]
        if r["actual"] == ln: w = None
        elif side == "over": w = r["actual"] > ln
        else: w = r["actual"] < ln
        pk = pricekey if side == "over" else pricekey.replace("over", "under").replace("o6", "u6")
        pr = r[pk]
        if pr is None: continue
        out.append(dict(g=r["gt"], date=r["date"], pl=r["pl"], tm=r["tm"], mk=r["mk"],
                        price=pr, won=w, row=r))
    return out

def summ(bets):
    if not bets: return dict(n=0, roi=0.0, w=0, wr=0.0, g=0, u=0.0)
    tot = sum(0.0 if b["won"] is None else ((b["price"]-1) if b["won"] else -1.0) for b in bets)
    dec = [b for b in bets if b["won"] is not None]
    w = sum(1 for b in dec if b["won"])
    return dict(n=len(bets), roi=tot/len(bets), w=w, wr=(w/len(dec) if dec else 0),
                g=len(set(b["g"] for b in bets)), u=tot)

def ci(bets, seed=1):
    return boot_ci_by_game([(b["g"], b["price"], b["won"]) for b in bets], iters=4000, seed=seed)

def perm_p_player(bets, iters=4000, seed=7):
    """null: shuffle outcomes within player (preserves each player's own over-rate)"""
    if not bets: return 1.0
    rr = random.Random(seed)
    real = summ(bets)["roi"]
    byp = collections.defaultdict(list)
    for i, b in enumerate(bets): byp[b["pl"]].append(i)
    won = [b["won"] for b in bets]; pri = [b["price"] for b in bets]
    beat = 0
    for _ in range(iters):
        nw = list(won)
        for idx in byp.values():
            v = [won[i] for i in idx]; rr.shuffle(v)
            for i, x in zip(idx, v): nw[i] = x
        tot = sum(0.0 if x is None else ((p-1) if x else -1.0) for p, x in zip(pri, nw))
        if tot/len(bets) >= real: beat += 1
    return (beat+1)/(iters+1)

def onepos(rows):
    best = {}
    for r in rows:
        k = (r["pl"], r["date"])
        if k not in best or (r["mk"], r["gt"]) < (best[k]["mk"], best[k]["gt"]): best[k] = r
    return sorted(best.values(), key=lambda r: (r["gt"], r["pl"]))

def folds_by_game(bets, k=3):
    gs = sorted(set(b["g"] for b in bets))
    size = len(gs)/k
    out = []
    for i in range(k):
        sel = set(gs[int(i*size):int((i+1)*size)])
        out.append([b for b in bets if b["g"] in sel])
    return out

def execstress(bets, label):
    base_ = summ(bets)
    rows = []
    for c in (0.0, 0.01, 0.02, 0.03):
        bb = [dict(b, price=b["price"]-c) for b in bets]
        rows.append((("slip %.0fc" % (100*c)), summ(bb)))
    czero = (base_["roi"]/base_["wr"]) if base_["wr"] > 0 else 0.0
    miss = []
    for m in (0.10, 0.25):
        acc = []
        rr = random.Random(99)
        for _ in range(2000):
            kept = [b for b in bets if rr.random() > m]
            if kept: acc.append(summ(kept)["roi"])
        miss.append((m, statistics.mean(acc), statistics.pstdev(acc)))
    return rows, czero, miss

def bankroll(bets, wr_oos, bank=100.0):
    """flat 1u plus fractional Kelly at the OOS win rate."""
    seq = [0.0 if b["won"] is None else ((b["price"]-1) if b["won"] else -1.0) for b in bets]
    res = {}
    res["flat"] = dict(mdd=drawdown(seq), streak=longest_losing(seq), final=sum(seq))
    o = statistics.mean(b["price"] for b in bets)
    bb = o - 1
    fk = (wr_oos*bb - (1-wr_oos))/bb if bb > 0 else 0.0
    for frac, nm in ((0.25, "kelly1/4"), (0.125, "kelly1/8")):
        f = max(0.0, fk*frac)
        eq = bank; peak = bank; mdd = 0.0
        for b in bets:
            st = eq*f
            if b["won"] is None: pass
            elif b["won"]: eq += st*(b["price"]-1)
            else: eq -= st
            peak = max(peak, eq); mdd = max(mdd, (peak-eq)/peak)
        res[nm] = dict(f=f, mdd_pct=100*mdd, final=eq)
    # risk of ruin at 100u, flat 1u, by resampling the bet order (game-clustered)
    byg = collections.defaultdict(list)
    for b in bets: byg[b["g"]].append(b)
    keys = list(byg)
    rr = random.Random(5)
    ruin50 = ruin100 = 0; T = 5000
    for _ in range(T):
        eq = bank; peak = bank; worst = 0.0
        for _ in range(len(keys)):
            for b in byg[keys[rr.randrange(len(keys))]]:
                eq += 0.0 if b["won"] is None else ((b["price"]-1) if b["won"] else -1.0)
                peak = max(peak, eq); worst = max(worst, peak-eq)
        if worst >= 50: ruin50 += 1
        if eq <= 0: ruin100 += 1
    res["ror"] = dict(dd50=ruin50/T, bust=ruin100/T, kelly_f=fk)
    return res

PVALS = []   # (name, p) collected for BH

# ================================================================ C1
P("="*100)
P("C1  GATE 3 / MODEL S STALENESS  --  book has not raised her line >= 0.5 since her previous game")
P("="*100)
cand = [r for r in R if any(s in SIGS for s in r["srcs"]) and r["mk"] in BM]
ms_rows = onepos([r for r in cand if r["prev"] is not None and r["line"] - r["prev"] < 0.5])
rj_rows = onepos([r for r in cand if r["prev"] is not None and r["line"] - r["prev"] >= 0.5])
MS = mkbets(ms_rows); RJ = mkbets(rj_rows)
s = summ(MS); lo, hi = ci(MS)
p1 = perm_p_player(MS)
P("  entry = last two-sided board quote at or before tip-1h, over side, one position per player-slate")
P("  MODEL S      n=%d  games=%d  W-L %d-%d (%.1f%%)  ROI %+.1f%%  95%%CI[%+.1f%%, %+.1f%%]  perm p=%.4f"
  % (s["n"], s["g"], s["w"], s["n"]-s["w"], 100*s["wr"], 100*s["roi"], 100*lo, 100*hi, p1))
sr = summ(RJ)
P("  REJECT group n=%d  ROI %+.1f%%   (the contrast the claim rests on: %+.1f pp)"
  % (sr["n"], 100*sr["roi"], 100*(s["roi"]-sr["roi"])))
P("  breakeven win rate at mean odds %.3f = %.1f%%" % (
    statistics.mean(b["price"] for b in MS), 100/statistics.mean(b["price"] for b in MS)))
PVALS.append(("C1 Model S staleness gate (over ROI, player-block perm)", p1))
# contrast test: is starred - raised bigger than chance?
allc = mkbets(onepos(cand))
def contrast_p(iters=4000, seed=13):
    rr = random.Random(seed)
    rows = [r for r in cand if r["prev"] is not None]
    rows = onepos(rows)
    star = [r["line"]-r["prev"] < 0.5 for r in rows]
    bts = mkbets(rows)
    def st(flags):
        a = [b for b, fl in zip(bts, flags) if fl]; b_ = [b for b, fl in zip(bts, flags) if not fl]
        if not a or not b_: return -9
        return summ(a)["roi"] - summ(b_)["roi"]
    real = st(star)
    byp = collections.defaultdict(list)
    for i, r in enumerate(rows): byp[r["pl"]].append(i)
    beat = 0
    for _ in range(iters):
        nf = list(star)
        for idx in byp.values():
            v = [star[i] for i in idx]; rr.shuffle(v)
            for i, x in zip(idx, v): nf[i] = x
        if st(nf) >= real: beat += 1
    return real, (beat+1)/(iters+1)
cr, cp = contrast_p()
P("  starred-minus-raised contrast %+.1f pp   player-block perm p=%.4f" % (100*cr, cp))
PVALS.append(("C1 starred-vs-raised contrast", cp))

P("")
P("  (a) CHRONOLOGICAL WALK-FORWARD, split by GAME")
for i, fb in enumerate(folds_by_game(MS, 3), 1):
    fs = summ(fb)
    d = sorted(set(b["date"] for b in fb))
    P("      fold %d  %s..%s  n=%-4d games=%-3d ROI %+7.1f%%  wr %.1f%%" % (
        i, d[0], d[-1], fs["n"], fs["g"], 100*fs["roi"], 100*fs["wr"]))
P("      per-month:")
for m in sorted(set(b["date"][:6] for b in MS)):
    fs = summ([b for b in MS if b["date"][:6] == m])
    P("        %s  n=%-4d ROI %+7.1f%%  wr %.1f%%" % (m, fs["n"], 100*fs["roi"], 100*fs["wr"]))
P("      per half-month:")
for m in sorted(set(b["date"][:6]+("A" if b["date"][6:8] <= "15" else "B") for b in MS)):
    fs = summ([b for b in MS if b["date"][:6]+("A" if b["date"][6:8] <= "15" else "B") == m])
    lo2, hi2 = ci([b for b in MS if b["date"][:6]+("A" if b["date"][6:8] <= "15" else "B") == m], seed=3)
    P("        %s n=%-4d ROI %+7.1f%%  CI[%+.0f%%,%+.0f%%]" % (m, fs["n"], 100*fs["roi"], 100*lo2, 100*hi2))

P("")
P("  (c) ROBUSTNESS")
P("      threshold perturbation on the gate (line - prev_line <):")
for g in (-0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 99):
    rw = onepos([r for r in cand if r["prev"] is not None and r["line"]-r["prev"] < g])
    fs = summ(mkbets(rw))
    P("        mv < %-5s n=%-4d ROI %+7.1f%%" % (g, fs["n"], 100*fs["roi"]))
P("      leave-one-team-out (team of the bet player):")
lo_t = []
for t in sorted(set(b["tm"] for b in MS)):
    fs = summ([b for b in MS if b["tm"] != t]); lo_t.append((t, fs["roi"], fs["n"]))
lo_t.sort(key=lambda x: x[1])
P("        worst 3: " + "  ".join("%s %+.1f%%" % (t, 100*v) for t, v, n in lo_t[:3]))
P("        best  3: " + "  ".join("%s %+.1f%%" % (t, 100*v) for t, v, n in lo_t[-3:]))
P("        spread of LOTO ROI %.1f pp  (drop any one team and ROI moves inside this band)"
  % (100*(lo_t[-1][1]-lo_t[0][1])))
lo_p = []
for pl in sorted(set(b["pl"] for b in MS)):
    fs = summ([b for b in MS if b["pl"] != pl]); lo_p.append((pl, fs["roi"], fs["n"]))
lo_p.sort(key=lambda x: x[1])
P("      leave-one-player-out (%d players):" % len(lo_p))
P("        worst 3: " + "  ".join("%s %+.1f%%" % (t.split()[-1][:9], 100*v) for t, v, n in lo_p[:3]))
P("        best  3: " + "  ".join("%s %+.1f%%" % (t.split()[-1][:9], 100*v) for t, v, n in lo_p[-3:]))
P("        removing the single best player takes ROI to %+.1f%%; %d/%d single-player deletions leave it positive"
  % (100*lo_p[0][1], sum(1 for x in lo_p if x[1] > 0), len(lo_p)))
# concentration
cnt = collections.Counter(b["pl"] for b in MS)
P("        top-5 players carry %d/%d bets (%.0f%%)" % (
    sum(c for _, c in cnt.most_common(5)), len(MS), 100*sum(c for _, c in cnt.most_common(5))/len(MS)))

P("")
P("  (d) EXECUTION STRESS")
rows_, czero, miss = execstress(MS, "C1")
for nm, fs in rows_:
    P("        %-9s n=%-4d ROI %+7.1f%%" % (nm, fs["n"], 100*fs["roi"]))
P("        slippage that takes C1 to zero: %.1f cents of decimal odds" % (100*czero))
for m, mu, sdv in miss:
    P("        %d%% missed entries (random): mean ROI %+.1f%%  sd %.1f pp" % (100*m, 100*mu, 100*sdv))
# open vs late entry - the measured execution cost in this repo
ms_open = onepos([r for r in cand if r["prev"] is not None and r["oline"] - r["prev"] < 0.5])
so = summ(mkbets(ms_open, pricekey="oover", linekey="oline"))
ms_6 = onepos([r for r in cand if r["prev"] is not None and r["l6"] is not None and r["l6"] - r["prev"] < 0.5])
s6 = summ(mkbets(ms_6, pricekey="o6", linekey="l6"))
P("        SAME RULE PRICED AT DIFFERENT INSTANTS (all gated and graded at that same instant):")
P("          open quote   n=%-4d ROI %+7.1f%%" % (so["n"], 100*so["roi"]))
P("          tip-6h quote n=%-4d ROI %+7.1f%%" % (s6["n"], 100*s6["roi"]))
P("          tip-1h quote n=%-4d ROI %+7.1f%%" % (s["n"], 100*s["roi"]))

P("")
P("  (e) BANKROLL")
f3 = folds_by_game(MS, 3)
wr_oos = summ(f3[1]+f3[2])["wr"]
bk = bankroll(MS, wr_oos)
P("        flat 1u: final %+.2fu  max drawdown %.1fu  longest losing streak %d" % (
    bk["flat"]["final"], bk["flat"]["mdd"], bk["flat"]["streak"]))
P("        full Kelly f=%.3f at OOS win rate %.1f%%" % (bk["ror"]["kelly_f"], 100*wr_oos))
for nm in ("kelly1/4", "kelly1/8"):
    P("        %-9s stake %.1f%% of bank  final %.1fu from 100u  max DD %.1f%%" % (
        nm, 100*bk[nm]["f"], bk[nm]["final"], bk[nm]["mdd_pct"]))
P("        risk of a 50u drawdown on a 100u bank, flat 1u, game-clustered resample: %.1f%%" % (100*bk["ror"]["dd50"]))
P("        risk of ruin (bank <= 0): %.1f%%" % (100*bk["ror"]["bust"]))

json.dump({"pvals": PVALS}, open(os.path.join(D, "outputs", "t4_c1_p.json"), "w"), indent=1)
open(os.path.join(D, "outputs", "t4_c1.txt"), "w", encoding="utf-8").write("\n".join(LOG))
