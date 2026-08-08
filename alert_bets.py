# alert_bets.py - Discord alerts for the drift-cleared live menu, in THREE stages per slate.
#   Stage 1  T-8h  (~23:00 MYT for a 07:00 tip) : FULL LIST - your main betting window.
#                                                 verdicts are 96.4% final by now, so most bets go here.
#   Stage 2  T-4h  (~03:00 MYT)                 : CHANGES ONLY - silent unless a bet turned bad or a new one appeared.
#   Stage 3  T-2h  (~05:00 MYT, near close)     : CHANGES ONLY + final confirmation (99.5% final).
# "Changes" = a bet you were told to place has since DRIFTED (pull it), or a new cleared bet appeared.
# Stages 2-3 stay quiet when nothing moved, so no useless 3am buzz.
import csv, os, sys, json, datetime, urllib.request
import espn_get   # hardened ESPN client (curl_cffi Chrome TLS); GitHub IPs 403 plain urllib
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
LIVE = ("flip", "flip_paper", "overshoot", "cascade")
STAGES = [("main", 8.0), ("mid", 4.0), ("close", 2.0)]     # hours before FIRST tip
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

def bet_id(r): return f"{r['player']}|{r['market']}|{r['side']}|{r['line']}"

def fmt(r):
    c = r.get("confidence", "")
    flag = "🟢" if "93" in c else ("🟡" if "NO READ" in c else "⚪")
    lm = f" ⇢line {r['line_moved']}" if r.get("line_moved") else ""
    return f"{flag} **{r['player']}** {r['market'].upper()} {r['side']} {r['line']} @ **{r['now_odds']}** ({r['move_pct']}%, {r['src']}){lm}"

def thin_warning(rows):
    """The drift filter only means something if prices have had TIME to move. After an outage the
    board restarts with ~2 captures and EVERY move_pct reads 0.0% - that is not "all clear", it is
    "no data". On a normal slate ~86% of prices move >0.5% (median 2.4%), so a wall of 0.0% is the
    signature of a blind filter. Say so out loud instead of presenting a flat list as if it passed."""
    caps = []
    for r in rows:
        try: caps.append(int(float(r.get("captures") or 0)))
        except Exception: pass
    if not caps: return ""
    med = sorted(caps)[len(caps)//2]
    if med >= 4: return ""
    return ("\n⚠️ **DRIFT FILTER IS BLIND** - only ~{} price checks behind these (want 4+). "
            "Every move reads 0.0% because nothing has been re-priced yet, *not* because they passed a "
            "test. **Wait for the near-close update before placing.**".format(med))

def main():
    # TEST MODE: `ALERT_TEST=1` sends a proof-of-life message immediately, ignoring the timing gate.
    # Lets you verify the CLOUD -> Discord path any time (workflow_dispatch input `test_alert`).
    if os.environ.get("ALERT_TEST") == "1":
        gp = os.path.join(D, "drift_gate_today.csv")
        rows = list(csv.DictReader(open(gp, encoding="utf-8"))) if os.path.exists(gp) else []
        bet = [r for r in rows if r["verdict"].startswith("BET") and r["src"] in LIVE]
        where = "☁️ CLOUD (GitHub Actions)" if os.environ.get("GITHUB_ACTIONS") else "💻 laptop"
        ok = send(f"🧪 **Alert test — sent from {where}**\n"
                  f"Discord path is working. Current board: **{len(bet)} cleared bets** "
                  f"({len(rows)} rows in the gate).\n_This is a test, not a bet instruction._")
        print("test alert sent" if ok else "test alert FAILED"); return
    # ESPN's default scoreboard returns the US-Eastern date, which late in the UTC day is YESTERDAY's
    # finished games - that made the alert report "no upcoming games" while tonight's slate was 8h out.
    # Query today AND tomorrow explicitly (2026-08-08 fix).
    now = datetime.datetime.now(datetime.timezone.utc)
    evs = []
    for _d in (now, now + datetime.timedelta(days=1)):
        try:
            evs += espn_get.getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
                                 {"dates": _d.strftime("%Y%m%d")}).get("events", [])
        except Exception as e:
            print("espn fail", e)
    seen_ids, j_events = set(), []
    for ev in evs:
        if ev.get("id") not in seen_ids:
            seen_ids.add(ev.get("id")); j_events.append(ev)
    tips = [datetime.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")) for ev in j_events
            if (((ev.get("competitions") or [{}])[0].get("status") or {}).get("type") or {}).get("state") == "pre"]
    tips = [t for t in tips if t > now]
    if not tips: print("no upcoming games"); return
    first = min(tips); hrs = (first - now).total_seconds()/3600
    slate = first.strftime("%Y-%m-%d")
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if st.get("slate") != slate: st = {"slate": slate, "done": [], "sent_ids": []}

    gp = os.path.join(D, "drift_gate_today.csv")
    if not os.path.exists(gp): print("no gate file"); return
    rows = list(csv.DictReader(open(gp, encoding="utf-8")))
    bet = [r for r in rows if r["verdict"].startswith("BET") and r["src"] in LIVE]
    skip = [r for r in rows if r["verdict"].startswith("SKIP")]
    cur_ids = {bet_id(r) for r in bet}

    # which stage are we in? the tightest one whose window has arrived and hasn't fired
    stage = None
    for name, h in STAGES:
        if hrs <= h and name not in st["done"]:
            stage = (name, h)
    if not stage:
        print(f"nothing to send (tip in {hrs:.1f}h, done={st['done']})"); return
    name, h = stage
    myt = (first + datetime.timedelta(hours=8)).strftime("%H:%M")

    if name == "main":
        parts = [f"🏀 **WNBA — {len(bet)} bets to place** · first tip {myt} MYT (in {hrs:.1f}h)",
                 "\n".join(fmt(r) for r in sorted(bet, key=lambda x: (x["src"], x["player"]))) if bet else "_no cleared bets_"]
        if skip:
            parts.append("\n🚫 **DO NOT BET** (drifted): " + ", ".join(
                f"{r['player']} {r['market'].upper()} {r['side']} {r['line']}" for r in skip[:8]))
        parts.append("\n_small stakes · board: http://localhost:8899_")
        parts.append(thin_warning(bet))
        if send("\n".join(parts)):
            st["done"].append(name); st["sent_ids"] = sorted(cur_ids)
            json.dump(st, open(STATE, "w")); print(f"[{name}] sent {len(bet)} bets")
        return

    # stages 2-3: changes only
    told = set(st.get("sent_ids", []))
    dropped = [r for r in skip if bet_id(r) in told]        # you were told to bet it; it has since drifted
    added = [r for r in bet if bet_id(r) not in told]       # newly cleared since the main alert
    if not dropped and not added:
        st["done"].append(name); json.dump(st, open(STATE, "w"))
        print(f"[{name}] no changes - staying quiet"); return
    tag = "⏰ NEAR CLOSE" if name == "close" else "🔄 UPDATE"
    parts = [f"{tag} · tip {myt} MYT (in {hrs:.1f}h)"]
    if dropped:
        parts.append("🚫 **PULL / don't place** (price has since drifted):\n" +
                     "\n".join(f"• {r['player']} {r['market'].upper()} {r['side']} {r['line']} ({r['move_pct']}%)" for r in dropped))
    if added:
        parts.append("➕ **newly cleared**:\n" + "\n".join(fmt(r) for r in added))
    parts.append(thin_warning(bet))          # still blind at the wire? say so
    if send("\n".join(parts)):
        st["done"].append(name); st["sent_ids"] = sorted(cur_ids)
        json.dump(st, open(STATE, "w")); print(f"[{name}] sent: {len(dropped)} pulls, {len(added)} adds")

if __name__ == "__main__":
    try: main()
    except Exception:
        import traceback; traceback.print_exc()
    sys.exit(0)
