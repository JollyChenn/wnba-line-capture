# tonight.py - tonight's card under the validated model
# ---------------------------------------------------------------------------------------------
# THE MODEL, exactly as backtested (425 bets, 63.5%, +68.45u, ROI +16.1%, positive all 3 months):
#   1 OVER side only            - unders are structurally -13% on this board and our under
#                                 selection adds NOTHING to that (46.0% vs a 46.7% blind baseline)
#   2 from the existing over signals (flip / flip_paper / cascade / overshoot / hotover)
#   3 SKIP if the book RAISED her number by 0.5+ since her previous game - it has already
#     repriced the mistake we are trying to bet on
#   4 SKIP if the price has DRIFTED (lengthened) 1%+ since this line opened
#   5 markets pra / pr / pts only - pa ran -14.1% in the backtest
#
# Everything below is computed from prior games only. Nothing here can see tonight's result.
import csv, os, sys, math, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
NOW = datetime.datetime.now(datetime.timezone.utc)
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
BET_MKTS = ("pra", "pr", "pts")
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

# tonight's games
tips, opp = {}, {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if not t or not (0 < (t-NOW).total_seconds() < 14*3600): continue
    tips[g["home"]] = t; tips[g["away"]] = t
    opp[g["home"]] = g["away"]; opp[g["away"]] = g["home"]
print(f"tonight: {len(tips)//2} games, teams {sorted(tips)}")
for tm, t in sorted(tips.items(), key=lambda x: x[1]):
    if tm in opp and tm < opp[tm]:
        print(f"   {tm} vs {opp[tm]}   tip {t.strftime('%H:%M')}Z  "
              f"= {(t+datetime.timedelta(hours=7)).strftime('%H:%M')} WIB  "
              f"({(t-NOW).total_seconds()/3600:+.1f}h)")

# player history -> anchor and team
plog = collections.defaultdict(list)
gm = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
teamnow = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(date=dt, tip=tp, team=r.get("team"), pts=pts, reb=reb, ast=ast,
                         pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast))
    teamnow[pl] = r.get("team")
for v in plog.values(): v.sort(key=lambda x: x["date"])
def anchor(pl, mk, n=10):
    v = plog.get(pl, [])[-n:]
    return statistics.median(x[mk] for x in v) if len(v) >= 6 else None
def last_n_min(pl, n=5):
    return [x for x in plog.get(pl, [])][-n:]

# the board: current line/price per selection, and the line she had in her PREVIOUS game
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
for v in raw.values(): v.sort()
nights = collections.defaultdict(list)          # (player, market) -> [(night_start, line, series)]
for (pl, mk, ln), v in raw.items():
    blocks, cur = [], [v[0]]
    for prev, nxt in zip(v, v[1:]):
        if (nxt[0]-prev[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(nxt)
    blocks.append(cur)
    for blk in blocks:
        if blk: nights[(pl, mk)].append((blk[0][0], ln, blk))
for v in nights.values(): v.sort()
def tonight_line(pl, mk):
    v = [x for x in nights.get((pl, mk), []) if (NOW - x[0]).total_seconds() < 30*3600]
    if not v: return None
    return max(v, key=lambda x: len(x[2]))       # the most-quoted line = the main market
def previous_line(pl, mk):
    v = [x for x in nights.get((pl, mk), []) if (NOW - x[0]).total_seconds() >= 30*3600]
    return v[-1][1] if v else None

# today's over signals from the live engine
seen, cand = set(), []
for b in load("bets_log.csv"):
    if (b.get("date") or "").replace("-", "")[:8] != NOW.strftime("%Y%m%d"): continue
    if b.get("side") != "Over": continue
    pl, mk, ln = (b.get("player") or "").lower(), b.get("market"), f(b.get("line"))
    if mk not in MKTS or ln is None: continue
    k = (pl, mk, ln)
    if k in seen: continue
    seen.add(k)
    cand.append(dict(pl=pl, name=b.get("player"), mk=mk, line=ln, src=b.get("src") or "?"))
print(f"\n{len(cand)} distinct OVER candidates logged by the engine today")

rows = []
for c in cand:
    tm = teamnow.get(c["pl"])
    if tm not in tips: continue                                  # not playing tonight
    tl = tonight_line(c["pl"], c["mk"])
    if not tl: continue
    _, ln, series = tl
    price = series[-1][1]
    drift = series[-1][1]/series[0][1] - 1 if len(series) >= 2 else 0.0
    a = anchor(c["pl"], c["mk"])
    pv = previous_line(c["pl"], c["mk"])
    rows.append(dict(**c, team=tm, opp=opp.get(tm), line_now=ln, price=price, drift=drift,
                     anchor=a, prev=pv, tip=tips[tm],
                     raised=(pv is not None and ln - pv >= 0.5),
                     gap=(ln - a) if a is not None else None))

# ONE BET PER PLAYER-MARKET. The engine logs a row every time the book moves its number, so a
# player whose line went 9.5 -> 8.5 during the day appears twice. Both resolve to the SAME current
# main line, and betting it twice would be a duplicate stake, not two bets.
dedup = {}
for r in rows:
    k = (r["pl"], r["mk"])
    if k not in dedup: dedup[k] = r
rows = list(dedup.values())

def show(r):
    mins = " ".join(f"{int(x['min'])}" if 'min' in x else "" for x in [])
    l5 = "/".join(f"{x[r['mk']]:.0f}" for x in last_n_min(r["pl"], 5))
    print(f"    {r['name'][:22]:<22} {r['mk'].upper():<4} O{r['line_now']:<5} @ {r['price']:.2f}  "
          f"[{r['src']}]")
    print(f"      {r['team']} vs {r['opp']} · tip {(r['tip']+datetime.timedelta(hours=7)).strftime('%H:%M')} WIB · "
          f"her last 5 {r['mk']}: {l5} · 10-game median {r['anchor']:.1f}" if r['anchor'] else "")
    print(f"      book: {('was '+format(r['prev'],'.1f')+' last game') if r['prev'] is not None else 'no previous line'}"
          f" -> {r['line_now']:.1f} now"
          f" · price moved {100*r['drift']:+.1f}% since this line opened")

print("\n" + "="*96)
print("  TONIGHT'S CARD - what passes the model")
print("="*96)
PASS = [r for r in rows if r["mk"] in BET_MKTS and not r["raised"] and r["drift"] < 0.01]
PASS.sort(key=lambda r: (r["tip"], -(r["gap"] is not None and -r["gap"] or 0)))
if not PASS:
    print("    nothing passes tonight.")
for r in PASS: show(r); print()

print("="*96)
print("  REJECTED, and why - so you can see the filter working")
print("="*96)
for r in sorted(rows, key=lambda x: x["name"]):
    why = []
    if r["mk"] not in BET_MKTS: why.append(f"market {r['mk']} (pa ran -14% in backtest)")
    if r["raised"]: why.append(f"book RAISED {r['prev']:.1f}->{r['line_now']:.1f} (already repriced)")
    if r["drift"] >= 0.01: why.append(f"price drifted +{100*r['drift']:.1f}%")
    if why:
        print(f"    {r['name'][:22]:<22} {r['mk'].upper():<4} O{r['line_now']:<5} [{r['src']:<10}] "
              f"-> {'; '.join(why)}")
print(f"\n    {len(PASS)} pass / {len(rows)} candidates on tonight's teams")

dbl = [pl for pl, c in collections.Counter(r["pl"] for r in PASS).items() if c > 1]
if dbl:
    print("\n" + "="*96)
    print("  CORRELATION WARNING")
    print("="*96)
    for pl in dbl:
        mks = [r["mk"].upper() for r in PASS if r["pl"] == pl]
        nm = next(r["name"] for r in PASS if r["pl"] == pl)
        print(f"    {nm} appears on {len(mks)} markets ({', '.join(mks)}). These are the SAME")
        print(f"    player having the same night - if she sits or gets in foul trouble both lose")
        print(f"    together. Treat it as ONE position, not two. The backtest counted them")
        print(f"    separately, so its variance is understated for nights like this.")
