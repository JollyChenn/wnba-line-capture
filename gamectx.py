# gamectx.py - does the GAME matter? total, spread, moneyline, and two bets in one game.
# ---------------------------------------------------------------------------------------------
# Last night's card was three players in ONE game: NaLyssa Smith and Jackie Young (LV) and Angel
# Reese (ATL, the other side). Three overs on 40 minutes of the same basketball. Two questions:
#
#   1 GAME CONTEXT. Does the game's own market - Pinnacle's total, spread and moneyline - predict
#     whether a player over lands? A high total is more possession and more counting stats for
#     everyone; a blowout spread is fourth-quarter garbage time and starters resting. The engine
#     already half-believes this: overshoot_overs drops pts/PRA overs when the team total is low.
#     That guard has never been tested on Model S bets specifically.
#
#   2 SAME-GAME STACKING. This is NOT an edge question, it is a RISK question, and they are
#     different. If three bets ride on one game their outcomes are correlated - a slow, ugly,
#     low-possession game sinks all three at once. Flat 1u on three correlated bets is not the
#     same risk as flat 1u on three independent ones, even if the ROI is identical. And SAME TEAM
#     (Smith + Young) should be MORE correlated than OPPOSING (Smith + Reese), because teammates
#     share possessions while opponents share only pace.
#
# Nulls are drawn at the GAME level throughout, because that is where the label lives.
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

# MODEL S, built the way the card builds it: gate 3 judged on the PING line
R = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    q = seq.get((pl, mk, gt), []); now = pgrow.get((pl, gt))
    if len(q) < 2 or not now: continue
    pv = prevline.get((pl, mk, gt))
    if pv is None: continue
    p_t, p_l, p_o = q[-1]
    if p_l - pv >= 0.5 or now[mk] == p_l: continue
    gid, dt, hm, aw = gof[(tm, gt)]
    R.append(dict(pl=pl, mk=mk, gt=gt, gid=gid, date=dt, src=src, tm=tm, hm=hm, aw=aw,
                  ln=p_l, od=p_o, won=now[mk] > p_l, act=now[mk],
                  home=(tm == hm), opp=(aw if tm == hm else hm)))
best = {}
for r in sorted(R, key=lambda x: -x["od"]): best.setdefault((r["pl"], r["gt"]), r)
R = sorted(best.values(), key=lambda r: (r["date"], r["gid"]))

# attach the game market
cov = 0
for r in R:
    ab = tuple(sorted((r["hm"], r["aw"])))
    s = GM.get((r["date"], ab), {})
    r["tot"] = s.get("tot", (None, None))[1]
    r["spr"] = s.get("spr", (None, None))[1]
    r["ml"] = s.get("ml", (None, None))[1]
    if r["tot"] is not None: cov += 1
ngames = len({r["gid"] for r in R})
print(f"MODEL S: {len(R)} bets across {ngames} games   (Pinnacle total on {cov} of {len(R)})")
print("")

def sc(rows):
    n = len(rows); w = sum(1 for r in rows if r["won"])
    u = sum((r["od"]-1) if r["won"] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def gboot(rows, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(100*sum((x["od"]-1) if x["won"] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, minn=12):
    if len(rows) < minn: print(f"  {lbl:<44} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows); lo, hi = gboot(rows)
    print(f"  {lbl:<44} n={n:<4}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%   95CI [{lo:+6.1f},{hi:+6.1f}]")

# ---- noise ceiling FIRST, at the game level -------------------------------------------------
CELLS = 14
bg = collections.defaultdict(list)
for r in R: bg[r["gid"]].append(r)
gk = list(bg)
peaks = []
for _ in range(3000):
    lab = {g: random.random() for g in gk}
    best_cell = -99
    for _ in range(CELLS):
        cut = random.random()
        pick = [x for g in gk if lab[g] < cut for x in bg[g]]
        if len(pick) >= 12:
            best_cell = max(best_cell, sc(pick)[3])
    if best_cell > -99: peaks.append(best_cell)
peaks.sort()
CEIL = peaks[int(len(peaks)*0.95)]
print("="*104)
print(f"  NOISE CEILING FIRST: {CELLS} random game-level splits of this same data reach")
print(f"  ROI {CEIL:+.1f}% at p95 by luck alone. Nothing below that number is a finding.")
print("="*104)
print("")

print("="*104)
print("  1. GAME CONTEXT")
print("="*104)
show(R, "  ALL Model S")
print("")
T = sorted(r["tot"] for r in R if r["tot"] is not None)
if len(T) >= 24:
    q1, q2 = T[len(T)//3], T[2*len(T)//3]
    show([r for r in R if r["tot"] is not None and r["tot"] <= q1], f"    game total LOW  (<= {q1:g})")
    show([r for r in R if r["tot"] is not None and q1 < r["tot"] <= q2], f"    game total MID  ({q1:g}-{q2:g})")
    show([r for r in R if r["tot"] is not None and r["tot"] > q2], f"    game total HIGH (> {q2:g})")
print("")
S = sorted(r["spr"] for r in R if r["spr"] is not None)
if len(S) >= 24:
    s1, s2 = S[len(S)//3], S[2*len(S)//3]
    show([r for r in R if r["spr"] is not None and r["spr"] <= s1], f"    spread TIGHT (<= {s1:g})")
    show([r for r in R if r["spr"] is not None and s1 < r["spr"] <= s2], f"    spread MID   ({s1:g}-{s2:g})")
    show([r for r in R if r["spr"] is not None and r["spr"] > s2], f"    spread WIDE  (> {s2:g}) - blowout risk")
print("")
fav = [r for r in R if r["ml"] is not None and ((r["ml"] > 0.5) == r["home"])]
dog = [r for r in R if r["ml"] is not None and ((r["ml"] > 0.5) != r["home"])]
show(fav, "    her team is the FAVOURITE")
show(dog, "    her team is the DOG")
print("")
show([r for r in R if r["home"]], "    she is at HOME")
show([r for r in R if not r["home"]], "    she is AWAY")
print("")

print("="*104)
print("  2. SAME-GAME STACKING - risk, not edge")
print("="*104)
cnt = collections.Counter(r["gid"] for r in R)
dist = collections.Counter(cnt.values())
print("  bets per game: " + ", ".join(f"{k} bet(s):{v} games" for k, v in sorted(dist.items())))
print("")
show([r for r in R if cnt[r["gid"]] == 1], "    lone bet in its game")
show([r for r in R if cnt[r["gid"]] == 2], "    one of 2 in the same game")
show([r for r in R if cnt[r["gid"]] >= 3], "    one of 3+ in the same game")
print("")
# pairwise agreement inside a game: same team vs opposing
same_t, opp_t = [], []
for g, rows in bg.items():
    for i in range(len(rows)):
        for j in range(i+1, len(rows)):
            a, b2 = rows[i], rows[j]
            agree = (a["won"] == b2["won"])
            (same_t if a["tm"] == b2["tm"] else opp_t).append(agree)
def agree(v, lbl):
    if len(v) < 8: print(f"  {lbl:<44} {len(v)} pairs - too few"); return
    p = sum(v)/len(v)
    se = math.sqrt(p*(1-p)/len(v))
    print(f"  {lbl:<44} {len(v):<4} pairs  both same result {100*p:5.1f}%  +/-{100*1.96*se:4.1f}")
print("  50% = independent. Above 50% = the bets move together and 1u each is more risk than it looks.")
agree(same_t, "    TEAMMATES (share possessions)")
agree(opp_t, "    OPPOSING sides (share only pace)")
print("")
print("="*104)
print("  3. THE STACKED NIGHTS THEMSELVES")
print("="*104)
for g, rows in sorted(bg.items(), key=lambda kv: -len(kv[1]))[:8]:
    if len(rows) < 2: continue
    d = rows[0]["date"]; tt = rows[0]["tot"]
    w = sum(1 for r in rows if r["won"])
    who = ", ".join(f"{r['pl'].split()[-1]}({r['tm']}){'W' if r['won'] else 'L'}" for r in rows)
    print(f"  {d}  total {tt if tt is not None else '   ?'}  {w}/{len(rows)}   {who}")
