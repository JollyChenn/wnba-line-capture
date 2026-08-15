# line_speed.py - HOW FAST does a line move after it first appears? This decides the loop cadence.
# ---------------------------------------------------------------------------------------------
# The user saw a card, went to bet it, and the number had already gone up. That is the 4.7pp we
# measured as the cost of betting late, arriving as a real missed bet. The question is not "is
# faster better" - obviously it is - it is "how much of the move happens in the first N minutes",
# because that determines whether a 30-min loop is losing us anything a 10-min loop would catch.
import csv, os, sys, datetime, collections, statistics
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
# every (player, market) night: the full sequence of (time, line) the board showed
q = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, ln, o = ts(b.get("captured_utc")), f(b.get("line")), f(b.get("odds"))
    if t and ln is not None and o and b.get("market") in MKTS and b.get("side") == "Over":
        q[((b.get("player") or "").lower(), b.get("market"))].append((t, ln, o))

nights = []
for k, v in q.items():
    v.sort()
    cur = [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600:
            nights.append((k, cur)); cur = []
        cur.append(b_)
    nights.append((k, cur))

moved_at, never = [], 0
first_move_dir = collections.Counter()
for k, seq in nights:
    if len(seq) < 2: continue
    t0, l0, o0 = seq[0]
    mv = next(((t, ln) for (t, ln, o) in seq if ln != l0), None)
    if mv is None:
        never += 1; continue
    mins = (mv[0]-t0).total_seconds()/60
    moved_at.append(mins)
    first_move_dir["UP (worse for our overs)" if mv[1] > l0 else "DOWN (better)"] += 1

tot = len(moved_at) + never
print(f"{tot} player-market nights with a live board series")
print(f"  line NEVER moved      {never:>5}  ({100*never/tot:4.1f}%)")
print(f"  line moved at least 1x {len(moved_at):>4}  ({100*len(moved_at)/tot:4.1f}%)")
print("")
print("  when it moved, which way first:")
for k, v in first_move_dir.most_common():
    print(f"    {k:<28} {v:>5}  ({100*v/len(moved_at):4.1f}%)")
print("")
print("="*88)
print("  HOW LONG FROM FIRST QUOTE TO FIRST LINE MOVE")
print("="*88)
moved_at.sort()
for pct in (10, 25, 50, 75, 90):
    print(f"  p{pct:<3} {moved_at[int(len(moved_at)*pct/100)]:8.0f} min")
print("")
print("  share of all line moves that happen within N minutes of the line appearing:")
for cut in (10, 15, 30, 60, 120, 240, 480):
    n = sum(1 for m in moved_at if m <= cut)
    print(f"    within {cut:>4} min   {n:>5} / {len(moved_at)}  = {100*n/len(moved_at):4.1f}%")
print("")
print("="*88)
print("  WHAT A FASTER LOOP WOULD ACTUALLY BUY")
print("="*88)
print("  A loop at cadence N can be up to N minutes stale. The bets we LOSE to a line move are")
print("  the ones that move within N minutes of first appearing - we would never have shown them")
print("  at the good number anyway.")
for cad in (30, 20, 15, 10, 5):
    n = sum(1 for m in moved_at if m <= cad)
    print(f"    loop every {cad:>2} min  ->  {100*n/len(moved_at):4.1f}% of moves happen inside the blind window")
