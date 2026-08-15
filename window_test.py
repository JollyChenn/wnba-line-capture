# window_test.py - the real latency question: not how OFTEN we look, but how EARLY we alert.
# ---------------------------------------------------------------------------------------------
# Lines take a median of 8 hours to move, so loop cadence is nearly irrelevant. But the card only
# considers games inside a 16h window, while 1xbet posts lines up to 48h out. If the number we
# want is on the board 30h before tip and we do not look at it until 16h before, we are choosing
# to be late by 14 hours - which is a completely different problem from the loop being slow.
import csv, os, sys, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

MKTS = ("pra", "pr", "pts")
gm, tip_of = {}, {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t:
        tip_of[g["home"]] = tip_of.get(g["home"], []) + [t]
        tip_of[g["away"]] = tip_of.get(g["away"], []) + [t]
team = {}
gd = {g.get("game_id"): g.get("date","") for g in load("data/games_2026.csv")}
for r in load("data/box_2026.csv"):
    if gd.get(r.get("game_id")): team[(r.get("player") or "").lower()] = r.get("team")

q = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, ln, o = ts(b.get("captured_utc")), f(b.get("line")), f(b.get("odds"))
    if t and ln is not None and o and b.get("market") in MKTS and b.get("side") == "Over":
        q[((b.get("player") or "").lower(), b.get("market"))].append((t, ln, o))

rows = []
for (pl, mk), v in q.items():
    v.sort()
    cur = [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600:
            cur = []
        cur.append(b_)
        if len(cur) < 2: continue
    # rebuild blocks properly
for (pl, mk), v in q.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
    blocks.append(cur)
    tm = team.get(pl)
    if not tm: continue
    for blk in blocks:
        if len(blk) < 2: continue
        t0 = blk[0][0]
        tips = [t for t in tip_of.get(tm, []) if 0 < (t - t0).total_seconds() < 72*3600]
        if not tips: continue
        tip = min(tips)
        lead = (tip - t0).total_seconds()/3600
        def line_at(hrs_before):
            cutoff = tip - datetime.timedelta(hours=hrs_before)
            got = [x for x in blk if x[0] <= cutoff]
            return got[-1] if got else None
        first = blk[0]
        at16 = line_at(16)
        if at16 is None: continue
        rows.append(dict(pl=pl, mk=mk, lead=lead, first_ln=first[1], first_od=first[2],
                         ln16=at16[1], od16=at16[2]))

print(f"{len(rows)} player-market nights where the board appeared before the 16h mark")
print("")
leads = sorted(r["lead"] for r in rows)
print("  how far ahead of tip does 1xbet first post the line?")
for pct in (10, 25, 50, 75, 90):
    print(f"    p{pct:<3} {leads[int(len(leads)*pct/100)]:6.1f} h before tip")
print("")
print("="*94)
print("  THE LINE YOU COULD HAVE HAD (first quote) vs THE LINE OUR 16h WINDOW SHOWS YOU")
print("="*94)
better = worse = same = 0
dl = []
for r in rows:
    d = r["ln16"] - r["first_ln"]
    dl.append(d)
    if d > 0: worse += 1          # line went UP by the time we look -> worse for an over
    elif d < 0: better += 1
    else: same += 1
n = len(rows)
print(f"  line UNCHANGED by the 16h mark   {same:>5}  ({100*same/n:4.1f}%)")
print(f"  line HIGHER  (we lost value)     {worse:>5}  ({100*worse/n:4.1f}%)   mean +{sum(x for x in dl if x>0)/max(worse,1):.2f}")
print(f"  line LOWER   (we gained)         {better:>5}  ({100*better/n:4.1f}%)   mean {sum(x for x in dl if x<0)/max(better,1):.2f}")
print(f"  net across all: {sum(dl)/n:+.3f} of a point ({'we LOSE' if sum(dl)>0 else 'we GAIN'} by waiting for the 16h window)")
print("")
print("  ...so widening the alert window would " +
      ("HELP - we are systematically arriving after the number moved up." if sum(dl)/n > 0.05
       else "NOT help much - the line is not systematically worse at 16h."))
