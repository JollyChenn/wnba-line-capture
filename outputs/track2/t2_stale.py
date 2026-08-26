import os,sys,pickle,collections,statistics
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
inwin=pickle.load(open(os.path.join(OUT,"inwin.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
print("DISTINCT MAIN-LINE VALUES PER GAME  (elapsed-min ranges at which each value was quoted)")
holds=[]
for gid in sorted(inwin,key=lambda x:games[x]["tip"]):
    g=games[gid]
    snaps=collections.defaultdict(dict)
    for x in inwin[gid]:
        r=x["row"]
        if r["alt"]=="1": continue
        snaps[x["el"]][(r["type"],r["side"])]=(r["points"],r["prices"])
    els=sorted(snaps)
    out=[]
    for k in ("moneyline","total","spread"):
        seq=[]; 
        for e in els:
            v=snaps[e].get((k,""))
            if v is None: continue
            if not seq or seq[-1][0]!=v: seq.append([v,e,e])
            else: seq[-1][2]=e
        for s in seq: holds.append((k,s[2]-s[1]))
        out.append("%s:%d"%(k,len(seq)))
    print("%-9s %-14s span %5.1f-%5.1f min  distinct: %s"%(g["date"],g["away"]+"@"+g["home"],els[0],els[-1]," ".join(out)))
    # print ML timeline
    seq=[]
    for e in els:
        v=snaps[e].get(("moneyline",""))
        if v is None: continue
        if not seq or seq[-1][0]!=v: seq.append([v,e,e])
        else: seq[-1][2]=e
    print("        ML:"," | ".join("%s @%.0f-%.0f"%(s[0][1],s[1],s[2]) for s in seq))
byk=collections.defaultdict(list)
for k,h in holds: byk[k].append(h)
print("\nHOLD TIME AT ONE QUOTED VALUE (minutes of game time a main line stayed frozen):")
for k,v in byk.items():
    v=[x for x in v]
    print("  %-10s n=%3d  median %5.1f  mean %5.1f  max %5.1f"%(k,len(v),statistics.median(v),sum(v)/len(v),max(v)))
