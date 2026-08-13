# results_report.py - grade a night's PINGED bets and send the full working to Discord.
# ---------------------------------------------------------------------------------------------
# Shows the raw pts/reb/ast for every bet, not just WIN/LOSS, so the grading can be checked against
# any box score by hand. If a combined market (PRA/PR/PA) is ever summed wrong, or a player's line is
# matched to the wrong game, it is visible here instead of hiding inside a P&L total.
#
#   python results_report.py              yesterday's slate
#   python results_report.py 2026-08-08   a specific night
#   python results_report.py --dry        print, do not send
import csv, os, sys, datetime
import espn_get
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import alert_bets as A

DRY = "--dry" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
night = args[0] if args else (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

# ---- box scores, keyed by (game date, player). A player can appear on consecutive nights, so a
# flat name->stats dict would let one night's line overwrite the other's - that produced a bogus
# "McBride 43 PTS" against an 08-08 bet when the 43 was her 08-09 game.
box = {}
base = datetime.date.fromisoformat(night)
for off in (0, 1):
    d = base + datetime.timedelta(days=off)
    for e in espn_get.getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
                           {"dates": d.strftime("%Y%m%d")}).get("events", []):
        comp = (e.get("competitions") or [{}])[0]
        if (((comp.get("status") or {}).get("type") or {}).get("state")) != "post": continue
        s = espn_get.getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event=" + str(e["id"]))
        for tm in (s.get("boxscore") or {}).get("players", []):
            for blk in tm.get("statistics", []):
                keys = [k.lower() for k in blk.get("keys", [])]
                for a in blk.get("athletes", []):
                    nm = ((a.get("athlete") or {}).get("displayName") or "")
                    v = a.get("stats") or []
                    if not nm or len(v) != len(keys): continue
                    dd = dict(zip(keys, v))
                    def g(k):
                        x = str(dd.get(k, "0"))
                        return float(x) if x.replace(".", "").isdigit() else 0.0
                    box[(e["date"][:10], nm.lower())] = (g("points"), g("rebounds"), g("assists"), g("minutes"))

def stats_for(pl):
    """A night's games can tip on that date or just after midnight UTC - check both."""
    nxt = (base + datetime.timedelta(days=1)).isoformat()
    return box.get((night, pl.lower())) or box.get((nxt, pl.lower()))

rows = [r for r in csv.DictReader(open(os.path.join(D, "pinged_bets.csv"), encoding="utf-8"))
        if r.get("date") == night]
if not rows:
    print(f"no pinged bets for {night}"); sys.exit(0)

lines, W, L, pnl, stk, pend, void = [], 0, 0, 0.0, 0.0, 0, 0
for r in sorted(rows, key=lambda x: (x.get("src", ""), x.get("player", ""))):
    tag = f"{r['player']} {r['market'].upper()} {r['side']} {r['line']}"
    if r.get("pulled_utc"):
        void += 1
        lines.append(f"⬜ {tag} — **not bet** ({'game not this slate' if 'VOID' in r['pulled_utc'] else 'pulled, drifted'})")
        continue
    s = stats_for(r["player"])
    if not s:
        pend += 1; lines.append(f"⏳ {tag} — no box score yet"); continue
    pts, reb, ast, mins = s
    val = {"pts": pts, "pra": pts + reb + ast, "pr": pts + reb,
           "pa": pts + ast, "ast": ast, "reb": reb}[r["market"]]
    u = 0.5 if r.get("stake", "").startswith("½") else 1.0
    win = val > float(r["line"]) if r["side"] == "Over" else val < float(r["line"])
    ret = (float(r["odds"]) - 1) * u if win else -u
    W += win; L += (not win); pnl += ret; stk += u
    show = f"{pts:g}p/{reb:g}r/{ast:g}a" if r["market"] != "pts" else f"{pts:g}pts"
    lines.append(f"{'✅' if win else '❌'} {tag} @{r['odds']} · {r['stake']} → "
                 f"**{val:g}** ({show}, {mins:g}min) · {ret:+.2f}u")

head = (f"📋 **RESULTS · {night}** — {W}-{L}"
        + (f" ({100*W/(W+L):.0f}%)" if W + L else "")
        + f" · **{pnl:+.2f}u** on {stk:g}u staked"
        + (f" = {100*pnl/stk:+.1f}% ROI" if stk else "")
        + (f" · {pend} pending" if pend else "") + (f" · {void} not bet" if void else ""))
msg = head + "\n" + "\n".join(lines) + "\n_check any line against the box score — the raw p/r/a is shown so the maths is verifiable._"
print(msg)
if not DRY:
    print("\nsent" if A.send(msg) else "\nSEND FAILED")
