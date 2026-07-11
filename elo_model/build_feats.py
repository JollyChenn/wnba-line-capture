# build_feats.py - v3 feature matrix, one row per game, EVERYTHING computed walk-forward (pregame).
# Emits feats_v3.csv: game_id,season,margin,total + home-minus-away features (fN...).
import csv, os, statistics, math, sys
from collections import defaultdict, deque
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except Exception: return 0.0
games = sorted(csv.DictReader(open(os.path.join(D, "games_full.csv"), encoding="utf-8")),
               key=lambda g: (g["date"], g["game_id"]))
box = defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "box_full.csv"), encoding="utf-8")):
    box[r["game_id"]].append(r)
zf = {r["game_id"]: f(r["matchup_diff"]) for r in csv.DictReader(open(os.path.join(D, "zone_feats.csv"), encoding="utf-8"))}

LGTS, C_M, C_SD, PPP_M, PPP_SD = 0.542, 4.80, 6.03, 101.9, 13.5
def comp36(r):
    m = f(r["min"])
    if m < 6: return None
    return ((f(r["pts"]) - LGTS * 2 * (f(r["fga"]) + 0.44 * f(r["fta"]))) + 0.7 * f(r["ast"]) - f(r["to"])
            + 0.7 * f(r["oreb"]) + 0.3 * f(r["dreb"]) + 0.15 * (f(r["fga"]) + 0.44 * f(r["fta"]))) * 36 / m

oR, dR, gp = defaultdict(float), defaultdict(float), defaultdict(int)
recmin = defaultdict(lambda: deque(maxlen=10))
roster = defaultdict(lambda: deque(maxlen=3))
telo = defaultdict(lambda: 1500.0)
lastdate = {}                                            # team -> date of last game
form = defaultdict(lambda: deque(maxlen=5))              # team -> recent margins
tstat = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10)))   # team -> stat -> recent per-game
def lr(g): return 0.28 * 15 / (15 + g) + 0.04
CLIP = 2.5
season_cur = None
out = [("game_id","season","margin","total","pstr","pnews","telo","zone","rest","b2b","form5",
        "pace_d","pace_s","tov","oreb","ftr","p3ar","p3pct","stk","bench","drop")]

def proj_minutes(team):
    seen = {}
    for s in roster[team]:
        for a in s: seen[a] = 1
    pm = {}
    for a in seen:
        ms = list(recmin[a])
        if not ms: continue
        w = [0.87 ** (len(ms) - 1 - i) for i in range(len(ms))]
        pm[a] = sum(m_ * w_ for m_, w_ in zip(ms, w)) / sum(w)
    tot = sum(pm.values())
    return None if tot < 100 else {a: m * 200 / tot for a, m in pm.items()}
def dec_avg(dq):
    L = list(dq)
    if not L: return None
    w = [0.9 ** (len(L) - 1 - i) for i in range(len(L))]
    return sum(a * b for a, b in zip(L, w)) / sum(w)

def dstr(d1, d2):  # days between YYYYMMDD
    from datetime import date
    def p(s): return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return (p(d2) - p(d1)).days

for g in games:
    if g["season"] != season_cur:
        season_cur = g["season"]
        for k in list(oR): oR[k] *= 0.7
        for k in list(dR): dR[k] *= 0.7
        for k in list(telo): telo[k] = 1500 + 0.7 * (telo[k] - 1500)
        lastdate.clear()
    rows = box.get(g["game_id"], []); T = defaultdict(list)
    for r in rows: T[r["team"]].append(r)
    if len(T) != 2 or not g["home_score"]: continue
    home, away = g["home"], g["away"]
    if home not in T or away not in T: continue
    margin = f(g["home_score"]) - f(g["away_score"]); total = f(g["home_score"]) + f(g["away_score"])
    # ---------- PREGAME features ----------
    def side(team):
        pm = proj_minutes(team)
        if not pm: return None
        played = {r["aid"] for r in T[team] if f(r["min"]) >= 6}
        pma = {a: m for a, m in pm.items() if a in played} or pm     # news-adjusted (actual actives)
        st = sum((oR[a] + dR[a]) * m for a, m in pm.items()) / 200
        sn = sum((oR[a] + dR[a]) * m for a, m in pma.items()) / (sum(pma.values()) or 1)
        rank = sorted(pma, key=lambda a: -pma[a])
        top5, bench5 = rank[:5], rank[5:10]
        bench = statistics.mean([oR[a] + dR[a] for a in bench5]) if bench5 else 0
        drop = (statistics.mean([oR[a] + dR[a] for a in top5]) if top5 else 0) - bench
        ld = lastdate.get(team)
        rest = min(dstr(ld, g["date"]), 5) if ld else 3
        ts = tstat[team]
        return dict(st=st, sn=sn, bench=bench, drop=drop, rest=rest, b2b=1 if rest <= 1 else 0,
                    form=dec_avg(form[team]) or 0, pace=dec_avg(ts["poss"]) or 78,
                    tov=dec_avg(ts["tov"]) or .16, oreb=dec_avg(ts["oreb"]) or .28,
                    ftr=dec_avg(ts["ftr"]) or .25, p3ar=dec_avg(ts["p3ar"]) or .32,
                    p3=dec_avg(ts["p3"]) or .33, stk=dec_avg(ts["stk"]) or 12)
    H, A = side(home), side(away)
    if H and A and gp:
        out.append((g["game_id"], g["season"], margin, total,
                    round(H["st"]-A["st"],4), round(H["sn"]-A["sn"],4), round(telo[home]-telo[away],1),
                    round(zf.get(g["game_id"],0),3), H["rest"]-A["rest"], H["b2b"]-A["b2b"],
                    round(H["form"]-A["form"],2), round(H["pace"]-A["pace"],2), round(H["pace"]+A["pace"],2),
                    round(H["tov"]-A["tov"],4), round(H["oreb"]-A["oreb"],4), round(H["ftr"]-A["ftr"],4),
                    round(H["p3ar"]-A["p3ar"],4), round(H["p3"]-A["p3"],4), round(H["stk"]-A["stk"],2),
                    round(H["bench"]-A["bench"],4), round(H["drop"]-A["drop"],4)))
    # ---------- updates ----------
    ed = telo[home] + 80 - telo[away]
    eh = 1 / (1 + 10 ** (-ed / 400))
    mov = (abs(margin) + 3) ** 0.8 / (7.5 + 0.006 * abs(ed))
    telo[home] += 20*mov*((1 if margin>0 else 0)-eh); telo[away] -= 20*mov*((1 if margin>0 else 0)-eh)
    (tA, ra), (tB, rb) = T.items()
    def agg(rr, R):
        tm_ = sum(f(r["min"]) for r in rr) or 1
        return sum(R[r["aid"]] * f(r["min"]) for r in rr) / tm_
    dAgg = {tA: agg(ra, dR), tB: agg(rb, dR)}; oAgg = {tA: agg(ra, oR), tB: agg(rb, oR)}
    for tm, rr, opp in ((tA, ra, tB), (tB, rb, tA)):
        for r in rr:
            c = comp36(r)
            if c is None: continue
            aid = r["aid"]
            act = max(-CLIP, min(CLIP, (c - C_M) / C_SD))
            oR[aid] += lr(gp[aid]) * min(f(r["min"])/30, 1) * (act - (oR[aid] - dAgg[opp]))
        poss = sum(f(x["fga"])+0.44*f(x["fta"])+f(x["to"])-f(x["oreb"]) for x in rr)
        opprr = [x for x in rows if x["team"] == opp]
        oposs = sum(f(x["fga"])+0.44*f(x["fta"])+f(x["to"])-f(x["oreb"]) for x in opprr)
        opts = sum(f(x["pts"]) for x in opprr)
        if oposs > 40:
            dz = max(-CLIP, min(CLIP, ((PPP_M + oAgg[opp]*3 - dAgg[tm]*3) - 100*opts/oposs) / PPP_SD))
            for r in rr:
                m = f(r["min"])
                if m < 6: continue
                stz = ((f(r["stl"])+f(r["blk"]))*36/m - 1.5)/1.5
                dR[r["aid"]] += lr(gp[r["aid"]])*(m/200)*(dz-dR[r["aid"]]) + 0.01*max(-2,min(2,stz))
        for r in rr:
            if f(r["min"]) >= 6:
                gp[r["aid"]] += 1; recmin[r["aid"]].append(f(r["min"]))
        roster[tm].append({r["aid"] for r in rr if f(r["min"]) >= 6})
        # team stat history
        fga = sum(f(x["fga"]) for x in rr); fta = sum(f(x["fta"]) for x in rr)
        tov = sum(f(x["to"]) for x in rr); orb = sum(f(x["oreb"]) for x in rr)
        drbo = sum(f(x["dreb"]) for x in opprr)
        tp = sum(f(x["tpa"]) for x in rr); tpm = sum(f(x["tpm"]) for x in rr)
        stk = sum(f(x["stl"])+f(x["blk"]) for x in rr)
        ts = tstat[tm]
        if poss > 40:
            ts["poss"].append(poss); ts["tov"].append(tov/poss); ts["ftr"].append(fta/(fga or 1))
            ts["p3ar"].append(tp/(fga or 1)); ts["p3"].append((tpm/tp) if tp else 0.33)
            ts["oreb"].append(orb/((orb+drbo) or 1)); ts["stk"].append(stk)
        mgn = margin if tm == home else -margin
        form[tm].append(mgn); lastdate[tm] = g["date"]
w = csv.writer(open(os.path.join(D, "feats_v3.csv"), "w", newline=""))
w.writerows(out)
print("feature rows:", len(out) - 1)
