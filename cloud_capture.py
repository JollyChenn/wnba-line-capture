# ============================================================================
# cloud_capture.py — 24/7 WNBA prop-line snapshotter (runs on GitHub Actions)
# ============================================================================
# Ported from the NBA line-capture repo. Captures timestamped Pinnacle (+ other
# EU-book) WNBA prop lines so we can measure CLOSING-LINE VALUE without your
# laptop on. Pinnacle is the SHARP benchmark — beating its close = real edge.
#
# QUOTA-FRUGAL (the-odds-api free tier = 500 req/month, SHARED with the MLB bot):
#   * the /events check is FREE — runs with no near-tip game spend NOTHING.
#   * WNBA games cluster in a few hours (US evening = Malaysia morning), so most
#     of the 24 hourly runs cost 0; only the ~3-4 near-tip runs actually spend.
#   * regions = "eu" ONLY (Pinnacle lives here; US books are useless to a MY
#     bettor) -> HALF the NBA repo's quota. 1xbet isn't on the-odds-api — capture
#     that separately; here we build the Pinnacle CLV benchmark.
#   * default markets = points + PRA (the two strongest role-lag survivors);
#     add rebounds,assists via the CAPTURE_MARKETS secret when quota allows.
#   * cap at MAX_GAMES per run.
#   -> ~2 markets x ~2 games/day x 1 region ~= 4/day ~= 120/month. Tune down if
#      MLB is eating the shared quota (narrow the window or drop to points only).
#
# Zero third-party deps (urllib only) so CI needs no pip install.
# Appends to line_snapshots.csv; the workflow commits it back to the repo.
# Pull the CSV and run CLV analysis locally (clv_from_snapshots.py).
#
# Env:
#   ODDS_API_KEYS / ODDS_API_KEY  (required) the-odds-api key(s) — repo SECRET
#   CAPTURE_MARKETS    default "player_points,player_points_rebounds_assists"
#   CAPTURE_REGIONS    default "eu"     (Pinnacle). widen to "eu,us" only if needed
#   CAPTURE_WINDOW_MIN default "90"     only capture games tipping within this
#   MAX_GAMES          default "5"      hard cap on games captured per run
# ============================================================================
import os, sys, csv, json, datetime, urllib.request, urllib.parse

BASE = "https://api.the-odds-api.com/v4"
SPORT = "basketball_wnba"


def _load_keys():
    """Keys from ODDS_API_KEYS (comma-separated) or ODDS_API_KEY env; else local
    file. Two keys = pooled ~1000 req/month."""
    env = os.environ.get("ODDS_API_KEYS") or os.environ.get("ODDS_API_KEY")
    if env:
        return [k.strip() for k in env.split(",") if k.strip()]
    for fn in (os.path.join("data", ".odds_api_keys"), os.path.join("data", ".odds_api_key")):
        if os.path.exists(fn):
            return [l.strip() for l in open(fn) if l.strip()]
    return []


def _remaining(k):
    """Remaining quota for a key (FREE /sports call). -1 on error."""
    try:
        url = f"{BASE}/sports?" + urllib.parse.urlencode({"apiKey": k})
        req = urllib.request.Request(url, headers={"User-Agent": "wnba-line-capture"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return int(float(r.headers.get("x-requests-remaining", 0)))
    except Exception:
        return -1


_KEYS = _load_keys()
if not _KEYS:
    print("no key — set the ODDS_API_KEYS secret (comma-separated) or ODDS_API_KEY")
    sys.exit(1)
# rotate to the key with the most remaining quota (balances both keys evenly)
KEY = _KEYS[0] if len(_KEYS) == 1 else max(_KEYS, key=_remaining)
MARKETS = [m.strip() for m in os.environ.get(
    "CAPTURE_MARKETS", "player_points,player_points_rebounds_assists").split(",") if m.strip()]
REGIONS = os.environ.get("CAPTURE_REGIONS", "eu")
WINDOW = int(os.environ.get("CAPTURE_WINDOW_MIN", "90"))
MAX_GAMES = int(os.environ.get("MAX_GAMES", "5"))
OUT = "line_snapshots.csv"


def get(path, params):
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "wnba-line-capture"})
    with urllib.request.urlopen(req, timeout=25) as r:
        remaining = r.headers.get("x-requests-remaining")
        return json.load(r), remaining


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.isoformat(timespec="seconds")
    # 1) FREE: list events
    events, rem = get(f"sports/{SPORT}/events", {"apiKey": KEY})
    if not isinstance(events, list) or not events:
        print(f"[{stamp}] no WNBA events. quota remaining {rem}. (free check)"); return

    # 2) keep only games tipping within the window (and not already past tip)
    soon = []
    for e in events:
        tip = datetime.datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00"))
        mins = (tip - now).total_seconds() / 60
        if -10 <= mins <= WINDOW:
            soon.append((mins, e))
    soon.sort(key=lambda t: t[0])   # key= required: bare sort() crashes on tied tip times (multi-game nights)
    soon = soon[:MAX_GAMES]
    if not soon:
        print(f"[{stamp}] no game within {WINDOW} min. quota remaining {rem}. (free check, 0 spent)")
        return

    # 3) capture the configured markets for each near-tip game
    rows = []
    for mins, e in soon:
        for mkt in MARKETS:
            try:
                data, rem = get(f"sports/{SPORT}/events/{e['id']}/odds",
                                {"apiKey": KEY, "regions": REGIONS, "markets": mkt, "oddsFormat": "decimal"})
            except Exception as ex:
                print(f"  {e['id']} {mkt} failed: {ex}"); continue
            for b in data.get("bookmakers", []):
                for m in b.get("markets", []):
                    if m.get("key") != mkt:
                        continue
                    for o in m.get("outcomes", []):
                        if o.get("point") is None:
                            continue
                        rows.append([stamp, e["id"], e["commence_time"], e["away_team"],
                                     e["home_team"], mkt, o.get("description"), o.get("name"),
                                     o.get("point"), o.get("price"), b.get("title")])
        print(f"  captured {e['away_team']} @ {e['home_team']} (tip in {mins:.0f}m)")

    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["captured_utc", "game_id", "tip", "away", "home", "market",
                        "player", "side", "line", "price", "book"])
        w.writerows(rows)
    print(f"[{stamp}] logged {len(rows)} line rows across {len(soon)} game(s). quota remaining {rem}.")


if __name__ == "__main__":
    main()
