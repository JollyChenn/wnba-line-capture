import csv,os,sys,collections,datetime
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=r"C:\Users\Axioo\wnba-line-capture"
def load(p):
    fp=os.path.join(D,p); 
    return list(csv.DictReader(open(fp,encoding="utf-8",errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except: return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except: return None
ALIAS={"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
 "janelle illona salaun":"janelle salaun","alexa held":"lexi held","valeriane vukosavljevic":"valeriane ayayi",
 "cheyenne parker":"cheyenne parker-tyus","xu han":"han xu"}
gm={}
for g in load("data/games_2026.csv"):
    t=ts(g.get("tip"))
    if t: gm[g["game_id"]]=(g.get("date",""),t,g.get("home"),g.get("away"))
teamof={}
for r in load("data/box_2026.csv"):
    if r.get("game_id") in gm: teamof[(r.get("player") or "").lower()]=r.get("team")
tips_of=collections.defaultdict(list)
gid_of={}
for gid,(dt,tp,hm,aw) in gm.items():
    tips_of[hm].append(tp); tips_of[aw].append(tp); gid_of[(hm,tp)]=gid; gid_of[(aw,tp)]=gid
for v in tips_of.values(): v.sort()
def game_for(tm,when):
    for t in tips_of.get(tm,[]):
        if when<=t and (t-when).total_seconds()<=60*3600: return t
    return None
pg=set(); gset=set(); dates=set(); gids=set()
nrow=0
for b in load("xbet_board.csv"):
    pl=(b.get("player") or "").lower()
    if pl not in ALIAS: continue
    nrow+=1
    can=ALIAS[pl]; tm=teamof.get(can); t=ts(b.get("captured_utc"))
    if not tm or not t: continue
    g2=game_for(tm,t)
    if not g2: continue
    pg.add((can,g2)); gset.add(g2); gids.add(gid_of.get((tm,g2)))
    dates.add(gm[gids and gid_of[(tm,g2)]][0] if (tm,g2) in gid_of else "")
print("rows for the 8:",nrow)
print("distinct player-game pairs:",len(pg))
print("distinct tip timestamps:",len(gset))
print("distinct game_ids:",len(gids))
print("distinct slate dates:",len(dates))
# capture-day count
cd={ (b.get("captured_utc") or "")[:10] for b in load("xbet_board.csv") if (b.get("player") or "").lower() in ALIAS}
print("distinct capture dates:",len(cd))
