# alert_bets.py - Discord alert with tonight's DRIFT-CLEARED live-menu bets.
# Sends ONCE per slate, ~4h before the first tip (so it lands at a sane hour in Malaysia and the
# drift verdicts are ~96% final). Live menu = flip / flip_paper / overshoot / cascade only.
# Skipped (drifted) bets are listed separately as DO-NOT-BET. Webhook from webhook.txt (gitignored).
import csv, os, sys, json, datetime, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
LIVE = ("flip", "flip_paper", "overshoot", "cascade")
LEAD_H = float(os.environ.get("ALERT_LEAD_H", "4"))     # fire when the first tip is <= this many hours away
STATE = os.path.join(D, "alert_state.json")
ESPN_H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain, */*",
          "Referer": "https://www.espn.com/wnba/scoreboard", "Origin": "https://www.espn.com"}

def hook():
    p = os.path.join(D, "webhook.txt")
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else os.environ.get("DISCORD_WEBHOOK", "")

def send(msg):
    wh = hook()
    if not wh: print("[no webhook]\n" + msg); return False
    try:
        urllib.request.urlopen(urllib.request.Request(
            wh, data=json.dumps({"content": msg[:1950]}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "wnba-bot"}), timeout=15)
        return True
    except Exception as e:
        print("discord err", e); return False

def main():
    # first tip tonight
    try:
        j = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard", headers=ESPN_H), timeout=20))
    except Exception as e:
        print("espn fail", e); return
    now = datetime.datetime.now(datetime.timezone.utc)
    tips = []
    for ev in j.get("events", []):
        st = (((ev.get("competitions") or [{}])[0].get("status") or {}).get("type") or {}).get("state")
        if st != "pre": continue
        t = datetime.datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        if t > now: tips.append(t)
    if not tips: print("no upcoming games"); return
    first = min(tips)
    hrs = (first - now).total_seconds() / 3600
    slate = first.strftime("%Y-%m-%d")
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if state.get("sent") == slate:
        print(f"already alerted for {slate}"); return
    if hrs > LEAD_H:
        print(f"too early: first tip in {hrs:.1f}h (alert at {LEAD_H}h)"); return
    gp = os.path.join(D, "drift_gate_today.csv")
    if not os.path.exists(gp): print("no gate file"); return
    rows = list(csv.DictReader(open(gp, encoding="utf-8")))
    bet = [r for r in rows if r["verdict"].startswith("BET") and r["src"] in LIVE]
    skip = [r for r in rows if r["verdict"].startswith("SKIP")]
    def line(r):
        conf = r.get("confidence", "")
        flag = "🟢" if "93" in conf else ("🟡" if "NO READ" in conf else "⚪")
        lm = f" ⇢line {r['line_moved']}" if r.get("line_moved") else ""
        return f"{flag} **{r['player']}** {r['market'].upper()} {r['side']} {r['line']} @ **{r['now_odds']}** ({r['move_pct']}%, {r['src']}){lm}"
    myt = (first + datetime.timedelta(hours=8)).strftime("%H:%M")
    parts = [f"🏀 **WNBA — {len(bet)} bets** · first tip {myt} MYT (in {hrs:.1f}h)"]
    if bet:
        parts.append("\n".join(line(r) for r in sorted(bet, key=lambda x: (x["src"], x["player"]))))
    else:
        parts.append("_no cleared bets on this slate_")
    if skip:
        parts.append(f"\n🚫 **DO NOT BET** (price drifted — market walked away): " +
                     ", ".join(f"{r['player']} {r['market'].upper()} {r['side']} {r['line']}" for r in skip[:8]))
    parts.append("\n_small stakes · drift-cleared only · board: http://localhost:8899_")
    if send("\n".join(parts)):
        json.dump({"sent": slate}, open(STATE, "w"))
        print(f"alerted {len(bet)} bets for {slate}")

if __name__ == "__main__":
    try: main()
    except Exception:
        import traceback; traceback.print_exc()
    sys.exit(0)
