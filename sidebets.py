# sidebets.py - a Model S bet says the book mispriced ONE player. Did it misprice her GAME?
# ---------------------------------------------------------------------------------------------
# The idea: our signal is "the book cut this line too far". Books do not usually make one isolated
# error - a stale median, a missed injury or a pace assumption leaks across the whole game sheet.
# If so, a Model S bet is a flag on the GAME, and the other props in that game are exploitable too.
#
# Three groups, every one priced from real two-sided board quotes (never 1/over):
#   OPPONENT   players on the other team, both sides. Never tested before.
#   TEAMMATES  her own team-mates, both sides. Tested once, on a different construction.
#   HERSELF    her other markets - the gate-4 discards, for completeness.
#
# THE CONTROL IS THE WHOLE EXPERIMENT. Opponent unders might return +5% in Model S games and also
# +5% in every other game, in which case Model S told us nothing and we have just rediscovered a
# board-wide bias. So every number below is reported against the SAME measurement taken in games
# with no Model S bet at all. The gap between them is the only thing that counts.
#
# Prices: mean board margin is 7.4%, so a side needs roughly 53.8% to break even. Any hit rate
# quoted below should be read against that, not against 50%.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260819)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS = ("flip", "hotover", "overshoot"); BET_MKTS = ("pra", "pr", "pts")
ALLMK = ("pts", "pr", "pra", "pa", "ra", "reb", "ast")

tip_on, gof, oppof = {}, {}, {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    tip_on[(hm, d2)] = t2; tip_on[(aw, d2)] = t2
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid
    oppof[(hm, t2)] = aw; oppof[(aw, t2)] = hm

# ---- where did Model S fire? ----------------------------------------------------------------
MS = {}
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt)); sdq = side.get((pl, mk, gt), {})
    if not now or "Over" not in sdq: continue
    ln = sdq["Over"][1]
    pv = prevline.get((pl, mk, gt))
    if pv is None or ln - pv >= 0.5 or now[mk] == ln: continue
    MS[(pl, gt)] = dict(tm=tm, mk=mk, won=now[mk] > ln)
msgames = {gt for (_, gt) in MS}
msteam = collections.defaultdict(set)
for (pl, gt), d in MS.items(): msteam[gt].add(d["tm"])
print(f"Model S fired in {len(msgames)} games, on {len(MS)} players")

# ---- every two-sided quote on the board, tagged by its relationship to a Model S bet ---------
Q = []
for (pl, mk, gt), sdq in side.items():
    if mk not in ALLMK or "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1] - sdq["Under"][1]) > 0.01: continue
    now = pgrow.get((pl, gt))
    if not now or mk not in now: continue
    ln = sdq["Over"][1]
    if now[mk] == ln: continue
    tm = teamof.get(pl)
    if not tm: continue
    if (pl, gt) in MS: rel = "herself"
    elif gt in msgames and tm in msteam[gt]: rel = "teammate"
    elif gt in msgames: rel = "opponent"
    else: rel = "no signal in this game"
    Q.append(dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], tm=tm, rel=rel, ln=ln,
                  o_od=sdq["Over"][2], u_od=sdq["Under"][2],
                  o_won=now[mk] > ln, u_won=now[mk] < ln))
print(f"{len(Q)} two-sided board quotes gradable")
print("  " + ", ".join(f"{k}:{v}" for k, v in collections.Counter(r["rel"] for r in Q).items()))
print("")

def sc(rows, wk, ok):
    n = len(rows); w = sum(1 for r in rows if r[wk])
    u = sum((r[ok]-1) if r[wk] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def gboot(rows, wk, ok, T=2500):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(100*sum((x[ok]-1) if x[wk] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, wk, ok, minn=25):
    if len(rows) < minn: print(f"    {lbl:<44} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows, wk, ok); lo, hi = gboot(rows, wk, ok)
    star = "  <<<" if lo > 0 else ""
    print(f"    {lbl:<44} n={n:<5}{h:>6.1f}%{u:>+9.2f}u{ro:>+8.1f}%  95CI [{lo:+6.1f},{hi:+6.1f}]{star}")

print("="*112)
print("  1. THE THREE GROUPS vs THE CONTROL - both sides, all markets")
print("="*112)
for rel in ("opponent", "teammate", "herself", "no signal in this game"):
    g = [r for r in Q if r["rel"] == rel]
    print(f"  {rel.upper()}   ({len(g)} quotes)")
    show(g, "OVER", "o_won", "o_od")
    show(g, "UNDER", "u_won", "u_od")
    print("")
print("  the control row is what the board does anyway. a group only matters if it BEATS it.")
print("")
print("="*112)
print("  2. OPPONENT, BROKEN DOWN - where would it hide if it were there?")
print("="*112)
OPP = [r for r in Q if r["rel"] == "opponent"]
CTL = [r for r in Q if r["rel"] == "no signal in this game"]
print("  by market:")
for m in ALLMK:
    a = [r for r in OPP if r["mk"] == m]; c = [r for r in CTL if r["mk"] == m]
    if len(a) < 25: continue
    _, ah, _, aro = sc(a, "u_won", "u_od"); _, ch, _, cro = sc(c, "u_won", "u_od")
    _, ah2, _, aro2 = sc(a, "o_won", "o_od"); _, ch2, _, cro2 = sc(c, "o_won", "o_od")
    print(f"    {m:<5} UNDER n={len(a):<5}{aro:+7.1f}%  (control {cro:+6.1f}%, gap {aro-cro:+6.1f})"
          f"   OVER {aro2:+7.1f}%  (control {cro2:+6.1f}%, gap {aro2-cro2:+6.1f})")
print("")
print("  by whether OUR bet won - not actionable, but it says if the games differ at all:")
for lbl, sel in (("our bet WON",  lambda r: any(MS[(p, g)]["won"] for (p, g) in MS if g == r["gt"])),
                 ("our bet LOST", lambda r: not any(MS[(p, g)]["won"] for (p, g) in MS if g == r["gt"]))):
    g = [r for r in OPP if sel(r)]
    show(g, lbl + ": opponent UNDER", "u_won", "u_od")
print("")
print("="*112)
print("  3. THE STRONGEST VERSION - opponent props when the signal was OVERSHOOT specifically")
print("="*112)
osgames = {gt for (pl, gt), d in MS.items() if True}
strong = {gt for (pl, gt) in MS if MS[(pl, gt)]["mk"] in ("pra", "pr")}
g = [r for r in OPP if r["gt"] in strong]
show(g, "opponent UNDER, PRA/PR-signal games", "u_won", "u_od")
show(g, "opponent OVER,  PRA/PR-signal games", "o_won", "o_od")
print("")
print("="*112)
print("  4. HOW MANY EXTRA BETS WOULD ANY OF THIS BE?")
print("="*112)
sl = len({r["gt"] for r in Q})
print(f"  opponent quotes per Model S game: {len(OPP)/max(len(msgames),1):.1f}")
print(f"  if even a tenth were bettable that is {len(OPP)/max(len(msgames),1)/10:.1f} extra bets a game -")
print("  which is why this was worth testing even though the prior was not strong.")
