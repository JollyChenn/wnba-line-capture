import csv,os,sys,collections,datetime,statistics
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
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
ALL_MK=("pts","pra","pr","pa","reb","ast","ra")
ALIAS={"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
 "janelle illona salaun":"janelle salaun","alexa held":"lexi held","valeriane vukosavljevic":"valeriane ayayi",
 "cheyenne parker":"cheyenne parker-tyus","xu han":"han xu"}

gm={}; 
for g in load("data/games_2026.csv"):
    t=ts(g.get("tip"))
    if t: gm[g["game_id"]]=(g.get("date",""),t,g.get("home"),g.get("away"))
pgrow={}; teamof={}; use=collections.defaultdict(float); gcount=collections.Counter()
tot_use=0.0
for r in load("data/box_2026.csv"):
    gid=r.get("game_id")
    if gid not in gm: continue
    dt,tp,hm,aw=gm[gid]
    pl=(r.get("player") or "").lower()
    u=(f(r.get("fga")) or 0)+0.44*(f(r.get("fta")) or 0)+(f(r.get("to")) or 0)
    p_=f(r.get("pts")) or 0; rb=f(r.get("reb")) or 0; a=f(r.get("ast")) or 0
    pgrow[(pl,tp)]=dict(tm=r.get("team"),pts=p_,reb=rb,ast=a,pra=p_+rb+a,pr=p_+rb,pa=p_+a,ra=rb+a,min=f(r.get("min")) or 0,use=u)
    teamof[pl]=r.get("team"); use[pl]+=u; gcount[pl]+=1; tot_use+=u
tips_of=collections.defaultdict(list)
for gid,(dt,tp,hm,aw) in gm.items(): tips_of[hm].append(tp); tips_of[aw].append(tp)
for v in tips_of.values(): v.sort()
def game_for(tm,when):
    for t in tips_of.get(tm,[]):
        if when<=t and (t-when).total_seconds()<=60*3600: return t
    return None

# usage rank
rank=sorted(((use[p]/max(gcount[p],1),use[p],p) for p in use),key=lambda x:-x[1])
print("TOP 10 by TOTAL usage:")
for i,(pg,tu,p) in enumerate(rank[:10],1): print("  %2d %-26s tot=%7.1f perG=%5.2f g=%d"%(i,p,tu,pg,gcount[p]))
rk2=sorted(((use[p]/gcount[p],p) for p in use if gcount[p]>=10),key=lambda x:-x[0])
print("TOP 10 by PER-GAME usage (>=10 g):")
for i,(pg,p) in enumerate(rk2[:10],1): print("  %2d %-26s perG=%5.2f g=%d"%(i,p,pg,gcount[p]))

# build two-sided gradable quote sets: baseline (exact) vs patched (alias)
def build(alias):
    raw=collections.defaultdict(list)
    for b in load("xbet_board.csv"):
        t,o,ln=ts(b.get("captured_utc")),f(b.get("odds")),f(b.get("line"))
        pl=(b.get("player") or "").lower()
        if alias: pl=ALIAS.get(pl,pl)
        if t and o and ln is not None and b.get("market") in ALL_MK:
            raw[(pl,b.get("market"),b.get("side"),ln)].append((t,o))
    side=collections.defaultdict(dict)
    for (pl,mk,sd,ln),v in raw.items():
        tm=teamof.get(pl)
        if not tm: continue
        for t,o in sorted(v):
            g2=game_for(tm,t)
            if not g2: continue
            cur=side[(pl,mk,g2)].get(sd)
            if cur is None or t>cur[0]: side[(pl,mk,g2)][sd]=(t,ln,o)
    # gradable = both sides AND box row exists
    grad=[k for k,v in side.items() if "Over" in v and "Under" in v and (k[0],k[2]) in pgrow]
    return side,grad
s0,g0=build(False); s1,g1=build(True)
print("\nGRADABLE two-sided quotes: exact-join=%d  alias-patched=%d  delta=%d (+%.1f%%)"%(len(g0),len(g1),len(g1)-len(g0),100*(len(g1)-len(g0))/len(g0)))
newq=[k for k in g1 if k not in set(g0)]
print("games touched by recovered quotes:",len({k[2] for k in newq}))
byp=collections.Counter(k[0] for k in newq)
for p,c in byp.most_common(): print("   %-26s %d gradable quotes"%(p,c))
# board rows for the 8 -> distinct games
rows=collections.defaultdict(set)
for b in load("xbet_board.csv"):
    pl=(b.get("player") or "").lower()
    if pl in ALIAS:
        t=ts(b.get("captured_utc")); tm=teamof.get(ALIAS[pl])
        if t and tm:
            g2=game_for(tm,t)
            if g2: rows[ALIAS[pl]].add(g2)
allg=set()
for p,s in rows.items(): allg|=s
print("distinct games covered by the 8 unresolved names' board rows:",len(allg))

# Wilson share of the recovered set
w=[k for k in newq if k[0]=="a'ja wilson"]
print("a'ja wilson recovered gradable quotes:",len(w),"games:",len({k[2] for k in w}))
print("a'ja wilson usage share of league total: %.2f%%"%(100*use["a'ja wilson"]/tot_use))
