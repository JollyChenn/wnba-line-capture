import os,sys,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
SER=pickle.load(open(os.path.join(OUT,"ser.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
for key in ["tot_line","sp_line","ml_p","tot_fair"]:
    z=0;n=0;absd=[]
    per=[]
    for gid in SER:
        a=sorted(SER[gid].get(key,[]))
        if len(a)<5: continue
        d=[b[1]-c[1] for c,b in zip(a,a[1:])]
        z+=sum(1 for x in d if abs(x)<1e-9); n+=len(d); absd+=[abs(x) for x in d]
        per.append((games[gid]["date"]+games[gid]["away"],statistics.pstdev(d) if len(d)>1 else 0,len(d)))
    print("%-9s consecutive-snapshot changes n=%d  zero-change %.1f%%  mean|d| %.4f  p90|d| %.4f"%(
        key,n,100*z/n,sum(absd)/n,sorted(absd)[int(.9*n)]))
    per.sort(key=lambda x:-x[1])
    print("     per-game sd of change, top5:",[(p[0],round(p[1],4),p[2]) for p in per[:5]])
    print("     per-game sd of change, bot5:",[(p[0],round(p[1],4),p[2]) for p in per[-5:]])
