# crawl_pbp_text.py - re-crawl pbp for TEXT details we skipped: assister on made shots, alley-oop/dunk/
# layup keywords, timeouts with team. Resume-safe, gentle 0.35s. -> plays_text.csv
import json,urllib.request,csv,os,time,sys,re
D=os.path.dirname(os.path.abspath(__file__));UA={"User-Agent":"Mozilla/5.0"}
OUT=os.path.join(D,"plays_text.csv")
done=set()
if os.path.exists(OUT):done={r.split(",")[0] for r in open(OUT,encoding="utf-8").read().splitlines()[1:]}
new=not os.path.exists(OUT)
fh=open(OUT,"a",newline="",encoding="utf-8");w=csv.writer(fh)
if new:w.writerow(["game_id","period","kind","team_id","shooter","assister","alley","dunk","layup","made"])
gids=[r.split(",")[0] for r in open(os.path.join(D,"games_full.csv"),encoding="utf-8").read().splitlines()[1:]]
AST=re.compile(r"\(([^)]+) assists\)");SHOT=re.compile(r"^(.*?) (makes|misses)")
n=0
for gid in gids:
    if gid in done:continue
    try:
        j=json.load(urllib.request.urlopen(urllib.request.Request(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event="+gid,headers=UA),timeout=25))
    except Exception:
        time.sleep(3);continue
    for p in j.get("plays",[]):
        t=p.get("text","")
        if p.get("shootingPlay"):
            m=SHOT.match(t)
            if not m:continue
            a=AST.search(t)
            w.writerow([gid,p.get("period",{}).get("number"),"shot",(p.get("team") or {}).get("id"),
                        m.group(1),a.group(1) if a else "", 1 if "alley" in t.lower() else 0,
                        1 if "dunk" in t.lower() else 0, 1 if "layup" in t.lower() else 0,
                        1 if m.group(2)=="makes" else 0])
        elif "imeout" in t:
            w.writerow([gid,p.get("period",{}).get("number"),"timeout","","",t[:40],0,0,0,0])
    fh.flush();done.add(gid);n+=1
    if n%100==0:print(n,flush=True)
    time.sleep(0.35)
print("DONE",len(done))
