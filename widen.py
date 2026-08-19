# widen.py - two jobs: kill or keep the AWAY cell, and find volume that is not just noise.
# ---------------------------------------------------------------------------------------------
# gamectx.py produced one cell whose game-block CI excludes zero: AWAY n=43 +32.6% [+6.9,+56.8],
# against HOME n=35 +1.5%. It sits under a +55.2% ceiling, but that ceiling was driven by tiny
# n=12 cells, and comparing an n=43 claim to an n=12 null is the WRONG null - too lax in one
# direction and meaningless in the other. So test it properly:
#   * a SIZE-MATCHED ceiling: only splits near 43 bets count
#   * a direct permutation of the home/away label
#   * leave-one-team-out and leave-one-player-out - a real split survives losing any single one
#   * in-sample / out-of-sample by date
# A basketball prior matters here too: home players normally do BETTER, not worse. A cell that
# points the wrong way against the known base rate needs more evidence, not less.
#
# VOLUME. Model S buys 78 bets over the season - roughly 1.3 a night. Three places to look, all
# priced the way the card prices, all gate-3-at-ping:
#   the markets gate 2 throws away    pa / ra / reb / ast
#   the bets gate 3 cannot judge      no previous line (a player's first game on the board)
#   the signals gate 1 throws away    everything that is not flip/hotover/overshoot
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")

seq = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Over": continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    tm = teamof.get(pl)
    if not tm: continue
    gt = game_for(tm, t)
    if gt: seq[(pl, mk, gt)].append((t, ln, o))
for v in seq.values(): v.sort()
tip_on, gof = {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = (gid, d2, hm, aw); gof[(aw, t2)] = (gid, d2, hm, aw)

ALLR = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if not mk: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    q = seq.get((pl, mk, gt), []); now = pgrow.get((pl, gt))
    if len(q) < 2 or not now or mk not in now: continue
    pv = prevline.get((pl, mk, gt))
    p_t, p_l, p_o = q[-1]
    if now[mk] == p_l: continue
    gid, dt, hm, aw = gof[(tm, gt)]
    ALLR.append(dict(pl=pl, mk=mk, gt=gt, gid=gid, date=dt, src=src, tm=tm,
                     ln=p_l, od=p_o, won=now[mk] > p_l, prev=pv,
                     noprev=(pv is None), raised=(pv is not None and p_l - pv >= 0.5),
                     home=(tm == hm)))
def dedupe(rows):
    best = {}
    for r in sorted(rows, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
    return sorted(best.values(), key=lambda r: r["date"])
def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def roi(rows): return sc(rows)[3] if rows else 0.0
def gboot(rows, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(roi(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=12):
    if len(rows) < minn: print(f"  {lbl:<46} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = gboot(rows)
    print(f"  {lbl:<46} n={n:<4}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%   95CI [{lo:+6.1f},{hi:+6.1f}]")

S = dedupe([r for r in ALLR if r["src"] in SIGS and r["mk"] in BET_MKTS
            and not r["noprev"] and not r["raised"]])
AWAY = [r for r in S if not r["home"]]
print(f"MODEL S = {len(S)} bets   (away {len(AWAY)}, home {len(S)-len(AWAY)})")
print("")
print("="*104)
print("  A. IS 'AWAY' REAL?")
print("="*104)
# size-matched ceiling
tgt = len(AWAY); peaks = []
bg = collections.defaultdict(list)
for r in S: bg[r["gid"]].append(r)
gk = list(bg)
for _ in range(4000):
    bestc = -99
    for _ in range(14):
        random.shuffle(gk); acc = []
        for g in gk:
            if len(acc) >= tgt: break
            acc.extend(bg[g])
        if abs(len(acc) - tgt) <= 6: bestc = max(bestc, roi(acc))
    if bestc > -99: peaks.append(bestc)
peaks.sort()
print(f"  size-matched ceiling: random game-blocks of ~{tgt} bets, best of 14 tries,")
print(f"    p95 = {peaks[int(len(peaks)*0.95)]:+.1f}%   p99 = {peaks[int(len(peaks)*0.99)]:+.1f}%   AWAY = {roi(AWAY):+.1f}%")
# direct label permutation, preserving each game's home/away composition
real = roi(AWAY) - roi([r for r in S if r["home"]])
beat = 0; T = 5000
for _ in range(T):
    fl = {}
    for g, rows in bg.items(): fl[g] = random.random() < 0.5
    a = [r for r in S if (not r["home"]) ^ fl[r["gid"]]]
    b = [r for r in S if not ((not r["home"]) ^ fl[r["gid"]])]
    if a and b and (roi(a) - roi(b)) >= real: beat += 1
print(f"  home/away label flipped at random per game: away-minus-home gap p = {beat/T:.4f}")
print("")
byteam = collections.Counter(r["tm"] for r in AWAY)
worst = []
for tm in byteam:
    g = [r for r in AWAY if r["tm"] != tm]
    worst.append((roi(g), tm, len(AWAY)-len(g)))
worst.sort()
print(f"  leave-one-TEAM-out of AWAY:  worst {worst[0][0]:+.1f}% (drop {worst[0][1]}, {worst[0][2]} bets)"
      f"   best {worst[-1][0]:+.1f}% (drop {worst[-1][1]})")
byp = collections.Counter(r["pl"] for r in AWAY)
wp = sorted((roi([r for r in AWAY if r["pl"] != p]), p) for p in byp)
print(f"  leave-one-PLAYER-out of AWAY: worst {wp[0][0]:+.1f}% (drop {wp[0][1]})   best {wp[-1][0]:+.1f}%")
print(f"  {sum(1 for v, _ in wp if v <= 0)} of {len(wp)} single-player removals take AWAY to zero or below")
print("")
dts = sorted({r["date"] for r in S}); cut = dts[int(len(dts)*0.6)]
show([r for r in AWAY if r["date"] < cut], f"    AWAY, first 60% of dates (< {cut})")
show([r for r in AWAY if r["date"] >= cut], f"    AWAY, last 40% (>= {cut})")
print("")
print("="*104)
print("  B. WHERE COULD MORE VOLUME COME FROM?")
print("="*104)
print("  all priced at the ping, gate 3 judged at the ping - same construction as the card")
print("")
show(S, "  MODEL S as it stands")
print("")
print("  -- markets gate 2 throws away --")
oth = dedupe([r for r in ALLR if r["src"] in SIGS and r["mk"] not in BET_MKTS
              and not r["noprev"] and not r["raised"]])
show(oth, "    pa/ra/reb/ast, otherwise full Model S")
for m in ("pa", "ra", "reb", "ast"):
    show([r for r in oth if r["mk"] == m], f"      {m}")
print("")
print("  -- bets gate 3 cannot judge (no previous line) --")
npv = dedupe([r for r in ALLR if r["src"] in SIGS and r["mk"] in BET_MKTS and r["noprev"]])
show(npv, "    no previous line, otherwise Model S")
print("")
print("  -- signals gate 1 throws away --")
oths = dedupe([r for r in ALLR if r["src"] not in SIGS and r["mk"] in BET_MKTS
               and not r["noprev"] and not r["raised"]])
show(oths, "    other srcs, otherwise full Model S")
for s in sorted({r["src"] for r in oths}):
    show([r for r in oths if r["src"] == s], f"      {s}")
print("")
print("  -- the gate-3 reject itself --")
rz = dedupe([r for r in ALLR if r["src"] in SIGS and r["mk"] in BET_MKTS and r["raised"]])
show(rz, "    RAISED (what gate 3 removes) - should be clearly worse")
