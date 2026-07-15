# full_crawl.py - the EVERYTHING backfill (resume-safe, 0.35s pace). Per game:
#  espn_odds.csv   gid,provider,spread(home),overUnder,homeML,awayML   <- HISTORICAL market lines!!
#  gameinfo.csv    gid,attendance,venue,officials
#  plays_full.csv  gid,period,clock,type_id,team_id,text,away,home    <- full pbp stream (simulation fuel)
import json,urllib.request,csv,os,time,sys
D=os.path.dirname(os.path.abspath(__file__));UA={"User-Agent":"Mozilla/5.0"}
done=set()
if os.path.exists(os.path.join(D,"gameinfo.csv")):
    done={r.split(",")[0] for r in open(os.path.join(D,"gameinfo.csv"),encoding="utf-8").read().splitlines()[1:]}
newf=not os.path.exists(os.path.join(D,"gameinfo.csv"))
fo=open(os.path.join(D,"espn_odds.csv"),"a",newline="",encoding="utf-8");wo=csv.writer(fo)
fg=open(os.path.join(D,"gameinfo.csv"),"a",newline="",encoding="utf-8");wg=csv.writer(fg)
fp=open(os.path.join(D,"plays_full.csv"),"a",newline="",encoding="utf-8");wp=csv.writer(fp)
if newf:
    wo.writerow(["game_id","provider","spread","overUnder","homeML","awayML"])
    wg.writerow(["game_id","attendance","venue","officials"])
    wp.writerow(["game_id","period","clock","type_id","team_id","text","away","home"])
gids=[r.split(",")[0] for r in open(os.path.join(D,"games_full.csv"),encoding="utf-8").read().splitlines()[1:]]
n=0
for gid in gids:
    if gid in done:continue
    try:j=json.load(urllib.request.urlopen(urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event="+gid,headers=UA),timeout=25))
    except Exception:time.sleep(3);continue
    for e in (j.get("pickcenter") or []):
        wo.writerow([gid,(e.get("provider") or {}).get("name",""),e.get("spread"),e.get("overUnder"),
                     (e.get("homeTeamOdds") or {}).get("moneyLine"),(e.get("awayTeamOdds") or {}).get("moneyLine")])
    gi=j.get("gameInfo",{})
    wg.writerow([gid,gi.get("attendance"),(gi.get("venue") or {}).get("fullName",""),
                 "|".join(o.get("displayName","") for o in gi.get("officials",[]))])
    for p in j.get("plays",[]):
        wp.writerow([gid,(p.get("period") or {}).get("number"),(p.get("clock") or {}).get("displayValue"),
                     (p.get("type") or {}).get("id"),(p.get("team") or {}).get("id"),
                     (p.get("text") or "")[:90],p.get("awayScore"),p.get("homeScore")])
    fo.flush();fg.flush();fp.flush();done.add(gid);n+=1
    if n%150==0:print(n,flush=True)
    time.sleep(0.35)
print("DONE",len(done))
