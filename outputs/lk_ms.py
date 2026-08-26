import csv,os,sys,collections,datetime,statistics,math,random
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
D=r"C:\Users\Axioo\wnba-line-capture"
def load(p):
    fp=os.path.join(D,p)
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
CAN=set(ALIAS.values())
ALL_MK=("pts","pra","pr","pa","reb","ast","ra")
gm={}
for g in load("data/games_2026.csv"):
    t=ts(g.get("tip"))
    if t: gm[g["game_id"]]=(g.get("date",""),t,g.get("home"),g.get("away"))
pgrow={}; teamof={}; gcount=collections.Counter()
for r in load("data/box_2026.csv"):
    gid=r.get("game_id")
    if gid not in gm: continue
    dt,tp,hm,aw=gm[gid]
    pl=(r.get("player") or "").lower()
    p_=f(r.get("pts")) or 0; rb=f(r.get("reb")) or 0; a=f(r.get("ast")) or 0
    pgrow[(pl,tp)]=dict(tm=r.get("team"),date=dt,pts=p_,reb=rb,ast=a,pra=p_+rb+a,pr=p_+rb,pa=p_+a,ra=rb+a,min=f(r.get("min")) or 0)
    teamof[pl]=r.get("team"); gcount[pl]+=1
print("box games for the 8:", {p:gcount[p] for p in CAN}, "sum:", sum(gcount[p] for p in CAN))
hist=collections.defaultdict(list)
for (pl,tp),row in pgrow.items(): hist[pl].append((tp,row))
for v in hist.values(): v.sort()
tips_of=collections.defaultdict(list)
for gid,(dt,tp,hm,aw) in gm.items(): tips_of[hm].append(tp); tips_of[aw].append(tp)
for v in tips_of.values(): v.sort()
def game_for(tm,when):
    for t in tips_of.get(tm,[]):
        if when<=t and (t-when).total_seconds()<=60*3600: return t
    return None
raw=collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t,o,ln=ts(b.get("captured_utc")),f(b.get("odds")),f(b.get("line"))
    pl=ALIAS.get((b.get("player") or "").lower(),(b.get("player") or "").lower())
    if t and o and ln is not None and b.get("market") in ALL_MK:
        raw[(pl,b.get("market"),b.get("side"),ln)].append((t,o))
side=collections.defaultdict(dict); lines_seen=collections.defaultdict(list)
for (pl,mk,sd,ln),v in raw.items():
    tm=teamof.get(pl)
    if not tm: continue
    for t,o in sorted(v):
        g2=game_for(tm,t)
        if not g2: continue
        cur=side[(pl,mk,g2)].get(sd)
        if cur is None or t>cur[0]: side[(pl,mk,g2)][sd]=(t,ln,o)
        if sd=="Over": lines_seen[(pl,mk)].append((g2,ln))
prevline={}
for (pl,mk),v in lines_seen.items():
    lastof={}
    for g2,ln in v: lastof[g2]=ln
    gs=sorted(lastof)
    for i in range(1,len(gs)): prevline[(pl,mk,gs[i])]=lastof[gs[i-1]]

# Model S proxy: market in (pra,pr,pts), line NOT raised >=0.5 vs prev game, bet OVER, one per player-game
# priced at the board's LAST Over quote (harshest: also test with 2c slippage on decimal odds)
def roi(rows,slip=0.0,missrate=0.0):
    st=0.0; pl_=0.0; n=0
    for (won,dec) in rows:
        d=max(1.01,dec-slip)
        n+=1; st+=1; pl_+= (d-1) if won else -1
    return n,(pl_/st*100 if st else 0)
res={"wilson":[], "eight":[], "rest":[]}
for (pl,mk,g2),v in side.items():
    if mk not in ("pra","pr","pts"): continue
    if "Over" not in v: continue
    t,ln,o=v["Over"]
    pv=prevline.get((pl,mk,g2))
    if pv is None or ln-pv>=0.5: continue
    row=pgrow.get((pl,g2))
    if not row: continue
    act=row[mk]
    won = act>ln
    if act==ln: continue
    key="wilson" if pl=="a'ja wilson" else ("eight" if pl in CAN else "rest")
    res[key].append((won,o,pl,g2,mk))
for k in ("wilson","eight","rest"):
    rows=[(w,o) for (w,o,_,_,_) in res[k]]
    n,r=roi(rows)
    n2,r2=roi(rows,slip=0.02)
    gcnt=len({(g) for (_,_,_,g,_) in res[k]})
    wins=sum(1 for w,_ in rows if w)
    se=100*math.sqrt(max(r/100+1,0.0001)) if False else 0
    print("%-7s n=%4d games=%3d hit=%.1f%% ROI=%+.1f%%  ROI(-2c)=%+.1f%%"%(k,n,gcnt,100*wins/max(n,1),r,r2))
