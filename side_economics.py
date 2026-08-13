# side_economics.py - is the under side bad because OUR signal picks unders, or is the whole
#                     board's under side unbettable?
# ---------------------------------------------------------------------------------------------
# The distinction decides what to cut. If newunder is picking badly, fix the signal. If the BOARD's
# under side loses no matter who bets it, no signal can rescue it and the side has to go.
#
# The test is a dumb one on purpose: bet EVERY prop the board ever posted, on each side, at the
# board's own closing price. No model, no selection, no cleverness. That isolates the venue.
#
# AND IT MUST BE PER MARKET. Hit rates on the two sides are complementary by construction (they
# sum to 100%), so a hit rate alone says nothing about whether a side pays - only the PRICE does.
# A 56% under at 1.70 loses money; a 46% over at 2.30 makes it. So ROI at real prices is the only
# column that matters here.
import csv, os, sys, math, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def d8(s):
    s = (s or "").replace("-", "")
    return s[:8] if len(s) >= 8 else ""
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")

games = {g.get("game_id"): dict(date=g.get("date",""), tip=ts(g.get("tip")))
         for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    g = games.get(r.get("game_id"))
    if not g or not g["date"]: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    plog[(r.get("player") or "").lower()].append(dict(date=g["date"], tip=g["tip"], pts=pts,
        reb=reb, ast=ast, pra=pts+reb+ast, pr=pts+reb, pa=pts+ast, ra=reb+ast))
for v in plog.values(): v.sort(key=lambda x: x["date"])
byplayer = collections.defaultdict(list)
for pl, v in plog.items():
    for g in v:
        if g["tip"]: byplayer[pl].append((g["tip"], g["date"], g))
for v in byplayer.values(): v.sort()
def game_after(pl, when):
    for tip, dt, rec in byplayer.get(pl, []):
        if when <= tip <= when + datetime.timedelta(hours=36): return dt, rec
    return None, None

# one row per (player, market, night): the MAIN line, with BOTH sides' closing prices
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS:
        raw[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
pergame = collections.defaultdict(dict)
for (pl, mk, side, ln), v in raw.items():
    v.sort()
    blocks, cur = [], [v[0]]
    for prev, nxt in zip(v, v[1:]):
        if (nxt[0]-prev[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(nxt)
    blocks.append(cur)
    for blk in blocks:
        if not blk: continue
        dt, rec = game_after(pl, blk[0][0])
        if not rec: continue
        pre = [x for x in blk if x[0] <= rec["tip"]]
        if pre: pergame[(pl, mk, dt)].setdefault(ln, {})[side] = pre
B = []
for (pl, mk, dt), lines in pergame.items():
    ln, sides = max(lines.items(), key=lambda kv: sum(len(x) for x in kv[1].values()))
    if "Over" not in sides or "Under" not in sides: continue
    rec = next((g for g in plog.get(pl, []) if g["date"] == dt), None)
    if rec is None or rec[mk] == ln: continue
    B.append(dict(pl=pl, mk=mk, date=dt, line=ln, over_won=rec[mk] > ln,
                  oo=sides["Over"][-1][1], uo=sides["Under"][-1][1]))
print(f"{len(B)} board props with BOTH sides priced and a settled outcome\n")

print("="*98)
print("  BET EVERY PROP BLIND, EACH SIDE, AT THE BOARD'S OWN PRICE - no model, no selection")
print("="*98)
print(f"    {'market':<7}{'n':>6}   {'--------- OVER ---------':<26}{'--------- UNDER --------':<26}{'margin':>8}")
print(f"    {'':<7}{'':>6}   {'hit%':>7}{'avg odds':>10}{'ROI':>9}{'hit%':>9}{'avg odds':>10}{'ROI':>9}{'':>8}")
tot = {"Over": [], "Under": []}
for mk in MKTS:
    rows = [r for r in B if r["mk"] == mk]
    if len(rows) < 60: continue
    ow = sum(1 for r in rows if r["over_won"])/len(rows)
    oroi = sum((r["oo"]-1) if r["over_won"] else -1.0 for r in rows)/len(rows)
    uroi = sum((r["uo"]-1) if not r["over_won"] else -1.0 for r in rows)/len(rows)
    ao = sum(r["oo"] for r in rows)/len(rows); au = sum(r["uo"] for r in rows)/len(rows)
    marg = sum(1/r["oo"] + 1/r["uo"] for r in rows)/len(rows) - 1
    tot["Over"] += [(r["oo"]-1) if r["over_won"] else -1.0 for r in rows]
    tot["Under"] += [(r["uo"]-1) if not r["over_won"] else -1.0 for r in rows]
    print(f"    {mk:<7}{len(rows):>6}   {100*ow:>6.1f}%{ao:>10.2f}{100*oroi:>+8.1f}%"
          f"{100*(1-ow):>8.1f}%{au:>10.2f}{100*uroi:>+8.1f}%{100*marg:>7.1f}%")
for side in ("Over", "Under"):
    v = tot[side]
    print(f"    {'ALL '+side:<13}n={len(v):<6} ROI {100*sum(v)/len(v):+.1f}%")
print("\n    hit% on the two sides sums to 100 BY CONSTRUCTION - only the ROI columns mean anything.")

print("\n" + "="*98)
print("  SO WHICH IS IT: our signal, or the venue?")
print("="*98)
seen, M = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    t, ln, o = ts(b.get("captured_utc")), f(b.get("line")), f(b.get("odds"))
    mk, side, src = b.get("market"), b.get("side"), (b.get("src") or "?")
    pl = (b.get("player") or "").lower()
    if not (t and ln is not None and o and mk in MKTS and side in ("Over", "Under")): continue
    k = (d8(b.get("date")), pl, mk, side, ln, src)
    if k in seen: continue
    seen.add(k)
    dt, rec = game_after(pl, t)
    if not rec or rec[mk] == ln: continue
    M.append(dict(mk=mk, side=side, src=src, odds=o,
                  won=(rec[mk] > ln) if side == "Over" else (rec[mk] < ln)))
blind = {}
for mk in MKTS:
    rows = [r for r in B if r["mk"] == mk]
    if len(rows) < 60: continue
    blind[(mk, "Over")] = sum((r["oo"]-1) if r["over_won"] else -1.0 for r in rows)/len(rows)
    blind[(mk, "Under")] = sum((r["uo"]-1) if not r["over_won"] else -1.0 for r in rows)/len(rows)
print(f"    {'our bets':<24}{'n':>6}{'our ROI':>10}{'blind ROI same cells':>24}{'we add':>10}")
for lbl, sel in (("all UNDER bets", lambda r: r["side"] == "Under"),
                 ("all OVER bets",  lambda r: r["side"] == "Over"),
                 ("  newunder only", lambda r: r["src"] == "newunder"),
                 ("  flip family",   lambda r: r["src"].startswith("flip")),
                 ("everything",      lambda r: True)):
    rows = [r for r in M if sel(r) and (r["mk"], r["side"]) in blind]
    if len(rows) < 30: continue
    ours = sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows)
    bench = sum(blind[(r["mk"], r["side"])] for r in rows)/len(rows)
    print(f"    {lbl:<24}{len(rows):>6}{100*ours:>+9.1f}%{100*bench:>+23.1f}%{100*(ours-bench):>+9.1f}%")
print("\n    'blind ROI same cells' = what betting those exact market/side combos AT RANDOM returns.")
print("    'we add' is the only measure of whether the SIGNAL is doing anything.")

print("\n" + "="*98)
print("  WHERE OUR UNDER BETS LIVE vs WHERE UNDERS ACTUALLY PAY")
print("="*98)
print(f"    {'market':<8}{'our under bets':>16}{'blind under ROI':>18}{'blind over ROI':>17}")
un = [r for r in M if r["side"] == "Under"]
for mk in MKTS:
    n = sum(1 for r in un if r["mk"] == mk)
    if (mk, "Under") not in blind: continue
    print(f"    {mk:<8}{n:>16}{100*blind[(mk,'Under')]:>17.1f}%{100*blind[(mk,'Over')]:>16.1f}%")
print(f"\n    total under bets: {len(un)}")
good = [mk for mk in MKTS if (mk,"Under") in blind and blind[(mk,"Under")] > blind[(mk,"Over")]]
print(f"    markets where the UNDER is the better blind side: {good or 'none'}")
print(f"    share of our under bets placed in those markets: "
      f"{100*sum(1 for r in un if r['mk'] in good)/len(un):.0f}%")
