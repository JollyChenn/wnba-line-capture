"""Pass 2: reconstruct per-player on-court seconds, foul times, points from PBP."""
import csv, os, sys, re, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows = list(csv.DictReader(open(os.path.join(R,"elo_model","plays_full.csv"), encoding="utf-8")))
games = collections.OrderedDict()
for r in rows: games.setdefault(r["game_id"], []).append(r)

SUB  = re.compile(r"^(.+?) enters the game for (.+?)$")
MAKE = re.compile(r"^(.+?) makes (.+)$")
MISS = re.compile(r"^(.+?) misses (.+)$")
REB  = re.compile(r"^(.+?) (?:offensive|defensive) rebound$")
AST  = re.compile(r"\(([^()]+?) assists\)")
STL  = re.compile(r"\(([^()]+?) steals\)")
BLK  = re.compile(r"\(([^()]+?) blocks\)")
TO   = re.compile(r"^(.+?) (?:bad pass|lost ball|traveling|offensive foul|out of bounds|3-second|5-second|8-second|shot clock|double dribble|palming|kicked ball|discontinue)")
FOULP= re.compile(r"^(.+?) (shooting|personal|offensive|loose ball|away from play|flagrant|transition take|take|double personal|delay of game)?\s*foul")
DIST = re.compile(r"(\d+)-foot")
TEAMWORD = re.compile(r"(Sky|Sun|Fever|Aces|Storm|Wings|Mystics|Liberty|Lynx|Mercury|Dream|Sparks|Valkyries|Tempo|team)$")

def plen(p):
    p=int(p); return 600.0 if p<=4 else 300.0
def base(p):
    p=int(p); return (p-1)*600.0 if p<=4 else 2400.0+(p-5)*300.0
def elapsed(period,c):
    c=c.strip()
    if ":" in c: m,s=c.split(":"); rem=int(m)*60+float(s)
    else: rem=float(c) if c else 0.0
    return base(period)+(plen(period)-rem)

def is3(t):
    if "three point" in t: return True
    m=DIST.search(t); return bool(m) and int(m.group(1))>=22

out=[]
for gid, ev in games.items():
    # side map (home/away) from score deltas
    tally=collections.defaultdict(collections.Counter); pa=ph=0
    for r in ev:
        try: a,h=int(r["away"]),int(r["home"])
        except Exception: continue
        da,dh=a-pa,h-ph; pa,ph=a,h; tid=r["team_id"]
        if not tid: continue
        if da>0 and dh==0: tally[tid]["away"]+=1
        elif dh>0 and da==0: tally[tid]["home"]+=1
    side={t:c.most_common(1)[0][0] for t,c in tally.items()}
    byper=collections.defaultdict(list)
    for r in ev: byper[int(r["period"])].append(r)

    secs=collections.Counter(); team_of={}
    stats=collections.defaultdict(lambda: collections.Counter())
    fouls=collections.defaultdict(list)
    starters=set()
    for p in sorted(byper):
        evs=byper[p]; b=base(p); end=b+plen(p)
        seen=set()      # appeared this period already accounted
        oncourt={}      # player -> time they came on
        started=set()
        def touch(name, t, tid):
            """player observed active at time t; if not yet known this period, they started it"""
            if not name: return
            name=name.strip()
            if not name or TEAMWORD.search(name): return
            if tid: team_of[name]=tid
            if name not in seen:
                seen.add(name); started.add(name); oncourt[name]=b
        for r in evs:
            t=r["text"]; tid=r["team_id"]; te=elapsed(p, r["clock"])
            m=SUB.match(t)
            if m:
                inn,out_=m.group(1).strip(), m.group(2).strip()
                touch(out_, te, tid)
                if out_ in oncourt:
                    secs[out_]+=max(0.0, te-oncourt.pop(out_))
                if inn and not TEAMWORD.search(inn):
                    if tid: team_of[inn]=tid
                    seen.add(inn); oncourt[inn]=te
                continue
            for rx in (MAKE,MISS,REB,TO,FOULP):
                mm=rx.match(t)
                if mm: touch(mm.group(1), te, tid); break
            for rx,opp in ((AST,False),(STL,True),(BLK,True)):
                mm=rx.search(t)
                if mm:
                    otid=None
                    if opp:
                        for k,v in side.items():
                            if k!=tid and v!=side.get(tid): otid=k
                    touch(mm.group(1), te, otid if opp else tid)
            # player stats
            mm=MAKE.match(t)
            if mm:
                who,tail=mm.group(1).strip(),mm.group(2).lower()
                if "free throw" in tail: stats[who]["pts"]+=1; stats[who]["fta"]+=1; stats[who]["ftm"]+=1
                elif is3(tail): stats[who]["pts"]+=3; stats[who]["fga"]+=1; stats[who]["tpa"]+=1; stats[who]["tpm"]+=1
                else: stats[who]["pts"]+=2; stats[who]["fga"]+=1
            mm=MISS.match(t)
            if mm:
                who,tail=mm.group(1).strip(),mm.group(2).lower()
                if "free throw" in tail: stats[who]["fta"]+=1
                else:
                    stats[who]["fga"]+=1
                    if is3(tail): stats[who]["tpa"]+=1
            if "foul" in t.lower():
                mm=FOULP.match(t)
                if mm:
                    who=mm.group(1).strip()
                    if who and not TEAMWORD.search(who) and " vs. " not in who:
                        fouls[who].append(te)
        for name,ton in list(oncourt.items()):
            secs[name]+=max(0.0, end-ton)
        if p==1: starters=set(started)
    for name in set(list(secs)+list(stats)+list(fouls)):
        f=sorted(fouls.get(name,[]))
        out.append(dict(game_id=gid, player=name, team_id=team_of.get(name,""),
            side=side.get(team_of.get(name,""),""), starter=int(name in starters),
            secs=round(secs.get(name,0.0),1), mins=round(secs.get(name,0.0)/60.0,2),
            pts=stats[name]["pts"], fga=stats[name]["fga"], tpa=stats[name]["tpa"], tpm=stats[name]["tpm"],
            fta=stats[name]["fta"], nfoul=len(f),
            t3=("%.1f"%f[2]) if len(f)>=3 else "", t4=("%.1f"%f[3]) if len(f)>=4 else "",
            ftimes="|".join("%.0f"%x for x in f)))
O=os.path.join(R,"outputs","hyp")
with open(os.path.join(O,"pbp_players.csv"),"w",newline="",encoding="utf-8") as fh:
    w=csv.DictWriter(fh,fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print("wrote pbp_players.csv", len(out))

# ---- validate minutes vs box_2026
box={}
for r in csv.DictReader(open(os.path.join(R,"data","box_2026.csv"),encoding="utf-8")):
    try: box[(r["game_id"], r["player"])]=float(r["min"])
    except Exception: pass
import statistics
d=[]; matched=0
for r in out:
    k=(r["game_id"], r["player"])
    if k in box and box[k]>0:
        matched+=1; d.append(r["mins"]-box[k])
print("minutes validation: matched player-games =", matched)
if d:
    print("  mean err %.3f  median err %.3f  mean|err| %.3f  sd %.3f  pct within 2min %.1f%%"
          % (statistics.mean(d), statistics.median(d), statistics.mean(abs(x) for x in d),
             statistics.pstdev(d), 100*sum(1 for x in d if abs(x)<=2)/len(d)))
# points validation
dp=[]
bp={}
for r in csv.DictReader(open(os.path.join(R,"data","box_2026.csv"),encoding="utf-8")):
    try: bp[(r["game_id"],r["player"])]=float(r["pts"])
    except Exception: pass
for r in out:
    k=(r["game_id"],r["player"])
    if k in bp: dp.append(r["pts"]-bp[k])
if dp:
    print("points validation: n=%d mean err %.3f mean|err| %.3f exact %.1f%%"
          % (len(dp), statistics.mean(dp), statistics.mean(abs(x) for x in dp),
             100*sum(1 for x in dp if x==0)/len(dp)))
