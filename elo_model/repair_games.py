# rebuild games_full.csv purely from scoreboards (fast, no summary calls)
import json,urllib.request,csv,datetime,time,os,sys
D=os.path.dirname(os.path.abspath(__file__));UA={"User-Agent":"Mozilla/5.0"}
w=csv.writer(open(os.path.join(D,"games_full.csv"),"w",newline="",encoding="utf-8"))
w.writerow("game_id,date,home,away,home_score,away_score,season".split(","))
n=0
for yr in(2023,2024,2025,2026):
    d=datetime.date(yr,5,1)
    while d<=datetime.date(yr,10,25):
        try:
            sb=json.load(urllib.request.urlopen(urllib.request.Request(f"https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard?dates={d:%Y%m%d}",headers=UA),timeout=25))
            for ev in sb.get("events",[]):
                c=ev["competitions"][0]
                if c.get("status",{}).get("type",{}).get("state")!="post":continue
                cs={x["homeAway"]:x for x in c["competitors"]}
                w.writerow([ev["id"],f"{d:%Y%m%d}",cs["home"]["team"]["abbreviation"],cs["away"]["team"]["abbreviation"],cs["home"].get("score"),cs["away"].get("score"),yr]);n+=1
        except Exception:time.sleep(2)
        d+=datetime.timedelta(days=1);time.sleep(0.25)
    print(yr,n,flush=True)
print("DONE",n)
