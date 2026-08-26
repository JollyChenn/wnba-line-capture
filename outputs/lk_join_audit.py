import csv, os, sys, collections, unicodedata
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = r"C:\Users\Axioo\wnba-line-capture"
def load(p):
    fp=os.path.join(D,p)
    return list(csv.DictReader(open(fp,encoding="utf-8",errors="replace"))) if os.path.exists(fp) else []

ALL_MK=("pts","pra","pr","pa","reb","ast","ra")
box=load("data/box_2026.csv")
teamof={}; use=collections.defaultdict(float); games=collections.defaultdict(set)
for r in box:
    pl=(r.get("player") or "").lower()
    teamof[pl]=r.get("team")
    def f(x):
        try: return float(x)
        except: return 0.0
    use[pl]+=f(r.get("fga"))+0.44*f(r.get("fta"))+f(r.get("to"))
    games[pl].add(r.get("game_id"))
print("box distinct players:",len(teamof),"box rows:",len(box))

bd=load("xbet_board.csv")
print("board rows:",len(bd))
miss=collections.Counter(); missmk=collections.Counter()
allnames=collections.Counter()
for b in bd:
    pl=(b.get("player") or "").lower()
    allnames[pl]+=1
    if pl not in teamof:
        miss[pl]+=1
        if b.get("market") in ALL_MK: missmk[pl]+=1
tot_miss=sum(miss.values())
print("distinct board names:",len(allnames))
print("UNRESOLVED distinct names:",len(miss),"rows:",tot_miss,"pct of board: %.2f%%"%(100*tot_miss/len(bd)))
print("unresolved rows in ALL_MK markets:",sum(missmk.values()))
print("\n-- every unresolved name --")
for n,c in miss.most_common():
    print("%6d  %6d(mk)  %s"%(c,missmk.get(n,0),n))
