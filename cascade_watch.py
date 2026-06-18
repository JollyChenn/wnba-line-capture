# ============================================================================
# cascade_watch.py — fire the cascade edge on SCRATCH NEWS (cloud, near tip)
# ============================================================================
# The cascade is the one edge the book can't pre-price: when a team's top-usage
# player is ruled OUT, the rank-3-6 teammates' PRA jumps but their props lag for
# 20-40 min (no-lineup-submission rule). This polls the FREE ESPN injuries feed
# and pings Discord the instant a flagged star flips to Out/Doubtful — with the
# beneficiaries + their PRA lines ready to fire.
#
# Idempotent: cascade_pinged.json remembers who we've already alerted (one ping
# per scratch). Reads the usage cache daily_picks maintains (data/box_2026.csv).
#
# Run frequently during game hours (workflow: every 20 min, 19:00-03:00 UTC).
# ============================================================================
import os, sys, json, csv, datetime
import requests, pandas as pd, numpy as np
try:
    import cloud_xbet as cx                  # reuse the 1xbet board-pull + helpers for live-line capture
except Exception:                            # never let a missing dep (e.g. curl_cffi) break the alert
    cx = None
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
_H = {"User-Agent": "Mozilla/5.0"}
SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
INJ = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries"
STATE = "cascade_pinged.json"
SCRATCH = {"out", "doubtful"}


def today_teams():
    try:
        r = requests.get(SB, headers=_H, timeout=20).json()
    except Exception:
        return set()
    teams = set()
    for ev in r.get("events", []):
        if (ev.get("status") or {}).get("type", {}).get("completed"):
            continue                                   # already played
        for c in (ev.get("competitions") or [{}])[0].get("competitors", []):
            ab = (c.get("team") or {}).get("abbreviation")
            if ab: teams.add(ab)
    return teams


def injuries():
    try:
        r = requests.get(INJ, headers=_H, timeout=20).json()
    except Exception:
        return {}
    out = {}
    for tm in r.get("injuries", []):
        for it in tm.get("injuries", []):
            ath = (it.get("athlete") or {}).get("displayName")
            st = (it.get("status") or "").lower()
            if ath: out[ath] = st
    return out


def _scratched(name, inj):
    """True if this player is OUT/doubtful. Exact match first, then first-initial+surname fallback for
    minor name-format diffs (so a beneficiary who is HERSELF out — e.g. Kiki Iriafen, ankle — is dropped)."""
    s = inj.get(name, "").lower()
    if s:
        return s in SCRATCH
    parts = name.lower().split()
    if len(parts) >= 2:
        key = parts[0][0] + " " + parts[-1]
        for k, v in inj.items():
            kp = k.lower().split()
            if len(kp) >= 2 and kp[0][0] + " " + kp[-1] == key:
                return v.lower() in SCRATCH
    return False


def watchlist():
    """Top-usage star + rank-3-6 PRA-beneficiaries per team, from the usage cache."""
    if not os.path.exists("data/box_2026.csv"):
        return {}
    box = pd.read_csv("data/box_2026.csv", dtype={"game_id": str})
    g = pd.read_csv("data/games_2026.csv", dtype={"game_id": str})
    box = box.join(g.set_index("game_id")[["date"]], on="game_id")
    box["dt"] = pd.to_datetime(box.date.astype(str), format="%Y%m%d", errors="coerce")
    for c in ["pts", "reb", "ast", "fga", "fta", "to", "min"]:
        box[c] = pd.to_numeric(box[c], errors="coerce")
    box["pra"] = box.pts + box.reb + box.ast
    box["usg"] = box.fga + 0.44 * box.fta + box.to
    box = box.sort_values(["aid", "dt"])
    feats = []
    for (aid, team), grp in box.groupby(["aid", "team"]):
        if len(grp) < 5: continue
        feats.append({"player": grp.player.iloc[-1], "team": team,
                      "usg": grp.usg.tail(5).mean(), "med_pra": grp.pra.tail(10).median(),
                      "mins": grp["min"].tail(5).mean()})
    f = pd.DataFrame(feats)
    wl = {}
    for team, tt in f.groupby("team"):
        tt = tt.sort_values("usg", ascending=False)
        if len(tt) < 5: continue
        star = tt.iloc[0]
        if star.mins < 24: continue                    # only real starters as the trigger
        ben = tt.iloc[2:6]
        wl[team] = {"star": star.player,
                    "ben": [(b.player, float(np.floor(b.med_pra - 0.001) + 0.5)) for _, b in ben.iterrows()]}
    return wl


def _capture_cascade(legs_by_team):
    """Pull the LIVE 1xbet PRA over for each beneficiary and append qualifying legs to
    bets_log.csv (src=cascade) so they GRADE with REAL odds + CLV (not a synthetic anchor).
    Best-effort: any failure is swallowed so the Discord alert is never affected."""
    if cx is None:
        print("  cloud_xbet unavailable -> cascade line-capture skipped (alert still sent)"); return
    disc = cx.get(f"{cx.BASE}/LineFeed/Get1x2_VZip?sports=3&champs={cx.CHAMP}"
                  "&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
    games = [e for e in (disc or {}).get("Value", []) if isinstance(e, dict) and e.get("I")]
    props = {}
    for e in games:
        mv = cx.get(cx.gz(e["I"]))
        sg = (mv.get("Value", {}) or {}).get("SG", []) if mv else []
        stat = next((s for s in sg if "stat" in str(s.get("TG", "")).lower()), None)
        if not stat:
            continue
        val = (cx.get(cx.gz(stat["I"])) or {}).get("Value", {}) or {}
        def walk(o):
            if isinstance(o, dict):
                pl, T = o.get("PL"), o.get("T")
                if isinstance(pl, dict) and T in cx.T2S and o.get("P") is not None and o.get("C"):
                    st, sd = cx.T2S[T]
                    props.setdefault(str(pl.get("N", "")).lower(), {}).setdefault((st, sd), []).append((float(o["P"]), float(o["C"])))
                for x in o.values(): walk(x)
            elif isinstance(o, list):
                for x in o: walk(x)
        walk(val)

    stamp = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    today_la = datetime.datetime.now(cx._SLATE_TZ).date().isoformat()    # slate date (matches cloud_xbet/grade_bets)
    seen = set()                                                          # don't double-log the same leg today
    if os.path.exists("bets_log.csv"):
        for r in csv.DictReader(open("bets_log.csv", encoding="utf-8")):
            if r.get("date") == today_la and r.get("src") == "cascade":
                seen.add(r["player"].lower())
    rows = []
    for team, ben in legs_by_team.items():
        for p, syn in ben:
            if p.lower() in seen:
                continue
            live = cx.pra_line(props, p)
            if not live:
                continue                                                  # line not posted yet -> a later cycle / cloud_xbet catches it
            bline, bodds = float(live[0]), float(live[1])
            if bline <= syn + 1 and bodds > cx.CASC_FAIR:                 # value zone + price beats fair (the actual bet rule)
                rows.append([stamp, today_la, p, "pra", "Over", bline, bodds,
                             "CASC", round(bodds / cx.CASC_FAIR - 1, 3), "", "cascade"])
    if rows:
        newf = not os.path.exists("bets_log.csv")
        with open("bets_log.csv", "a", newline="", encoding="utf-8") as bf:
            w = csv.writer(bf)
            if newf:
                w.writerow(["captured_utc", "date", "player", "market", "side", "line", "odds", "tier", "ev", "pinn", "src"])
            w.writerows(rows)
        print(f"  captured {len(rows)} cascade leg(s) -> bets_log (REAL 1xbet line, src=cascade)")
    else:
        print("  no qualifying live cascade line yet (no real PRA line in value zone > fair)")


def main():
    state = set(json.load(open(STATE))) if os.path.exists(STATE) else set()
    teams = today_teams()
    if not teams:
        print("no upcoming games right now"); return
    inj, wl = injuries(), watchlist()
    today = datetime.date.today().isoformat()
    new = []
    for team in teams:
        w = wl.get(team)
        if not w: continue
        star = w["star"]; st = inj.get(star, "")
        key = f"{today}|{star}"
        if st in SCRATCH and key not in state:
            new.append((team, star, st, w["ben"])); state.add(key)
    if new:
        legs_by_team = {}
        for team, star, st, ben in new:
            ben = [(p, ln) for p, ln in ben if not _scratched(p, inj)]   # drop beneficiaries who are THEMSELVES out — they can't carry the cascade (Kiki Iriafen ankle bug)
            if not ben:
                print(f"  {star} scratch but every beneficiary is also out — no cascade"); continue
            legs_by_team[team] = ben
            tg = ", ".join(f"{p} OVER {ln:.1f} PRA" for p, ln in ben)
            msg = (f"🚨 **SCRATCH — {star} ({team}) {st.upper()}**\n"
                   f"Cascade → **PRA OVER** (fair ~1.75): {tg}\n"
                   f"_Fire FAST at 1xbet/Melbet if line ≤ shown & price > 1.75 — window is 20-40 min._")
            if WEBHOOK:
                try: requests.post(WEBHOOK, json={"content": msg}, headers=_H, timeout=15)
                except Exception as e: print("discord err", e)
            print("PINGED:", star, team, st)
        if legs_by_team:
            try: _capture_cascade(legs_by_team)          # log REAL 1xbet lines -> bets_log (src=cascade) so the cascade GRADES with odds + CLV
            except Exception as e: print("cascade capture err (alert unaffected):", e)
        json.dump(sorted(state), open(STATE, "w"))
    else:
        nstars = sum(1 for t in teams if wl.get(t))
        print(f"checked {len(teams)} teams / {nstars} watch-stars — no NEW scratches")


if __name__ == "__main__":
    main()
