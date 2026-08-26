"""Hypothesis C part 2: (a) team-level confound control, (b) the next-game prop bet at REAL 1xbet prices."""
import csv, os, sys, math, collections, random, statistics, datetime, pickle
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
random.seed(20260826)
HD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HD)
from pbpx_lib import R, H, load_master, block_boot, ols

# ---- data layer (board) ----
sys.path.insert(0, R)
D = R
__file__ = os.path.join(R, "mega_sweep.py")   # mega_sweep resolves its own paths from __file__
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

P = pickle.load(open(os.path.join(H, "pbpx_c_pg.pkl"), "rb"))
for r in P:
    r["f_h1"] = sum(1 for t in r["ft"] if t < 1200.0)
    r["trouble"] = int(r["f_h1"] >= 3)
ser = collections.defaultdict(list)
for r in P: ser[(r["season"], r["player"], r["team"])].append(r)
for k, v in ser.items():
    v.sort(key=lambda x: x["date"])
    for i, r in enumerate(v):
        pri = [p for p in v[:i] if p["mins"] > 0]
        if len(pri) >= 5:
            r["b_min"] = statistics.mean(p["mins"] for p in pri)
            r["b_pts"] = statistics.mean(p["pts"] for p in pri)
        r["nxt"] = v[i + 1] if i + 1 < len(v) else None
ST = [r for r in P if r.get("b_min", 0) >= 24.0]

print("=== (a) TEAM-LEVEL confound control: teams score MORE with a star in foul trouble. Why? ===")
rowsm = load_master()
mm = {(r["game_id"], r["side"]): r for r in rowsm}
byteam = collections.defaultdict(list)
for r in ST: byteam[(r["gid"], r["side"])].append(r)
A = []
for key, lst in byteam.items():
    g = mm.get(key)
    if not g or g["total"] is None or g["sp_team"] is None: continue
    imp = g["total"] / 2.0 - g["sp_team"] / 2.0      # implied team points from close
    A.append(dict(ntr=sum(x["trouble"] for x in lst), pts=g["pts"], imp=imp,
                  fta=g["fta"], opp_fta=g["opp_fta"], gfta=g["fta"] + g["opp_fta"],
                  gt=g["game_total"], total=g["total"], ou_o=g["ou_o"], ou_u=g["ou_u"],
                  gid=g["game_id"], side=g["side"]))
print("%-14s %6s %9s %9s %10s %10s %10s" % ("stars in trbl", "n", "team pts", "implied", "pts - imp", "game FTA", "game total"))
for k, lab in ((0, "0"), (1, "1"), (2, "2+")):
    sub = [a for a in A if (a["ntr"] == k if k < 2 else a["ntr"] >= 2)]
    if len(sub) < 20: continue
    print("%-14s %6d %9.2f %9.2f %+10.2f %10.1f %10.2f" %
          (lab, len(sub), statistics.mean(a["pts"] for a in sub), statistics.mean(a["imp"] for a in sub),
           statistics.mean(a["pts"] - a["imp"] for a in sub), statistics.mean(a["gfta"] for a in sub),
           statistics.mean(a["gt"] for a in sub)))
b, se, t = ols([float(a["pts"] - a["imp"]) for a in A], [[float(a["ntr"])] for a in A])
print("  (team pts - closing implied) ~ n_stars_in_trouble: slope %+.3f pts (t=%.2f, n=%d)" % (b[1], t[1], len(A)))
b, se, t = ols([float(a["gfta"]) for a in A], [[float(a["ntr"])] for a in A])
print("  game FTA ~ n_stars_in_trouble: slope %+.2f FTA (t=%.2f)  <-- the confound: foul-trouble games are whistle-heavy" % (b[1], t[1]))

print("\n=== (b) NEXT-GAME PROP BET at real two-sided 1xbet prices ===")
gd = {}
for gid, (dt, tip, home, away) in gmeta.items():
    gd.setdefault(str(dt)[:10].replace("-", ""), []).append(tip)
tipdate = {}
for gid, (dt, tip, home, away) in gmeta.items():
    tipdate.setdefault(str(dt)[:10].replace("-", ""), set()).add(tip)

nres = 0
cand = []
for r in ST:
    nx = r.get("nxt")
    if not nx or nx.get("b_pts") is None: continue
    key = _pl(nx["player"])
    if not key: continue
    d = nx["date"]
    tips = tipdate.get(d, set())
    hit = None
    for tp in tips:
        s = side.get((key, "pts", tp))
        if s and "Over" in s and "Under" in s:
            hit = (tp, s); break
    if hit:
        nres += 1
        cand.append(dict(r=r, nx=nx, tip=hit[0], s=hit[1], trouble=r["trouble"], player=key))
print("player-games whose NEXT game has a two-sided 1xbet points prop: %d (of %d starter-pool rows)" % (nres, len(ST)))
print("  of those, next-after-foul-trouble: %d" % sum(1 for c in cand if c["trouble"]))
if sum(1 for c in cand if c["trouble"]) >= 15:
    for lab, flt in (("after 3+ fouls by half", lambda c: c["trouble"] == 1),
                     ("after 0-1 fouls by half", lambda c: c["r"]["f_h1"] <= 1)):
        sub = [c for c in cand if flt(c)]
        if len(sub) < 10: continue
        for sd_ in ("Over", "Under"):
            ps = []
            for c in sub:
                t_, line, odds = c["s"][sd_]
                act = c["nx"]["pts"]
                if abs(act - line) < 1e-9: ps.append(0.0)
                elif (act > line) == (sd_ == "Over"): ps.append(odds - 1)
                else: ps.append(-1.0)
            byp = collections.defaultdict(list)
            for c, p in zip(sub, ps): byp[c["player"]].append(p)
            m, lo, hi = block_boot(list(byp.values()), 4000, 13)
            print("  %-24s %-5s n=%3d (players=%2d)  ROI %+7.2f%%  CI[%+.1f%%,%+.1f%%]" %
                  (lab, sd_, len(ps), len(byp), 100 * m, 100 * lo, 100 * hi))
else:
    print("  NOT EXECUTABLE at this n: fewer than 15 gradable next-game props follow a foul-trouble event.")
