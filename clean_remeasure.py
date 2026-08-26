# clean_remeasure.py - re-measure all four claims on the repaired data layer, and search for the
# best cell that survives a pre-declared ceiling.
# ---------------------------------------------------------------------------------------------
# Two data-layer bugs were fixed today and BOTH biased prior work:
#   * the board-to-box join deleted 3,201 rows (3.9%) including A'ja Wilson's 1,530 - so every
#     study ran on a population missing the league's highest-usage player;
#   * GM's total/spread took an arbitrary rung of Pinnacle's 7-line alternate ladder, differing
#     from the main line by a median 1.5 points.
# Nothing measured before today can be trusted at face value. This re-runs the four standing
# claims and a declared search grid on clean inputs, with the ceiling computed FIRST.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
SIGS=("flip","hotover","overshoot"); BET=("pra","pr","pts")
gof, oppof = {}, {}
for gid,(d2,t2,hm,aw) in gmeta.items():
    gof[(hm,t2)]=gid; gof[(aw,t2)]=gid; oppof[(hm,t2)]=aw; oppof[(aw,t2)]=hm
_mc={}
def med_team(pl,mk,gt):
    k=(pl,mk,gt)
    if k in _mc: return _mc[k]
    g=[r for r in hist.get(pl,[]) if r["tip"]<gt]; out=None
    if g:
        cur=g[-1]["tm"]; g2=[r for r in g if r["tm"]==cur]
        if len(g2)>=5: out=statistics.median([r[mk] for r in g2[-10:]])
    _mc[k]=out; return out
def sd_team(pl,mk,gt):
    g=[r for r in hist.get(pl,[]) if r["tip"]<gt]
    if not g: return None
    cur=g[-1]["tm"]; g2=[r for r in g if r["tm"]==cur]
    return statistics.pstdev([r[mk] for r in g2[-10:]]) if len(g2)>=5 else None
pin=collections.defaultdict(list)
for src,col in (("pinn_snapshots.csv","pinn_line"),("bets_log.csv","pinn"),("pinn_board.csv","pinn_line")):
    for r in load(src):
        t,ln=ts(r.get("captured_utc")),f(r.get(col))
        pl,mk=(r.get("player") or "").strip(),r.get("market")
        if t and ln is not None and pl and mk: pin[(_pl(pl),mk)].append((t,ln))
for v in pin.values(): v.sort()
def sharp_at(pl,mk,gt,h=6):
    cut=gt-datetime.timedelta(hours=h)
    g=[x for x in pin.get((pl,mk),[]) if x[0]<=cut and (gt-x[0]).total_seconds()<30*3600]
    return g[-1][1] if g else None

Q=[]
for (pl,mk,gt),sdq in side.items():
    if "Over" not in sdq or "Under" not in sdq: continue
    if abs(sdq["Over"][1]-sdq["Under"][1])>0.01: continue
    now=pgrow.get((pl,gt)); tm=teamof.get(pl)
    if not now or mk not in now or not tm: continue
    ln=sdq["Over"][1]
    if now[mk]==ln: continue
    md=med_team(pl,mk,gt); sd_=sd_team(pl,mk,gt); pv=prevline.get((pl,mk,gt))
    gid=gof[(tm,gt)]; d2,t2,hm,aw=gmeta[gid]
    s=GM.get((d2,tuple(sorted((hm,aw)))),{})
    sp=sharp_at(pl,mk,gt)
    Q.append(dict(pl=pl,mk=mk,gt=gt,gid=gid,date=d2,ln=ln,
        o_od=sdq["Over"][2],u_od=sdq["Under"][2],
        o_won=now[mk]>ln,u_won=now[mk]<ln,
        cush=(md-ln) if md is not None else None,
        relvol=(sd_/max(ln,1)) if sd_ else None,
        star=(pv is not None and ln-pv<0.5), hasprev=(pv is not None),
        tot=s.get("tot",(None,None,None))[1],
        gap=(sp-ln) if sp is not None else None,
        sig=None))
gr={}
for r in load("graded_bets.csv"):
    if (r.get("result") or "").upper() not in ("WIN","LOSS"): continue
    s_,mk,pl=(r.get("src") or ""),(r.get("market") or ""),_pl(r.get("player"))
    tm=teamof.get(pl)
    if not tm: continue
    for t in tips_of.get(tm,[]):
        if t.strftime("%Y%m%d")==(r.get("date") or "").replace("-","") or gmeta.get(gof.get((tm,t),""),("",))[0]==(r.get("date") or ""):
            gr[(pl,mk,t)]=s_; break
for r in Q: r["sig"]=gr.get((r["pl"],r["mk"],r["gt"]))
print(f"{len(Q)} gradable two-sided quotes | {len({r['gid'] for r in Q})} games | "
      f"{sum(1 for r in Q if r['sig'] in SIGS)} carry a live signal")
def ret(r,s): return ((r[s+"_od"]-1) if r[s+"_won"] else -1.0)
def roi(rows,s): return 100*sum(ret(r,s) for r in rows)/len(rows) if rows else 0.0
def hit(rows,s): return 100*sum(1 for r in rows if r[s+"_won"])/len(rows) if rows else 0.0
def gboot(rows,s,T=2500):
    bg=collections.defaultdict(list)
    for r in rows: bg[r["gid"]].append(r)
    k=list(bg); o=[]
    for _ in range(T): o.append(roi([x for p in [random.choice(k) for _ in k] for x in bg[p]],s))
    o.sort(); return o[int(T*.025)],o[int(T*.975)]
CELLS=[
 ("C1 MODEL S (sig + pra/pr/pts + not raised)", lambda r: r["sig"] in SIGS and r["mk"] in BET and r["star"], "o"),
 ("C1b gate3 alone, whole board",               lambda r: r["star"], "o"),
 ("C1c gate3 REJECT (book raised her)",         lambda r: r["hasprev"] and not r["star"], "o"),
 ("C2 sharp gap >=1 toward Pinnacle: OVER",     lambda r: r["gap"] is not None and r["gap"]>=1.0, "o"),
 ("C2 sharp gap <=-1 toward Pinnacle: UNDER",   lambda r: r["gap"] is not None and r["gap"]<=-1.0, "u"),
 ("C2b sharp gap >=1 AND gate3",                lambda r: r["gap"] is not None and r["gap"]>=1.0 and r["star"], "o"),
 ("C3 total HIGH (>=180) overs",                lambda r: r["tot"] is not None and r["tot"]>=180, "o"),
 ("C3 total LOW (<172) overs",                  lambda r: r["tot"] is not None and r["tot"]<172, "o"),
 ("C4 volatility LOW third overs",              lambda r: r["relvol"] is not None and r["relvol"]<=0.32, "o"),
 ("C4 volatility HIGH third overs",             lambda r: r["relvol"] is not None and r["relvol"]>0.45, "o"),
 ("cushion>=3 overs (overshoot rule)",          lambda r: r["cush"] is not None and r["cush"]>=3, "o"),
 ("cushion>=3 AND gate3",                       lambda r: r["cush"] is not None and r["cush"]>=3 and r["star"], "o"),
 ("blind OVER (control)",                       lambda r: True, "o"),
 ("blind UNDER (control)",                      lambda r: True, "u"),
]
peaks=[]
for _ in range(1200):
    pool=[(r["o_won"],r["u_won"]) for r in Q]; random.shuffle(pool)
    for r,x in zip(Q,pool): r["_o"],r["_u"]=x
    best=-99
    for lbl,sel,s in CELLS:
        g=[r for r in Q if sel(r)]
        if len(g)<40: continue
        best=max(best,100*sum((r[s+"_od"]-1) if r["_"+s] else -1.0 for r in g)/len(g))
    if best>-99: peaks.append(best)
peaks.sort(); CEIL=peaks[int(len(peaks)*0.95)]
print(f"\nNOISE CEILING FIRST: {len(CELLS)} declared cells -> p95 best {CEIL:+.1f}%  (min n=40)\n")
print(f"  {'cell':<44}{'n':>6}{'games':>7}{'hit%':>8}{'ROI':>9}   95% CI (game-block)")
res=[]
for lbl,sel,s in CELLS:
    g=[r for r in Q if sel(r)]
    if len(g)<40: print(f"  {lbl:<44}{len(g):>6}  too few"); continue
    lo,hi=gboot(g,s); ng=len({r['gid'] for r in g})
    flag="  <<< CLEARS" if roi(g,s)>CEIL else ""
    print(f"  {lbl:<44}{len(g):>6}{ng:>7}{hit(g,s):>7.1f}%{roi(g,s):>+8.1f}%   [{lo:+6.1f},{hi:+6.1f}]{flag}")
    res.append((roi(g,s),lbl,len(g),ng))
print()
win=[x for x in res if x[0]>CEIL]
print("  ABOVE CEILING: " + (", ".join(f"{l} ({v:+.1f}%)" for v,l,n,ng in sorted(win,reverse=True)) if win else "NONE"))
