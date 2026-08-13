# cross_game.py - how the book re-rates a player BETWEEN games, and does the flip signal get CLV?
# ---------------------------------------------------------------------------------------------
# Everything we have measured so far lives INSIDE one game: the price at open, at T-2h, at close.
# The question here is different and has never been tested: what happens to a player's number
# FROM ONE GAME TO THE NEXT.
#
#   "player A's over is 1.90 this match, then 1.80 next match - what does that mean?"
#
# It means the book has re-rated her. Two things can move between games and they mean different
# things, so they must be separated or the answer is mush:
#
#   THE LINE moved   (18.5 -> 20.5)  the book thinks she will SCORE MORE. This is the book's
#                                    forecast changing. Our whole season started from the theory
#                                    that books chase recent form too slowly (role-lag).
#   THE PRICE moved at the SAME line (1.90 -> 1.80)  the book kept its number but now thinks the
#                                    OVER is likelier. This is a purer opinion change, with no
#                                    line move to confound it - exactly the case asked about.
#
# Three hypotheses, all with a real prior, tested against the 53.4% over baseline:
#   H1 the book CHASES last game's result (mechanical check - does it move at all?)
#   H2 the book OVERREACTS to it -> fade the move
#   H3 the book UNDERREACTS to it -> follow the move
# Plus: does the FLIP signal (the one thing with real lift) actually earn CLV?
import csv, os, sys, math, random, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
random.seed(20260811)
def load(p):
    fp = os.path.join(D, p)
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

gtip = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
pbox = {}
for r in load("data/box_2026.csv"):
    dt, tp = gtip.get(r.get("game_id"), ("", None))
    if not (dt and tp): continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pbox[(dt, (r.get("player") or "").lower())] = dict(tip=tp, pts=pts, reb=reb, ast=ast,
                                                       pra=pts+reb+ast, pr=pts+reb, pa=pts+ast)
byplayer = collections.defaultdict(list)
for (dt, pl), rec in pbox.items(): byplayer[pl].append((rec["tip"], dt, rec))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

# ---- one row per (player, market, GAME): the MAIN line and its closing over price ---------------
# a player can have several alt lines on a night; the main market is the one the book quoted most
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in ("pts","pra","pr","pa"):
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
# THE SAME BUG, THIRD APPEARANCE: a line like 18.5 that the book posts on several different
# nights lands in ONE list here. Assigning that whole list to the first game means every LATER
# game with that same line vanishes - which is exactly why "line unchanged" came back n=0 on the
# first run. Split every series into per-night blocks (gap > 12h) BEFORE assigning it to a game.
pergame = collections.defaultdict(dict)     # (player, market, gamedate) -> {line: {side: [(t,o)]}}
for (pl, mk, side, ln), v in raw.items():
    v.sort()
    blocks, cur = [], [v[0]]
    for prev, nxt in zip(v, v[1:]):
        if (nxt[0]-prev[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(nxt)
    blocks.append(cur)
    for blk in blocks:
        if not blk: continue
        dt, rec = game_after(pl, blk[0][0])
        if not rec: continue
        pre = [x for x in blk if x[0] <= rec["tip"]]
        if not pre: continue
        pergame[(pl, mk, dt)].setdefault(ln, {})[side] = pre
G = []
for (pl, mk, dt), lines in pergame.items():
    main = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
    ln, sides = main
    if "Over" not in sides: continue
    rec = pbox.get((dt, pl))
    if not rec or rec[mk] == ln: continue
    G.append(dict(pl=pl, mk=mk, date=dt, tip=rec["tip"], line=ln,
                  open_o=sides["Over"][0][1], close_o=sides["Over"][-1][1],
                  actual=rec[mk], over_won=rec[mk] > ln))
G.sort(key=lambda r: (r["pl"], r["mk"], r["date"]))
print(f"{len(G)} player-market-games with a main line and a finished box score")

# ---- chain consecutive games for the same player-market ------------------------------------------
chain = collections.defaultdict(list)
for r in G: chain[(r["pl"], r["mk"])].append(r)
PAIRS = []
for k, v in chain.items():
    v.sort(key=lambda r: r["date"])
    for prev, cur in zip(v, v[1:]):
        gap = (cur["tip"] - prev["tip"]).days
        if gap > 10: continue                       # not a sensible "next match"
        PAIRS.append(dict(pl=k[0], mk=k[1], date=cur["date"], tip=cur["tip"],
                          line=cur["line"], odds=cur["close_o"], over_won=cur["over_won"],
                          dline=cur["line"] - prev["line"],
                          dprice=cur["close_o"] - prev["close_o"],
                          same_line=abs(cur["line"] - prev["line"]) < 0.01,
                          prev_vs_line=prev["actual"] - prev["line"],
                          prev_over=prev["over_won"], gap_days=gap))
PAIRS.sort(key=lambda r: r["date"])
print(f"{len(PAIRS)} consecutive-game pairs for the same player and market\n")

BASE = 0.534          # measured board over baseline from fade_hunt.py
def show(rows, label, minn=25):
    n = len(rows)
    if n < minn:
        print(f"    {label:<48} n={n} too few"); return None
    w = sum(1 for r in rows if r["over_won"])/n
    rr = [(r["odds"]-1) if r["over_won"] else -1.0 for r in rows]
    m = sum(rr)/n
    se = math.sqrt(BASE*(1-BASE)/n)
    z = (w-BASE)/se
    print(f"    {label:<48} n={n:<5} win {100*w:5.1f}%  ROI {100*m:+6.1f}%  "
          f"lift {100*(w-BASE):+5.1f}pp  z={z:+5.2f}")
    return w, m, n, z

print("="*84)
print("  H1. DOES THE BOOK CHASE? (does last game's result move the next line at all?)")
print("="*84)
xs = [r["prev_vs_line"] for r in PAIRS]; ys = [r["dline"] for r in PAIRS]
n = len(xs); mx, my = sum(xs)/n, sum(ys)/n
sx = (sum((a-mx)**2 for a in xs)/n)**.5; sy = (sum((b-my)**2 for b in ys)/n)**.5
rr_ = sum((a-mx)*(b-my) for a, b in zip(xs, ys))/n/(sx*sy) if sx and sy else 0
tt = rr_*math.sqrt((n-2)/max(1e-9, 1-rr_*rr_))
print(f"    correlation(last game's beat/miss vs line, NEXT line move) = {rr_:+.3f}  "
      f"t={tt:+.2f}  p={math.erfc(abs(tt)/math.sqrt(2)):.4f}")
for lo, hi, nm in ((-99,-5,"missed by 5+"), (-5,-2,"missed by 2-5"), (-2,2,"landed near the line"),
                   (2,5,"beat by 2-5"), (5,99,"beat by 5+")):
    grp = [r for r in PAIRS if lo <= r["prev_vs_line"] < hi]
    if len(grp) < 15: continue
    print(f"      after she {nm:<22} n={len(grp):<5} next line moves "
          f"{sum(r['dline'] for r in grp)/len(grp):+.2f} pts, "
          f"price {sum(r['dprice'] for r in grp)/len(grp):+.3f}")
print("    -> a clear gradient here means the book DOES chase. That is necessary for H2/H3.")

print("\n" + "="*84)
print("  H2/H3. THE LINE MOVED BETWEEN GAMES - follow it or fade it?")
print("="*84)
for lo, hi, nm in ((2,99,"book RAISED the line 2+"), (0.5,2,"raised 0.5-2"),
                   (-0.5,0.5,"line unchanged"), (-2,-0.5,"cut 0.5-2"), (-99,-2,"book CUT the line 2+")):
    show([r for r in PAIRS if lo <= r["dline"] < hi], f"bet the OVER after: {nm}")
print("    (all graded as the OVER, so a lift below 0 means the UNDER was the play)")

print("\n" + "="*84)
print("  THE EXACT CASE ASKED ABOUT: same line, price moved (1.90 -> 1.80)")
print("="*84)
SL = [r for r in PAIRS if r["same_line"]]
print(f"    {len(SL)} pairs where the book kept the IDENTICAL line across both games")
for lo, hi, nm in ((0.04,9,"price LENGTHENED 4c+ (1.86->1.90+)"),
                   (0.01,0.04,"lengthened 1-4c"),
                   (-0.01,0.01,"price unchanged"),
                   (-0.04,-0.01,"shortened 1-4c"),
                   (-9,-0.04,"price SHORTENED 4c+ (1.90->1.86-)")):
    show([r for r in SL if lo <= r["dprice"] < hi], f"  {nm}", minn=20)
print("\n    a SHORTER over price = the book likes the over more. If that is information, the")
print("    shortened bucket should beat 53.4%. If it is just the book taking a position, it will not.")

print("\n" + "="*84)
print("  GATE: is the best of the above better than a search that knows nothing?")
print("="*84)
CELLS = []
for lo, hi in ((2,99),(0.5,2),(-0.5,0.5),(-2,-0.5),(-99,-2)):
    CELLS.append(("dline", lo, hi))
for lo, hi in ((0.04,9),(0.01,0.04),(-0.01,0.01),(-0.04,-0.01),(-9,-0.04)):
    CELLS.append(("dprice_same", lo, hi))
def sel(rows, cell):
    kind, lo, hi = cell
    if kind == "dline": return [i for i, r in enumerate(rows) if lo <= r["dline"] < hi]
    return [i for i, r in enumerate(rows) if r["same_line"] and lo <= r["dprice"] < hi]
def stat(idx, rows, outcomes=None):
    if len(idx) < 25: return None
    xs = [((rows[i]["odds"]-1) if (outcomes[i] if outcomes else rows[i]["over_won"]) else -1.0)
          for i in idx]
    m = sum(xs)/len(xs); sd = (sum((x-m)**2 for x in xs)/(len(xs)-1))**.5
    return (m/(sd/math.sqrt(len(xs))), m*100, len(xs)) if sd else None
def search(rows, outcomes=None):
    best = None
    for c in CELLS:
        s = stat(sel(rows, c), rows, outcomes)
        if s and (best is None or abs(s[0]) > abs(best[0][0])): best = (s, c)
    return best
cut_i = int(len(PAIRS)*2/3)
IN, OUT = PAIRS[:cut_i], PAIRS[cut_i:]
print(f"    IN {len(IN)} (to {IN[-1]['date']})   OUT {len(OUT)} (from {OUT[0]['date']})")
implied = lambda r: min(0.97, max(0.03, (1/r["odds"])/1.076))
nulls = []
for _ in range(400):
    sim = [random.random() < implied(r) for r in IN]
    b = search(IN, sim)
    if b: nulls.append(abs(b[0][0]))
nulls.sort()
real = search(IN)
if real:
    beat = sum(1 for x in nulls if x >= abs(real[0][0]))/len(nulls)
    print(f"    null best-|t|: median {nulls[len(nulls)//2]:.2f}  95th {nulls[int(len(nulls)*.95)]:.2f}")
    print(f"    our best in-sample: {real[1]} -> t={real[0][0]:+.2f} ROI={real[0][1]:+.1f}% n={real[0][2]}")
    print(f"    null beats it {beat*100:.1f}%  ({'PASSES' if beat < 0.05 else 'FAILS'})")
    o = stat(sel(OUT, real[1]), OUT)
    print(f"    OUT-OF-SAMPLE: " + (f"n={o[2]} ROI={o[1]:+.1f}% t={o[0]:+.2f}" if o else "too few"))

# ---- THE CONVERGENCE, tested as a pre-specified hypothesis (not a mined cell) --------------------
print("\n" + "="*84)
print("  CONVERGENCE: 'book CUT the line hard -> take the over' is the SAME hypothesis as FLIP,")
print("  reached independently. It is pre-specified with a mechanism, so it gets its own test")
print("  rather than being judged by the max-|t| search above.")
print("="*84)
for lo, hi, nm in ((-99,-3,"cut 3+ pts"), (-3,-2,"cut 2-3"), (-2,-1,"cut 1-2"),
                   (-1,-0.5,"cut 0.5-1"), (-0.5,0.5,"unchanged"), (0.5,99,"raised")):
    show([r for r in PAIRS if lo <= r["dline"] < hi], f"  book {nm:<14} -> bet OVER", minn=25)
CUT = [r for r in PAIRS if r["dline"] <= -2]
if len(CUT) >= 40:
    h = len(CUT)//2
    print(f"\n    holdout check on 'cut 2+' (n={len(CUT)}):")
    for lbl, part in (("first half ", CUT[:h]), ("second half", CUT[h:])):
        show(part, f"      {lbl} {part[0]['date']}-{part[-1]['date']}", minn=20)
    w = sum(1 for r in CUT if r["over_won"]); n = len(CUT)
    nulls2 = []
    for _ in range(2000):
        sim = sum(1 for _ in range(n) if random.random() < BASE)
        nulls2.append(sim)
    beat = sum(1 for x in nulls2 if x >= w)/len(nulls2)
    print(f"      one pre-specified test, {w}/{n} vs a {100*BASE:.1f}% baseline: "
          f"p={beat:.4f}  ({'PASSES' if beat < 0.05 else 'FAILS'})")

# ---- DOES FLIP EARN CLV? --------------------------------------------------------------------------
print("\n" + "="*84)
print("  DOES FLIP ACTUALLY EARN CLV? (does the market move toward us after we bet?)")
print("="*84)
anchors = {}
for r in load("picks_log.csv"):
    a = f(r.get("anchor")); mk = (r.get("market") or "").split("_")[0]
    if a is None or not mk: continue
    anchors.setdefault(((r.get("player") or "").lower(), mk), []).append((d8(r.get("pick_date")), a))
for v in anchors.values(): v.sort()
def anchor_for(pl, mk, dt):
    v = anchors.get((pl, mk))
    if not v or not dt: return None
    near = min(v, key=lambda x: abs(int(x[0]) - int(dt)) if x[0] else 9e9)
    return near[1] if near[0] and abs(int(near[0]) - int(dt)) <= 2 else None
bidx = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None:
        bidx[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
for v in bidx.values(): v.sort()
seen, FL = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if not (b.get("src") or "").startswith("flip"): continue
    t, ln, o = ts(b.get("captured_utc")), f(b.get("line")), f(b.get("odds"))
    mk, side, pl = b.get("market"), b.get("side"), (b.get("player") or "").lower()
    if not (t and ln is not None and o and mk in ("pts","pra","pr","pa")): continue
    k = (d8(b.get("date")), pl, mk, side, ln)
    if k in seen: continue
    seen.add(k)
    dt, rec = game_after(pl, t)
    if not rec or rec[mk] == ln: continue
    v = bidx.get((pl, mk, side, ln), [])
    night = [x for x in v if t <= x[0] <= rec["tip"]]
    if not night: continue
    a = anchor_for(pl, mk, dt)
    FL.append(dict(entry=o, close=night[-1][1], clv=o/night[-1][1]-1,
                   won=(rec[mk] > ln) if side == "Over" else (rec[mk] < ln),
                   crater=(a - ln) if a is not None else None))
print(f"    {len(FL)} flip bets with an entry price AND a later closing price")
if FL:
    cl = [r["clv"] for r in FL]
    print(f"    mean CLV {100*sum(cl)/len(cl):+.2f}%   positive on "
          f"{sum(1 for x in cl if x>0)}/{len(cl)} ({100*sum(1 for x in cl if x>0)/len(cl):.0f}%)")
    for lo, hi, nm in ((4,99,"crater 4+ (the tightened rule)"), (2,4,"crater 2-4"), (-9,2,"crater <2")):
        grp = [r for r in FL if r["crater"] is not None and lo <= r["crater"] < hi]
        if len(grp) < 15:
            print(f"      {nm:<34} n={len(grp)} too few"); continue
        c = [r["clv"] for r in grp]
        w = sum(1 for r in grp if r["won"])/len(grp)
        rr = [(r["entry"]-1) if r["won"] else -1.0 for r in grp]
        print(f"      {nm:<34} n={len(grp):<4} CLV {100*sum(c)/len(c):+5.2f}%  "
              f"win {100*w:4.1f}%  ROI {100*sum(rr)/len(rr):+6.1f}%")
    print("\n    positive CLV here would mean the market moves TOWARD the flip after we take it -")
    print("    independent confirmation that the book had overcorrected and then walked it back.")

print("\n" + "="*84)
print("  HOLDOUT on the asked-about case: same line, over price LENGTHENED 4c+ (1.80 -> 1.90)")
print("="*84)
LG = [r for r in PAIRS if r["same_line"] and r["dprice"] >= 0.04]
SH = [r for r in PAIRS if r["same_line"] and r["dprice"] <= -0.04]
for nm, grp in (("price LENGTHENED 4c+", LG), ("price SHORTENED 4c+", SH)):
    if len(grp) < 60: continue
    h = len(grp)//2
    print(f"\n    {nm}  (n={len(grp)})")
    show(grp[:h], f"      first half  {grp[0]['date']}-{grp[h-1]['date']}", minn=25)
    show(grp[h:], f"      second half {grp[h]['date']}-{grp[-1]['date']}", minn=25)
    w = sum(1 for r in grp if r["over_won"]); n = len(grp)
    z = (w/n - BASE)/math.sqrt(BASE*(1-BASE)/n)
    print(f"      FULL n={n}  {w}-{n-w}  lift {100*(w/n-BASE):+.1f}pp  z={z:+.2f}  "
          f"p={math.erfc(abs(z)/math.sqrt(2)):.4f}  (10 cells tested -> Bonferroni bar p<0.005)")
    print(f"      betting the UNDER instead: win {100*(1-w/n):.1f}% vs under baseline 46.7% "
          f"-> lift {100*((1-w/n)-0.467):+.1f}pp")
