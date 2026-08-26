import csv,os,sys,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=r"C:\Users\Axioo\wnba-line-capture"
box=list(csv.DictReader(open(os.path.join(D,"data","box_2026.csv"),encoding="utf-8",errors="replace")))
names=sorted({(r["player"], r["team"]) for r in box})
pats=["wilson","fam","hillmon","salaun","held","ayayi","vukos","parker","xu","han"]
for n,t in names:
    l=n.lower()
    if any(p in l for p in pats): print(repr(n),t)
