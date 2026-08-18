# grade_forward.py - settle the over-model's forward picks against the box score.
# ---------------------------------------------------------------------------------------------
# model_card.py writes each night's picks to model_forward.csv with result blank and note
# "pending". This fills them in once the game is final. It is the only thing that turns the
# forward tracker into a record rather than a wish list.
#
# Rewrites the file atomically (temp + os.replace) so a crash mid-write can never truncate it -
# a lesson from losing 1500 rows of a paper-trading file to exactly that.
import csv, os, sys, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
FWD = os.path.join(D, "model_forward.csv")
if not os.path.exists(FWD):
    print("  no model_forward.csv yet"); raise SystemExit

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

gm = {g.get("game_id"): g.get("date", "") for g in load("data/games_2026.csv")}
box = {}
for r in load("data/box_2026.csv"):
    dt = gm.get(r.get("game_id"))
    if not dt: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    box[(dt, (r.get("player") or "").strip().lower())] = dict(
        pts=pts, reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast)

# DO NOT TRUST THE LOCAL BOX FOR A RECENT SLATE.
# data/box_2026.csv is written once per game and never refreshed, so if the fetch landed while the
# game was still finalising, the cached line is wrong FOREVER. Tonight Erica Wheeler was stored
# with 5 assists; the ESPN final says 6. PRA 15 vs 16. Both lose to a 16.5 line so the grade held,
# but on a 15.5 line we would have booked a WIN as a LOSS and never known.
# So for any slate in the last 4 days, go back to ESPN and let that be the authority.
import urllib.request, json
def espn_box(datestr):
    out = {}
    try:
        sb = json.load(urllib.request.urlopen(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
            f"?dates={datestr}", timeout=25))
    except Exception as e:
        print(f"  (espn scoreboard {datestr} unavailable: {e})"); return out
    for ev in sb.get("events", []):
        try:
            d = json.load(urllib.request.urlopen(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary"
                f"?event={ev['id']}", timeout=25))
        except Exception:
            continue
        st = d.get("header", {}).get("competitions", [{}])[0].get("status", {}) \
              .get("type", {}).get("detail", "")
        if "Final" not in st: continue            # only settle finished games
        for t in d.get("boxscore", {}).get("players", []):
            for grp in t.get("statistics", []):
                keys = [k.lower() for k in grp.get("keys", [])]
                for a in grp.get("athletes", []):
                    nm = a.get("athlete", {}).get("displayName"); s = a.get("stats", [])
                    if not nm or len(s) != len(keys): continue
                    m = dict(zip(keys, s))
                    def num(k):
                        try: return float(m.get(k, "0") or 0)
                        except Exception: return 0.0
                    p, rb, asst = num("points"), num("rebounds"), num("assists")
                    out[nm.strip().lower()] = dict(pts=p, reb=rb, ast=asst, pra=p+rb+asst,
                                                   pr=p+rb, pa=p+asst, ra=rb+asst)
    return out

def one_position(rows):
    """ONE POSITION PER PLAYER on a slate - the rule we bet. Without this, a player who
       qualifies in two markets is counted twice: Hamby on 2026-08-11 went in as pts 13.5 AND
       pra 22.5, both won, and the headline read 6-6 instead of 5-6."""
    best = {}
    for r in sorted(rows, key=lambda x: -(float(x.get("odds") or 0))):
        best.setdefault((r.get("slate"), (r.get("player") or "").strip().lower()), r)
    return list(best.values())

rows = load("model_forward.csv")
# THE SLATE IS NOT THE GAME DATE, AND GRADING ON IT LEAVES BETS PENDING FOREVER.
# `slate` is the label the card gave the night (min tip inside its window); the box score is
# keyed on the GAME's own date. They differ whenever a game tips after midnight UTC - e.g.
# Arike Ogunbowale on 2026-08-18: slate 20260818, DAL@GS dated 20260817, tip 02:00Z. The
# lookup missed and she would have stayed PENDING indefinitely. Rows now carry `tip`, so
# derive the game date from it and fall back to the slate only for older rows.
def _ts(x):
    try: return datetime.datetime.fromisoformat((x or "").replace("Z", "+00:00"))
    except Exception: return None

def game_date(r):
    t = _ts(r.get("tip")) if r.get("tip") else None
    if t is None: return r.get("slate", "")
    # find the games file entry whose tip matches, and use ITS date
    return TIP2DATE.get(t.strftime("%Y-%m-%dT%H:%MZ"), r.get("slate", ""))
TIP2DATE = {}
for _g in load("data/games_2026.csv"):
    _t = _ts(_g.get("tip"))
    if _t: TIP2DATE[_t.strftime("%Y-%m-%dT%H:%MZ")] = _g.get("date", "")
today = datetime.date.today()
recent = sorted({game_date(r) for r in rows if r.get("result") not in ("WIN", "loss", "push")
                 and game_date(r)[:8].isdigit()
                 and (today - datetime.date(int(game_date(r)[:4]), int(game_date(r)[4:6]),
                                            int(game_date(r)[6:8]))).days <= 4})
for ds in recent:
    fresh = espn_box(ds)
    if fresh:
        for k, v in fresh.items(): box[(ds, k)] = v
        print(f"  refreshed {len(fresh)} box lines for {ds} straight from ESPN")
changed = 0
for r in rows:
    if r.get("result") in ("WIN", "loss"): continue
    key = (game_date(r), (r["player"] or "").strip().lower())
    b = box.get(key)
    if not b:                                   # game not final, or she did not play
        continue
    mk, ln = r["market"], f(r["line"])
    if mk not in b or ln is None: continue
    val = b[mk]
    if val == ln:                               # exact push, refund
        r["result"], r["actual"], r["pnl"], r["note"] = "push", val, 0.0, "push - stake returned"
    else:
        won = val > ln                          # every forward pick is an Over
        odds = f(r["odds"]) or 0
        r["result"] = "WIN" if won else "loss"
        r["actual"] = val
        r["pnl"] = round((odds - 1) if won else -1.0, 3)
        r["note"] = (r["note"] or "").replace("pending", "").strip() or ""
    changed += 1

if changed:
    tmp = FWD + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, FWD)                        # atomic - never leaves a half-written file
# EVERY number below is one-position, because that is the rule we bet. Counting a player
# twice when she qualifies in two markets read 6-6 / -1.13u where the truth is 5-6 / -1.86u.
g = one_position([r for r in rows if r.get("result") in ("WIN", "loss")])
w_ = sum(1 for r in g if r["result"] == "WIN")
pnl = sum(f(r["pnl"]) or 0 for r in g)
pend = sum(1 for r in rows if r.get("result") not in ("WIN", "loss", "push"))
print(f"  graded {changed} newly settled | forward record (one position): {len(g)} bets "
      f"{w_}-{len(g)-w_} {pnl:+.2f}u ROI {100*pnl/len(g):+.1f}%" if g else "  nothing settled yet")
print(f"  {pend} still pending")
by = collections.defaultdict(list)
for r in g: by[r["slate"]].append(r)
for s in sorted(by):
    v = by[s]; ww = sum(1 for r in v if r["result"] == "WIN")
    print(f"    {s}: {ww}-{len(v)-ww}  {sum(f(r['pnl']) or 0 for r in v):+.2f}u")
