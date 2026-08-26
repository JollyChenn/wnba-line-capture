import csv, os, sys, math, random, statistics, datetime, collections, unicodedata
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
__file__ = os.path.join(REPO, "mega_sweep.py")
D = REPO
exec(open(os.path.join(REPO, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])
print("sanity: pgrow", len(pgrow), "side", len(side), "gmeta", len(gmeta))

box = load("data/box_2026.csv")
allbox = sorted(set((r.get("player") or "").lower() for r in box))
def fold(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).replace("'","").replace("’","").replace("-"," ").replace(".","")
aliases = ["aja wilson","awa fam thiam","nazahrah hillmon-baker","janelle illona salaun",
           "alexa held","valeriane vukosavljevic","cheyenne parker","xu han"]
print("\n=== A) surname-fold candidates in box ===")
for a in aliases:
    fa = set(fold(a).split())
    cands = [b for b in allbox if fa & set(fold(b).split())]
    print(f"  {a!r:32s} -> {cands}")

ALIAS = {"aja wilson":"a'ja wilson","awa fam thiam":"awa fam","nazahrah hillmon-baker":"naz hillmon",
         "janelle illona salaun":"janelle salaun","alexa held":"lexi held",
         "valeriane vukosavljevic":"valeriane ayayi","cheyenne parker":"cheyenne parker-tyus",
         "xu han":"han xu"}
def build(use_alias):
    raw2 = collections.defaultdict(list)
    for b in load("xbet_board.csv"):
        pl = (b.get("player") or "").lower()
        if use_alias: pl = ALIAS.get(pl, pl)
        t,o,ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
        if t and o and ln is not None and b.get("market") in ALL_MK:
            raw2[(pl, b.get("market"), b.get("side"), ln)].append((t,o))
    sd2 = collections.defaultdict(dict)
    for (pl,mk,s,ln),v in raw2.items():
        tm = teamof.get(pl)
        if not tm: continue
        for t,o in sorted(v):
            g2 = game_for(tm,t)
            if not g2: continue
            cur = sd2[(pl,mk,g2)].get(s)
            if cur is None or t>cur[0]: sd2[(pl,mk,g2)][s]=(t,ln,o)
    two = {k:v for k,v in sd2.items() if "Over" in v and "Under" in v}
    grad = {k:v for k,v in two.items() if (k[0],k[2]) in pgrow}
    return two, grad
print("\n=== B) MATERIALITY: gradable two-sided quotes, base vs alias-patched ===")
t0,g0 = build(False); t1,g1 = build(True)
print(f"  two-sided quotes  base={len(t0)}  patched={len(t1)}  delta=+{len(t1)-len(t0)}")
print(f"  GRADABLE quotes   base={len(g0)}  patched={len(g1)}  delta=+{len(g1)-len(g0)}"
      f"   ({100*(len(g1)-len(g0))/max(len(g1),1):.2f}% of patched gradable book)")
newk = sorted(set(g1)-set(g0))
for p,c in collections.Counter(k[0] for k in newk).most_common(): print(f"     {c:5d} gradable  {p}")
print("  independent GAMES with recovered gradable quotes:", len(set(k[2] for k in newk)))
print("  raw-row-level games touched (any unresolved row, any market/no gradability):")
tou=set()
for b in load("xbet_board.csv"):
    pl=(b.get("player") or "").lower()
    if pl in ALIAS:
        tm=teamof.get(ALIAS[pl]); t=ts(b.get("captured_utc"))
        if tm and t:
            g2=game_for(tm,t)
            if g2: tou.add((tm,g2))
print("    ", len(tou), "team-nights;", len(set(x[1] for x in tou)), "distinct tips")
