# flip_ml.py - does the flip/over signal say anything about the GAME? moneyline or total?
# ---------------------------------------------------------------------------------------------
# Tonight Kelsey Mitchell went over 24.5 and Indiana won by 14. The obvious question is whether
# that is a pattern - if our player overs travel with team wins or with high-scoring games, then
# the same signal could be played on the moneyline or the total, which are far more liquid markets
# with roughly a third of the prop margin.
#
# TWO DIFFERENT QUESTIONS, and only one of them can make money:
#   DESCRIPTIVE  when a prop over WINS, did her team also win / was the game high scoring?
#                Interesting, but useless for betting - you only know the prop result afterwards.
#   TRADEABLE    does the signal FIRING (which you know before tip) predict the game result?
#                That is the only version you can act on, and it is what gets the gates.
#
# Four pre-declared tests -> Bonferroni bar p < 0.0125.
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
ODDS = r"C:\Users\Axioo\Downloads\wnba_odds_history.csv"
def load(p, absolute=False):
    fp = p if absolute else os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def d8(s):
    s = (s or "").replace("-", "")
    return s[:8] if len(s) >= 8 else ""
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
FULL2AB = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
           "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA",
           "Las Vegas Aces":"LV","Minnesota Lynx":"MIN","New York Liberty":"NY",
           "Phoenix Mercury":"PHX","Portland Fire":"POR","Seattle Storm":"SEA",
           "Toronto Tempo":"TOR","Washington Mystics":"WSH"}

G, res = {}, {}
for g in load("data/games_2026.csv"):
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    G[g.get("game_id")] = dict(date=g.get("date",""), tip=ts(g.get("tip")), home=g.get("home"),
                               away=g.get("away"), hs=hs, as_=as_)
    if hs is None: continue
    res[(g.get("date"), g.get("home"))] = dict(won=hs > as_, pf=hs, total=hs+as_, marg=hs-as_)
    res[(g.get("date"), g.get("away"))] = dict(won=as_ > hs, pf=as_, total=hs+as_, marg=as_-hs)

plog = collections.defaultdict(list); teamon = {}
for r in load("data/box_2026.csv"):
    g = G.get(r.get("game_id"))
    if not g or not g["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(date=g["date"], tip=g["tip"], team=r.get("team"), pts=pts, reb=reb,
                         ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast))
    teamon[(g["date"], pl)] = r.get("team")
for v in plog.values(): v.sort(key=lambda x: x["date"])
byplayer = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v:
        if g["tip"]: byplayer[pl].append((g["tip"], g["date"], g))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

# closing moneyline and closing total
mlp = {}
mlser = collections.defaultdict(list)
for r in load(ODDS, absolute=True):
    t, c = f(r.get("ts")), ts(r.get("commence"))
    hp, ap = f(r.get("home_novig")), f(r.get("away_novig"))
    if t and c and hp and ap:
        mlser[(c, r.get("home"), r.get("away"))].append((datetime.datetime.fromtimestamp(t, datetime.timezone.utc), hp, ap))
for (c, home, away), v in mlser.items():
    v.sort(); hab, aab = FULL2AB.get(home), FULL2AB.get(away)
    if not (hab and aab): continue
    for key in (c.strftime("%Y%m%d"), (c - datetime.timedelta(hours=6)).strftime("%Y%m%d")):
        mlp[(key, hab)] = v[-1][1]; mlp[(key, aab)] = v[-1][2]
def dec(am):
    a = f(am)
    return None if a is None or a == 0 else (1 + a/100 if a > 0 else 1 + 100/abs(a))
snap = collections.defaultdict(list)
for r in load("gamelines.csv"):
    t, st = ts(r.get("captured_utc")), ts((r.get("start") or "") + "Z" if r.get("start") else None)
    if not (t and st) or t > st or r.get("type") != "total": continue
    pr = (r.get("prices") or "").split(",")
    if len(pr) != 2: continue
    d1, d2 = dec(pr[0]), dec(pr[1])
    if d1 and d2 and f(r.get("points")) is not None:
        snap[(r.get("teams"), st)].append((t, f(r.get("points")), d1, d2))
closetot = {}
for (teams, st), v in snap.items():
    last = max(x[0] for x in v)
    same = [x for x in v if x[0] == last]
    if same: closetot[(teams, st)] = min(same, key=lambda x: abs(x[2]-x[3]))
print(f"{len(mlp)} closing moneylines, {len(closetot)} closing totals\n")

# our over bets
seen, OV = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    t, ln, o = ts(b.get("captured_utc")), f(b.get("line")), f(b.get("odds"))
    mk, side, src = b.get("market"), b.get("side"), (b.get("src") or "?")
    pl = (b.get("player") or "").lower()
    if not (t and ln is not None and o and mk in MKTS and side == "Over"): continue
    k = (d8(b.get("date")), pl, mk, ln)
    if k in seen: continue
    seen.add(k)
    dt, rec = game_after(pl, t)
    if not rec or rec[mk] == ln: continue
    tm = teamon.get((dt, pl))
    r_ = res.get((dt, tm))
    if not r_: continue
    OV.append(dict(date=dt, pl=pl, mk=mk, src=src, team=tm, won=rec[mk] > ln,
                   team_won=r_["won"], total=r_["total"], marg=r_["marg"],
                   wp=mlp.get((dt, tm))))
FL = [r for r in OV if r["src"].startswith("flip")]
print(f"{len(OV)} over bets with a game result, {len(FL)} of them flip\n")

def pct(v): return 100*sum(v)/len(v) if v else 0
print("="*92)
print("  A. DESCRIPTIVE - when the prop over WINS, what else happened? (not tradeable)")
print("="*92)
for nm, rows in (("all over bets", OV), ("flip only", FL)):
    w = [r for r in rows if r["won"]]; l = [r for r in rows if not r["won"]]
    if len(w) < 30 or len(l) < 30: continue
    a, b = pct([r["team_won"] for r in w]), pct([r["team_won"] for r in l])
    n1, n2 = len(w), len(l)
    p = (sum(r["team_won"] for r in rows))/len(rows)
    z = (a/100-b/100)/math.sqrt(p*(1-p)*(1/n1+1/n2))
    ta, tb = sum(r["total"] for r in w)/n1, sum(r["total"] for r in l)/n2
    ma, mb = sum(r["marg"] for r in w)/n1, sum(r["marg"] for r in l)/n2
    print(f"    {nm}:")
    print(f"      prop WON  (n={n1:<4}) her team won {a:5.1f}%   game total {ta:6.1f}   margin {ma:+5.1f}")
    print(f"      prop LOST (n={n2:<4}) her team won {b:5.1f}%   game total {tb:6.1f}   margin {mb:+5.1f}")
    print(f"      difference: team-win {a-b:+5.1f}pp (z={z:+.2f})   total {ta-tb:+5.1f} pts\n")
print("    -> a big gap here just says good games and good player nights coincide. It cannot be")
print("       bet, because you learn the prop result at the same time as the game result.")

print("\n" + "="*92)
print("  B. TRADEABLE - does the signal FIRING predict the game? (this is the one that pays)")
print("="*92)
byteam = collections.defaultdict(list)
for r in OV: byteam[(r["date"], r["team"])].append(r)
flipteam = {k: v for k, v in byteam.items() if any(x["src"].startswith("flip") for x in v)}
print(f"    {len(flipteam)} team-games where at least one FLIP fired")
rows = [(k, v) for k, v in flipteam.items() if mlp.get(k) is not None]
print(f"    {len(rows)} of those have a closing moneyline\n")
if len(rows) >= 30:
    won = [res[k]["won"] for k, _ in rows]
    exp = sum(mlp[k] for k, _ in rows)
    sd = math.sqrt(sum(mlp[k]*(1-mlp[k]) for k, _ in rows))
    z = (sum(won) - exp)/sd
    print(f"    H3 back the ML of a team with a flip: won {sum(won)}/{len(rows)}, "
          f"market expected {exp:.1f}")
    print(f"       z={z:+.2f}  p={math.erfc(abs(z)/math.sqrt(2)):.3f}   "
          f"ROI at fair price {100*(sum((1/mlp[k]-1) if res[k]['won'] else -1 for k, _ in rows)/len(rows)):+.1f}%")
    print(f"       (fair price = no vig. A real book takes ~4.5%, so this must clear that.)")
    many = [(k, v) for k, v in rows if len(v) >= 3]
    if len(many) >= 25:
        w2 = [res[k]["won"] for k, _ in many]
        e2 = sum(mlp[k] for k, _ in many); s2 = math.sqrt(sum(mlp[k]*(1-mlp[k]) for k, _ in many))
        print(f"    H3b same, but only when 3+ overs fired on that team: {sum(w2)}/{len(many)}, "
              f"expected {e2:.1f}, z={(sum(w2)-e2)/s2:+.2f}")

gt = collections.defaultdict(list)
for r in OV: gt[(r["date"], r["team"])].append(r)
tot_rows = []
for g in G.values():
    if g["hs"] is None or not g["tip"]: continue
    hn = next((k for k, ab in FULL2AB.items() if ab == g["home"]), None)
    an = next((k for k, ab in FULL2AB.items() if ab == g["away"]), None)
    if not (hn and an): continue
    key = next((k for k in closetot if k[0] == f"{hn}|{an}"
                and abs((k[1]-g["tip"]).total_seconds()) < 6*3600), None)
    if not key: continue
    _, pts, dov, dun = closetot[key]
    nflip = sum(1 for t in (g["home"], g["away"])
                for r in gt.get((g["date"], t), []) if r["src"].startswith("flip"))
    if g["hs"]+g["as_"] == pts: continue
    tot_rows.append((nflip, g["hs"]+g["as_"] > pts, dov, dun))
print(f"\n    {len(tot_rows)} games with a closing total AND our signals")
if len(tot_rows) >= 30:
    for lo, nm in ((1, "1+ flips in the game"), (2, "2+ flips"), (3, "3+ flips")):
        sel = [x for x in tot_rows if x[0] >= lo]
        if len(sel) < 25: continue
        r_ = [(x[2]-1) if x[1] else -1.0 for x in sel]
        w = sum(1 for x in sel if x[1])
        print(f"    H4 bet the OVER when {nm:<22} n={len(sel):<4} {w}-{len(sel)-w} "
              f"({100*w/len(sel):.0f}%)  ROI {100*sum(r_)/len(r_):+.1f}%")
    base = [(x[2]-1) if x[1] else -1.0 for x in tot_rows]
    w = sum(1 for x in tot_rows if x[1])
    print(f"       BASELINE every over, no signal      n={len(tot_rows):<4} {w}-{len(tot_rows)-w} "
          f"({100*w/len(tot_rows):.0f}%)  ROI {100*sum(base)/len(base):+.1f}%")
print("\n    4 tests -> Bonferroni bar p<0.0125. And the totals cells must beat the BASELINE row,")
print("    not zero - that baseline is what made the minutes-spillover result look real.")

print("\n" + "="*92)
print("  C. THE H4 CONTRAST, DONE PROPERLY")
print("="*92)
print("    '1+ flips' covers 58 of 77 games, so comparing it to 'all 77' is comparing a sample")
print("    to itself. The only honest control is the games with NO flip at all.\n")
for lo, hi, nm in ((1, 99, "games WITH a flip"), (0, 1, "games with NO flip (the control)")):
    sel = [x for x in tot_rows if lo <= x[0] < hi]
    if not sel: continue
    w = sum(1 for x in sel if x[1])
    r_ = [(x[2]-1) if x[1] else -1.0 for x in sel]
    se = math.sqrt(0.5*0.5/len(sel))
    print(f"    {nm:<34} n={len(sel):<4} {w}-{len(sel)-w} ({100*w/len(sel):.0f}%)  "
          f"ROI {100*sum(r_)/len(r_):+6.1f}%   +/-{100*1.96*se:.0f}pp at 95%")
a = [x for x in tot_rows if x[0] >= 1]; b = [x for x in tot_rows if x[0] == 0]
if len(a) >= 20 and len(b) >= 10:
    pa_, pb = sum(1 for x in a if x[1])/len(a), sum(1 for x in b if x[1])/len(b)
    p = (sum(1 for x in a if x[1]) + sum(1 for x in b if x[1]))/(len(a)+len(b))
    z = (pa_-pb)/math.sqrt(p*(1-p)*(1/len(a)+1/len(b)))
    print(f"\n    difference {100*(pa_-pb):+.1f}pp   z={z:+.2f}   "
          f"p={math.erfc(abs(z)/math.sqrt(2)):.3f}  "
          f"({'clears' if math.erfc(abs(z)/math.sqrt(2))<0.0125 else 'FAILS'} the p<0.0125 bar)")
    print(f"    control group is n={len(b)} - it cannot resolve anything smaller than "
          f"~{100*1.96*math.sqrt(0.5*0.5/len(b)):.0f}pp.")
