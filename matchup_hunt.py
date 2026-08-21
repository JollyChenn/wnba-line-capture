# matchup_hunt.py - the matchup layer: does WHO SHE PLAYS move her props, beyond her own median?
# ---------------------------------------------------------------------------------------------
# Sources never combined before:
#   * box scores       -> each team's CONCESSION per stat: what it allows opponents, vs league
#                         average, computed strictly from games BEFORE the one predicted (the
#                         "heat map" - a 13-team x 3-stat matrix of defensive softness)
#   * elo_model/ratings.csv -> per-player defensive ratings (dR), minutes-weighted to a team
#                         defensive quality number - an independent instrument for the same thing
#
# The test: her expected production tonight = her median + (opponent concession scaled by her
# share of team output). If the book prices only HER (median-ish) and ignores the OPPONENT, then
# the matchup increment should predict over/under results. If the book already prices matchups,
# it predicts nothing. Trend test at the GAME level - the matchup is a game-level label.
#
# Danger declared up front: concession is partly PACE (a fast team concedes more of everything).
# The pace finding says realised pace moves overs 19 points but is NOT forecastable from props.
# If concession works, we must check it is not just pace re-entering by the back door - so the
# concession is also split into its pace component (possessions) and efficiency component.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260822)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
BASEMK = {"pts": ("pts",), "reb": ("reb",), "ast": ("ast",),
          "pr": ("pts", "reb"), "pa": ("pts", "ast"), "ra": ("reb", "ast"),
          "pra": ("pts", "reb", "ast")}
gof, oppof, dateof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm; dateof[t2] = d2

# ---- team totals per game, from the box, for concession ------------------------------------
tg = collections.defaultdict(lambda: collections.defaultdict(float))   # (team, gt) -> stat sums
for (pl, gt), row in pgrow.items():
    tm = row["tm"]
    for st in ("pts", "reb", "ast"):
        tg[(tm, gt)][st] += row[st]
def concession(op, gt, st):
    """what OP allowed opponents in ST per game, minus league average - games before gt only"""
    allowed = []
    for t in tips_of.get(op, []):
        if t >= gt: break
        rival = oppof.get((op, t))
        if rival and (rival, t) in tg: allowed.append(tg[(rival, t)][st])
    if len(allowed) < 6: return None
    allowed = allowed[-12:]
    lg = [v[st] for (tm2, t2), v in tg.items() if t2 < gt]
    if len(lg) < 40: return None
    return statistics.mean(allowed) - statistics.mean(lg)

# ---- Elo defensive quality per team (independent instrument) --------------------------------
elo_dR = collections.defaultdict(list)
for r in load("elo_model/ratings.csv"):
    tm, dr, gp = r.get("team"), f(r.get("dR")), f(r.get("gp"))
    if tm and dr is not None and gp and gp >= 8: elo_dR[tm].append(dr)
teamdef = {tm: statistics.mean(v) for tm, v in elo_dR.items() if len(v) >= 4}

_mc = {}
def med_team(pl, mk, gt):
    k = (pl, mk, gt)
    if k in _mc: return _mc[k]
    g = [r for r in hist.get(pl, []) if r["tip"] < gt]
    out = None
    if g:
        cur = g[-1]["tm"]; g2 = [r for r in g if r["tm"] == cur]
        if len(g2) >= 5: out = statistics.median([r[mk] for r in g2[-10:]])
    _mc[k] = out
    return out

Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in BASEMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    op = oppof.get((tm, gt))
    md = med_team(pl, mk, gt)
    if not op or md is None: continue
    # matchup increment: opponent concession per component, scaled by her share of team output
    inc = 0.0; ok = True
    for st in BASEMK[mk]:
        c = concession(op, gt, st)
        tt = [tg[(tm, t)][st] for t in tips_of.get(tm, []) if t < gt and (tm, t) in tg]
        pm = med_team(pl, st, gt)
        if c is None or not tt or pm is None: ok = False; break
        share = pm / max(statistics.mean(tt[-12:]), 1e-9)
        inc += c * share
    if not ok: continue
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, op=op, date=dateof.get(gt, ""),
                  ln=ln, md=md, cush=md-ln, inc=inc,
                  edef=teamdef.get(op),
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln,
                  oret=((sdq["Over"][2]-1) if now[mk] > ln else -1.0),
                  resid=now[mk] - md))
print(f"{len(Q)} two-sided quotes with a matchup increment, {len({r['gid'] for r in Q})} games")
print("")
# ---- the heat map: concession matrix at season end ------------------------------------------
print("="*100)
print("  THE HEAT MAP - points/rebounds/assists each defence CONCEDES vs league average")
print("="*100)
gt_last = max(t for v in tips_of.values() for t in v)
teams = sorted({tm for (tm, _) in tg})
print(f"  {'':<5}" + "".join(f"{st:>8}" for st in ("pts", "reb", "ast")) + "     (+ = soft, - = stingy)")
heat = {}
for tm in teams:
    row = []
    for st in ("pts", "reb", "ast"):
        c = concession(tm, gt_last + datetime.timedelta(hours=1), st)
        row.append(c)
    heat[tm] = row
    print(f"  {tm:<5}" + "".join(f"{('%+.1f' % c) if c is not None else '-':>8}" for c in row))
print("")
def roi(rows): return 100*sum(r["oret"] for r in rows)/len(rows) if rows else 0.0
def spearman(xs, ys):
    def rk(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for i, j in enumerate(s): r[j] = i
        return r
    a, b = rk(xs), rk(ys); ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((a[i]-ma)*(b[i]-mb) for i in range(len(a)))
    den = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return num/den if den else 0.0

print("="*100)
print("  1. DOES THE MATCHUP INCREMENT PREDICT HER PRODUCTION? (resid = actual minus median)")
print("="*100)
rho_p = spearman([r["inc"] for r in Q], [r["resid"] for r in Q])
print(f"  corr(matchup increment, production residual) rho = {rho_p:+.4f}   n={len(Q)}")
v = sorted(r["inc"] for r in Q); t1, t2_ = v[len(v)//3], v[2*len(v)//3]
for nm, sel in ((f"opponent SOFT (inc > {t2_:+.2f})", lambda r: r["inc"] > t2_),
                (f"neutral", lambda r: t1 < r["inc"] <= t2_),
                (f"opponent STINGY (inc <= {t1:+.2f})", lambda r: r["inc"] <= t1)):
    g = [r for r in Q if sel(r)]
    print(f"    {nm:<34} n={len(g):<5} mean resid {statistics.mean(r['resid'] for r in g):+.2f}"
          f"   over ROI {roi(g):+6.1f}%")
print("")
print("="*100)
print("  2. DOES IT PREDICT THE BET? - game-level trend test on over returns")
print("="*100)
bg = collections.defaultdict(list)
for r in Q: bg[r["gid"]].append(r)
gk = list(bg)
ginc = {}
for r in Q: ginc.setdefault((r["gid"], r["tm"]), r["inc"])
real = spearman([r["inc"] for r in Q], [r["oret"] for r in Q])
keys = list(ginc); vals = [ginc[k] for k in keys]
beat = 0; T = 3000
for _ in range(T):
    random.shuffle(vals); lab = dict(zip(keys, vals))
    rho = spearman([lab[(r["gid"], r["tm"])] for r in Q], [r["oret"] for r in Q])
    if rho >= real: beat += 1
print(f"  rho(increment, over return) = {real:+.4f}   game-side permutation p = {beat/T:.4f}")
print("")
print("="*100)
print("  3. BEYOND THE CUSHION? - adjusted cushion vs raw, and the increment inside cushion bands")
print("="*100)
cm = statistics.median(r["cush"] for r in Q)
for clab, csel in ((f"cushion small (<= {cm:+.1f})", lambda r: r["cush"] <= cm),
                   (f"cushion big   (>  {cm:+.1f})", lambda r: r["cush"] > cm)):
    a = [r for r in Q if csel(r) and r["inc"] > t2_]
    b = [r for r in Q if csel(r) and r["inc"] <= t1]
    print(f"  {clab}:  soft opp {roi(a):+6.1f}% (n={len(a)})   stingy opp {roi(b):+6.1f}% (n={len(b)})")
print("")
print("="*100)
print("  4. THE ELO INSTRUMENT - same question, independent defence measure")
print("="*100)
E = [r for r in Q if r["edef"] is not None]
if len(E) >= 100:
    rho_e = spearman([r["edef"] for r in E], [r["oret"] for r in E])
    print(f"  rho(opponent Elo dR, over return) = {rho_e:+.4f}   n={len(E)}")
    ve = sorted(r["edef"] for r in E); e1, e2_ = ve[len(ve)//3], ve[2*len(ve)//3]
    for nm, sel in (("weakest defences", lambda r: r["edef"] <= e1),
                    ("strongest defences", lambda r: r["edef"] > e2_)):
        g = [r for r in E if sel(r)]
        print(f"    {nm:<22} n={len(g):<5} over ROI {roi(g):+6.1f}%")
    agree = spearman([r["inc"] for r in E], [r["edef"] for r in E])
    print(f"  corr(box concession, Elo dR) = {agree:+.3f}  (the two instruments should agree)")
print("")
print("="*100)
print("  5. IS IT JUST PACE AGAIN? - concession split into pace and efficiency")
print("="*100)
# pace proxy: total points both teams score in the opponent's games (concession includes it)
def gamespace(op, gt):
    tot = []
    for t in tips_of.get(op, []):
        if t >= gt: break
        rival = oppof.get((op, t))
        if rival and (rival, t) in tg and (op, t) in tg:
            tot.append(tg[(rival, t)]["pts"] + tg[(op, t)]["pts"])
    return statistics.mean(tot[-12:]) if len(tot) >= 6 else None
sub = [r for r in Q if gamespace(r["op"], r["gt"]) is not None]
if len(sub) >= 200:
    paces = {r["op"]: gamespace(r["op"], r["gt"]) for r in sub}
    rho_pc = spearman([paces[r["op"]] for r in sub], [r["inc"] for r in sub])
    print(f"  corr(opponent game pace, matchup increment) = {rho_pc:+.3f}")
    print("  high = concession is mostly pace re-entering; the pace finding already showed the")
    print("  board cannot forecast pace, so a pace-dominated increment inherits that verdict.")
