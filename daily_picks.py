# ============================================================================
# daily_picks.py — CORE-ONLY WNBA picks, cloud-runnable (GitHub Actions)
# ============================================================================
# Generates the REAL-MONEY core portfolio only (the validated 11-season backtest):
#   UNDER pts  : any 2 of {minutes-shrink, cold-form, stingy-defense}  (61.6%)
#   CASCADE    : contingency list — if a team's top-usage starter is ruled OUT,
#                PRA OVER on the rank-3-6 usage teammates                (57.0%)
# Everything else (singles) is filler tier — NOT printed here by design.
#
# Self-contained: pulls the 2026 season from ESPN (keyless), caches game data in
# data/box_2026.csv (committed back by the workflow; only NEW games fetched each
# run), writes PICKS.md (human) + appends picks_log.csv (machine — graded later
# vs line_snapshots.csv for CLV).
#
# Run:  python daily_picks.py            (locally or in Actions)
# ============================================================================
import os, sys, csv, datetime
import requests
import pandas as pd
import numpy as np

_H = {"User-Agent": "Mozilla/5.0"}
SB = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"
SEASON_START = datetime.date(2026, 5, 8)
DATA = "data"; os.makedirs(DATA, exist_ok=True)
BOX_CSV = os.path.join(DATA, "box_2026.csv")
GAMES_CSV = os.path.join(DATA, "games_2026.csv")
PICKS_MD = "PICKS.md"
LOG_CSV = "picks_log.csv"
IDX = {"min": 0, "pts": 1, "fg": 2, "tp": 3, "ft": 4, "reb": 5, "ast": 6,
       "to": 7, "stl": 8, "blk": 9, "oreb": 10, "dreb": 11, "pf": 12, "pm": 13}
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")    # set as a GitHub secret; never hardcode

# Fair P(win) by signal combo, from the corrected 11-season backtest (final_backtest.py).
# Historical hit rate vs the median-anchor line = the fair win probability.
# fair (no-vig) decimal odds = 1 / P. BET ONLY when 1xbet's price EXCEEDS fair (that gap
# is the captured edge). These are historical, so demand a real margin, not a razor-thin beat.
FAIR_P = {
    "shrink+cold+stingy": 0.70,   # backtest 76% (n=38) shaded down for the tiny sample
    "shrink+cold":        0.684,
    "shrink+stingy":      0.642,
    "cold+stingy":        0.620,
    "shrink":             0.594, "cold": 0.588, "stingy": 0.560,
}
CASCADE_FAIR_P = 0.57             # star-out cascade rank3-6 PRA OVER


def fair_odds(p):
    return round(1.0 / p, 2)


# ESPN team code -> full name (2026 WNBA, 15 teams + historical aliases)
TEAM_NAMES = {
    "ATL": "Atlanta Dream", "CHI": "Chicago Sky", "CON": "Connecticut Sun",
    "CONN": "Connecticut Sun", "DAL": "Dallas Wings", "GS": "Golden State Valkyries",
    "IND": "Indiana Fever", "LA": "Los Angeles Sparks", "LV": "Las Vegas Aces",
    "LVA": "Las Vegas Aces", "MIN": "Minnesota Lynx", "NY": "New York Liberty",
    "PHX": "Phoenix Mercury", "POR": "Portland Fire", "SEA": "Seattle Storm",
    "TOR": "Toronto Tempo", "WSH": "Washington Mystics", "WAS": "Washington Mystics",
    "SA": "San Antonio Stars",
}
def NAME(code):
    return TEAM_NAMES.get(code, code)


def notify_discord(date, core_picks, cascade_lines):
    """Ping Discord with the day's core signal. Heartbeat even on quiet days so
    you know the cron is alive. Webhook comes from env (DISCORD_WEBHOOK), not code."""
    if not DISCORD_WEBHOOK:
        print("discord: no webhook set, skipping ping")
        return
    head = f"🏀 **WNBA — {date}**"
    if core_picks:
        body = (f"\n\n✅ **BET NOW — {len(core_picks)} core UNDER(s), 1u each:**\n" + "\n".join(core_picks)
                + "\n_Bet at 1xbet only if its line ≥ the number shown._")
    else:
        body = "\n\n😴 **No core bet today.** Sit out — do NOT reach for singles."
    # cascade is a CONTINGENCY, not a bet — one-line pointer only, full list in PICKS.md
    casc = (f"\n\n_(+{len(cascade_lines)} cascade contingencies in PICKS.md — only if a star is scratched)_"
            if cascade_lines else "")
    foot = "\n_Flat 1u. Never Clark. Graded vs Pinnacle close._"
    msg = head + body + casc + foot
    if len(msg) > 1900:
        msg = msg[:1880] + "\n…(truncated — see PICKS.md)"
    try:
        r = requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=15)
        print(f"discord ping: HTTP {r.status_code}")
    except Exception as e:
        print(f"discord notify failed: {e}")


def _f(x):
    try: return float(str(x).split("-")[0]) if "-" in str(x) and ":" not in str(x) else float(x)
    except Exception: return float("nan")


def fetch_day(d):
    """Scoreboard for one date -> (finished games list, upcoming games list)."""
    try:
        r = requests.get(SB, params={"dates": d.strftime("%Y%m%d")}, headers=_H, timeout=20)
        r.raise_for_status(); js = r.json()
    except Exception:
        return [], []
    fin, up = [], []
    for ev in js.get("events", []):
        if (ev.get("season") or {}).get("type") != 2:
            continue                                   # regular season only
        comp = (ev.get("competitions") or [{}])[0]
        cs = comp.get("competitors", [])
        home = next((t for t in cs if t.get("homeAway") == "home"), {})
        away = next((t for t in cs if t.get("homeAway") == "away"), {})
        g = {"game_id": ev.get("id"), "date": d.strftime("%Y%m%d"),
             "home": (home.get("team") or {}).get("abbreviation"),
             "away": (away.get("team") or {}).get("abbreviation"),
             "tip": ev.get("date", "")}
        if (ev.get("status") or {}).get("type", {}).get("completed"):
            g["home_score"] = _f(home.get("score")); g["away_score"] = _f(away.get("score"))
            fin.append(g)
        else:
            up.append(g)
    return fin, up


def fetch_box(gid):
    """Per-player box for one finished game (ESPN summary)."""
    r = requests.get(SUMMARY, params={"event": gid}, headers=_H, timeout=20)
    r.raise_for_status()
    rows = []
    for tm in r.json().get("boxscore", {}).get("players", []):
        code = (tm.get("team") or {}).get("abbreviation")
        for sg in tm.get("statistics", []) or []:
            for a in sg.get("athletes", []) or []:
                st = a.get("stats", []) or []
                if len(st) <= IDX["pm"]:
                    continue
                mn = _f(st[IDX["min"]])
                if not (mn > 0):
                    continue
                ath = a.get("athlete", {}) or {}
                fga = _f(str(st[IDX["fg"]]).split("-")[-1])
                fta = _f(str(st[IDX["ft"]]).split("-")[-1])
                rows.append({"game_id": str(gid), "team": code, "player": ath.get("displayName"),
                             "aid": ath.get("id"), "min": mn, "pts": _f(st[IDX["pts"]]),
                             "reb": _f(st[IDX["reb"]]), "ast": _f(st[IDX["ast"]]),
                             "fga": fga, "fta": fta, "to": _f(st[IDX["to"]])})
    return rows


def refresh():
    """Incremental: fetch finished games + boxes we don't have; return (games, box, upcoming)."""
    games = pd.read_csv(GAMES_CSV, dtype={"game_id": str}) if os.path.exists(GAMES_CSV) else pd.DataFrame()
    box = pd.read_csv(BOX_CSV, dtype={"game_id": str}) if os.path.exists(BOX_CSV) else pd.DataFrame()
    have = set(games.game_id) if len(games) else set()
    today = datetime.date.today()
    fin_all, upcoming = [], []
    d = SEASON_START
    while d <= today + datetime.timedelta(days=1):
        fin, up = fetch_day(d)
        fin_all += [g for g in fin if g["game_id"] not in have]
        if d >= today:
            upcoming += up
        d += datetime.timedelta(days=1)
    newbox = []
    for g in fin_all:
        try:
            newbox += fetch_box(g["game_id"])
        except Exception as e:
            print(f"  box {g['game_id']} failed: {e}")
    if fin_all:
        games = pd.concat([games, pd.DataFrame(fin_all)], ignore_index=True)
        games.to_csv(GAMES_CSV, index=False)
    if newbox:
        box = pd.concat([box, pd.DataFrame(newbox)], ignore_index=True)
        box.to_csv(BOX_CSV, index=False)
    print(f"games: {len(games)} (+{len(fin_all)} new) | box rows: {len(box)} | upcoming: {len(upcoming)}")
    return games, box, upcoming


def main():
    games, box, upcoming = refresh()
    if box.empty or not upcoming:
        open(PICKS_MD, "w", encoding="utf-8").write(
            f"# WNBA core picks — {datetime.date.today()}\n\nNo upcoming games found.\n")
        print("no upcoming games"); return

    # join date + opponent onto box
    meta = games.set_index("game_id")
    box = box.join(meta[["date", "home", "away"]], on="game_id").dropna(subset=["date"])
    box["opp"] = np.where(box.team == box.home, box.away, box.home)
    box["dt"] = pd.to_datetime(box.date.astype(str), format="%Y%m%d")
    box["pra"] = box.pts + box.reb + box.ast
    box["usg_raw"] = box.fga + 0.44 * box.fta + box.to
    box = box.sort_values(["aid", "dt"])
    g = box.groupby("aid")
    feats = []
    for aid, grp in g:
        if len(grp) < 6:
            continue
        last = grp.tail(10)
        feats.append({
            "aid": aid, "player": grp.player.iloc[-1], "team": grp.team.iloc[-1],
            "med_pts": last.pts.median(), "med_pra": last.pra.median(),
            "t3_pts": grp.pts.tail(3).mean(),
            "t5_min": grp["min"].tail(5).mean(), "t10_min": last["min"].mean(),
            "usg": grp.usg_raw.tail(5).mean(),
        })
    f = pd.DataFrame(feats)
    f["trend"] = f.t5_min - f.t10_min

    # team trailing-10 defense (points allowed)
    da = pd.concat([
        games.rename(columns={"home": "team"})[["team", "date"]].assign(allowed=games.away_score),
        games.rename(columns={"away": "team"})[["team", "date"]].assign(allowed=games.home_score),
    ])
    da["dt"] = pd.to_datetime(da.date.astype(str), format="%Y%m%d")
    dmap = {t: d.sort_values("dt").allowed.tail(10).mean() for t, d in da.groupby("team")}
    stingy_thr = np.nanpercentile(list(dmap.values()), 25)

    today = datetime.date.today()
    lines_md = [f"# WNBA core picks — {today}",
                "", f"_Stingy-D threshold (trailing-10 allowed, bottom quartile): {stingy_thr:.0f}_",
                "", "## REAL-MONEY CORE — UNDER pts (need >=2 signals, flat 1u)", ""]
    log_rows = []
    core_picks = []          # compact lines for the Discord ping
    cascade_lines = []
    n_unders = 0
    for gm_ in upcoming:
        a, h = gm_["away"], gm_["home"]
        opp_of = {a: h, h: a}
        sub = f[f.team.isin([a, h])].copy()
        if sub.empty:
            continue
        sub["opp_def"] = sub.team.map(lambda t: dmap.get(opp_of.get(t), np.nan))
        sub["shrink"] = sub.trend <= -3
        sub["cold"] = sub.t3_pts <= sub.med_pts - 4
        sub["stingy"] = sub.opp_def <= stingy_thr
        sub["nsig"] = sub[["shrink", "cold", "stingy"]].sum(axis=1)
        core = sub[(sub.nsig >= 2) & (sub.med_pts >= 8.5)]
        for _, r in core.iterrows():
            tags = "+".join(t for t, on in [("shrink", r.shrink), ("cold", r.cold), ("stingy", r.stingy)] if on)
            p = FAIR_P.get(tags, 0.58)
            fo = fair_odds(p)
            lines_md.append(f"- **UNDER {r.player}** ({NAME(r.team)}, {NAME(a)} @ {NAME(h)}) — "
                            f"pts line ~**{r.med_pts:.1f}** [{tags}] · fair **{p*100:.0f}%** = **{fo}** dec "
                            f"→ BET if 1xbet under > {fo} · mins {r.t5_min:.0f} trend {r.trend:+.1f} oppDef {r.opp_def:.0f}")
            log_rows.append([str(today), gm_["game_id"], r.player, NAME(r.team), NAME(opp_of[r.team]),
                             "pts_under", round(r.med_pts, 1), tags, round(p, 3), fo])
            core_picks.append(f"• UNDER **{r.player}** ({NAME(r.team)}) pts ~{r.med_pts:.1f} — "
                              f"fair **{fo}** _(bet only if 1xbet > {fo})_")
            n_unders += 1
    if not n_unders:
        lines_md.append("_(no 2-signal core unders today — do NOT reach for singles)_")

    lines_md += ["", "## CASCADE contingencies — fire ONLY on scratch news (PRA OVER rank-3-6, flat 1u)", ""]
    for gm_ in upcoming:
        a, h = gm_["away"], gm_["home"]
        for tm in (a, h):
            tt = f[f.team == tm].sort_values("usg", ascending=False)
            if len(tt) < 5:
                continue
            star = tt.iloc[0]
            ben = tt.iloc[2:6]
            names = ", ".join(f"{b.player} (pra {b.med_pra:.0f})" for _, b in ben.iterrows())
            lines_md.append(f"- {NAME(tm)}: if **{star.player}** OUT -> PRA OVER (fair {fair_odds(CASCADE_FAIR_P)}, "
                            f"bet if 1xbet over > {fair_odds(CASCADE_FAIR_P)}): {names}")
            top2 = ", ".join(b.player.split()[-1] for _, b in ben.head(2).iterrows())
            cascade_lines.append(f"• {tm}: {star.player} OUT → {top2}…")

    lines_md += ["", "---", "_Rules: flat 1u stakes. Bet 1xbet only where its line >= anchor (under) or",
                 "<= anchor (cascade over). Skip Clark props. Grade vs Pinnacle close (line_snapshots.csv)._"]
    open(PICKS_MD, "w", encoding="utf-8").write("\n".join(lines_md) + "\n")

    # IDEMPOTENT write: re-running the same day REPLACES today's rows (never stacks
    # duplicates — that's the counting-artifact bug we refuse to reintroduce).
    cols = ["pick_date", "game_id", "player", "team", "opp", "market", "anchor", "signals", "fair_p", "fair_odds"]
    new_df = pd.DataFrame(log_rows, columns=cols)
    if os.path.exists(LOG_CSV):
        old = pd.read_csv(LOG_CSV, dtype=str)
        old = old[old.pick_date != str(today)]
        new_df = pd.concat([old, new_df], ignore_index=True)
    new_df.to_csv(LOG_CSV, index=False)
    print(f"PICKS.md written: {n_unders} core unders + cascade lists. log rows: {len(log_rows)}")
    notify_discord(today, core_picks, cascade_lines)


if __name__ == "__main__":
    main()
