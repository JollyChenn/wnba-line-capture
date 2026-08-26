# Is the 2-rung "ladder" a real alternate market, or a transient during a LINE MOVE?
import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)
rows=load("xbet_board.csv")
inst=collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t,o,ln=b.get("captured_utc"),f(b.get("odds")),f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")),b.get("market"),t)][ln][b.get("side")]=o
seq=collections.defaultdict(list)
for (pl,mk,t),v in inst.items():
    seq[(pl,mk)].append((ts(t), sorted(v)))
for v in seq.values(): v.sort()

n2=0; transient=0; persist=0; before_after={}
runlen=[]
for k,v in seq.items():
    i=0
    while i<len(v):
        if len(v[i][1])<2: i+=1; continue
        j=i
        while j+1<len(v) and len(v[j+1][1])>=2 and set(v[j+1][1])==set(v[i][1]): j+=1
        n2+=1; runlen.append(j-i+1)
        prev = v[i-1][1] if i>0 else None
        nxt  = v[j+1][1] if j+1<len(v) else None
        lo,hi = min(v[i][1]), max(v[i][1])
        tag=None
        if prev and nxt and len(prev)==1 and len(nxt)==1:
            if prev[0]!=nxt[0] and prev[0] in (lo,hi) and nxt[0] in (lo,hi): tag="MOVE-THROUGH"
            elif prev[0]==nxt[0]: tag="blip-return"
            else: tag="other"
        elif prev is None or nxt is None: tag="edge-of-capture"
        else: tag="other"
        before_after[tag]=before_after.get(tag,0)+1
        i=j+1
print(f"contiguous 2-rung episodes: {n2}")
print(f"  scrapes per episode: median {statistics.median(runlen):.0f}  mean {statistics.mean(runlen):.2f}  max {max(runlen)}")
print("  what surrounds the episode:")
for k2 in sorted(before_after, key=lambda x:-before_after[x]):
    print(f"    {k2:<18} {before_after[k2]:>4}  ({100*before_after[k2]/n2:.1f}%)")
# how long does a single-line state last, for scale?
one=[]
for k,v in seq.items():
    i=0
    while i<len(v):
        if len(v[i][1])!=1: i+=1; continue
        j=i
        while j+1<len(v) and v[j+1][1]==v[i][1]: j+=1
        one.append(j-i+1); i=j+1
print(f"  (for scale) scrapes per SINGLE-line episode: median {statistics.median(one):.0f} mean {statistics.mean(one):.2f}")
