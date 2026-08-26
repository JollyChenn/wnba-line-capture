import csv, os, sys, math, random, statistics, datetime, collections, unicodedata
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
__file__ = os.path.join(REPO,"mega_sweep.py"); D = REPO
exec(open(os.path.join(REPO,"mega_sweep.py"),encoding="utf-8").read().split('print(f"{len(B)} two-sided board quotes')[0])
ALIAS = {"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
         "janelle illona salaun":"janelle salaun","alexa held":"lexi held",
         "valeriane vukosavljevic":"valeriane ayayi","cheyenne parker":"cheyenne parker-tyus","xu han":"han xu"}
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
    return {k:v for k,v in sd2.items() if "Over" in v and "Under" in v and (k[0],k[2]) in pgrow}, pv
g0,pv0=build(False); g1,pv1=build(True)

# strictly-prior usage rank at each quote (no look-ahead)
def prior_usage(pl,tp):
    v=[r["use"] for r in hist.get(pl,[]) if r["tip"]<tp]
    return statistics.median(v) if len(v)>=5 else None
def tierroi(grad,pv,ranksel,gate3=False):
    # rank players by prior usage within each game-night, take selected decile
    out=[]; bygame=collections.defaultdict(list)
    for k in grad: bygame[k[2]].append(k)
    n=0;w=0;p=0.0;gm=set()
    for tp,ks in bygame.items():
        us=[(prior_usage(k[0],tp),k) for k in ks]
        us=[(u,k) for u,k in us if u is not None]
        if len(us)<6: continue
        us.sort(reverse=True)
        cut=max(1,int(len(us)*0.20))
        sel = us[:cut] if ranksel=="top" else us[-cut:]
        for u,k in sel:
            o=grad[k]["Over"]; ln=o[1]; od=o[2]
            if gate3:
                pr=pv.get(k)
                if pr is None or ln-pr>=0.5: continue
            act=pgrow[(k[0],k[2])][k[1]]
            if act==ln: continue
            n+=1; gm.add(tp)
            if act>ln: p+=od-1; w+=1
            else: p-=1
    return n,w,(100*p/n if n else 0),len(gm)
print("=== E) STRATIFIED INSIDE 'usage rank' (the stratum the claim says is corrupted) ===")
for sel in ("top","bot"):
    a=tierroi(g0,pv0,sel); b=tierroi(g1,pv1,sel)
    print(f"  usage-{sel:3s} quintile OVERS   base n={a[0]:4d} ROI={a[2]:+6.2f}% g={a[3]}   "
          f"patched n={b[0]:4d} ROI={b[2]:+6.2f}% g={b[3]}   shift={b[2]-a[2]:+.2f}pp")
print("\n=== F) how often does the top-usage quintile even CONTAIN a dropped player after patch? ===")
cnt=0; tot=0
bygame=collections.defaultdict(list)
for k in g1: bygame[k[2]].append(k)
for tp,ks in bygame.items():
    us=[(prior_usage(k[0],tp),k) for k in ks]; us=[(u,k) for u,k in us if u is not None]
    if len(us)<6: continue
    us.sort(reverse=True); cut=max(1,int(len(us)*0.20)); tot+=1
    if any(k[0] in ALIAS.values() for u,k in us[:cut]): cnt+=1
print(f"  {cnt}/{tot} game-nights ({100*cnt/max(tot,1):.1f}%) have a previously-dropped player in the top-usage quintile")

print("\n=== G) NOVELTY: does the repo already document/handle this? ===")
import subprocess
