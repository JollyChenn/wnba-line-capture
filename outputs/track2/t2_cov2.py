import os,sys,pickle,collections,statistics
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
SER=pickle.load(open(os.path.join(OUT,"ser.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
inwin=pickle.load(open(os.path.join(OUT,"inwin.pkl"),"rb"))
print("%-10s %-16s %6s %6s %6s %6s %8s"%("date","matchup","allobs","main","ml","elmin","elmax"))
tot=0
for gid in sorted(SER,key=lambda x:games[x]["tip"]):
    g=games[gid]; s=SER[gid]
    tl=s.get("tot_line",[]); ml=s.get("ml_p",[])
    els=[e for e,_ in tl]
    print("%-10s %-16s %6d %6d %6d %6.1f %8.1f"%(g["date"],g["away"]+"@"+g["home"],len(inwin[gid]),len(tl),len(ml),
          min(els) if els else -1, max(els) if els else -1))
    tot+=len(tl)
print("total main-line total-market snapshots:",tot)
