import csv, os, sys, re, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

rows = list(csv.DictReader(open(os.path.join(R,"elo_model","plays_full.csv"), encoding="utf-8")))
games = collections.OrderedDict()
for r in rows: games.setdefault(r["game_id"], []).append(r)

MAKE = re.compile(r"^(.+?) makes (.+)$")
MISS = re.compile(r"^(.+?) misses (.+)$")
REB  = re.compile(r"^(.+?) (offensive|defensive) rebound$")
DIST = re.compile(r"(\d+)-foot")

def is3(tail):
    if "three point" in tail: return True
    m = DIST.search(tail)
    return bool(m) and int(m.group(1)) >= 22

def clk(period, c):
    c = c.strip()
    if ":" in c:
        m,s = c.split(":"); rem = int(m)*60+float(s)
    else: rem = float(c) if c else 0.0
    p = int(period)
    if p <= 4: return (p-1)*600.0 + (600.0-rem)
    return 2400.0 + (p-5)*300.0 + (300.0-rem)

out_team=[]; out_foul=[]; out_p3=[]; recon_err=[]; nbadside=0
for gid, ev in games.items():
    fin_a=fin_h=None
    for r in reversed(ev):
        if r["away"] and r["home"]: fin_a,fin_h=int(r["away"]),int(r["home"]); break
    if fin_a is None: continue
    tally=collections.defaultdict(collections.Counter); pa=ph=0
    for r in ev:
        try: a,h=int(r["away"]),int(r["home"])
        except Exception: continue
        da,dh=a-pa,h-ph; pa,ph=a,h; tid=r["team_id"]
        if not tid: continue
        if da>0 and dh==0: tally[tid]["away"]+=1
        elif dh>0 and da==0: tally[tid]["home"]+=1
    side={t:c.most_common(1)[0][0] for t,c in tally.items()}
    if len(set(side.values()))!=2: nbadside+=1; continue

    st={s:collections.Counter() for s in ("home","away")}
    fouls=collections.defaultdict(list); p3=collections.defaultdict(lambda:[0,0]); pt={}
    for r in ev:
        t=r["text"]; tid=r["team_id"]; s=side.get(tid); low=t.lower()
        if not s: continue
        m=MAKE.match(t)
        if m:
            who,tail=m.group(1),m.group(2).lower(); pt[who]=tid
            if "free throw" in tail: st[s]["ftm"]+=1; st[s]["fta"]+=1; st[s]["pts"]+=1
            elif is3(tail):
                st[s]["fgm"]+=1; st[s]["fga"]+=1; st[s]["tpm"]+=1; st[s]["tpa"]+=1; st[s]["pts"]+=3
                p3[who][0]+=1; p3[who][1]+=1
            else: st[s]["fgm"]+=1; st[s]["fga"]+=1; st[s]["pts"]+=2
            continue
        m=MISS.match(t)
        if m:
            who,tail=m.group(1),m.group(2).lower(); pt[who]=tid
            if "free throw" in tail: st[s]["fta"]+=1
            elif is3(tail): st[s]["fga"]+=1; st[s]["tpa"]+=1; p3[who][1]+=1
            else: st[s]["fga"]+=1
            continue
        m=REB.match(t)
        if m:
            st[s]["oreb" if m.group(2)=="offensive" else "dreb"]+=1
            continue
        if "foul" in low:
            mm=re.match(r"^(.+?) (shooting|personal|offensive|loose ball|away from play|flagrant|transition take|take|double personal|delay of game|technical)?\s*foul", t)
            if mm:
                who=mm.group(1).strip()
                if who and " vs. " not in who and not who.endswith(("Sky","Sun","Fever","Aces","Storm","Wings","Mystics","Liberty","Lynx","Mercury","Dream","Sparks","Valkyries")):
                    pt[who]=tid; fouls[who].append((clk(r["period"],r["clock"]), int(r["period"])))
    e_h=st["home"]["pts"]-fin_h; e_a=st["away"]["pts"]-fin_a
    recon_err += [abs(e_h),abs(e_a)]; ok=(e_h==0 and e_a==0)
    for s in ("home","away"):
        o=st[s]; op=st["away" if s=="home" else "home"]
        out_team.append(dict(game_id=gid, side=s, recon_ok=int(ok), err=(e_h if s=="home" else e_a),
            pts=o["pts"], fga=o["fga"], fgm=o["fgm"], tpa=o["tpa"], tpm=o["tpm"], fta=o["fta"], ftm=o["ftm"],
            oreb=o["oreb"], dreb=o["dreb"], opp_oreb=op["oreb"], opp_dreb=op["dreb"],
            opp_fga=op["fga"], opp_fgm=op["fgm"], opp_tpa=op["tpa"], opp_tpm=op["tpm"], opp_fta=op["fta"],
            opp_pts=op["pts"], final=(fin_h if s=="home" else fin_a)))
    for who,l in fouls.items():
        l.sort(); t3=("%.1f"%l[2][0]) if len(l)>=3 else ""
        out_foul.append(dict(game_id=gid, player=who, side=side.get(pt.get(who),""), nfoul=len(l),
            t3=t3, f3_h1=(1 if (t3 and float(t3)<1200.0) else 0),
            t2=("%.1f"%l[1][0]) if len(l)>=2 else "",
            times="|".join("%.0f"%x[0] for x in l)))
    for who,(a,b) in p3.items():
        if b: out_p3.append(dict(game_id=gid, player=who, side=side.get(pt.get(who),""), tpm=a, tpa=b))

n=len(recon_err)
print("games parsed %d, side-detect failures %d" % (len(games)-nbadside, nbadside))
print("RECONCILIATION derived team pts vs final score: mean|err| = %.4f ; exact = %.2f%% ; |err|<=1 = %.2f%% ; |err|>=3 = %.2f%%"
      % (sum(recon_err)/n, 100*sum(1 for e in recon_err if e==0)/n,
         100*sum(1 for e in recon_err if e<=1)/n, 100*sum(1 for e in recon_err if e>=3)/n))
gok=set(r["game_id"] for r in out_team if r["recon_ok"])
print("games with BOTH teams exact: %d / %d (%.1f%%)  <- analysis universe" % (len(gok), len(games)-nbadside, 100*len(gok)/(len(games)-nbadside)))
O=os.path.join(R,"outputs","hyp")
def dump(p,rs):
    with open(os.path.join(O,p),"w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rs[0].keys())); w.writeheader(); w.writerows(rs)
    print("wrote",p,len(rs))
dump("pbp_derived.csv",out_team); dump("pbp_fouls.csv",out_foul); dump("pbp_p3.csv",out_p3)
