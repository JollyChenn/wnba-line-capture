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

# Anchor the slate to the US sports day, NOT the local (Malaysia) clock. After midnight
# MYT, datetime.date.today() rolls to tomorrow and silently skips tonight's US games
# (the timezone bug from NBA_HANDOFF §5.2). The cloud runs UTC so it was fine; this makes
# a local run match. Pacific = latest US tipoffs all land on one calendar day.
try:
    from zoneinfo import ZoneInfo
    _SLATE_TZ = ZoneInfo("America/Los_Angeles")
except Exception:
    _SLATE_TZ = datetime.timezone(datetime.timedelta(hours=-7))   # PDT fallback (WNBA season is always DST)


def _slate_today():
    return datetime.datetime.now(_SLATE_TZ).date()

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
FAIR_P = {   # per market — PRA combos run slightly lower than PTS (gauntlet-measured)
    "pts": {"shrink+cold+stingy": 0.70, "shrink+cold": 0.684, "shrink+stingy": 0.642, "cold+stingy": 0.626},
    "pra": {"shrink+cold+stingy": 0.66, "shrink+cold": 0.641, "shrink+stingy": 0.620, "cold+stingy": 0.621},
}
FAIR_DEFAULT = 0.60              # any-2-of-3 floor (both markets ~61.7%, shaded for safety)
CASCADE_FAIR_P = 0.57           # star-out cascade rank3-6 PRA OVER
# HOT-streak OVER on PRA (only over-market that passed the gauntlet): hot+expanding+leaky
OVER_FAIR_P = {"hot+leaky": 0.62, "hot+expand+leaky": 0.62, "hot+expand": 0.55}
OVER_DEFAULT = 0.58             # PRA hot any-2-of-3 = 58.7%
STAR_PRA_MIN = 22.0            # PRA is STAR-ONLY on 1xbet -> only PING overs for high-PRA stars
#                               (role-player PRA-overs you can't actually bet stay in PICKS.md, not the ping)


def fair_odds(p):
    return round(1.0 / p, 2)


import math
def _ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def _nppf(p):
    # Acklam inverse-normal approximation (no scipy needed in CI)
    p = min(max(p, 1e-6), 1 - 1e-6)
    a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239]
    b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1]
    c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p <= 1 - pl:
        q = p - 0.5; r = q*q; return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1-p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

def fair_ladder(our_line, p, sd, offsets=(-1, 0, 1)):
    """Fair UNDER odds at our_line+offset, given hit-rate p at our_line and spread sd.
    mu implied so P(under our_line)=p; extrapolate with a Normal(mu, sd)."""
    zp = _nppf(p)
    out = []
    for off in offsets:
        pu = _ncdf(zp + off / max(sd, 1.0))      # P(under our_line+off)
        out.append((our_line + off, round(1.0 / max(pu, 0.01), 2)))
    return out


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
        body = "\n\n✅ **BET 1u** _(only if 1xbet beats the fair odds)_\n" + "\n".join(core_picks)
    else:
        body = "\n\n😴 No core bet today."
    casc = f"\n_+{len(cascade_lines)} cascade watches in PICKS.md_" if cascade_lines else ""
    msg = head + body + casc
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
    today = _slate_today()
    fin_all, upcoming = [], []
    d = SEASON_START
    while d <= today + datetime.timedelta(days=1):
        fin, up = fetch_day(d)
        fin_all += [g for g in fin if g["game_id"] not in have]
        if d >= today:
            upcoming += up
        d += datetime.timedelta(days=1)
    newbox, ok_games = [], []                       # only record a game once its box is safely fetched (a failed box must be RETRIED, not lost forever)
    for g in fin_all:
        try:
            b = fetch_box(g["game_id"])
        except Exception as e:
            print(f"  box {g['game_id']} failed (will retry next run): {e}"); continue
        if b:
            newbox += b; ok_games.append(g)
    if newbox:                                      # write BOX first, then games, so a mid-write crash can't leave a game recorded with no box
        box = pd.concat([box, pd.DataFrame(newbox)], ignore_index=True).drop_duplicates(["game_id", "aid"], keep="last")
        box.to_csv(BOX_CSV, index=False)
    if ok_games:
        games = pd.concat([games, pd.DataFrame(ok_games)], ignore_index=True).drop_duplicates("game_id", keep="last")
        games.to_csv(GAMES_CSV, index=False)
    print(f"games: {len(games)} (+{len(ok_games)} new) | box rows: {len(box)} | upcoming: {len(upcoming)}")
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
            "t3_pts": grp.pts.tail(3).mean(), "t3_pra": grp.pra.tail(3).mean(),
            "med_pr": (last.pts + last.reb).median(), "t3_pr": (grp.pts + grp.reb).tail(3).mean(),
            "med_pa": (last.pts + last.ast).median(), "t3_pa": (grp.pts + grp.ast).tail(3).mean(),
            "med_ra": (last.reb + last.ast).median(), "t3_ra": (grp.reb + grp.ast).tail(3).mean(),
            "t5_min": grp["min"].tail(5).mean(), "t10_min": last["min"].mean(),
            "sd_pts": max(last.pts.std(), 3.0), "sd_pra": max(last.pra.std(), 4.0),
            "sd_pr": max((last.pts + last.reb).std(), 3.5), "sd_pa": max((last.pts + last.ast).std(), 3.5),
            "sd_ra": max((last.reb + last.ast).std(), 2.5),
            "med_reb": last.reb.median(), "t3_reb": grp.reb.tail(3).mean(), "sd_reb": max(last.reb.std(), 2.0),
            "med_ast": last.ast.median(), "t3_ast": grp.ast.tail(3).mean(), "sd_ast": max(last.ast.std(), 1.5),
            "med5_min": grp["min"].tail(5).median(), "med10_min": last["min"].median(),
            "last_min": grp["min"].iloc[-1],
            "recent_min": " ".join(f"{m:.0f}" for m in grp["min"].tail(5)),
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
    leaky_thr = np.nanpercentile(list(dmap.values()), 75)   # top-quartile defense = LEAKY (for hot-overs)

    today = _slate_today()
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
        sub["shrink"] = sub.trend <= -3                       # validated trigger (mean) — keep
        sub["stingy"] = sub.opp_def <= stingy_thr
        # HONEST sub-labels for WHY minutes look down (the mean trigger gets fooled by a
        # single anomaly game; median tells us if it's a real consistent decline):
        sub["declining"] = sub.med5_min <= sub.med10_min - 2          # consistent role cut
        sub["disrupted"] = sub.last_min < 0.6 * sub.med10_min         # one anomalous low game
        # All deployable markets (passed cluster + shading). Priority order = robustness +
        # availability. A player shows every market they independently qualify for; you bet
        # the first one 1xbet offers (they're correlated — ONE bet per player).
        #   (key, floor, cold_thr, uses_stingy, label, fair_default)
        # ORDER = AVAILABILITY on the book (NOT robustness). PRA is STAR-ONLY on 1xbet/melbet,
        # so it goes LAST — lead with POINTS (offered for everyone), then the 2-way combos.
        # Edge is nearly identical (pts any-2 61.8% vs PRA 61.7%), so leading with points costs
        # ~nothing and means the headline market is one you can actually bet.
        MKTS = [("pts", 8.5, 4, True, "points", 0.60), ("pr", 11.5, 4, True, "PR", 0.59),
                ("pa", 11.5, 4, True, "PA", 0.61), ("ra", 6.5, 3, False, "RA", 0.61),
                ("pra", 13.5, 4, True, "PRA", 0.60),
                ("reb", 3.5, 2, False, "reb", 0.58), ("ast", 2.5, 2, False, "ast", 0.58)]  # singles: fragile
        FRAGILE = {"reb", "ast"}                          # real edge but die on a 1pt shade — book-line-near-median only
        pm = {}
        for mkt, floor_, cthr, use_st, label, fdef in MKTS:
            cold = sub[f"t3_{mkt}"] <= sub[f"med_{mkt}"] - cthr
            ok = ((sub.shrink.astype(int) + cold.astype(int) + sub.stingy.astype(int)) >= 2) if use_st \
                 else (sub.shrink & cold)
            for idx, r in sub[ok & (sub[f"med_{mkt}"] >= floor_)].iterrows():
                slab = "declining" if r.declining else ("disrupted" if r.disrupted else "mins-dip")
                flags = [(slab, bool(r.shrink)), ("cold", bool(cold[idx]))]
                if use_st:
                    flags.append(("stingy", bool(r.stingy)))
                tg = "+".join(t for t, on in flags if on)
                # consistent declines get the validated combo rate; noisy "disrupted"/dip
                # one-offs fall to the conservative default (they're a weaker signal).
                fair_key = tg.replace("declining", "shrink")
                fp = FAIR_P.get(mkt, {}).get(fair_key, fdef); fo = fair_odds(fp)
                ln = float(np.floor(r[f"med_{mkt}"] - 0.001) + 0.5)
                pm.setdefault(r.player, {"r": r, "opts": []})
                pm[r.player]["opts"].append((label, ln, tg, fp, fo, mkt))
        for player, d in pm.items():
            r = d["r"]
            shown = d["opts"][:5]                      # FULL menu (PRA is star-only on books — list every option)
            parts = []
            for i, (label, ln, tg, fp, fo, mkt) in enumerate(shown):
                sd_m = r[f"sd_{mkt}"]; med = r[f"med_{mkt}"]
                mu = ln - sd_m * _nppf(fp)             # our forward projection (≈ where the book centers)
                frag = "⚠frag" if mkt in FRAGILE else ""
                if i == 0:                             # primary: median + projection + fair ladder (value zone)
                    c = round(mu * 2) / 2
                    lad = " ".join(f"{c+off:.1f}={round(1/max(_ncdf((c+off-mu)/max(sd_m,1)),0.01),2)}" for off in (0, 1, 2))
                    parts.append(f"{label} median~{med:.0f}→proj~{mu:.1f} fair[{lad}]")
                else:
                    parts.append(f"{label}{frag} {med:.0f}→{mu:.1f}")
            opts = " · ".join(parts)
            tg0 = shown[0][2]
            warn = " ⚠VERIFY (last game anomaly — skip if blowout/garbage time)" if r.disrupted and not r.declining else ""
            lines_md.append(f"- **{player}** ({NAME(r.team)}, {NAME(a)} @ {NAME(h)}): {opts} "
                            f"· [{tg0}] · last5 mins [{r.recent_min}] oppDef {r.opp_def:.0f}{warn} "
                            f"· UNDER value zone = book line between proj and median (MAX edge near median=book naive, NONE near proj=book moved)")
            for label, ln, tg, fp, fo, mkt in d["opts"]:
                mu = round(ln - r[f"sd_{mkt}"] * _nppf(fp), 1)     # our projection (for CLV grading)
                log_rows.append([str(today), gm_["game_id"], player, NAME(r.team), NAME(opp_of[r.team]),
                                 f"{mkt}_under", ln, tg, round(fp, 3), fo, mu, round(r[f"sd_{mkt}"], 2)])
            if not (r.disrupted and not r.declining):     # don't PING one-game minute anomalies (still listed in PICKS.md w/ ⚠VERIFY)
                core_picks.append(f"• **{player}** ({NAME(r.team)}) — {opts}")
            n_unders += 1

        # HOT-streak OVER on PRA (the one over-market that cleared the gauntlet, 58.7%)
        sub["leaky"] = sub.opp_def >= leaky_thr
        for idx, r in sub[sub.med_pra >= 13.5].iterrows():
            if r.player in pm:                          # hot & cold are mutually exclusive — skip dupes
                continue
            hot = bool(r.t3_pra >= r.med_pra + 4); exp = bool(r.trend >= 3); lk = bool(r.leaky)
            if (int(hot) + int(exp) + int(lk)) < 2:
                continue
            tg = "+".join(t for t, on in [("hot", hot), ("expand", exp), ("leaky", lk)] if on)
            fp = OVER_FAIR_P.get(tg, OVER_DEFAULT); fo = fair_odds(fp)
            med = r.med_pra; sd_m = r.sd_pra
            mu = med + sd_m * _nppf(fp)                  # over projection (ABOVE the median)
            c = round(mu * 2) / 2
            lad = " ".join(f"{c-off:.1f}={round(1/max(_ncdf((mu-(c-off))/max(sd_m,1)),0.01),2)}" for off in (0, 1, 2))
            ln = float(np.floor(med - 0.001) + 0.5)
            lines_md.append(f"- **{r.player}** ({NAME(r.team)}, {NAME(a)} @ {NAME(h)}): **PRA OVER** "
                            f"median~{med:.0f}→proj~{mu:.1f} fair[{lad}] · [{tg}] · "
                            f"last5 mins [{r.recent_min}] oppDef {r.opp_def:.0f} "
                            f"· OVER value zone = book line between median and proj (MAX edge near median)")
            log_rows.append([str(today), gm_["game_id"], r.player, NAME(r.team), NAME(opp_of[r.team]),
                             "pra_over", ln, tg, round(fp, 3), fo, round(mu, 1), round(r.sd_pra, 2)])
            if med >= STAR_PRA_MIN:     # PRA star-only on 1xbet -> only PING star overs (role overs stay in PICKS.md)
                core_picks.append(f"• **{r.player}** ({NAME(r.team)}) — PRA OVER median~{med:.0f}→proj~{mu:.1f} [{tg}]")
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
            names = ", ".join(f"{b.player} OVER {np.floor(b.med_pra - 0.001) + 0.5:.1f} PRA"
                              for _, b in ben.iterrows())
            lines_md.append(f"- {NAME(tm)}: if **{star.player}** OUT -> (fair {fair_odds(CASCADE_FAIR_P)}, "
                            f"bet if 1xbet over > {fair_odds(CASCADE_FAIR_P)}) {names}")
            top2 = ", ".join(b.player.split()[-1] for _, b in ben.head(2).iterrows())
            cascade_lines.append(f"• {tm}: {star.player} OUT → {top2}…")

    lines_md += ["", "---", "_Rules: flat 1u stakes. Bet 1xbet only where its line >= anchor (under) or",
                 "<= anchor (cascade over). Skip Clark props. Grade vs Pinnacle close (line_snapshots.csv)._"]
    open(PICKS_MD, "w", encoding="utf-8").write("\n".join(lines_md) + "\n")

    # IDEMPOTENT write: re-running the same day REPLACES today's rows (never stacks
    # duplicates — that's the counting-artifact bug we refuse to reintroduce).
    cols = ["pick_date", "game_id", "player", "team", "opp", "market", "anchor", "signals", "fair_p", "fair_odds", "proj", "sd"]
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
