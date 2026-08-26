import csv, os, sys, math, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D=os.path.dirname(os.path.abspath(__file__))
R=list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"),encoding="utf-8")))
print("family      n     ROI      CI95              record")
for s in sorted(set(x["src"] for x in R)):
    a=[x for x in R if x["src"]==s]
    pn=[float(x["pnl"]) for x in a]
    m=sum(pn)/len(pn); se=statistics.pstdev(pn)/math.sqrt(len(pn))
    w=sum(1 for x in a if x["result"]=="WIN")
    print("%-11s %-5d %+6.1f%%  [%+6.1f,%+6.1f]   %d-%d (%.1f%%)  units %+.2f"
          %(s,len(a),100*m,100*(m-1.96*se),100*(m+1.96*se),w,len(a)-w,100*w/len(a),sum(pn)))
