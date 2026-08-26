# Track 2 - build clean per-game in-play price series from live_lines.csv
import csv, os, sys, math, random, statistics, datetime, collections, pickle
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"
OUT = os.path.join(D, "outputs", "track2")

def load(p):
    fp=os.path.join(D,p); return list(csv.DictReader(open(fp,encoding="utf-8",errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError,ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z","+00:00"))
    except Exception: return None
def am(p):
    v=f(p)
    if v is None: return None
    return (-v)/((-v)+100) if v<0 else 100/(v+100)
FULL={"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA","Las Vegas Aces":"LV",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Portland Fire":"POR",
 "Seattle Storm":"SEA","Toronto Tempo":"TOR","Washington Mystics":"WSH"}

games=[]
for g in load("data/games_2026.csv"):
    t=ts(g.get("tip"))
    if not t: continue
    games.append(dict(gid=g["game_id"],date=g["date"],home=g["home"],away=g["away"],tip=t,
                      hs=f(g.get("home_score")),as_=f(g.get("away_score"))))
print("games in schedule:",len(games))

LL=load("live_lines.csv")
print("live_lines rows:",len(LL))
# index games by unordered abbr pair
bypair=collections.defaultdict(list)
for g in games: bypair[frozenset((g["home"],g["away"]))].append(g)

matched=collections.defaultdict(list)   # gid -> rows
unmatched=collections.Counter()
for r in LL:
    t=ts(r["ts"])
    if not t: continue
    parts=(r["teams"] or "").split("|")
    if len(parts)!=2: continue
    a1,a2=FULL.get(parts[0].strip()),FULL.get(parts[1].strip())
    if not a1 or not a2: unmatched[r["teams"]]+=1; continue
    cands=bypair.get(frozenset((a1,a2)),[])
    best=None
    for g in cands:
        el=(t-g["tip"]).total_seconds()/60.0
        if -240<=el<=240:
            if best is None or abs(el)<abs(best[1]): best=(g,el)
    if best is None: unmatched[r["teams"]+" NOGAME"]+=1; continue
    g,el=best
    matched[g["gid"]].append(dict(row=r,el=el,t=t,teamstr=parts,a1=a1,a2=a2,g=g))
print("games with any live row:",len(matched))
print("unmatched sample:",unmatched.most_common(6))

# orientation check: does teams field = "home|away"?
ok=bad=0
for gid,rs in matched.items():
    g=rs[0]["g"]
    if rs[0]["a1"]==g["home"]: ok+=1
    else: bad+=1
print("teams-field order home-first:",ok,"away-first:",bad)

# in-window rows 0..150 min after tip
inwin=collections.defaultdict(list)
for gid,rs in matched.items():
    for x in rs:
        if 0<=x["el"]<=150: inwin[gid].append(x)
inwin={k:v for k,v in inwin.items() if v}
print("games with in-window (0-150m) rows:",len(inwin))
print("total in-window obs:",sum(len(v) for v in inwin.values()))
cnt=sorted(((len(v),k) for k,v in inwin.items()),reverse=True)
print("per-game obs counts:",[c for c,_ in cnt])
# alt breakdown in-window
altc=collections.Counter()
for v in inwin.values():
    for x in v: altc[(x["row"]["type"],x["row"]["alt"])]+=1
print("in-window type/alt:",dict(altc))
# pre-game rows availability (anchor)
pre=collections.Counter()
for gid,rs in matched.items():
    n=sum(1 for x in rs if x["el"]<0)
    pre[gid]=n
print("games with any pre-tip rows:",sum(1 for k in inwin if pre[k]>0), "of", len(inwin))
print("pre-tip counts:",sorted(pre[k] for k in inwin))
# results availability
print("in-window games with final score:",sum(1 for k in inwin if inwin[k][0]["g"]["hs"] is not None))
pickle.dump({k:[dict(row=x["row"],el=x["el"],t=x["t"],a1=x["a1"],a2=x["a2"]) for x in v] for k,v in inwin.items()},
            open(os.path.join(OUT,"inwin.pkl"),"wb"))
pickle.dump({g["gid"]:g for g in games}, open(os.path.join(OUT,"games.pkl"),"wb"))
# also dump ALL matched rows (incl pre-tip) for anchor work
pickle.dump({k:[dict(row=x["row"],el=x["el"],t=x["t"],a1=x["a1"],a2=x["a2"]) for x in v] for k,v in matched.items()},
            open(os.path.join(OUT,"allmatched.pkl"),"wb"))
