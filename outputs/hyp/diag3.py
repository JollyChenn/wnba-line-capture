import csv,os,sys,collections
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows=list(csv.DictReader(open(os.path.join(R,"elo_model","plays_full.csv"),encoding="utf-8")))
n=0
for r in rows:
    if r["type_id"]=="584":
        print(repr(r["text"]), r["team_id"], r["period"], r["clock"]); n+=1
        if n>8: break
# how many games have subs
g=collections.defaultdict(int)
for r in rows:
    if r["type_id"]=="584": g[r["game_id"]]+=1
print("games with subs:",len(g), "median subs/game", sorted(g.values())[len(g)//2])
