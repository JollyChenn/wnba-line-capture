import csv, os, sys, statistics, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D=os.path.dirname(os.path.abspath(__file__))
R=list(csv.DictReader(open(os.path.join(D,"fam_bets.csv"),encoding="utf-8")))
def roi(rows,fade=False):
    if not rows: return None,0
    p=0
    for x in rows:
        w = (x["won"]=="True")
        if fade: p += -1.0 if w else (float(x["oppod"])-1)
        else:    p += (float(x["od"])-1) if w else -1.0
    return p/len(rows), len(rows)
for s in sorted(set(x["src"] for x in R)):
    a=[x for x in R if x["src"]==s]
    has=[x for x in a if x["oppod"]]; no=[x for x in a if not x["oppod"]]
    r1=roi(a); r2=roi(has); r3=roi(no)
    print(f"{s:<11} all n={r1[1]:<4} ROI {100*r1[0]:+6.1f}% | withOpp n={r2[1]:<4} {100*r2[0]:+6.1f}% | noOpp n={r3[1]:<4} "
          + (f"{100*r3[0]:+6.1f}%" if r3[0] is not None else "  --"))
# cascade: what markets/lines
c=[x for x in R if x["src"]=="cascade"]
print("cascade markets", collections.Counter(x["mk"] for x in c))
print("cascade withopp markets", collections.Counter(x["mk"] for x in c if x["oppod"]))
print("cascade line halves", collections.Counter((float(x["ln"])%1==0.5) for x in c))
print("dates coverage", collections.Counter(x["date"][:6] for x in R))
