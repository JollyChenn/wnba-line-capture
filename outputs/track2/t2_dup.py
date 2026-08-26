import os,sys,pickle,collections,statistics
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
inwin=pickle.load(open(os.path.join(OUT,"inwin.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
tot_snap=0; dup_snap=0; movegaps=[]
per=[]
for gid,rows in inwin.items():
    snaps=collections.defaultdict(dict)
    for x in rows:
        r=x["row"]; snaps[x["el"]][(r["type"],r["side"],r["points"],r["alt"])]=r["prices"]
    els=sorted(snaps)
    prev=None; prevel=None; nmov=0
    for e in els:
        cur=snaps[e]
        tot_snap+=1
        if prev is not None:
            if cur==prev: dup_snap+=1
            else:
                nmov+=1
                if prevel is not None: movegaps.append(e-prevel)
                prevel=e
        else: prevel=e
        prev=cur
    per.append((games[gid]["date"]+" "+games[gid]["away"]+"@"+games[gid]["home"],len(els),nmov,round(100*nmov/max(1,len(els)-1),1)))
print("snapshots (all markets incl alts): %d   IDENTICAL to previous snapshot: %d (%.1f%%)"%(tot_snap,dup_snap,100*dup_snap/tot_snap))
print("median gap between genuine payload CHANGES: %.2f min (n=%d)"%(statistics.median(movegaps),len(movegaps)))
print("\n%-28s %6s %6s %7s"%("game","snaps","changes","%chg"))
for p in sorted(per): print("%-28s %6d %6d %6.1f%%"%p)
