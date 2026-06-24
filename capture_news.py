# capture_news.py - GENTLE, stdlib-only capture of WNBA INJURY reports + OFFICIAL LINEUPS to CSV history.
# ---------------------------------------------------------------------------------------------------
# WHY: the bot already SCRAPES odds, but injuries / who-actually-starts were only ever pinged to Discord,
# never SAVED. This logs them so later you can ask "was the line stale because a star was ruled out?".
#
# HOW IT STAYS LIGHT/GENTLE:
#   * stdlib only (no pandas) -> imports + runs in well under a second.
#   * 2 public ESPN endpoints (injuries feed + per-game summary). No 1xbet, no scraping load.
#   * DEDUP: a row is written ONLY when something actually CHANGES (status flips, or a player is first
#     confirmed in a lineup). State lives in news_last.json. So the CSVs become a clean time-series of
#     CHANGES, not a giant re-dump every 30 min.
#   * Whole body is wrapped in try/except + always exits 0 -> an ESPN hiccup can NEVER fail the capture job.
# ---------------------------------------------------------------------------------------------------
import os, sys, json, csv, datetime, urllib.request, unicodedata, re
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles choke on non-ASCII names otherwise
except Exception:
    pass

# --- public ESPN endpoints (same ones lineup_check.py already uses) ---
UA  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
INJ = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries"      # league-wide injury report
SB  = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"    # today's games -> game ids
SUM = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event="  # per-game confirmed actives/starters

INJ_CSV, LIN_CSV, STATE = "injuries_log.csv", "lineups_log.csv", "news_last.json"


def getj(url):
    """Fetch JSON, return {} on any error (so one bad call never stops the rest)."""
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))
    except Exception as e:
        print("fetch fail", url[:65], e)
        return {}


def key_of(n):
    """Normalize a player name to a stable key (fold accents, drop punctuation) so dedup is robust."""
    s = unicodedata.normalize("NFKD", str(n or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("-", " ").replace(".", " ").replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip() or str(n or "").lower()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # load the dedup memory (what we've already logged)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    inj_state = state.get("inj", {})   # player_key -> "status|detail" we last wrote
    lin_state = state.get("lin", {})   # "game_id|player_key" -> 1 once we've logged that player as confirmed

    # ---- 1) INJURIES: log every time a player's status/detail CHANGES ----
    inj_rows = []
    teams = getj(INJ).get("injuries", [])
    for tm in teams:
        team = tm.get("displayName") or tm.get("abbreviation") or ""
        for it in tm.get("injuries", []):
            name = ((it.get("athlete") or {}).get("displayName"))
            if not name:
                continue
            status = (it.get("status") or "").strip()                      # Out / Day-To-Day / Doubtful / ...
            detail = ((it.get("details") or {}).get("detail")              # short human reason, best-effort
                      or it.get("shortComment")
                      or (it.get("type") or {}).get("description") or "")
            detail = re.sub(r"\s+", " ", str(detail)).strip()[:140]
            k = key_of(name)
            sig = status + "|" + detail
            if inj_state.get(k) != sig:        # changed (or brand new) -> record it
                inj_rows.append([stamp, name, team, status, detail])
                inj_state[k] = sig

    # ---- 2) OFFICIAL LINEUPS: log each player ONCE per game, when first confirmed active/starter ----
    lin_rows = []
    for ev in getj(SB).get("events", []):
        gid = str(ev.get("id") or "")
        if not gid:
            continue
        comp = (ev.get("competitions") or [{}])[0]
        state_str = (((comp.get("status") or {}).get("type") or {}).get("state") or "").lower()
        if state_str not in ("pre", "in"):     # only upcoming/live games -> stays gentle, skips finished games
            continue
        for tm in getj(SUM + gid).get("boxscore", {}).get("players", []):
            team = (tm.get("team") or {}).get("abbreviation") or (tm.get("team") or {}).get("displayName") or ""
            for st in tm.get("statistics", []):
                for a in st.get("athletes", []):
                    nm = (a.get("athlete") or {}).get("displayName")
                    if not nm:
                        continue
                    ck = gid + "|" + key_of(nm)
                    if not lin_state.get(ck):                          # first time we see this player confirmed
                        role = "starter" if a.get("starter") else "active"
                        lin_rows.append([stamp, gid, nm, team, role])
                        lin_state[ck] = 1

    # ---- write (append, create header on first run) ----
    def append(path, header, rows):
        if not rows:
            return 0
        new_file = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(header)
            w.writerows(rows)
        return len(rows)

    ni = append(INJ_CSV, ["captured_utc", "player", "team", "status", "detail"], inj_rows)
    nl = append(LIN_CSV, ["captured_utc", "game_id", "player", "team", "role"], lin_rows)
    json.dump({"inj": inj_state, "lin": lin_state}, open(STATE, "w"))
    print(f"news: +{ni} injury change(s), +{nl} lineup confirmation(s)  (feed: {len(teams)} teams)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                 # never let a news hiccup fail the capture workflow
        print("capture_news error (ignored):", e)
    sys.exit(0)
