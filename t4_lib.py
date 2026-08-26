# shared helpers for the Track-4 audit
import os, sys, json, math, random, statistics, collections, datetime
D = os.path.dirname(os.path.abspath(__file__))

def base():
    return json.load(open(os.path.join(D, "outputs", "t4_base.json")))

def pnl(b, price, won):
    """b = decimal odds, won bool/None(push)"""
    if won is None: return 0.0
    return (price - 1.0) if won else -1.0

def over_won(r, linekey="line"):
    if r["actual"] == r[linekey]: return None
    return r["actual"] > r[linekey]

def roi_of(bets):
    """bets: list of (price, won) ; won None = push (staked, returned)"""
    if not bets: return 0.0, 0, 0, 0.0
    tot = sum(pnl(None, p, w) for p, w in bets)
    n = len(bets)
    wins = sum(1 for p, w in bets if w is True)
    dec = sum(1 for p, w in bets if w is not None)
    return tot/n, n, wins, (wins/dec if dec else 0.0)

def boot_ci_by_game(bets_g, iters=4000, seed=1):
    """bets_g: list of (game_id, price, won). Cluster bootstrap on GAME."""
    rnd = random.Random(seed)
    byg = collections.defaultdict(list)
    for g, p, w in bets_g: byg[g].append((p, w))
    keys = list(byg)
    if len(keys) < 3: return (float("nan"), float("nan"))
    out = []
    for _ in range(iters):
        tot = 0.0; n = 0
        for _ in range(len(keys)):
            for p, w in byg[keys[rnd.randrange(len(keys))]]:
                tot += pnl(None, p, w); n += 1
        if n: out.append(tot/n)
    out.sort()
    return (out[int(0.025*len(out))], out[int(0.975*len(out))])

def block_perm_p(rows, blockkey, statfn, iters=2000, seed=7):
    """Permute the OUTCOME within blocks (shuffle which row in a block got which result).
    rows: list of dicts each with 'won' and whatever statfn needs.
    statfn(rows) -> scalar. p = P(perm >= real)."""
    rnd = random.Random(seed)
    real = statfn(rows)
    byb = collections.defaultdict(list)
    for i, r in enumerate(rows): byb[r[blockkey]].append(i)
    won = [r["won"] for r in rows]
    beat = 0; sims = []
    for _ in range(iters):
        newwon = list(won)
        for b, idx in byb.items():
            vals = [won[i] for i in idx]
            rnd.shuffle(vals)
            for i, v in zip(idx, vals): newwon[i] = v
        rr = [dict(r, won=w) for r, w in zip(rows, newwon)]
        s = statfn(rr)
        sims.append(s)
        if s >= real: beat += 1
    sims.sort()
    return real, (beat+1)/(iters+1), sims

def label_perm_p(rows, blockkey, labelkey, statfn, iters=2000, seed=11):
    """Permute the LABEL across blocks: every row in a block carries the block's label,
    labels are reassigned among blocks. Correct null for block-level attributes
    (game total on a game, volatility on a player)."""
    rnd = random.Random(seed)
    real = statfn(rows)
    byb = collections.defaultdict(list)
    for i, r in enumerate(rows): byb[r[blockkey]].append(i)
    blocks = list(byb)
    blab = {b: rows[byb[b][0]][labelkey] for b in blocks}
    beat = 0; sims = []
    for _ in range(iters):
        vals = [blab[b] for b in blocks]
        rnd.shuffle(vals)
        m = dict(zip(blocks, vals))
        rr = [dict(r, **{labelkey: m[r[blockkey]]}) for r in rows]
        s = statfn(rr)
        sims.append(s)
        if s >= real: beat += 1
    sims.sort()
    return real, (beat+1)/(iters+1), sims

def bh(pvals, q=0.10):
    """Benjamini-Hochberg. pvals: list of (name, p). returns list of (name,p,crit,pass)"""
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i][1])
    m = len(pvals)
    out = [None]*m
    kmax = 0
    for rank, i in enumerate(idx, 1):
        crit = q*rank/m
        if pvals[i][1] <= crit: kmax = rank
    for rank, i in enumerate(idx, 1):
        out[i] = (pvals[i][0], pvals[i][1], q*rank/m, rank <= kmax)
    return out

def drawdown(seq):
    eq = 0.0; peak = 0.0; mdd = 0.0
    for x in seq:
        eq += x
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    return mdd

def longest_losing(seq):
    best = cur = 0
    for x in seq:
        if x < 0: cur += 1; best = max(best, cur)
        else: cur = 0
    return best
