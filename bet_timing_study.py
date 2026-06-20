# bet_timing_study.py — does betting at TIP-OFF (the close) or grabbing 2.0 odds beat betting ON-SIGHT (the open)?
# Re-grades every settled bet under 4 timings using the prices we actually logged in bets_log. Read-only.
import csv, os
from collections import defaultdict

gd = {r["game_id"]: r.get("date") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
actual = {}
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    d = gd.get(r["game_id"])
    if not d:
        continue
    try:
        p, rb, a = float(r["pts"]), float(r["reb"]), float(r["ast"])
    except (ValueError, TypeError):
        continue
    for mk, v in {"pts": p, "pr": p + rb, "pa": p + a, "ra": rb + a, "pra": p + rb + a}.items():
        actual[(r["player"].lower(), d, mk)] = v

caps = defaultdict(list)
for b in csv.DictReader(open("bets_log.csv", encoding="utf-8")):
    d = b["date"].replace("-", "")
    src = b.get("src", "") or ("model" if b["side"] == "Under" else "overshoot")
    try:
        caps[(d, b["player"].lower(), b["market"], b["side"])].append(
            (b["captured_utc"], float(b["line"]), float(b["odds"]), src))
    except (ValueError, TypeError):
        pass

player_dates = defaultdict(set)
for (plow, dd, mk) in actual:
    player_dates[(plow, mk)].add(dd)
def game_date(plow, mk, slate):
    later = sorted(x for x in player_dates.get((plow, mk), ()) if x >= slate)
    return later[0] if later else slate

merged = defaultdict(list)
for (d, plow, mk, side), cl in caps.items():
    merged[(game_date(plow, mk, d), plow, mk, side)].extend(cl)

def won(side, line, act):
    return (act < line) if side == "Under" else (act > line)

LABEL = {"open": "OPEN  (on-sight = current)", "close": "CLOSE (bet at tip-off)",
         "best": "BEST  (grab the peak odds)", "hyp2": "if we ALWAYS got 2.0 odds"}

def study(keep):
    s = {k: [0, 0, 0.0] for k in LABEL}
    n = r2 = 0
    for (d, plow, mk, side), cl in merged.items():
        act = actual.get((plow, d, mk))
        if act is None:
            continue
        cl.sort()
        src = cl[0][3]
        if not keep(src):
            continue
        n += 1
        if max(x[2] for x in cl) >= 1.98:
            r2 += 1
        o_line, o_odds = cl[0][1], cl[0][2]
        c_line, c_odds = cl[-1][1], cl[-1][2]
        best = max(cl, key=lambda x: x[2])
        for key, (ln, od) in [("open", (o_line, o_odds)), ("close", (c_line, c_odds)), ("best", (best[1], best[2]))]:
            if act == ln:
                continue                                  # push
            w = won(side, ln, act)
            s[key][0 if w else 1] += 1
            s[key][2] += (od - 1) if w else -1
        if act != o_line:                                 # hypothetical: our OPEN line but a flat 2.0 price
            w = won(side, o_line, act)
            s["hyp2"][0 if w else 1] += 1
            s["hyp2"][2] += 1.0 if w else -1.0
    return s, n, r2

for title, keep in [("ALL SIGNALS", lambda s: True), ("REAL-MONEY (model) only", lambda s: s == "model")]:
    s, n, r2 = study(keep)
    if not n:
        continue
    print(f"=== {title} — {n} settled bets ({r2} hit >=1.98 odds at some point = {r2 / n * 100:.0f}%) ===")
    print(f"  {'timing':28}{'W-L':>9}{'hit':>6}{'P&L':>9}{'ROI/bet':>10}")
    for k in ("open", "close", "best", "hyp2"):
        w, l, p = s[k]
        t = w + l or 1
        print(f"  {LABEL[k]:28}{f'{w}-{l}':>9}{w / t * 100:>5.0f}%{p:>+8.2f}u{p / t * 100:>+9.1f}%")
    print()
