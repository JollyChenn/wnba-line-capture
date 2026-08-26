import os,sys,pickle,math,statistics,collections,datetime,csv
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=os.path.dirname(os.path.abspath(__file__))
S3=pickle.load(open(os.path.join(D,"gm_sub3.pkl"),"rb")); rows=S3["rows"]; teammean=S3["teammean"]
# how big is tonight's team-total deviation, and what does it buy on a single player?
seen=set(); dev=[]
for r in rows:
    k=(r["gt"],r["tm"])
    if k in seen: continue
    seen.add(k); dev.append(r["F"]["tt_own"]-teammean[r["tm"]])
print("sd of tonight's team_total around the team's own mean = %.2f pts (n=%d team-games)"%(statistics.pstdev(dev),len(dev)))
sh=[r["hmshare"] for r in rows if r["mk"]=="pts"]
print("median historical PTS share = %.3f"%statistics.median(sh))
resid=[r["actual"]-(r["line"]) for r in rows if r["mk"]=="pts"]
print("sd of (actual pts - line) = %.2f"%statistics.pstdev(resid))
mv=statistics.pstdev(dev)*statistics.median(sh)
print("=> a 1-sd team_total move shifts her expectation by %.2f pts, against %.2f pts of per-game noise: SNR = %.3f"%(
    mv,statistics.pstdev(resid),mv/statistics.pstdev(resid)))
print("   an SNR of %.3f implies a max attainable |rho| of about %.3f - below what %d quotes / %d games can resolve"%(
    mv/statistics.pstdev(resid), mv/statistics.pstdev(resid), len(rows), len(set((r["gt"],r["tm"] if r["home"] else r["opp"]) for r in rows))))

# live graded Model-S bets split by her team's team_total
gb=list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"),encoding="utf-8",errors="replace")))
MK=("pra","pr","pts")
key={}
for r in rows:
    key[(r["date"],r["pl"],r["mk"])]=r["F"]["tt_own"]
sel=[]
for b in gb:
    if b.get("src") not in ("flip","hotover","overshoot"): continue
    if b.get("market") not in MK or b.get("side")!="Over": continue
    tt=key.get((b.get("date"),(b.get("player") or "").lower(),b.get("market")))
    if tt is None: continue
    try: sel.append((tt,float(b["pnl"])))
    except Exception: pass
print()
print("LIVE graded Model-S bets matched to a Pinnacle team_total: n=%d"%len(sel))
if len(sel)>=30:
    sel.sort(); n=len(sel); a,b_=sel[n//3][0],sel[2*n//3][0]
    for lab,f_ in [("LOW tt",lambda t:t<=a),("MID",lambda t:a<t<=b_),("HIGH tt",lambda t:t>b_)]:
        g=[p for t,p in sel if f_(t)]
        if g: print("  %-8s n=%3d pnl=%+6.2fu ROI=%+6.2f%%"%(lab,len(g),sum(g),100*sum(g)/len(g)))
