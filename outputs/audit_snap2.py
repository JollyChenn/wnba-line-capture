import csv, os, sys, datetime, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
 "Golden State Valkyries":"GS","Indiana Fever":"IND","Las Vegas Aces":"LV","Los Angeles Sparks":"LA",
 "Minnesota Lynx":"MIN","New York Liberty":"NY","Phoenix Mercury":"PHX","Seattle Storm":"SEA",
 "Washington Mystics":"WSH"}
bad=collections.Counter()
for r in csv.DictReader(open(os.path.join(R,"live_lines.csv"),encoding="utf-8")):
    for p in r["teams"].split("|"):
        if p.strip() not in FULL: bad[p.strip()]+=1
print("UNMAPPED TEAM STRINGS:", bad.most_common(20))

print("\n=== SNAPSHOT FIELD QUALITY (is the 'rich state' real?) ===")
rows=list(csv.DictReader(open(os.path.join(R,"live_snapshots.csv"),encoding="utf-8")))
for col in ["period","clock","away_score","home_score","h_fouls","a_fouls","h_to","a_to","h_reb","a_reb","last_play"]:
    vals=[r[col] for r in rows]
    nz=sum(1 for v in vals if v not in ("","0","0.0"))
    print("%-11s nonblank=%4d  non-zero/nonempty=%4d (%.0f%%)  distinct=%3d  ex=%r"%(
        col,sum(1 for v in vals if v!=""),nz,100*nz/len(vals),len(set(vals)),vals[5]))

# rebounds sanity: do they look like real team rebounds late in games?
q4=[r for r in rows if r["period"] in ("4","5")]
print("\nQ4 rows:",len(q4))
if q4:
    hr=[float(r["h_reb"]) for r in q4 if r["h_reb"] not in ("",)]
    print("Q4 h_reb  median=%.0f max=%.0f  (real WNBA team reb by Q4 ~ 25-35)"%(statistics.median(hr),max(hr)))
    hf=[float(r["h_fouls"]) for r in q4 if r["h_fouls"]!=""]
    print("Q4 h_fouls median=%.0f max=%.0f  (ESPN resets fouls per-quarter; team-game ~15-20)"%(statistics.median(hf),max(hf)))

print("\n=== CLOCK PARSEABILITY / MONOTONICITY WITHIN PERIOD ===")
bysnap=collections.defaultdict(list)
for r in rows: bysnap[r["game_id"]].append(r)
badclock=0; nonmono=0; tot=0
for g,lst in bysnap.items():
    prev=None
    for r in lst:
        tot+=1
        c=r["clock"]
        try:
            mm,ss=c.split(":"); v=int(mm)*60+float(ss)
        except Exception:
            badclock+=1; prev=None; continue
        if prev is not None and prev[0]==r["period"] and v>prev[1]+1: nonmono+=1
        prev=(r["period"],v)
print("unparseable clock: %d/%d   clock RUNNING BACKWARD within a period: %d"%(badclock,tot,nonmono))

print("\n=== TRUE COMPLETE TRACE (starts near tip AND ends at final) ===")
def T(s):
    s=s.replace("Z","")
    try: return datetime.datetime.strptime(s,"%Y-%m-%dT%H:%M:%S")
    except Exception:
        try: return datetime.datetime.strptime(s,"%Y-%m-%dT%H:%M")
        except Exception: return None
games={}
for g in csv.DictReader(open(os.path.join(R,"data","games_2026.csv"),encoding="utf-8")):
    games[g["game_id"]]=(T(g["tip"]),g.get("home_score"),g.get("away_score"))
full=0; endfinal=0; startq1early=0
for g,lst in bysnap.items():
    lst=sorted(lst,key=lambda r:r["ts"])
    tp,hs,as_=games.get(g,(None,None,None))
    s_ok = lst[0]["period"]=="1" and (T(lst[0]["ts"])-tp).total_seconds()<=180 if tp else False
    e_ok=False
    if hs and as_:
        try: e_ok = float(lst[-1]["home_score"])==float(hs) and float(lst[-1]["away_score"])==float(as_)
        except Exception: pass
    if s_ok: startq1early+=1
    if e_ok: endfinal+=1
    if s_ok and e_ok: full+=1
print("games starting in Q1 within 3min of tip: %d/27"%startq1early)
print("games ending exactly at FINAL score:     %d/27"%endfinal)
print("games with BOTH (true tip-to-final trace): %d/27"%full)
