# shadow_backfill.py - replay shadow_log for slates missed while the laptop was off.
# ---------------------------------------------------------------------------------------------
# THE PROBLEM. shadow_log only records a bet while NOW < tip, so any slate that passed with the
# machine asleep is absent from shadow_forward.csv forever. That is not a cosmetic gap: the whole
# point of the file is to compare configs on the SAME bets, and a missing slate removes different
# bets from different configs. On 2026-08-23 the live tracker held 16 Model S bets and the shadow
# held 6 - and the surviving 6 happened to skew winning, making MODEL_S read +58% against its real
# +5.9%. Every scoreboard number was quietly wrong in the flattering direction.
#
# THE FIX, AND ITS LIMIT. This calls shadow_log.py --asof <one hour before the slate's first tip>.
# In that mode every source is capped at the as-of moment: the board, bets_log, the sharp lines
# and the box-score history. So the rows record what the rule WOULD HAVE SELECTED with only the
# information that existed then.
#
# What it cannot restore is that we were awake. A backfilled row proves selection, not execution,
# so rows are stamped backfill=1 and grade_shadow prints live and replayed populations separately.
# If the replayed set ever looks much better than the live one, the cap is leaking and the replay
# is not to be trusted - that comparison is built into the scoreboard deliberately.
#
#   python shadow_backfill.py            # replay every missing settled slate
#   python shadow_backfill.py 2026-08-19 # one slate
import csv, os, sys, subprocess, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
NOW = datetime.datetime.now(datetime.timezone.utc)

# every slate that has actually been played, keyed the way shadow_log names them
games = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t and (g.get("home_score") or "").strip(): games[g.get("date")].append(t)
played = {d: min(v) for d, v in games.items() if v}

# a slate counts as covered if shadow_forward already holds ANY row for it
have = collections.Counter()
for r in load("shadow_forward.csv"):
    have[(r.get("slate") or "").replace("-", "")] += 1

want = sys.argv[1].replace("-", "") if len(sys.argv) > 1 else None
todo = []
for d, first in sorted(played.items()):
    if want and d != want: continue
    if not want and have.get(d): continue
    if first > NOW: continue
    todo.append((d, first))
if not todo:
    print("  backfill: nothing missing - every played slate already has shadow rows")
    raise SystemExit
print(f"  backfill: {len(todo)} slate(s) to replay -> " + ", ".join(d for d, _ in todo))
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
for d, first in todo:
    asof = (first - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # WINDOW_H must be wide enough to still see this slate's games from one hour before the
    # earliest tip; 16h is the live default and covers a full slate comfortably.
    r = subprocess.run([sys.executable, os.path.join(D, "shadow_log.py"), "--asof", asof, "16"],
                       cwd=D, env=env, capture_output=True, text=True, timeout=600)
    out = (r.stdout or "").strip().splitlines()
    tail = out[-1] if out else (r.stderr or "").strip().splitlines()[-1:] or ["no output"]
    print(f"    {d}  asof {asof}  ->  {tail if isinstance(tail, str) else tail}")
print("")
print("  now run: python grade_shadow.py   (it will settle the replayed rows and show the")
print("  live-vs-backfilled split - if backfill looks much better, the cap is leaking)")
