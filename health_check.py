# health_check.py - STALENESS ALARM. Catches silent failures the way the two ESPN outages should
# have been caught (both ran "successfully" for days while collecting nothing).
# Checks, and Discord-pings ONLY when something is actually wrong (max one alert per issue per day):
#   1. box scores stale     - newest graded game older than 36h while games have finished
#   2. capture stale        - no 1xbet board row in 3h during the capture window
#   3. no bets on a slate   - games tonight but zero cleared bets (signal pipeline broken)
#   4. ESPN unreachable     - the exact failure that bit us twice
#   5. grading stalled      - unsettled bets older than 48h
# Run from the watchdog every hour. stdlib + espn_get. Never raises.
import csv, os, sys, json, datetime, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(D, "health_state.json")

def hook():
    p = os.path.join(D, "webhook.txt")
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else os.environ.get("DISCORD_WEBHOOK", "")

def ping(msg):
    wh = hook()
    if not wh: print("[no webhook]", msg); return
    try:
        urllib.request.urlopen(urllib.request.Request(
            wh, data=json.dumps({"content": msg[:1900]}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "wnba-health"}), timeout=15)
    except Exception as e: print("discord err", e)

def rows(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8"))) if os.path.exists(fp) else []

def hours_since(tstr, fmt=None):
    try:
        t = (datetime.datetime.strptime(tstr, fmt) if fmt
             else datetime.datetime.fromisoformat(tstr.replace("Z", "+00:00")))
        if t.tzinfo is None: t = t.replace(tzinfo=datetime.timezone.utc)
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600
    except Exception:
        return None

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    issues = []
    # --- 4. ESPN reachable? (the root cause of both outages) ---
    try:
        import espn_get
        sb = espn_get.getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard")
        espn_ok = sb.get("events") is not None
    except Exception:
        sb, espn_ok = {}, False
    if not espn_ok:
        issues.append(("espn", "🔴 **ESPN unreachable** — capture + grading will silently stall (this is what broke us twice). Check espn_get.py / IP block."))
    # --- 1. box scores stale ---
    g = rows("data/games_2026.csv")   # also used by check 2 below
    finished = [r for r in g if r.get("home_score")]
    if finished:
        newest = max(r.get("date", "") for r in finished)
        h = hours_since(newest, "%Y%m%d")
        # only complain if a game has actually finished since then
        played_since = any(r.get("date", "") > newest for r in g if r.get("tip") and hours_since(r["tip"]) and hours_since(r["tip"]) > 4)
        if h and h > 36 and played_since:
            issues.append(("box", f"🟠 **Box scores stale {h:.0f}h** (newest {newest}) — grading is frozen. daily_picks likely can't reach ESPN."))
    # --- 2. capture stale — TIGHTENED 2026-08-08 after the 37h silent outage.
    # The old version only complained if a game was within 24h, so a gap that started in a quiet
    # window went unreported for a day and a half. Now: during the season, ANY 6h gap is an alarm,
    # and 3h if a game is actually near. (Season = we have a scheduled game in the last/next 5 days.)
    b = rows("xbet_board.csv")
    _evs = sb.get("events", [])
    _soon = False
    for e in _evs:
        try:
            _t = datetime.datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
            if -3 <= (_t - now).total_seconds()/3600 <= 24: _soon = True
        except Exception: pass
    # in-season? a game finished or is scheduled within +/-5 days
    _inseason = False
    for r in g:
        try:
            _d = datetime.datetime.strptime(r.get("date", ""), "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
            if abs((_d - now).days) <= 5: _inseason = True
        except Exception: pass
    if b:
        h = hours_since(b[-1].get("captured_utc", ""))
        limit = 3 if _soon else (6 if _inseason else None)
        if h and limit and h > limit:
            where = "with a game near" if _soon else "during the season"
            issues.append(("capture", f"🟠 **No 1xbet capture for {h:.0f}h** {where} — the board is stale. "
                                      f"This is the silent-outage pattern: workflows report success but collect nothing."))
    # --- 3. games tonight but no cleared bets ---
    pre = [e for e in sb.get("events", []) if (((e.get("competitions") or [{}])[0].get("status") or {}).get("type") or {}).get("state") == "pre"]
    if pre:
        gate = rows("drift_gate_today.csv")
        LIVE = ("flip", "flip_paper", "overshoot", "cascade")
        cleared = [r for r in gate if r.get("verdict", "").startswith("BET") and r.get("src") in LIVE]
        tips = [datetime.datetime.fromisoformat(e["date"].replace("Z", "+00:00")) for e in pre]
        hrs_to_tip = (min(tips) - now).total_seconds() / 3600 if tips else 99
        if not cleared and hrs_to_tip < 6:
            issues.append(("nobets", f"🟠 **{len(pre)} games tip in {hrs_to_tip:.1f}h but ZERO cleared bets** — signal pipeline may be broken."))
    # --- 5. grading stalled: newest graded slate far behind the newest finished game.
    # (do NOT count ungraded bets_log rows: grade_bets keeps only the top-EV bet per player per day,
    #  so most rows are never graded by design - that produced a false alarm on 2026-08-07.)
    gr = rows("graded_bets.csv")
    if gr and finished:
        newest_graded = max(r.get("date", "") for r in gr)              # YYYYMMDD
        newest_final = max(r.get("date", "") for r in finished)         # YYYYMMDD
        gap = hours_since(newest_graded, "%Y%m%d")
        if newest_graded < newest_final and gap and gap > 36:
            issues.append(("grade", f"🟠 **Grading stalled** — newest graded slate {newest_graded} but games are final through {newest_final} ({gap:.0f}h behind)."))

    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    today = now.strftime("%Y-%m-%d")
    fresh = [(k, m) for k, m in issues if st.get(k) != today]      # one alert per issue per day
    if fresh:
        ping("🩺 **WNBA bot health**\n" + "\n".join(m for _, m in fresh))
        for k, _ in fresh: st[k] = today
        json.dump(st, open(STATE, "w"))
        print(f"alerted {len(fresh)} issue(s)")
    else:
        print("healthy" if not issues else f"{len(issues)} issue(s), already alerted today")
    for _, m in issues: print("  ", m)

if __name__ == "__main__":
    try: main()
    except Exception:
        import traceback; traceback.print_exc()
    sys.exit(0)
