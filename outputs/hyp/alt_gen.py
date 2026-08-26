# GENERAL: across the WHOLE board, when 1xbet moves a line, how much does the PRICE move?
import os,sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _boot import ROOT, _src
exec(_src)
random.seed(20260826)
def vf(o,u): return (1.0/o)/((1.0/o)+(1.0/u))
rows=load("xbet_board.csv")
inst=collections.defaultdict(lambda: collections.defaultdict(dict))
for b in rows:
    t,o,ln=b.get("captured_utc"),f(b.get("odds")),f(b.get("line"))
    if not (t and o and ln is not None and b.get("market") in ALL_MK): continue
    inst[(_pl(b.get("player")),b.get("market"),t)][ln][b.get("side")]=o
seq=collections.defaultdict(list)
for (pl,mk,t),v in inst.items():
    r={ln:s for ln,s in v.items() if "Over" in s and "Under" in s}
    if len(r)==1:
        ln=list(r)[0]; seq[(pl,mk)].append((ts(t), ln, vf(r[ln]["Over"],r[ln]["Under"])))
for v in seq.values(): v.sort()
d=[]
for k,v in seq.items():
    for i in range(len(v)-1):
        if v[i][1]!=v[i+1][1]:
            dl=v[i+1][1]-v[i][1]
            d.append(((v[i][2]-v[i+1][2])/dl, abs(dl), k[1]))
print(f"consecutive single-line MOVES on the board: n={len(d)}")
s=[x[0] for x in d]
print(f"  price step dP(over) per point of line move: median {statistics.median(s):+.4f}  mean {statistics.mean(s):+.4f}")
print(f"  fraction where the price did NOT move at all: {sum(1 for x in d if abs(x[0])<1e-9)/len(d):.3f}")
for mk in ("pts","reb","ast","pra","pr","pa","ra"):
    ss=[x[0] for x in d if x[2]==mk]
    if len(ss)>=30: print(f"    {mk:<4} n={len(ss):>5} median {statistics.median(ss):+.4f}/pt")
print("\n  vs the REALISED dP(over)/pt from actual boxes: +0.069/pt (ladder pairs, CI +0.047..+0.091)")
print("  -> the book re-prices a line move by roughly HALF of what the move is worth,")
print("     i.e. it corrects almost entirely by moving the NUMBER, not the price.")
