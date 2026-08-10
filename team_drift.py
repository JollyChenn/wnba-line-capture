# team_drift.py - does AGGREGATE player-prop drift predict the TEAM's scoring?
# ---------------------------------------------------------------------------------------------
# THE IDEA (yours): a drifted OVER means the market is walking away from that player scoring. If
# many players on one team drift the same way, that is not noise about one player - it is the book
# repricing the whole team's output. That should show up in the team total, the game total, and
# possibly the moneyline.
#
# This is a genuinely different claim from the prop-level one. Prop drift is unusable because only
# half of it is visible before tip (reaudit_drift.py) - but a TEAM-level average pools 5-10 props,
# so even a partial read on each could aggregate into something legible.
#
# Tested honestly:
#   - drift measured OPEN -> LAST CAPTURE (the full signal, to see if the effect exists at all)
#   - then re-measured at T-2h (causal, what you could actually act on)
#   - outcome = the team's actual points, and the game total, vs the league norm for that slate
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

# ---- games: date, teams, scores, tip -----------------------------------------------------------
games = load("data/games_2026.csv")
gm = {}
for g in games:
    hs, as_ = f(g.get("home_score")), f(g.get("away_score"))
    if hs is None or as_ is None: continue
    gm[g.get("game_id")] = dict(date=g.get("date", ""), home=g.get("home"), away=g.get("away"),
                                hs=hs, as_=as_, tip=ts(g.get("tip")))

# ---- player -> team, per game date -------------------------------------------------------------
gdate = {g.get("game_id"): g.get("date", "") for g in games}
pteam = {}                                     # (date, player) -> team
for r in load("data/box_2026.csv"):
    d, pl, tm = gdate.get(r.get("game_id"), ""), (r.get("player") or "").lower(), r.get("team") or ""
    if d and pl and tm: pteam[(d, pl)] = tm

# ---- prop price series from the two-sided board ------------------------------------------------
# Use xbet_board (both sides) rather than bets_log: we want EVERY player's props on a team, not
# just the ones a signal happened to fire on. A team-level read needs the whole roster.
ser = collections.defaultdict(list)
for r in load("xbet_board.csv"):
    t, o, ln = ts(r.get("captured_utc")), f(r.get("odds")), f(r.get("line"))
    if not (t and o and ln is not None): continue
    ser[(t.strftime("%Y%m%d"), (r.get("player") or "").lower(), r.get("market"), r.get("side"), ln)].append((t, o))

def drift_of(series_pts, cutoff=None):
    s = sorted(x for x in series_pts if (cutoff is None or x[0] <= cutoff))
    if len(s) < 2: return None
    return s[-1][1]/s[0][1] - 1

# ---- build per-team aggregate drift ------------------------------------------------------------
def team_rows(hours_before=None):
    out = []
    for gid, g in gm.items():
        if not g["date"]: continue
        cut = (g["tip"] - datetime.timedelta(hours=hours_before)) if (hours_before and g["tip"]) else None
        for side, team, pts, opp_pts in ((0, g["home"], g["hs"], g["as_"]), (1, g["away"], g["as_"], g["hs"])):
            drifts = []
            for (d8, pl, mk, sd, ln), sp in ser.items():
                # a prop belongs to this game if the player's team matches and the capture date is
                # the slate date or the day either side (tips straddle midnight UTC)
                if sd != "Over": continue
                if mk not in ("pts", "pra", "pr", "pa"): continue
                if pteam.get((g["date"], pl)) != team: continue
                if abs(int(d8) - int(g["date"])) > 1: continue
                dv = drift_of(sp, cut)
                if dv is not None: drifts.append(dv)
            if len(drifts) >= 3:
                out.append(dict(gid=gid, date=g["date"], team=team, n=len(drifts),
                                mean_drift=sum(drifts)/len(drifts), pts=pts,
                                total=g["hs"]+g["as_"], won=pts > opp_pts))
    return out

def summarise(rows, key, label):
    """Split on the aggregate drift and compare outcomes. Terciles, so no threshold is invented."""
    if len(rows) < 24:
        print(f"  {label}: only {len(rows)} team-games - too few"); return
    rows = sorted(rows, key=lambda r: r["mean_drift"])
    k = len(rows)//3
    lo, mid, hi = rows[:k], rows[k:2*k], rows[2*k:]
    def m(g, kk): return sum(r[kk] for r in g)/len(g)
    print(f"  {label}  (n={len(rows)} team-games)")
    print(f"    {'bucket':<28}{'mean drift':>12}{'team pts':>10}{'game total':>12}{'win%':>7}")
    for nm, g in (("props SHORTENED (lo drift)", lo), ("middle", mid), ("props DRIFTED (hi drift)", hi)):
        print(f"    {nm:<28}{m(g,'mean_drift')*100:>11.2f}%{m(g,'pts'):>10.1f}{m(g,'total'):>12.1f}"
              f"{100*sum(r['won'] for r in g)/len(g):>6.0f}%")
    # is the gap real? two-sample t on team points
    a = [r["pts"] for r in hi]; b = [r["pts"] for r in lo]
    ma, mb = sum(a)/len(a), sum(b)/len(b)
    va = sum((x-ma)**2 for x in a)/(len(a)-1); vb = sum((x-mb)**2 for x in b)/(len(b)-1)
    t = (mb-ma)/math.sqrt(va/len(a)+vb/len(b))
    print(f"    -> shortened minus drifted = {mb-ma:+.1f} pts, t={t:+.2f}, "
          f"p={math.erfc(abs(t)/math.sqrt(2)):.3f}")

print("\n" + "="*78)
print("  FULL SIGNAL (open -> last capture). Does the effect exist at all?")
print("="*78)
summarise(team_rows(None), "pts", "team points vs aggregate prop drift")

print("\n" + "="*78)
print("  CAUSAL (drift as visible at T-2h). Could you actually trade it?")
print("="*78)
summarise(team_rows(2.0), "pts", "team points vs aggregate prop drift at T-2h")
