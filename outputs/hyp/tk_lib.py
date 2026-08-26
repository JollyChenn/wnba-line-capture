"""Shared loader for the season-timing / market-recency track.
Reads ONLY outputs/gm/gm_dataset.csv (+ elo_model box for the turnover proxy).
Nothing here writes to any existing file.
"""
import csv, os, math, random, statistics, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GM = os.path.join(ROOT, "outputs", "gm", "gm_dataset.csv")

def _f(x):
    try:
        return float(x)
    except Exception:
        return None

def load_games():
    R = list(csv.DictReader(open(GM, encoding="utf-8")))
    out = []
    for r in R:
        g = dict(
            gid=r["game_id"], date=r["date"], season=int(r["season"]),
            home=r["home"], away=r["away"],
            hs=_f(r["home_score"]), as_=_f(r["away_score"]),
            ml_h=_f(r["ml_h"]), ml_a=_f(r["ml_a"]),
            spread=_f(r["spread"]), sp_h=_f(r["sp_h"]), sp_a=_f(r["sp_a"]),
            total=_f(r["total"]), ou_o=_f(r["ou_o"]), ou_u=_f(r["ou_u"]),
        )
        if g["hs"] is None or g["as_"] is None:
            continue
        g["margin"] = g["hs"] - g["as_"]          # home margin
        g["gtot"] = g["hs"] + g["as_"]
        out.append(g)
    out.sort(key=lambda g: (g["date"], g["gid"]))
    return out

def annotate(games):
    """Adds: tgi_h/tgi_a (team game index within season, 1-based, PRE-game count+1),
    lgi (league game index within season), wk (league week 1-based from season start),
    season_start date."""
    starts = {}
    for g in games:
        s = g["season"]
        if s not in starts or g["date"] < starts[s]:
            starts[s] = g["date"]
    cnt = collections.Counter()
    lcnt = collections.Counter()
    import datetime
    for g in games:
        s = g["season"]
        g["tgi_h"] = cnt[(s, g["home"])] + 1
        g["tgi_a"] = cnt[(s, g["away"])] + 1
        cnt[(s, g["home"])] += 1
        cnt[(s, g["away"])] += 1
        lcnt[s] += 1
        g["lgi"] = lcnt[s]
        d0 = datetime.date(int(starts[s][:4]), int(starts[s][4:6]), int(starts[s][6:]))
        d1 = datetime.date(int(g["date"][:4]), int(g["date"][4:6]), int(g["date"][6:]))
        g["days"] = (d1 - d0).days
        g["wk"] = g["days"] // 7 + 1
    return games

def devig2(o1, o2):
    if not o1 or not o2:
        return None
    a, b = 1.0 / o1, 1.0 / o2
    return a / (a + b)

def roi_units(picks):
    """picks = list of (win01, dec_odds). push -> win01 == 0.5 handled as stake back."""
    tot = 0.0
    for w, o in picks:
        if w == 0.5:
            continue
        tot += (o - 1.0) if w == 1 else -1.0
    n = sum(1 for w, o in picks if w != 0.5)
    return (tot / n if n else 0.0), tot, n

def block_boot(units_by_block, iters=4000, seed=20260826):
    """units_by_block: list of lists of per-bet net units, grouped by independent block."""
    rnd = random.Random(seed)
    blocks = [b for b in units_by_block if b]
    if not blocks:
        return (0, 0)
    K = len(blocks)
    rois = []
    for _ in range(iters):
        s = 0.0; n = 0
        for _ in range(K):
            b = blocks[rnd.randrange(K)]
            s += sum(b); n += len(b)
        if n:
            rois.append(s / n)
    rois.sort()
    return (rois[int(0.025 * len(rois))], rois[int(0.975 * len(rois))])
