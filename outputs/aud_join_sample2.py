import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
def rd(p):
    with open(p, encoding="utf-8") as fh: return list(csv.DictReader(fh))
board = rd(os.path.join(R,"xbet_board.csv")); box=rd(os.path.join(R,"data","box_2026.csv"))
games = rd(os.path.join(R,"data","games_2026.csv"))
boxnames = sorted(set(r["player"].strip() for r in box))
ALIAS = {"aja wilson":None,"awa fam thiam":None,"nazahrah hillmon-baker":None,
 "janelle illona salaun":None,"alexa held":None,"valeriane vukosavljevic":None,
 "cheyenne parker":None,"xu han":None}
# fuzzy resolve: surname token overlap
def toks(s): return set(t for t in s.lower().replace("'","").replace("-"," ").replace(".","").split() if len(t)>2)
for a in ALIAS:
    ta=toks(a); best=[]
    for b in boxnames:
        ov=len(ta & toks(b))
        if ov: best.append((ov,b))
    best.sort(reverse=True)
    ALIAS[a]=best[:3]
print("=== alias resolution (token-overlap candidates) ===")
for a,v in ALIAS.items(): print("  %-26s -> %s" % (a, v))

# game index
gmeta={g["game_id"]:g for g in games}
def tipdt(s):
    s=s.replace("Z","+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None
pl_games=collections.defaultdict(list)   # lower player -> [(tipdt, game_id)]
for r in box:
    g=gmeta.get(r["game_id"]);
    if not g: continue
    t=tipdt(g["tip"])
    if t: pl_games[r["player"].strip().lower()].append((t,r["game_id"]))
for k in pl_games: pl_games[k].sort()

RES={"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
 "janelle illona salaun":"janelle salaun","alexa held":None,"valeriane vukosavljevic":None,
 "cheyenne parker":None,"xu han":"han xu"}
# fill remaining by best candidate
for a,c in ALIAS.items():
    if RES.get(a) is None and c: RES[a]=c[0][1].lower()
print("\n=== final alias map ===")
for a,b in RES.items(): print("  %-26s -> %-24s box_games=%d" % (a,b,len(pl_games.get(b,[]))))

def assign(pl_lower, cap):
    gs=pl_games.get(pl_lower,[])
    for t,gid in gs:
        d=(t-cap).total_seconds()/3600.0
        if -3 <= d <= 30: return gid
    return None

fail_units=collections.defaultdict(set); fail_gids=set(); fail_rows=collections.Counter()
ok_units=collections.defaultdict(set); ok_gids=set(); ok_rows=0
boxlow=set(r["player"].strip().lower() for r in box)
for r in board:
    p=r["player"].strip().lower(); cap=tipdt(r["captured_utc"])
    if p in RES:
        fail_rows[p]+=1
        gid=assign(RES[p],cap)
        if gid: fail_units[p].add((gid,r["market"])); fail_gids.add(gid)
    elif p in boxlow:
        ok_rows+=1
        gid=assign(p,cap)
        if gid: ok_units[p].add((gid,r["market"])); ok_gids.add(gid)

tot_fail_units=sum(len(v) for v in fail_units.values())
tot_ok_units=sum(len(v) for v in ok_units.values())
print("\n=== ROW share vs UNIT share (distinct player x market x game) ===")
print("failing: rows %d (%.2f%% of board)  units %d  distinct games %d"%(sum(fail_rows.values()),100*sum(fail_rows.values())/len(board),tot_fail_units,len(fail_gids)))
print("joining: rows %d (%.2f%%)          units %d  distinct games %d"%(ok_rows,100*ok_rows/len(board),tot_ok_units,len(ok_gids)))
print("UNIT share of failing = %.2f%%   ROW share = %.2f%%"%(100*tot_fail_units/max(1,tot_fail_units+tot_ok_units),100*sum(fail_rows.values())/len(board)))
print("rows-per-unit failing %.1f  joining %.1f"%(sum(fail_rows.values())/max(1,tot_fail_units), ok_rows/max(1,tot_ok_units)))
print("\nper failing player: rows / units / games")
for p,n in fail_rows.most_common():
    print("  %-26s %5d %5d %4d"%(p,n,len(fail_units[p]),len(set(g for g,_ in fail_units[p]))))

# concentration
tot=sum(fail_rows.values()); top=fail_rows.most_common()
print("\ntop1 share %.1f%%  top2 %.1f%%  top3 %.1f%%"%(100*top[0][1]/tot,100*(top[0][1]+top[1][1])/tot,100*sum(x[1] for x in top[:3])/tot))
u=[(p,len(v)) for p,v in fail_units.items()]; u.sort(key=lambda x:-x[1]); tu=sum(x[1] for x in u)
print("UNITS: top1 %.1f%%  top2 %.1f%%"%(100*u[0][1]/tu,100*(u[0][1]+u[1][1])/tu))

# MDE for a star-cohort ROI test at Wilson's unit count, odds 1.90
def mde(n,dec=1.90):
    p=1/dec; sd=math.sqrt(p*(1-p))*dec  # sd of profit per 1u
    return 1.96*sd/math.sqrt(n)
for p,k in u[:4]:
    print("MDE(95%%) on ROI with n=%d units for %-22s = +/- %.1f%%"%(k,p,100*mde(k)))
print("MDE at all-failing units n=%d : +/- %.1f%%"%(tu,100*mde(tu)))
print("MDE at joined units n=%d : +/- %.1f%%"%(tot_ok_units,100*mde(tot_ok_units)))
