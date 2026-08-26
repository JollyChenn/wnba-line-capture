import csv,os,sys,datetime,collections,pickle
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=r"C:\Users\Axioo\wnba-line-capture"; OUT=os.path.join(D,"outputs","track2")
def load(p): 
    fp=os.path.join(D,p); return list(csv.DictReader(open(fp,encoding="utf-8",errors="replace")))
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None
FULL={"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA","Las Vegas Aces":"LV",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Portland Fire":"POR",
 "Seattle Storm":"SEA","Toronto Tempo":"TOR","Washington Mystics":"WSH"}
inwin=pickle.load(open(os.path.join(OUT,"inwin.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
gids=set(inwin)
print("target games:",len(gids))
for g in sorted(gids,key=lambda x:games[x]["tip"]):
    gg=games[g]; print(" ",gg["date"],gg["away"],"@",gg["home"],gg["tip"].isoformat(),"obs",len(inwin[g]))
# Pinnacle pre-game gamelines coverage
pin=collections.defaultdict(list)
for r in load("gamelines.csv"):
    t=ts(r["start"]+("Z" if not r["start"].endswith("Z") else "")) or ts(r["start"])
    parts=r["teams"].split("|")
    if len(parts)!=2: continue
    a1,a2=FULL.get(parts[0].strip()),FULL.get(parts[1].strip())
    if not a1: continue
    pin[(a1,a2,(r["start"] or "")[:10])].append(r)
hit=0
for g in gids:
    gg=games[g]; d=gg["tip"].date().isoformat()
    k=(gg["home"],gg["away"],d)
    k2=(gg["home"],gg["away"],(gg["tip"]-datetime.timedelta(days=1)).date().isoformat())
    if k in pin or k2 in pin: hit+=1
print("Pinnacle pre-game gamelines cover:",hit,"of",len(gids))
# 1xbet pre-game
xb=collections.defaultdict(list)
for r in load("xbet_gamelines.csv"):
    parts=r["teams"].split("|")
    if len(parts)!=2: continue
    a1,a2=FULL.get(parts[0].strip()),FULL.get(parts[1].strip())
    if not a1: continue
    xb[(a1,a2,(r["start"] or "")[:10])].append(r)
hit=0; detail=[]
for g in gids:
    gg=games[g]; d=gg["tip"].date().isoformat()
    k=(gg["home"],gg["away"],d); k2=(gg["home"],gg["away"],(gg["tip"]-datetime.timedelta(days=1)).date().isoformat())
    n=len(xb.get(k,[]))+len(xb.get(k2,[]))
    if n: hit+=1
    detail.append((gg["date"],gg["away"],gg["home"],n))
print("1xbet pre-game gamelines cover:",hit,"of",len(gids))
for d in detail: print("   ",d)
