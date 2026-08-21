# pbp_hunt.py - mine the play-by-play for what the BOX SCORE cannot see, then bet against it.
# ---------------------------------------------------------------------------------------------
# The box score says "18 points". The play-by-play says WHEN: 12 of them in a decided fourth
# quarter against bench defence. A trailing-window line model (the book's, and ours) eats the 18
# whole. If the padded portion does not repeat - and garbage-time production should not - then
# players whose recent games were PADDED carry lines that are too high: FADE. Players whose real
# production was CONCEALED by early blowouts (starters benched in Q4) carry lines too low: OVER.
#
# Features per player-game from plays_full.csv (running score on every row):
#   pad    points scored while the game was DECIDED (|margin| >= 15 in Q4)
#   burn   minutes-proxy: her team's Q4 plays she appears in, when decided (was she even out?)
# Rolled into her last-3 games before tonight:
#   padded3   share of her last-3 scoring that came in decided Q4s   -> FADE her over
#   hidden3   she sat decided Q4s (0 appearances) while team blew out -> her line UNDERSTATES her
#
# BRUTE FORCE: those two, plus every cheap PBP formula (FT share, three-share, assisted share,
# early-exit) - all declared in one grid, one ceiling, both sides, real two-sided prices.
import csv, os, sys, math, random, statistics, datetime, collections, re as _re
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260823)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
gof = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
gid2tip = {gid: t2 for gid, (d2, t2, hm, aw) in gmeta.items()}

# ---- parse the PBP once: per player-game scoring split by game state ------------------------
MK = _re.compile(r"^(.+?) makes (.+)")
FT = _re.compile(r"free throw")
TH = _re.compile(r"three point")
pts_split = collections.defaultdict(lambda: [0, 0, 0, 0, 0])  # (pl,gid): [total, padQ4, ft, three, q4appear]
team_q4dec = collections.Counter()                              # (gid): decided-Q4 play count
for r in csv.DictReader(open(os.path.join(D, "elo_model/plays_full.csv"), encoding="utf-8", errors="replace")):
    gid = r.get("game_id")
    if gid not in gid2tip: continue
    txt = r.get("text") or ""
    m = MK.match(txt)
    try:
        per = int(r.get("period") or 0)
        margin = abs(int(r.get("home") or 0) - int(r.get("away") or 0))
    except ValueError:
        continue
    decided = per >= 4 and margin >= 15
    if decided: team_q4dec[gid] += 1
    if not m: continue
    pl = m.group(1).strip().lower(); what = m.group(2)
    v = 1 if FT.search(what) else (3 if TH.search(what) else 2)
    e = pts_split[(pl, gid)]
    e[0] += v
    if decided: e[1] += v
    if FT.search(what): e[2] += v
    if v == 3: e[3] += v
    if per >= 4: e[4] += 1

# roll into pre-game features: her last-3 PBP games before tonight
bypl = collections.defaultdict(list)
for (pl, gid), e in pts_split.items():
    t = gid2tip.get(gid)
    if t: bypl[pl].append((t, gid, e))
for v in bypl.values(): v.sort()
def feats(pl, gt):
    g = [x for x in bypl.get(pl, []) if x[0] < gt][-3:]
    if len(g) < 2: return None
    tot = sum(e[0] for _, _, e in g)
    if tot < 10: return None
    pad = sum(e[1] for _, _, e in g)
    ft = sum(e[2] for _, _, e in g); th = sum(e[3] for _, _, e in g)
    hid = sum(1 for _, gid, e in g if e[4] == 0 and team_q4dec.get(gid, 0) >= 8)
    return dict(padded3=pad/tot, ft3=ft/tot, three3=th/tot, hidden3=hid)

Q = []
for (pl, mk, gt), sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt)); tm = teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    fx = feats(pl, gt)
    if not fx: continue
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], ln=ln,
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln, **fx))
print(f"{len(Q)} two-sided quotes with a 3-game PBP profile "
      f"({len({r['pl'] for r in Q})} players)")
pd = sorted(r["padded3"] for r in Q)
P90 = pd[int(len(pd)*0.9)] if pd else 0
print(f"  padded-share distribution: median {pd[len(pd)//2]:.2f}, p90 {P90:.2f}")
def ret_(r, s): return ((r[s+"_od"]-1) if r[s+"_won"] else -1.0)
def roi(rows, s): return 100*sum(ret_(r, s) for r in rows)/len(rows) if rows else 0.0
def hitr(rows, s): return 100*sum(1 for r in rows if r[s+"_won"])/len(rows) if rows else 0.0
def pboot(rows, s, T=2000):
    bp = collections.defaultdict(list)
    for r in rows: bp[r["pl"]].append(r)
    k = list(bp); o = []
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bp[p]], s))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
CELLS = [
    ("PADDED 20%+ of recent pts in dead Q4s: UNDER", lambda r: r["padded3"] >= 0.20, "u"),
    ("PADDED 10-20%: UNDER", lambda r: 0.10 <= r["padded3"] < 0.20, "u"),
    ("clean production (pad < 5%): OVER", lambda r: r["padded3"] < 0.05, "o"),
    ("clean production: UNDER (control)", lambda r: r["padded3"] < 0.05, "u"),
    ("HIDDEN (sat 1+ decided Q4): OVER", lambda r: r["hidden3"] >= 1, "o"),
    ("HIDDEN 2+ of last 3: OVER", lambda r: r["hidden3"] >= 2, "o"),
    ("FT-heavy scorer (30%+ from line): UNDER", lambda r: r["ft3"] >= 0.30, "u"),
    ("FT-heavy scorer: OVER", lambda r: r["ft3"] >= 0.30, "o"),
    ("three-dependent (40%+ from 3s): UNDER", lambda r: r["three3"] >= 0.40, "u"),
    ("three-dependent: OVER", lambda r: r["three3"] >= 0.40, "o"),
    ("inside scorer (<10% from 3s): OVER", lambda r: r["three3"] < 0.10, "o"),
    ("PADDED 20%+ AND pts-market only: UNDER",
     lambda r: r["padded3"] >= 0.20 and r["mk"] in ("pts", "pr", "pra"), "u"),
]
peaks = []
for _ in range(1000):
    pool = [(r["o_won"], r["u_won"]) for r in Q]; random.shuffle(pool)
    for r, x in zip(Q, pool): r["_o"], r["_u"] = x
    best = -99
    for lbl, sel, s in CELLS:
        g = [r for r in Q if sel(r)]
        if len(g) < 50: continue
        best = max(best, 100*sum((r[s+"_od"]-1) if r["_"+s] else -1.0 for r in g)/len(g))
    if best > -99: peaks.append(best)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("")
print("="*104)
print(f"  NOISE CEILING FIRST: {len(CELLS)} declared cells -> p95 best {CEIL:+.1f}%  (min n=50)")
print("="*104)
res = []
for lbl, sel, s in CELLS:
    g = [r for r in Q if sel(r)]
    if len(g) < 50:
        print(f"    {lbl:<52} n={len(g)} too few"); continue
    lo, hi = pboot(g, s)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<52} n={len(g):<5}{hitr(g,s):>6.1f}%{roi(g,s):>+8.1f}%  [{lo:+6.1f},{hi:+6.1f}]{star}")
    res.append((roi(g, s), lbl, len(g)))
print("")
win = [x for x in res if x[0] > CEIL]
print("  ABOVE THE CEILING: " + (", ".join(f"{l} ({v:+.1f}%, n={n})" for v, l, n in sorted(win, reverse=True)) if win else "none"))
print("")
# does padding actually fail to repeat? the mechanism check that decides if the idea was even right
pad_hi = [r for r in Q if r["padded3"] >= 0.20]
pad_lo = [r for r in Q if r["padded3"] < 0.05]
def resid(rows):
    out = []
    for r in rows:
        g = [x for x in bypl.get(r["pl"], []) if x[0] < r["gt"]][-3:]
        exp = sum(e[0] for _, _, e in g)/len(g)
        act = pts_split.get((r["pl"], r["gid"]), [None])[0]
        if act is not None and exp: out.append(act - exp)
    return out
a, b = resid(pad_hi), resid(pad_lo)
if a and b:
    print(f"  MECHANISM CHECK - next-game scoring vs her recent average:")
    print(f"    padded players : {statistics.mean(a):+.2f} pts (n={len(a)})")
    print(f"    clean players  : {statistics.mean(b):+.2f} pts (n={len(b)})")
    print("    padding must predict a DROP for the fade to have a mechanism at all.")
