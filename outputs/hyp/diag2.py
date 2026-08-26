import csv,os,sys,re,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows=list(csv.DictReader(open(os.path.join(R,"elo_model","plays_full.csv"),encoding="utf-8")))
g=collections.defaultdict(list)
for r in rows: g[r["game_id"]].append(r)
MAKE=re.compile(r"^(.+?) makes (.+)$")
DIST=re.compile(r"(\d+)-foot")
# cross tab: for made non-FT shots, score delta (2 or 3) vs (has 'three point', distance)
tab=collections.Counter(); distdelta=collections.defaultdict(collections.Counter)
notail=collections.Counter()
for gid,ev in g.items():
    pa=ph=0
    for r in ev:
        try: a,h=int(r["away"]),int(r["home"])
        except Exception: continue
        da,dh=a-pa,h-ph; pa,ph=a,h; d=da+dh
        m=MAKE.match(r["text"])
        if not m: continue
        t=m.group(2).lower()
        if "free throw" in t: continue
        has3="three point" in t
        dm=DIST.search(t); dist=int(dm.group(1)) if dm else -1
        if d in (2,3): tab[(has3,d)]+=1; distdelta[dist][d]+=1
        if not has3 and d==3: notail[re.sub(r"\(.*","",t).strip()]+=1
print("has3 x delta:",tab)
print()
for dd in sorted(distdelta): print(dd, dict(distdelta[dd]))
print()
print("no-'three point' but delta 3, top phrasings:", notail.most_common(12))
