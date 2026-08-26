import csv, os, sys, math, random, statistics, datetime, collections, unicodedata
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
__file__ = os.path.join(REPO, "mega_sweep.py"); D = REPO
exec(open(os.path.join(REPO,"mega_sweep.py"),encoding="utf-8").read().split('print(f"{len(B)} two-sided board quotes')[0])

ALIAS = {"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
         "janelle illona salaun":"janelle salaun","alexa held":"lexi held",
         "valeriane vukosavljevic":"valeriane ayayi","cheyenne parker":"cheyenne parker-tyus",
         "xu han":"han xu"}
print("=== C) is the dropped name really the LEAGUE'S TOP-USAGE player? (survivorship severity) ===")
tot = collections.defaultdict(float); gp = collections.Counter(); pra = collections.defaultdict(float)
for (pl,tp),r in pgrow.items():
    tot[pl]+=r["use"]; gp[pl]+=1; pra[pl]+=r["pra"]
rank = sorted([(tot[p]/gp[p], p, gp[p], pra[p]/gp[p]) for p in tot if gp[p]>=10], reverse=True)
for i,(u,p,g,x) in enumerate(rank[:8],1):
    mark = "  <-- DROPPED BY JOIN" if p in ALIAS.values() else ""
    print(f"  usage#{i:2d}  {p:24s} use/g={u:5.1f}  pra/g={x:5.1f}  g={g}{mark}")
drop_ranks = [(i,p) for i,(u,p,g,x) in enumerate(rank,1) if p in ALIAS.values()]
print("  dropped players' usage ranks:", drop_ranks)

print("\n=== D) MODEL-S POPULATION IMPACT: would the recovered quotes have been bettable? ===")
def build(use_alias):
    raw2=collections.defaultdict(list)
    for b in load("xbet_board.csv"):
        pl=(b.get("player") or "").lower()
        if use_alias: pl=ALIAS.get(pl,pl)
        t,o,ln=ts(b.get("captured_utc")),f(b.get("odds")),f(b.get("line"))
        if t and o and ln is not None and b.get("market") in ALL_MK: raw2[(pl,b.get("market"),b.get("side"),ln)].append((t,o))
    sd2=collections.defaultdict(dict); ls=collections.defaultdict(list)
    for (pl,mk,s,ln),v in raw2.items():
        tm=teamof.get(pl)
        if not tm: continue
        for t,o in sorted(v):
            g2=game_for(tm,t)
            if not g2: continue
            cur=sd2[(pl,mk,g2)].get(s)
            if cur is None or t>cur[0]: sd2[(pl,mk,g2)][s]=(t,ln,o)
            if s=="Over": ls[(pl,mk)].append((g2,ln))
    pv={}
    for (pl,mk),v in ls.items():
        lastof={}
        for g2,ln in v: lastof[g2]=ln
        gs=sorted(lastof)
        for i in range(1,len(gs)): pv[(pl,mk,gs[i])]=lastof[gs[i-1]]
    grad={k:v for k,v in sd2.items() if "Over" in v and "Under" in v and (k[0],k[2]) in pgrow}
    return grad,pv
g0,pv0=build(False); g1,pv1=build(True)
new=sorted(set(g1)-set(g0))
# Model S gate 3: book has NOT raised her line >= .5 vs previous game; markets pra/pr/pts; bet OVER
MS_MK={"pra","pr","pts"}
def roi(keys,grad,pv,gate3=True):
    n=0;p=0.0;w=0;gms=set()
    for k in keys:
        pl,mk,tp=k
        if mk not in MS_MK: continue
        o=grad[k]["Over"]; ln=o[1]; od=o[2]
        prev=pv.get(k)
        if gate3 and (prev is None or ln-prev>=0.5): continue
        act=pgrow[(pl,tp)][mk]
        if act==ln: continue
        n+=1; gms.add(tp)
        if act>ln: p+=od-1; w+=1
        else: p-=1
    return n,w,(100*p/n if n else 0.0),len(gms)
print("  recovered quotes that survive Model-S gate3 + market filter:")
print("     n=%d  W=%d  ROI=%+.1f%%  games=%d"%roi(new,g1,pv1))
print("  base board (same filter):  n=%d  W=%d  ROI=%+.1f%%  games=%d"%roi(list(g0),g0,pv0))
print("  patched board (same filter): n=%d  W=%d  ROI=%+.1f%%  games=%d"%roi(list(g1),g1,pv1))
# per dropped player
for p_ in sorted(set(k[0] for k in new)):
    kk=[k for k in new if k[0]==p_]
    n,w,r,g=roi(kk,g1,pv1)
    print(f"     {p_:22s} n={n:3d} W={w:3d} ROI={r:+6.1f}% games={g}")
