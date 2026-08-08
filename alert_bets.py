# alert_bets.py - Discord alerts for the drift-cleared live menu.
# ---------------------------------------------------------------------------------------------
# RULE (2026-08-08): only ever alert on bets the drift filter has ACTUALLY VETTED.
# A bet needs MIN_CAPS price checks behind it before its verdict means anything. After an outage
# the board restarts with ~2 captures and every move_pct reads 0.0% - that is "no data", NOT
# "all clear", and sending it looks identical to a genuine clean sweep. On a normal slate ~86% of
# prices move >0.5% (median 2.4%), so a wall of zeros is the fingerprint of a blind filter.
# Un-vetted menus are ~breakeven and the drifted bets inside them run -28% ROI, so silence beats
# a list you can't trust.
#
# STAGES, each fired once per slate, all gated on the vetted rule above:
#   T-8h  ~17:00 MYT : main betting window, verdicts 96.4% final
#   T-4h  ~21:00 MYT
#   T-2h  ~23:00 MYT : near close, 99.5% final
# The FULL list goes out at the FIRST stage that has real price history - so on a night that
# starts blind the list simply arrives later, near kickoff, instead of arriving worthless.
# Every stage after that is CHANGES ONLY (a bet drifted -> pull it, or a new one cleared), so
# there is no useless 3am buzz. If the board is still blind at T-2h you get one "sitting out"
# note rather than being left guessing.
import csv, os, sys, json, datetime, urllib.request
import espn_get   # hardened ESPN client (curl_cffi Chrome TLS); GitHub IPs 403 plain urllib
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
LIVE = ("flip", "flip_paper", "overshoot", "cascade")
STAGES = [("main", 8.0), ("mid", 4.0), ("close", 2.0)]     # hours before FIRST tip
MIN_CAPS = 4          # price checks needed before a drift verdict is worth acting on
LAST_CALL = 2.0       # if still blind by here, send the one "sitting out" note
STATE = os.path.join(D, "alert_state.json")

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

def caps(r):
    try: return int(float(r.get("captures") or 0))
    except Exception: return 0

def vetted(rows):
    """Bets with a real drift READ behind them - enough price checks, and not a brand-new line."""
    return [r for r in rows if caps(r) >= MIN_CAPS and "NO READ" not in r.get("confidence", "")]

def fmt(r):
    # show the DRIFT itself, not just the price - that number is the whole point of the alert
    c = r.get("confidence", "")
    flag = "🟢" if "93" in c else ("🟡" if "81" in c else "⚪")
    lm = f" ⇢line {r['line_moved']}" if r.get("line_moved") else ""
    return (f"{flag} **{r['player']}** {r['market'].upper()} {r['side']} {r['line']} @ **{r['now_odds']}**"
            f"  ·  drift {r['move_pct']}% over {caps(r)} checks  ·  {r['src']}{lm}")

def main():
    # TEST MODE: `ALERT_TEST=1` sends a proof-of-life message immediately, ignoring the timing gate.
    # Lets you verify the CLOUD -> Discord path any time (workflow_dispatch input `test_alert`).
    if os.environ.get("ALERT_TEST") == "1":
        gp = os.path.join(D, "drift_gate_today.csv")
        rows = list(csv.DictReader(open(gp, encoding="utf-8"))) if os.path.exists(gp) else []
        bet = [r for r in rows if r["verdict"].startswith("BET") and r["src"] in LIVE]
        where = "☁️ CLOUD (GitHub Actions)" if os.environ.get("GITHUB_ACTIONS") else "💻 laptop"
        ok = send(f"🧪 **Alert test — sent from {where}**\n"
                  f"Discord path is working. Board: **{len(bet)} cleared**, of which "
                  f"**{len(vetted(bet))} are drift-vetted** ({len(rows)} rows in the gate).\n"
                  f"_This is a test, not a bet instruction._")
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
    ok = vetted(bet)                      # <- the ONLY rows we are ever willing to alert on
    cur_ids = {bet_id(r) for r in ok}

    # which stage are we in? the tightest one whose window has arrived and hasn't fired
    stage = None
    for name, h in STAGES:
        if hrs <= h and name not in st["done"]:
            stage = (name, h)
    if not stage:
        print(f"nothing to send (tip in {hrs:.1f}h, done={st['done']})"); return
    name, h = stage
    myt = (first + datetime.timedelta(hours=8)).strftime("%H:%M")

    # ---- THE GATE: no vetted bets -> stay silent, and do NOT burn the stage (retry next capture) ----
    if not ok:
        med = sorted(caps(r) for r in bet)[len(bet)//2] if bet else 0
        if hrs <= LAST_CALL and not st.get("blind_notice"):
            if send(f"🏀 **WNBA · tip {myt} MYT — sitting out.**\n"
                    f"{len(bet)} bets on the board but the drift filter has only ~{med} price checks "
                    f"behind them (needs {MIN_CAPS}+), so none are vetted. An un-vetted menu is roughly "
                    f"breakeven and the drifted bets hiding inside it run −28% ROI. No bet is the bet."):
                st["blind_notice"] = True; json.dump(st, open(STATE, "w"))
        print(f"[{name}] {len(bet)} cleared but 0 drift-vetted (median {med} checks) — silent")
        return

    # ---- NEAR CLOSE: the ping you actually bet off, so it always carries the FULL final list
    # (not just changes) with the freshest drift reads of the night - 99.5% verdict-final here. ----
    if name == "close":
        told = set(st.get("sent_ids", []))
        dropped = [r for r in skip if bet_id(r) in told]
        parts = [f"⏰ **FINAL — bet these** · {len(ok)} drift-vetted · tip {myt} MYT (in {hrs:.1f}h)",
                 "\n".join(fmt(r) for r in sorted(ok, key=lambda x: (x["src"], x["player"])))]
        held = len(bet) - len(ok)
        if held:
            parts.append(f"_({held} cleared but never got enough price history — excluded.)_")
        if dropped:
            parts.append("🚫 **PULL** (drifted since the earlier ping):\n" + "\n".join(
                f"• {r['player']} {r['market'].upper()} {r['side']} {r['line']} ({r['move_pct']}%)" for r in dropped))
        parts.append("\n_small stakes · board: http://localhost:8899_")
        if send("\n".join(parts)):
            st["done"].append(name); st["sent_full"] = True; st["sent_ids"] = sorted(cur_ids)
            json.dump(st, open(STATE, "w")); print(f"[close] sent FINAL list: {len(ok)} bets, {len(dropped)} pulls")
        return

    # ---- FULL LIST: fires at the first stage where the filter actually has something to say ----
    if not st.get("sent_full"):
        held = len(bet) - len(ok)
        parts = [f"🏀 **WNBA — {len(ok)} drift-vetted bets** · first tip {myt} MYT (in {hrs:.1f}h)",
                 "\n".join(fmt(r) for r in sorted(ok, key=lambda x: (x["src"], x["player"])))]
        if held:
            parts.append(f"_({held} more cleared but not enough price history to vet — excluded.)_")
        if skip:
            parts.append("\n🚫 **DO NOT BET** (drifted): " + ", ".join(
                f"{r['player']} {r['market'].upper()} {r['side']} {r['line']}" for r in skip[:8]))
        parts.append("\n_small stakes · board: http://localhost:8899_")
        if send("\n".join(parts)):
            st["done"].append(name); st["sent_full"] = True; st["sent_ids"] = sorted(cur_ids)
            json.dump(st, open(STATE, "w")); print(f"[{name}] sent FULL list: {len(ok)} bets ({held} held back)")
        return

    # ---- later stages: changes only, silent when nothing moved ----
    told = set(st.get("sent_ids", []))
    dropped = [r for r in skip if bet_id(r) in told]        # you were told to bet it; it has since drifted
    added = [r for r in ok if bet_id(r) not in told]        # newly vetted+cleared since the full list
    if not dropped and not added:
        st["done"].append(name); json.dump(st, open(STATE, "w"))
        print(f"[{name}] no changes - staying quiet"); return
    tag = "⏰ NEAR CLOSE" if name == "close" else "🔄 UPDATE"
    parts = [f"{tag} · tip {myt} MYT (in {hrs:.1f}h)"]
    if dropped:
        parts.append("🚫 **PULL / don't place** (price has since drifted):\n" +
                     "\n".join(f"• {r['player']} {r['market'].upper()} {r['side']} {r['line']} ({r['move_pct']}%)" for r in dropped))
    if added:
        parts.append("➕ **newly vetted**:\n" + "\n".join(fmt(r) for r in added))
    if send("\n".join(parts)):
        st["done"].append(name); st["sent_ids"] = sorted(cur_ids)
        json.dump(st, open(STATE, "w")); print(f"[{name}] sent: {len(dropped)} pulls, {len(added)} adds")

if __name__ == "__main__":
    try: main()
    except Exception:
        import traceback; traceback.print_exc()
    sys.exit(0)
