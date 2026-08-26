# TEST C - PRE-GAME ANCHOR vs LIVE PRICE as predictors of the FINAL RESULT
import os,sys,csv,math,random,statistics,pickle,collections,datetime
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
DD=r"C:\Users\Axioo\wnba-line-capture"; OUT=os.path.join(DD,"outputs","track2")
def load(p): return list(csv.DictReader(open(os.path.join(DD,p),encoding="utf-8",errors="replace")))
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
def pr(pv):
    s=(pv or "").split(",")
    if len(s)!=2: return None
    a,b=am(s[0]),am(s[1])
    if a is None or b is None or a+b<=0: return None
    return a/(a+b)
FULL={"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Los Angeles Sparks":"LA","Las Vegas Aces":"LV",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Portland Fire":"POR",
 "Seattle Storm":"SEA","Toronto Tempo":"TOR","Washington Mystics":"WSH"}
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
REF=pickle.load(open(os.path.join(OUT,"ref.pkl"),"rb"))
# --- anchors: LAST Pinnacle pre-game capture strictly before tip ---
anch=collections.defaultdict(dict)
gl=load("gamelines.csv")
byg=collections.defaultdict(list)
for r in gl:
    parts=r["teams"].split("|")
    if len(parts)!=2: continue
    a1,a2=FULL.get(parts[0].strip()),FULL.get(parts[1].strip())
    if not a1 or not a2: continue
    byg[(a1,a2)].append(r)
found=0
for gid in REF:
    g=games[gid]; tip=g["tip"]
    cands=[r for r in byg.get((g["home"],g["away"]),[]) 
           if (ts(r["captured_utc"]) is not None and ts(r["captured_utc"])<tip 
               and (tip-ts(r["captured_utc"])).total_seconds()<=36*3600)]
    if not cands: continue
    last=max(ts(r["captured_utc"]) for r in cands)
    snap=[r for r in cands if ts(r["captured_utc"])==last]
    a={}
    for r in snap:
        v=pr(r["prices"])
        if r["type"]=="moneyline": a["ml_p"]=v
        elif r["type"]=="spread": a["sp_line"]=f(r["points"]); a["sp_p"]=v
        elif r["type"]=="total": a["tot_line"]=f(r["points"]); a["tot_p"]=v
        elif r["type"]=="team_total":
            a[("tth_line" if r["side"]=="home" else "tta_line")]=f(r["points"])
    a["age_h"]=(tip-last).total_seconds()/3600
    anch[gid]=a; found+=1
print("anchors built for %d of %d in-play games"%(found,len(REF)))
ages=[anch[g]["age_h"] for g in anch]
print("anchor age before tip (hours): median %.2f  min %.2f  max %.2f"%(statistics.median(ages),min(ages),max(ages)))
print("  NOTE: this is the last PRE-GAME capture, not a true closing line. Ages >3h are stale anchors.")
print("  games with anchor within 3h of tip: %d"%sum(1 for a in ages if a<=3))

NUM=pickle.load(open(os.path.join(OUT,"num.pkl"),"rb"))
# --- assemble (game, refresh) observations ---
OBS=[]
for gid,seq in REF.items():
    if gid not in anch: continue
    g=games[gid]
    if g["hs"] is None or g["as_"] is None: continue
    fin_tot=g["hs"]+g["as_"]; fin_mar=g["hs"]-g["as_"]; home_win=1.0 if fin_mar>0 else 0.0
    a=anch[gid]
    for el,snap in seq:
        rec=dict(gid=gid,el=el,fin_tot=fin_tot,fin_mar=fin_mar,home_win=home_win,
                 a_tot=a.get("tot_line"),a_sp=a.get("sp_line"),a_ml=a.get("ml_p"),age_h=a["age_h"])
        for (tp,side,pts,alt),(p_,pv) in snap.items():
            if alt=="1": continue
            if tp=="moneyline": rec["l_ml"]=pr(pv)
            elif tp=="spread": rec["l_sp"]=f(pts); rec["l_sp_p"]=pr(pv); rec["l_sp_px"]=pv
            elif tp=="total": rec["l_tot"]=f(pts); rec["l_tot_p"]=pr(pv); rec["l_tot_px"]=pv
        OBS.append(rec)
print("\nobservations (game x refresh) with anchor+result: %d over %d games"%(len(OBS),len(set(o['gid'] for o in OBS))))

def rmse(e): return math.sqrt(sum(x*x for x in e)/len(e))
print("\n"+"="*100)
print("C1 - SHRINKAGE TEST.  predictor P(lam) = lam*LIVE + (1-lam)*ANCHOR ; target = FINAL")
print("  lam=1 -> trust live line fully.  lam<1 best -> live line OVER-REACTS -> fade extreme live deviations.")
print("  GRID DECLARED: 2 markets (total, spread) x 5 elapsed bands x lam in 0..1.4 step .05")
print("  Independent unit = GAME. CI by game bootstrap.")
print("="*100)
BANDS=[(0,30),(30,60),(60,90),(90,150),(0,150)]
def shrink(rows,lk,ak,tk):
    best=None; curve=[]
    for i in range(29):
        lam=i*0.05
        e=[(lam*r[lk]+(1-lam)*r[ak])-r[tk] for r in rows]
        v=rmse(e); curve.append((lam,v))
        if best is None or v<best[1]: best=(lam,v)
    return best,curve
for name,lk,ak,tk in (("TOTAL","l_tot","a_tot","fin_tot"),("SPREAD","l_sp","a_sp","fin_mar")):
    print("\n%s  (spread target = home margin; live spread sign-flipped to a margin forecast)"%name)
    print("  %-10s %5s %5s %9s %9s %9s %-24s"%("band(min)","n","games","rmse@lam1","rmse@lam0","best_lam","95% CI on best_lam"))
    for lo,hi in BANDS:
        rows=[r for r in OBS if lo<=r["el"]<hi and r.get(lk) is not None and r.get(ak) is not None]
        if name=="SPREAD": rows=[dict(r,**{lk:-r[lk],ak:-r[ak]}) for r in rows]   # spread -> margin forecast
        if len(rows)<15: print("  %-10s %5d  (too few)"%("%d-%d"%(lo,hi),len(rows))); continue
        gs=sorted(set(r["gid"] for r in rows))
        best,curve=shrink(rows,lk,ak,tk)
        r1=[c[1] for c in curve if abs(c[0]-1.0)<1e-9][0]; r0=curve[0][1]
        # game bootstrap on best lam
        bl=[]
        for _ in range(1500):
            s=[random.choice(gs) for _ in gs]
            rr=[]
            for g in s: rr+=[r for r in rows if r["gid"]==g]
            if len(rr)<10: continue
            b,_=shrink(rr,lk,ak,tk); bl.append(b[0])
        bl.sort()
        ci="[%.2f, %.2f]"%(bl[int(.025*len(bl))],bl[int(.975*len(bl))]) if len(bl)>50 else "n/a"
        print("  %-10s %5d %5d %9.3f %9.3f %9.2f %-24s"%("%d-%d"%(lo,hi),len(rows),len(gs),r1,r0,best[0],ci))
pickle.dump((OBS,anch),open(os.path.join(OUT,"obs.pkl"),"wb"))
