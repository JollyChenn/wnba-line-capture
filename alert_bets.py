# alert_bets.py - Discord alerts for the drift-cleared live menu.
# ---------------------------------------------------------------------------------------------
# RULE (2026-08-08): only ever alert on bets the drift filter has ACTUALLY VETTED.
# A bet needs a real WATCH WINDOW (>=3h, or >=4 checks) behind it before its verdict means anything. After an outage
# the board restarts with ~2 captures and every move_pct reads 0.0% - that is "no data", NOT
# "all clear", and sending it looks identical to a genuine clean sweep. On a normal slate ~86% of
# prices move >0.5% (median 2.4%), so a wall of zeros is the fingerprint of a blind filter.
# Un-vetted menus are ~breakeven and the drifted bets inside them run -28% ROI, so silence beats
# a list you can't trust.
#
# STAGES, each fired once per slate, all gated on the vetted rule above:
#   T-8h  ~16:00 WIB : main betting window, verdicts 96.4% final
#   T-4h  ~20:00 WIB
#   T-2h  ~22:00 WIB : near close, 99.5% final  <- the one you bet off
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
# WHEN TO BET. Comparing horizons on a FIXED COHORT (same 115 bets evaluable at every hour, so
# sample composition cannot drive the answer) the ROI is essentially flat:
#   T-10h +11.2%  T-8h +12.7%  T-6h +11.7%  T-4h +13.6%  T-3h +15.9%  T-2h +15.1%  T-1h +15.1%
# All t=1.3-1.8. There is a mild tilt toward later, nothing more. The earlier 'skip-drift costs
# money before T-2h' reading came from comparing DIFFERENT samples at each horizon and does not
# survive the fixed-cohort test. WNBA tips land 23:00-09:00 WIB, so a tip-relative stage can
# easily fire at 4am; since timing is not worth much, the list goes out early enough to be
# actionable and is confirmed once near the wire.
STAGES = [("main", 6.0), ("t1h", 2.0)]   # hours before FIRST tip
MIN_CAPS = 4          # checks that vet a bet on their own, regardless of span
MIN_CAPS_ABS = 2      # never vet on a single observation - that is not a "move", it is a price
MIN_SPAN_H = 3.0      # hours the price must have been watchable for the read to mean anything
LAST_CALL = 2.0       # if still blind by here, send the one "sitting out" note
STATE = os.path.join(D, "alert_state.json")

def hook():
    p = os.path.join(D, "webhook.txt")
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else os.environ.get("DISCORD_WEBHOOK", "")

def send(msg):
    # MUTED 2026-08-14. This module is no longer a pinger - it is kept only because
    # audit_strategy.py imports its guard()/vetted() helpers, and deleting the file broke the
    # nightly regression audit. Exactly two things notify now: model_card.py (tonight's bets)
    # and ping_results.py (last night's result). This one prints and returns.
    print("[alert_bets muted - would have sent]\n" + msg[:400]); return False
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

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def caps(r):
    try: return int(float(r.get("captures") or 0))
    except Exception: return 0

def span(r):
    try: return float(r.get("span_h") or 0)
    except Exception: return 0.0

MAX_STALE_H = 3.0     # a read whose last look was longer ago than this is not a read, it is a memory
BOARD_ALIVE = 0.03    # SAFETY RAIL, not an edge rule. At 10% it cost 1.3-3pp of ROI by
                      # dropping quiet-but-working boards. At 3% it fires only on an
                      # essentially-zero board (08-09 07:16, lines just posted) - that is a
                      # broken-pipeline signal, not a betting signal.

def guard(rows, tip_of=None, horizon=None, verbose=True):
    """THE ENFORCER. Every rule the strategy depends on, checked in one place, with a named reason
    for each rejection. Nothing reaches Discord except through here.

    Each of these exists because it was VIOLATED in live running, not because it sounded prudent:
      menu      - retired signals (newunder -15.5%, model -22.9%) must never be pinged
      verdict   - the skip-drift rule itself; skipped bets run -20% to -27% ROI
      read      - a brand-new line has no drift history, so its 0.0% means nothing
      window    - >=3h watched (or >=4 checks); a blind board reads 0.0% and looks like all-clear
      fresh     - last look within 3h; a wide span with a stale end is the outage signature
      tonight   - the 48h capture window served bets on games two days out (TOR/CHI, 2026-08-09)
    """
    out, rejected = [], {}
    now = datetime.datetime.now(datetime.timezone.utc)
    # BOARD-LEVEL LIVENESS. No per-bet rule can see a dead board: each row looks individually fine
    # (enough checks, wide enough span) while the book simply has not repriced anything. Measured
    # across 34 gate runs, a healthy board has 20-58% of rows moved >0.3%; the two genuinely dead
    # ones read 5% (2026-08-08 09:12, straight after the outage) and 0% (2026-08-09 07:16, lines
    # just posted). Below 10% the drift verdicts are describing silence, not agreement.
    if len(rows) >= 8:
        moved = sum(1 for r in rows if abs(f(r.get("move_pct")) or 0) > 0.3)
        if moved / len(rows) < BOARD_ALIVE:
            if verbose:
                print(f"guard: DEAD BOARD - only {moved}/{len(rows)} rows ({100*moved/len(rows):.0f}%) "
                      f"have moved; need {BOARD_ALIVE:.0%}. Nothing sent.")
            return []
    for r in rows:
        why = None
        if r.get("src") not in LIVE:                                   why = "menu"
        elif not (r.get("verdict") or "").startswith("BET"):           why = "verdict"
        elif "NO READ" in r.get("confidence", "") or caps(r) < MIN_CAPS_ABS: why = "read"
        # NO SPAN RULE. Requiring >=3h watched cost 2.5pp at T-2h (8.6% -> 6.1%) while adding
        # nothing the caps>=2 and NO-READ checks above do not already do. It was reasoning,
        # not evidence, and the evidence went against it.
        else:
            try:
                seen = datetime.datetime.fromisoformat((r.get("last_utc") or "").replace("Z", "+00:00"))
                if (now - seen).total_seconds()/3600 > MAX_STALE_H:    why = "fresh"
            except Exception:
                pass                                                   # no stamp yet -> other gates carry it
            if not why and tip_of is not None:
                t = tip_of.get((r.get("player") or "").lower())
                if not t or (horizon and t > horizon):                 why = "tonight"
        if why: rejected[why] = rejected.get(why, 0) + 1
        else:   out.append(r)
    if verbose and rejected:
        print("guard rejected: " + ", ".join(f"{k}={v}" for k, v in sorted(rejected.items())))
    return out

def vetted(rows):
    """Kept as the read-quality half of the guard (used by the dashboard and the blind-board notice)."""
    return [r for r in rows
            if "NO READ" not in r.get("confidence", "")
            and caps(r) >= MIN_CAPS_ABS
            and (span(r) >= MIN_SPAN_H or caps(r) >= MIN_CAPS)]

# CONVICTION TIERS. cascade is the weakest signal on the menu, but it is POSITIVE: +3.6% ROI,
# +5.4u over n=151, and IMPROVING (1st half -1.8%, 2nd half +8.9%). Cutting it raises the menu's
# average ROI 10.4% -> 16.1% while LOWERING total profit 34.3u -> 28.9u - the average only rises
# because you deleted the low-margin half. Its gap vs the other three is not distinguishable from
# noise (t=1.28, p=0.199), so cutting it would be picking winners after seeing the results, the same
# selection trap that produced the fake gold-bot edge. Half stake keeps the expectancy while
# refusing to give 46%-of-volume-for-16%-of-profit equal weight.
HALF_STAKE = {"cascade"}
def stake(r): return "½u" if r.get("src") in HALF_STAKE else "1u"

PING_COLS = ["sent_utc", "stage", "date", "player", "market", "side", "line",
             "odds", "stake", "src", "move_pct", "captures", "span_h", "confidence", "pulled_utc"]

def log_pinged(rows, stage, slate):
    """PERMANENT RECORD of what Discord actually told you to bet.

    Without this we can only grade "what the signal produced", which is not the same thing - the
    ping is the signal AFTER the drift vet, the stake tier and the live-menu filter. That is the
    only list you ever acted on, so it is the only list worth grading. Append-only, deduped on
    (slate, player, market, side, line) so a re-send at a later stage does not double-count."""
    p = os.path.join(D, "pinged_bets.csv")
    seen = set()
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            seen.add((r["date"], r["player"], r["market"], r["side"], r["line"]))
    new = [[datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), stage, slate,
            r["player"], r["market"], r["side"], r["line"], r["now_odds"], stake(r), r["src"],
            r["move_pct"], caps(r), span(r), r.get("confidence", ""), ""]
           for r in rows if (slate, r["player"], r["market"], r["side"], r["line"]) not in seen]
    if not new: return 0
    # SCHEMA GUARD. Adding span_h to PING_COLS while the file on disk still had the OLD 14-column
    # header appended 15-value rows under it, shifting every field right - `pulled_utc` ended up
    # holding the confidence string, so 15 live bets read as "pulled" and vanished from the P&L.
    # If the header no longer matches, migrate the file in place (pad old rows) before appending.
    if os.path.exists(p):
        raw = list(csv.reader(open(p, encoding="utf-8")))
        if raw and raw[0] != PING_COLS:
            old = raw[0]
            fixed = [[r[old.index(c)] if c in old and old.index(c) < len(r) else "" for c in PING_COLS]
                     for r in raw[1:]]
            tmp = p + ".tmp"
            with open(tmp, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh); w.writerow(PING_COLS); w.writerows(fixed)
            os.replace(tmp, p)
            print(f"pinged_bets.csv migrated {len(old)} -> {len(PING_COLS)} columns")
    isnew = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if isnew: w.writerow(PING_COLS)
        w.writerows(new)
    return len(new)

def mark_pulled(rows, slate):
    """Stamp bets we later told you to PULL, so grading never counts them as bets we recommended.

    Without this the ping record keeps a bet at its main-stage state even after the near-close
    message said "don't place this" - which would quietly grade a bet we withdrew and flatter or
    punish the filter for a bet you never made. Atomic write (temp + replace): this file is the
    only record of what was recommended, so a half-written file must never be possible."""
    p = os.path.join(D, "pinged_bets.csv")
    if not os.path.exists(p) or not rows: return 0
    keys = {(slate, r["player"], r["market"], r["side"], r["line"]) for r in rows}
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = list(csv.DictReader(open(p, encoding="utf-8")))
    n = 0
    for r in cur:
        if (r["date"], r["player"], r["market"], r["side"], r["line"]) in keys and not r.get("pulled_utc"):
            r["pulled_utc"] = stamp; n += 1
    if not n: return 0
    tmp = p + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=PING_COLS, extrasaction="ignore")
        w.writeheader()
        for r in cur: w.writerow({k: r.get(k, "") for k in PING_COLS})
    os.replace(tmp, p)
    return n

def fmt(r):
    # show the DRIFT itself, not just the price - that number is the whole point of the alert
    c = r.get("confidence", "")
    flag = "🟢" if ("93" in c or "81" in c) else "⚪"
    lm = f" ⇢line {r['line_moved']}" if r.get("line_moved") else ""
    return (f"{flag} **{r['player']}** {r['market'].upper()} {r['side']} {r['line']} @ **{r['now_odds']}**"
            f"  ·  **{stake(r)}**  ·  drift {r['move_pct']}% over {caps(r)} checks / {span(r):.1f}h"
            f"  ·  {r['src']}{lm}")

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
    # SLATE = the BETTING NIGHT, not the calendar date of the earliest remaining tip.
    # WNBA tips run 16:00-02:00 UTC, so a 3-game night straddles midnight UTC. Once the early
    # games tipped on 2026-08-08, the earliest REMAINING tip was 00:30 UTC on 08-09 -> the slate
    # key changed -> state reset -> the bot re-sent the entire list at 02:42 WIB, 11 of 17 bets
    # being duplicates of the afternoon ping. Shifting back 6h puts the whole night on one key.
    slate = (first - datetime.timedelta(hours=6)).strftime("%Y-%m-%d")
    last = max(tips)                       # late games tip hours after the first - see the "late" stage
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if st.get("slate") != slate: st = {"slate": slate, "done": [], "sent_ids": []}

    gp = os.path.join(D, "drift_gate_today.csv")
    if not os.path.exists(gp): print("no gate file"); return
    rows = list(csv.DictReader(open(gp, encoding="utf-8")))
    bet = [r for r in rows if r["verdict"].startswith("BET") and r["src"] in LIVE]
    skip = [r for r in rows if r["verdict"].startswith("SKIP")]

    # ---- PER-GAME LAST CALL --------------------------------------------------------------------
    # Every slate stage keys off the FIRST tip, but a night spans hours of them. On 2026-08-09 the
    # T-1h call fired at 22:30 WIB for the 23:30 game and the 02:00 / 02:30 / 06:00 games got nothing
    # at all - their bets were quoted 4-7h before they tipped and never confirmed. So each GAME now
    # gets its own last call an hour before its own tip, listing only that game's bets.
    tip_of = {}                                     # player(lower) -> that game's tip
    gname = {}                                      # player(lower) -> "AWY@HOM" for the header
    try:
        team_of = {}
        _gd = {r.get("game_id"): r.get("date", "") for r in csv.DictReader(
            open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8"))}
        for r in csv.DictReader(open(os.path.join(D, "data", "box_2026.csv"), encoding="utf-8")):
            pl, tm, dd = (r.get("player") or "").lower(), r.get("team") or "", _gd.get(r.get("game_id"), "")
            if pl and tm and (pl not in team_of or dd >= team_of[pl][0]):
                team_of[pl] = (dd, tm)              # keep the LATEST team (handles mid-season moves)
        for ev in j_events:
            comp = (ev.get("competitions") or [{}])[0]
            if ((comp.get("status") or {}).get("type") or {}).get("state") != "pre": continue
            t = datetime.datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            abbrs = {(c.get("team") or {}).get("abbreviation") for c in comp.get("competitors", [])}
            label = "@".join(sorted(a for a in abbrs if a))
            for pl, (_dd, tm) in team_of.items():
                if tm in abbrs: tip_of[pl] = t; gname[pl] = label
    except Exception as e:
        print("game map failed (per-game calls disabled):", e)

    # EVERY rule in one place. Nothing is sent that has not passed guard().
    ok = guard(rows, tip_of=tip_of if tip_of else None,
               horizon=(last + datetime.timedelta(hours=1)) if tip_of else None)
    cur_ids = {bet_id(r) for r in ok}

    gdone = st.setdefault("game_done", [])
    if st.get("sent_full"):                          # only after you have seen the slate list
        for label in sorted({gname.get(r["player"].lower(), "") for r in ok} - {""}):
            if label in gdone: continue
            mine = [r for r in ok if gname.get(r["player"].lower()) == label]
            gt = min(tip_of[r["player"].lower()] for r in mine)
            gh = (gt - now).total_seconds()/3600
            if not (0 < gh <= 1.25): continue        # its own T-1h window
            told = set(st.get("sent_ids", []))
            pulls = [r for r in skip if bet_id(r) in told and gname.get(r["player"].lower()) == label]
            u = sum(0.5 if stake(r).startswith("½") else 1.0 for r in mine)
            gl = (gt + datetime.timedelta(hours=7)).strftime("%H:%M") + " WIB"
            parts = [f"🔔 **LAST CALL · {label}** — tips {gl} (in {gh:.1f}h) · {len(mine)} bets, {u:g}u",
                     "\n".join(fmt(r) for r in sorted(mine, key=lambda x: (x["src"], x["player"])))]
            if pulls:
                parts.append("🚫 **PULL** (drifted since the list):\n" + "\n".join(
                    f"• {r['player']} {r['market'].upper()} {r['side']} {r['line']} ({r['move_pct']}%)"
                    for r in pulls))
            if send("\n".join(parts)):
                gdone.append(label); st["sent_ids"] = sorted(cur_ids)
                json.dump(st, open(STATE, "w"))
                print(f"[game {label}] last call: {len(mine)} bets, {len(pulls)} pulls, "
                      f"+{log_pinged(mine, 'game_' + label, slate)} logged, "
                      f"{mark_pulled(pulls, slate)} pulled")
                return

    # which stage are we in? the tightest one whose window has arrived and hasn't fired
    stage = None
    for name, h in STAGES:
        if hrs <= h and name not in st["done"]:
            stage = (name, h)
    # LATE GAMES. All three stages key off the FIRST tip, but a slate can span 8h of tips - a game at
    # 00:30 UTC gets "T-8h" treatment 15h before it actually starts, when its lines may not be posted.
    # So allow ONE extra ping near the last tip, carrying only bets that were never sent. This is what
    # legitimately surfaced Olivia Miles PR Over 23.5; the bug was re-sending the other 11 with her.
    hrs_last = (last - now).total_seconds()/3600
    if not stage and st.get("sent_full") and "late" not in st["done"] and 0 < hrs_last <= 2.5:
        stage = ("late", 2.5)
    if not stage:
        print(f"nothing to send (first tip {hrs:.1f}h, last {hrs_last:.1f}h, done={st['done']})"); return
    name, h = stage
    # You are on WIB (Indonesia, UTC+7). This said MYT (+8) for months, so every time quoted in an
    # alert was an hour later than your actual clock - "23:13 MYT" is 22:13 on your phone.
    loc = (first + datetime.timedelta(hours=7)).strftime("%H:%M") + " WIB"

    # ---- THE GATE: no vetted bets -> stay silent, and do NOT burn the stage (retry next capture) ----
    if not ok:
        med = sorted(caps(r) for r in bet)[len(bet)//2] if bet else 0
        if hrs <= LAST_CALL and not st.get("blind_notice"):
            if send(f"🏀 **WNBA · tip {loc} — sitting out.**\n"
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
        parts = [f"⏰ **FINAL — bet these** · {len(ok)} drift-vetted · tip {loc} (in {hrs:.1f}h)",
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
            json.dump(st, open(STATE, "w"))
            print(f"[close] sent FINAL: {len(ok)} bets, {len(dropped)} pulls, "
                  f"+{log_pinged(ok, name, slate)} logged, "
                  f"{mark_pulled(dropped, slate)} marked pulled")
        return

    # ---- FULL LIST: fires at the first stage where the filter actually has something to say ----
    if not st.get("sent_full"):
        held = len(bet) - len(ok)
        parts = [f"🏀 **WNBA — {len(ok)} drift-vetted bets** · first tip {loc} (in {hrs:.1f}h)",
                 "\n".join(fmt(r) for r in sorted(ok, key=lambda x: (x["src"], x["player"])))]
        if held:
            parts.append(f"_({held} more cleared but not enough price history to vet — excluded.)_")
        if skip:
            parts.append("\n🚫 **DO NOT BET** (drifted): " + ", ".join(
                f"{r['player']} {r['market'].upper()} {r['side']} {r['line']}" for r in skip[:8]))
        parts.append("\n_small stakes · board: http://localhost:8899_")
        if send("\n".join(parts)):
            st["done"].append(name); st["sent_full"] = True; st["sent_ids"] = sorted(cur_ids)
            json.dump(st, open(STATE, "w"))
            print(f"[{name}] sent FULL: {len(ok)} bets ({held} held back), "
                  f"+{log_pinged(ok, name, slate)} logged to pinged_bets.csv")
        return

    # ---- T-1h LAST CALL: this one ALWAYS sends. Full refreshed list if anything moved, otherwise a
    # one-line confirmation. Silence at the wire is ambiguous - you cannot tell "nothing changed"
    # from "the cron died", and that ambiguity is exactly what cost the whole 2026-08-08 slate. ----
    if name == "t1h":
        told = set(st.get("sent_ids", []))
        dropped = [r for r in skip if bet_id(r) in told]
        added = [r for r in ok if bet_id(r) not in told]
        full = "\n".join(fmt(r) for r in sorted(ok, key=lambda x: (x["src"], x["player"])))
        if dropped or added:
            parts = [f"🔔 **LAST CALL — {hrs:.1f}h to tip {loc}** · {len(ok)} live"]
            if dropped:
                parts.append("🚫 **PULL** (drifted since the last list):\n" + "\n".join(
                    f"• {r['player']} {r['market'].upper()} {r['side']} {r['line']} ({r['move_pct']}%)"
                    for r in dropped))
            if added:
                parts.append("➕ **newly vetted**:\n" + "\n".join(fmt(r) for r in added))
            parts.append("\n_the full standing list:_\n" + full)
        else:
            u = sum(0.5 if stake(r).startswith("½") else 1.0 for r in ok)
            parts = [f"🔔 **LAST CALL — {hrs:.1f}h to tip {loc}**",
                     f"No changes. The **{len(ok)} bets** from the earlier list still stand (**{u:g}u** total). "
                     f"Nothing drifted off, nothing new cleared."]
        if send("\n".join(parts)):
            st["done"].append(name); st["sent_ids"] = sorted(cur_ids)
            json.dump(st, open(STATE, "w"))
            print(f"[t1h] LAST CALL: {len(ok)} live, {len(dropped)} pulls, {len(added)} adds, "
                  f"+{log_pinged(added, name, slate)} logged, {mark_pulled(dropped, slate)} pulled")
        return

    # ---- later stages: changes only, silent when nothing moved ----
    told = set(st.get("sent_ids", []))
    dropped = [r for r in skip if bet_id(r) in told]        # you were told to bet it; it has since drifted
    added = [r for r in ok if bet_id(r) not in told]        # newly vetted+cleared since the full list
    if not dropped and not added:
        st["done"].append(name); json.dump(st, open(STATE, "w"))
        print(f"[{name}] no changes - staying quiet"); return
    tag = "⏰ NEAR CLOSE" if name == "close" else "🔄 UPDATE"
    parts = [f"{tag} · tip {loc} (in {hrs:.1f}h)"]
    if dropped:
        parts.append("🚫 **PULL / don't place** (price has since drifted):\n" +
                     "\n".join(f"• {r['player']} {r['market'].upper()} {r['side']} {r['line']} ({r['move_pct']}%)" for r in dropped))
    if added:
        parts.append("➕ **newly vetted**:\n" + "\n".join(fmt(r) for r in added))
    if send("\n".join(parts)):
        st["done"].append(name); st["sent_ids"] = sorted(cur_ids)
        json.dump(st, open(STATE, "w"))
        print(f"[{name}] sent: {len(dropped)} pulls, {len(added)} adds, "
              f"+{log_pinged(added, name, slate)} logged, "
              f"{mark_pulled(dropped, slate)} marked pulled")

if __name__ == "__main__":
    try: main()
    except Exception:
        import traceback; traceback.print_exc()
    sys.exit(0)
