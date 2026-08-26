import csv,os,sys,datetime,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=os.path.dirname(os.path.abspath(__file__)); R=os.path.dirname(D)
def rd(p):
    with open(p,encoding="utf-8") as fh: return list(csv.DictReader(fh))
board=rd(os.path.join(R,"xbet_board.csv")); box=rd(os.path.join(R,"data","box_2026.csv")); games=rd(os.path.join(R,"data","games_2026.csv"))
RES={"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
 "janelle illona salaun":"janelle salaun","alexa held":"lexi held",
 "valeriane vukosavljevic":"valeriane ayayi","cheyenne parker":"cheyenne parker-tyus","xu han":"han xu"}
gm={g["game_id"]:g for g in games}
def dt(s):
    s=(s or "").replace("Z","+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None
plg=collections.defaultdict(list)
for r in box:
    g=gm.get(r["game_id"]);
    if g and dt(g["tip"]): plg[r["player"].strip().lower()].append((dt(g["tip"]),r["game_id"]))
for k in plg: plg[k].sort()
for W in (24,30,48,72,120):
    gs=set(); pg=set()
    for r in board:
        p=r["player"].strip().lower()
        if p not in RES: continue
        c=dt(r["captured_utc"])
        for t,gid in plg.get(RES[p],[]):
            h=(t-c).total_seconds()/3600
            if -3<=h<=W: gs.add(gid); pg.add((RES[p],gid)); break
    print("window %3dh -> distinct games %3d  player-games %3d"%(W,len(gs),len(pg)))
# same-DATE join (loosest reasonable)
gd={g["game_id"]:g["date"] for g in games}
bydate=collections.defaultdict(set)
for r in box: bydate[(r["player"].strip().lower(),gd.get(r["game_id"]))].add(r["game_id"])
gs=set(); pg=set()
for r in board:
    p=r["player"].strip().lower()
    if p not in RES: continue
    d=r["captured_utc"][:10]
    for dd in (d,(datetime.date.fromisoformat(d)+datetime.timedelta(days=1)).isoformat()):
        for gid in bydate.get((RES[p],dd),()): gs.add(gid); pg.add((RES[p],gid))
print("same-date/+1d -> distinct games %d  player-games %d"%(len(gs),len(pg)))
