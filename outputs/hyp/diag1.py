import csv,os,sys,re,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows=list(csv.DictReader(open(os.path.join(R,"elo_model","plays_full.csv"),encoding="utf-8")))
g=collections.defaultdict(list)
for r in rows: g[r["game_id"]].append(r)
MAKE=re.compile(r"^(.+?) makes (.+)$")
bad=collections.Counter()
for gid in ("401620246","401857021","401507144","401507333"):
    pa=ph=0
    print("=== ",gid)
    for r in g[gid]:
        try: a,h=int(r["away"]),int(r["home"])
        except Exception: continue
        da,dh=a-pa,h-ph; pa,ph=a,h
        d=da+dh
        m=MAKE.match(r["text"])
        exp=0
        if m:
            t=m.group(2).lower()
            exp=1 if "free throw" in t else (3 if "three point" in t else 2)
        if d!=exp:
            print("  d=%d exp=%d tid=%r p%s %s | %r"%(d,exp,r["team_id"],r["period"],r["clock"],r["text"]))
            bad[(d,exp)]+=1
print(bad.most_common())
