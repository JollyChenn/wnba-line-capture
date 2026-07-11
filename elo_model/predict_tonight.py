# predict_tonight.py - THE EDGE MACHINE (forward test). Nightly:
#   1. refresh history (collect_history is resume-safe -> pulls any new final games)
#   2. replay all games -> current player ratings + team states (walk-forward, seconds)
#   3. for TODAY's scheduled games: project minutes, drop ESPN-injury OUTs, compute v3/v4/v5 margin
#      + total + win prob, log alongside the CURRENT Pinnacle game lines -> elo_forward_log.csv
# Grading later compares model vs closing line vs result = the only proof that matters.
# stdlib only. Never fails the workflow (exit 0).
import csv, os, sys, json, math, statistics, datetime, urllib.request
from collections import defaultdict, deque
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0"}
def f(x):
    try: return float(x)
    except Exception: return 0.0
def getj(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20))
    except Exception: return {}

def main():
    games = sorted(csv.DictReader(open(os.path.join(D, "games_full.csv"), encoding="utf-8")),
                   key=lambda g: (g["date"], g["game_id"]))
    box = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(D, "box_full.csv"), encoding="utf-8")):
        box[r["game_id"]].append(r)
    LGTS, C_M, C_SD = 0.542, 4.80, 6.03
    def comp36(r):
        m = f(r["min"])
        if m < 6: return None
        return ((f(r["pts"]) - LGTS*2*(f(r["fga"])+0.44*f(r["fta"]))) + 0.7*f(r["ast"]) - f(r["to"])
                + 0.7*f(r["oreb"]) + 0.3*f(r["dreb"]) + 0.15*(f(r["fga"])+0.44*f(r["fta"]))) * 36/m
    oR, oRf, dR, gp = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(int)
    resid = defaultdict(lambda: deque(maxlen=4))
    recmin = defaultdict(lambda: deque(maxlen=10)); roster = defaultdict(lambda: deque(maxlen=3))
    telo = defaultdict(lambda: 1500.0)
    ts = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10)))
    name_of, team_of = {}, {}
    season = None
    def lr(g_): return 0.28*15/(15+g_)+0.04
    PPP_M, PPP_SD = 101.9, 13.5
    for g in games:
        if g["season"] != season:
            season = g["season"]
            for k in list(oR): oR[k] *= 0.7
            for k in list(oRf): oRf[k] *= 0.7
            for k in list(dR): dR[k] *= 0.7
            for k in list(telo): telo[k] = 1500 + 0.7*(telo[k]-1500)
        rows = box.get(g["game_id"], []); T = defaultdict(list)
        for r in rows: T[r["team"]].append(r)
        if len(T) != 2 or not g["home_score"]: continue
        margin = f(g["home_score"]) - f(g["away_score"])
        ed = telo[g["home"]] + 80 - telo[g["away"]]
        eh = 1/(1+10**(-ed/400)); mov = (abs(margin)+3)**0.8/(7.5+0.006*abs(ed))
        dl = 20*mov*((1 if margin > 0 else 0)-eh); telo[g["home"]] += dl; telo[g["away"]] -= dl
        (tA, ra), (tB, rb) = T.items()
        def agg(rr, R_):
            tm_ = sum(f(r["min"]) for r in rr) or 1
            return sum(R_[r["aid"]]*f(r["min"]) for r in rr)/tm_
        dAgg = {tA: agg(ra, dR), tB: agg(rb, dR)}; oAgg = {tA: agg(ra, oR), tB: agg(rb, oR)}
        for tm, rr, opp in ((tA, ra, tB), (tB, rb, tA)):
            opprr = [x for x in rows if x["team"] == opp]
            for r in rr:
                c = comp36(r)
                if c is None: continue
                aid = r["aid"]; name_of[aid] = r["player"]; team_of[aid] = tm
                act = max(-2.5, min(2.5, (c-C_M)/C_SD)); mf = min(f(r["min"])/30, 1)
                oR[aid] += lr(gp[aid])*mf*(act-(oR[aid]-dAgg[opp]))
                err = act - oRf[aid]; rs = resid[aid]; rs.append(err)
                boost = 1+min(1.5, abs(statistics.mean(rs))) if len(rs) >= 3 else 1
                oRf[aid] += lr(gp[aid])*boost*mf*err
            oposs = sum(f(x["fga"])+0.44*f(x["fta"])+f(x["to"])-f(x["oreb"]) for x in opprr)
            opts = sum(f(x["pts"]) for x in opprr)
            if oposs > 40:
                dz = max(-2.5, min(2.5, ((PPP_M+oAgg[opp]*3-dAgg[tm]*3)-100*opts/oposs)/PPP_SD))
                for r in rr:
                    m = f(r["min"])
                    if m < 6: continue
                    stz = ((f(r["stl"])+f(r["blk"]))*36/m-1.5)/1.5
                    dR[r["aid"]] += lr(gp[r["aid"]])*(m/200)*(dz-dR[r["aid"]])+0.01*max(-2, min(2, stz))
            for r in rr:
                if f(r["min"]) >= 6: gp[r["aid"]] += 1; recmin[r["aid"]].append(f(r["min"]))
            roster[tm].append({r["aid"] for r in rr if f(r["min"]) >= 6})
            poss = sum(f(x["fga"])+0.44*f(x["fta"])+f(x["to"])-f(x["oreb"]) for x in rr)
            fga = sum(f(x["fga"]) for x in rr); tp = sum(f(x["tpa"]) for x in rr)
            orb = sum(f(x["oreb"]) for x in rr); drbo = sum(f(x["dreb"]) for x in opprr)
            t_ = ts[tm]
            if poss > 40:
                t_["poss"].append(poss); t_["p3ar"].append(tp/(fga or 1))
                t_["oreb"].append(orb/((orb+drbo) or 1)); t_["pf"].append(sum(f(x["pf"]) for x in rr))
                t_["tov"].append(sum(f(x["to"]) for x in rr)/poss)
                tpm = sum(f(x["tpm"]) for x in rr); t_["p3"].append((tpm/tp) if tp else 0.33)
    def dav(dq, d=None):
        L = list(dq)
        if not L: return d
        w = [0.9**(len(L)-1-i) for i in range(len(L))]
        return sum(a*b for a, b in zip(L, w))/sum(w)
    # ---- today's slate + injury OUTs ----
    inj = set()
    for tm in getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries").get("injuries", []):
        for it in tm.get("injuries", []):
            if (it.get("status") or "").lower() in ("out", "doubtful"):
                a = (it.get("athlete") or {}).get("id")
                if a: inj.add(str(a))
    sb = getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # current pinnacle lines (from gamelines.csv, latest per game)
    glines = {}
    gl = os.path.join(os.path.dirname(D), "gamelines.csv")
    if os.path.exists(gl):
        for r in csv.DictReader(open(gl, encoding="utf-8")):
            glines[(r["teams"], r["type"], r.get("side", ""))] = (r["points"], r["prices"], r["captured_utc"])
    def proj(team, exclude):
        seen = {}
        for s in roster[team]:
            for a in s: seen[a] = 1
        pm = {}
        for a in seen:
            if a in exclude: continue
            ms = list(recmin[a])
            if not ms: continue
            w = [0.87**(len(ms)-1-i) for i in range(len(ms))]
            pm[a] = sum(x*y for x, y in zip(ms, w))/sum(w)
        t = sum(pm.values())
        return None if t < 100 else {a: m*200/t for a, m in pm.items()}
    # coefficients fit on ALL history (walk-forward features from feats_v5.csv)
    fr = list(csv.DictReader(open(os.path.join(D, "feats_v5.csv"), encoding="utf-8")))
    def ols(fs, tgt="margin"):
        X = [[f(r[k]) for k in fs]+[1] for r in fr]; y = [f(r[tgt]) for r in fr]; k = len(fs)+1
        XtX = [[sum(X[i][p]*X[i][q] for i in range(len(X)))+(1e-3 if p == q else 0) for q in range(k)] for p in range(k)]
        Xty = [sum(X[i][p]*y[i] for i in range(len(X))) for p in range(k)]
        M = [row[:]+[Xty[i]] for i, row in enumerate(XtX)]
        for c in range(k):
            pv = max(range(c, k), key=lambda r_: abs(M[r_][c])); M[c], M[pv] = M[pv], M[c]
            M[c] = [v/M[c][c] for v in M[c]]
            for r_ in range(k):
                if r_ != c and M[r_][c]: M[r_] = [x2-M[r_][c]*y2 for x2, y2 in zip(M[r_], M[c])]
        return [M[i][k] for i in range(k)]
    B3 = ols(["pnews", "telo", "oreb", "p3ar"])
    B5 = ols(["pnews", "p3ar", "oreb", "fluid", "drop", "pfr"])
    # totals in DEVIATION form: total = league-env(last 60 finals) + f(pace,tov,3p%) -> absorbs scoring drift
    lgtot = [f(g["home_score"]) + f(g["away_score"]) for g in games if g["home_score"]]
    LGENV = statistics.mean(lgtot[-60:])
    genv = {}
    run = []
    for g in games:
        if not g["home_score"]: continue
        genv[g["game_id"]] = statistics.mean(run[-60:]) if len(run) >= 25 else 162
        run.append(f(g["home_score"]) + f(g["away_score"]))
    for r in fr: r["tdev"] = f(r["total"]) - genv.get(r["game_id"], 162)
    BT = ols(["pace_s", "tov", "p3pct"], "tdev")
    outp = os.path.join(D, "elo_forward_log.csv")
    new = not os.path.exists(outp)
    fh = open(outp, "a", newline="", encoding="utf-8"); w = csv.writer(fh)
    if new: w.writerow(["logged_utc","date","home","away","tip","v3_margin","v5_margin","tot_pred",
                        "pin_spread","pin_total","pin_ml","outs"])
    nrows = 0
    ABBR = {}  # espn abbrev used throughout
    for ev in sb.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        if (((comp.get("status") or {}).get("type") or {}).get("state") or "") != "pre": continue
        cs = {c["homeAway"]: c for c in comp.get("competitors", [])}
        h = cs["home"]["team"]["abbreviation"]; a = cs["away"]["team"]["abbreviation"]
        hn = cs["home"]["team"]["displayName"]; an = cs["away"]["team"]["displayName"]
        def side(team):
            pm = proj(team, inj)
            if not pm: return None
            tot = sum(pm.values())
            t_ = ts[team]
            return dict(
                pnews=sum((oR[k]+dR[k])*v for k, v in pm.items())/tot,
                fluid=sum(oRf[k]*v for k, v in pm.items())/tot,
                drop=(statistics.mean([oR[k]+dR[k] for k in sorted(pm, key=lambda x: -pm[x])[:5]])
                      - (statistics.mean([oR[k]+dR[k] for k in sorted(pm, key=lambda x: -pm[x])[5:10]])
                         if len(pm) > 5 else 0)),
                pf=dav(t_["pf"], 17), p3ar=dav(t_["p3ar"], .32), oreb=dav(t_["oreb"], .28),
                pace=dav(t_["poss"], 78), tov=dav(t_["tov"], .16), p3=dav(t_["p3"], .33))
        H, A = side(h), side(a)
        if not H or not A: continue
        teld = telo[h]-telo[a]
        x3 = [H["pnews"]-A["pnews"], teld, H["oreb"]-A["oreb"], H["p3ar"]-A["p3ar"], 1]
        x5 = [H["pnews"]-A["pnews"], H["p3ar"]-A["p3ar"], H["oreb"]-A["oreb"],
              H["fluid"]-A["fluid"], H["drop"]-A["drop"], H["pf"]-A["pf"], 1]
        xt = [H["pace"]+A["pace"], H["tov"]-A["tov"], H["p3"]-A["p3"], 1]
        m3 = sum(b*x for b, x in zip(B3, x3)); m5 = sum(b*x for b, x in zip(B5, x5))
        tp = LGENV + sum(b*x for b, x in zip(BT, xt))
        key = an+"|"+hn  # pinnacle lists away|home? check both orders
        def pin(typ, side_=""):
            for k_ in (an+"|"+hn, hn+"|"+an):
                v = glines.get((k_, typ, side_))
                if v: return f"{v[0]}@{v[1]}"
            return ""
        outs = [name_of.get(k, k) for k in inj if team_of.get(k) in (h, a)]
        w.writerow([stamp, ev.get("date", "")[:10], h, a, ev.get("date", "")[11:16],
                    round(m3, 2), round(m5, 2), round(tp, 1),
                    pin("spread"), pin("total"), pin("moneyline"), ";".join(outs[:6])])
        nrows += 1
        print(f"{a}@{h}: v3 {m3:+.1f} v5 {m5:+.1f} total {tp:.0f} | pin sp={pin('spread')} tot={pin('total')} | outs={len(outs)}")
    fh.close()
    print(f"logged {nrows} game(s)")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc()
    sys.exit(0)
