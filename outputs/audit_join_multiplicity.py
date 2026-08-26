import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except: return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except: return None

ALL_MK = ("pts","pra","pr","pa","reb","ast","ra")
board = load("xbet_board.csv")
box   = load("data/box_2026.csv")
games = load("data/games_2026.csv")
print("board rows total:", len(board))
print("box rows:", len(box), " games rows:", len(games))

teamof = {}
boxnames = collections.Counter()
for r in box:
    pl = (r.get("player") or "").lower()
    teamof[pl] = r.get("team"); boxnames[pl]+=1

# unresolved board player strings
unres = collections.Counter()
res = 0
for b in board:
    pl = (b.get("player") or "").lower()
    if pl in teamof: res += 1
    else: unres[pl]+=1
print("\nresolved rows:", res, " unresolved rows:", sum(unres.values()),
      " pct:", round(100*sum(unres.values())/len(board),2))
print("distinct unresolved strings:", len(unres))
for nm,c in unres.most_common(30): print(f"   {c:6d}  {nm!r}")
