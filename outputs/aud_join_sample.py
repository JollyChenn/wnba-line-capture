import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(D)

def rd(p):
    with open(p, encoding="utf-8") as fh: return list(csv.DictReader(fh))

board = rd(os.path.join(R,"xbet_board.csv"))
box   = rd(os.path.join(R,"data","box_2026.csv"))
games = rd(os.path.join(R,"data","games_2026.csv"))
print("board rows", len(board), "box rows", len(box))
print("games cols", list(games[0].keys())[:12])

boxnames = set(r["player"].strip().lower() for r in box)
# player -> set of game_ids in box
boxg = collections.defaultdict(set)
for r in box: boxg[r["player"].strip().lower()].add(r["game_id"])

cnt = collections.Counter(r["player"].strip().lower() for r in board)
fail = {k:v for k,v in cnt.items() if k not in boxnames}
print("\ndistinct board names", len(cnt), " failing", len(fail),
      " failing rows", sum(fail.values()),
      " pct of board rows %.2f%%" % (100*sum(fail.values())/len(board)))
for k,v in sorted(fail.items(), key=lambda x:-x[1]):
    print("  %-28s %5d" % (k,v))
