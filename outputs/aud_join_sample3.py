import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D=os.path.dirname(os.path.abspath(__file__)); R=os.path.dirname(D)
def rd(p):
    with open(p,encoding="utf-8") as fh: return list(csv.DictReader(fh))
board=rd(os.path.join(R,"xbet_board.csv")); box=rd(os.path.join(R,"data","box_2026.csv"))
games=rd(os.path.join(R,"data","games_2026.csv"))
RES={"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
 "janelle illona salaun":"janelle salaun","alexa held":"lexi held",
 "valeriane vukosavljevic":"valeriane ayayi","cheyenne parker":"cheyenne parker-tyus","xu han":"han xu"}
gm={g["game_id"]:g for g in games}
plg=collections.defaultdict(set); use=collections.Counter(); mins=collections.Counter(); gp=collections.Counter()
for r in box:
    p=r["player"].strip().lower(); plg[p].add(r["game_id"])
    try:
        use[p]+= float(r["pts"])+float(r["reb"])+float(r["ast"]); mins[p]+=float(r["min"]); gp[p]+=1
    except Exception: pass
un=set()
for a,b in RES.items(): un |= plg.get(b,set())
print("A) union of BOX game_ids for the 8 failing players = %d"%len(un))
print("   sum of per-player box games = %d"%sum(len(plg.get(b,set())) for b in RES.values()))
print("   total games in games_2026 = %d"%len(games))

print("\nB) usage rank check (box_2026, >=10 GP, mean PRA per game)")
rk=sorted(((use[p]/gp[p],p,gp[p],mins[p]/gp[p]) for p in gp if gp[p]>=10),reverse=True)
for i,(v,p,g,m) in enumerate(rk[:8],1):
    tag="  <-- FAILS JOIN" if p in RES.values() else ""
    print("   %2d %-24s PRA/g %5.1f  GP %2d  MPG %4.1f%s"%(i,p,v,g,m,tag))
tot=sum(use[p] for p in gp)
print("   a'ja wilson share of league total PRA = %.2f%%"%(100*use["a'ja wilson"]/tot))

print("\nC) leave-out-top-k on the DEFECT itself (board rows)")
cnt=collections.Counter(r["player"].strip().lower() for r in board)
f={k:cnt[k] for k in RES}; tot_rows=len(board)
srt=sorted(f.items(),key=lambda x:-x[1])
rem=sum(f.values())
for k in range(0,4):
    rest=sum(v for _,v in srt[k:])
    print("   drop top-%d players -> %d names, %d rows, %.2f%% of board still silently dropped"%(k,len(srt)-k,rest,100*rest/tot_rows))

print("\nD) GAME-BLOCK bootstrap of the failure RATE (block = board game-date)")
# block by capture DATE (proxy for slate) since board rows carry no game id
byday=collections.defaultdict(lambda:[0,0])
for r in board:
    d=r["captured_utc"][:10]; p=r["player"].strip().lower()
    byday[d][1]+=1
    if p in RES: byday[d][0]+=1
days=list(byday.values()); print("   blocks (slate-days) =",len(days))
bs=[]
for _ in range(5000):
    s=[random.choice(days) for _ in days]
    a=sum(x[0] for x in s); b=sum(x[1] for x in s); bs.append(100*a/b)
bs.sort(); print("   failure-rate point %.2f%%  block-bootstrap 95%% CI [%.2f%%, %.2f%%]"%(100*sum(f.values())/tot_rows,bs[125],bs[4874]))
# and excluding wilson
bs2=[]
byday2=collections.defaultdict(lambda:[0,0])
for r in board:
    d=r["captured_utc"][:10]; p=r["player"].strip().lower()
    byday2[d][1]+=1
    if p in RES and p!="aja wilson": byday2[d][0]+=1
d2=list(byday2.values())
for _ in range(5000):
    s=[random.choice(d2) for _ in d2]; a=sum(x[0] for x in s); b=sum(x[1] for x in s); bs2.append(100*a/b)
bs2.sort(); print("   ex-Wilson rate %.2f%%  CI [%.2f%%, %.2f%%]"%(100*(sum(f.values())-f['aja wilson'])/tot_rows,bs2[125],bs2[4874]))

print("\nE) does the LIVE engine emit any of the 8? (bets_log.csv, all rows)")
bl=rd(os.path.join(R,"bets_log.csv"))
names=set(x.strip().lower() for x in (r.get("player","") for r in bl))
print("   bets_log rows %d, distinct players %d"%(len(bl),len(names)))
for a,b in RES.items():
    print("   %-26s board_name_in_log=%s  box_name_in_log=%s"%(a, a in names, b in names))
