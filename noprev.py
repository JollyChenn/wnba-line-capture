# noprev.py - Tiffany Hayes is on tonight's card in the DO-NOT-BET box. How bad is that group?
# ---------------------------------------------------------------------------------------------
# She looks like the best thing on the card: overshoot, PRA 14.5 against a 10-game median of 18.0,
# priced at 2.00 (+11.1% over fair). The only reason she is screened out is that gate 3 cannot be
# EVALUATED on her - she has no line in her previous game to compare tonight's number against.
#
# That is an honest reason to skip, but it is not the same as evidence she loses. So measure it.
# The card's footnote quotes n=64, ROI -10.0%, which came from the OPENING-line construction that
# basis_check.py retired. Rebuild it the card's way - price and gate both at the ping - and report
# whatever the sample actually supports, including "too few".
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
    gof[(hm, t2)] = gid; gof[(aw, t2)] = gid

ROWS = []
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN", "LOSS"): continue
    src, mk, pl = (r.get("src") or ""), (r.get("market") or ""), (r.get("player") or "").lower()
    if src not in SIGS or mk not in BET_MKTS: continue
    tm = teamof.get(pl)
    gt = tip_on.get((tm, r.get("date") or "")) if tm else None
    if not gt: continue
    now = pgrow.get((pl, gt))
    if not now: continue
    q = seq.get((pl, mk, gt), [])
    pv = prevline.get((pl, mk, gt))
    o_ln, o_od = f(r.get("line")), f(r.get("odds"))
    row = dict(pl=pl, mk=mk, gt=gt, gid=gof[(tm, gt)], date=r.get("date"), src=src,
               noprev=(pv is None), o_ln=o_ln, o_od=o_od, o_w=(o_ln is not None and now[mk] > o_ln))
    if len(q) >= 2:
        p_t, p_l, p_o = q[-1]
        if now[mk] != p_l:
            row.update(p_l=p_l, p_o=p_o, p_w=now[mk] > p_l,
                       raised=(pv is not None and p_l - pv >= 0.5))
    ROWS.append(row)

def dedupe(rows, ok):
    best = {}
    for r in sorted(rows, key=lambda x: -(x.get(ok) or 0)): best.setdefault((r["pl"], r["gt"]), r)
    return list(best.values())
def sc(rows, wk, ok):
    n = len(rows); w = sum(1 for r in rows if r[wk])
    u = sum((r[ok]-1) if r[wk] else -1.0 for r in rows)
    return n, 100*w/n, u, 100*u/n
def gboot(rows, wk, ok, T=3000):
    bg = collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k = list(bg); o = []
    for _ in range(T):
        g = [x for p in [random.choice(k) for _ in k] for x in bg[p]]
        o.append(100*sum((x[ok]-1) if x[wk] else -1.0 for x in g)/len(g))
    o.sort(); return o[int(T*.025)], o[int(T*.975)]
def show(rows, lbl, wk, ok, minn=10):
    rows = [r for r in rows if wk in r and r.get(ok)]
    if len(rows) < minn: print(f"  {lbl:<48} n={len(rows)} too few"); return
    n, h, u, ro = sc(rows, wk, ok); lo, hi = gboot(rows, wk, ok)
    print(f"  {lbl:<48} n={n:<4}{h:>6.1f}%{u:>+8.2f}u{ro:>+8.1f}%   95CI [{lo:+6.1f},{hi:+6.1f}]")

print("="*104)
print("  THE NO-PREVIOUS-LINE GROUP, both constructions")
print("="*104)
NP = [r for r in ROWS if r["noprev"]]
HV = [r for r in ROWS if not r["noprev"]]
print("  OPENING line (the construction the card's -10.0% footnote came from)")
show(dedupe(NP, "o_od"), "    no previous line", "o_w", "o_od")
show(dedupe(HV, "o_od"), "    has a previous line", "o_w", "o_od")
print("")
print("  PING line, gate 3 at the ping (what the card actually does)")
show(dedupe([r for r in NP if "p_w" in r], "p_o"), "    no previous line", "p_w", "p_o")
show(dedupe([r for r in HV if "p_w" in r and not r.get("raised")], "p_o"),
     "    has a previous line AND not raised = MODEL S", "p_w", "p_o")
print("")
print("="*104)
print("  WHY THE SAMPLE SHRANK - no previous line means thin board history by definition")
print("="*104)
print(f"  no-prev rows in graded_bets            : {len(dedupe(NP,'o_od'))}")
print(f"  of those with 2+ board quotes tonight  : {len(dedupe([r for r in NP if 'p_w' in r],'p_o'))}")
print("")
print("  a player with no line in her last game usually has few quotes in this one too - she is new")
print("  to the board. So the group the card screens out is the group we can measure least well.")
print("")
print("="*104)
print("  IS IT THE MISSING GATE, OR IS IT THE PLAYERS?")
print("="*104)
npl = {r["pl"] for r in NP}
print(f"  distinct players with a no-prev bet: {len(npl)}")
mult = collections.Counter(r["pl"] for r in NP)
print(f"  appearing more than once: {sum(1 for v in mult.values() if v > 1)}")
print(f"  top: " + ", ".join(f"{p}({c})" for p, c in mult.most_common(6)))
