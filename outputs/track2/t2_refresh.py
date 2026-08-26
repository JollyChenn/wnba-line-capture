import os,sys,pickle,collections,statistics
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
allm=pickle.load(open(os.path.join(OUT,"allmatched.pkl"),"rb"))
inwin=pickle.load(open(os.path.join(OUT,"inwin.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
# refresh interval measured on the FULL payload incl alts, all matched rows -240..+240
gaps=[]
for gid,rows in allm.items():
    snaps=collections.defaultdict(dict)
    for x in rows:
        r=x["row"]; snaps[x["el"]][(r["type"],r["side"],r["points"],r["alt"])]=r["prices"]
    els=sorted(snaps); prev=None; lastchg=None
    for e in els:
        if prev is not None and snaps[e]!=prev:
            if lastchg is not None: gaps.append(e-lastchg)
            lastchg=e
        elif prev is None: lastchg=e
        prev=snaps[e]
gaps.sort()
print("GENUINE PAYLOAD REFRESH INTERVAL (min), all matched games, full payload:")
print("  n=%d  p10 %.2f  p25 %.2f  median %.2f  p75 %.2f  p90 %.2f  max %.2f"%(
    len(gaps),gaps[int(.1*len(gaps))],gaps[int(.25*len(gaps))],statistics.median(gaps),
    gaps[int(.75*len(gaps))],gaps[int(.9*len(gaps))],gaps[-1]))
print("  share of intervals in [13,17] min: %.1f%%"%(100*sum(1 for g in gaps if 13<=g<=17)/len(gaps)))
print("  share < 5 min: %.1f%%"%(100*sum(1 for g in gaps if g<5)/len(gaps)))
# refresh-level series
REF={}
for gid,rows in inwin.items():
    snaps=collections.defaultdict(dict)
    for x in rows:
        r=x["row"]; snaps[x["el"]][(r["type"],r["side"],r["points"],r["alt"])]=(r["points"],r["prices"])
    els=sorted(snaps)
    seq=[]; prev=None
    for e in els:
        if prev is None or snaps[e]!=prev: seq.append((e,snaps[e]))
        prev=snaps[e]
    REF[gid]=seq
n=sum(len(v) for v in REF.values())
print("\nEFFECTIVE IN-PLAY SAMPLE after collapsing stale repeats:")
print("  distinct in-window quote refreshes: %d across %d games (median %.1f per game)"%(
    n,len(REF),statistics.median([len(v) for v in REF.values()])))
print("  per-game refresh counts:",sorted((len(v) for v in REF.values()),reverse=True))
print("  nominal rows were 24,645 -> %.1f%% of the in-play file is duplicated stale quotes"%(100*(1-n*1.0/1256)))
pickle.dump(REF,open(os.path.join(OUT,"ref.pkl"),"wb"))
