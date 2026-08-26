import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)
rows = load("xbet_board.csv")
inst = collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t, o, ln = b.get("captured_utc"), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")), b.get("market"), t)][ln][b.get("side")] = o
allq=[]
for k,v in inst.items():
    for ln,s in v.items():
        if "Over" in s and "Under" in s: allq.append((s["Over"],s["Under"]))
print("two-sided quotes:",len(allq))
print("over-odds distribution:",collections.Counter(round(o,2) for o,u in allq).most_common(15))
ov=[1/o+1/u for o,u in allq]
print("book margin: median %.4f  mean %.4f"%(statistics.median(ov),statistics.mean(ov)))
vfs=sorted((1/o)/(1/o+1/u) for o,u in allq)
print("vig-free P(over): p10 %.3f p25 %.3f med %.3f p75 %.3f p90 %.3f"%(vfs[len(vfs)//10],vfs[len(vfs)//4],vfs[len(vfs)//2],vfs[3*len(vfs)//4],vfs[9*len(vfs)//10]))
print("exact 0.500 fraction: %.3f"%(sum(1 for x in vfs if abs(x-0.5)<0.002)/len(vfs)))
# ladder pairs: how often are BOTH rungs priced identically?
ident=0; tot=0
for k,v in inst.items():
    r={ln:s for ln,s in v.items() if "Over" in s and "Under" in s}
    if len(r)<2: continue
    tot+=1
    ks=sorted(r)
    if r[ks[0]]==r[ks[1]]: ident+=1
print(f"ladder pairs with byte-identical prices at both rungs: {ident}/{tot}")
