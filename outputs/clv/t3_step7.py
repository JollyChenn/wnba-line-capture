# TRACK 3 step 7: pre-game GAME market -- open vs latest vs close; does movement predict the close, or the result?
import csv, os, sys, math, statistics, collections, random, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"
FULL = {"Atlanta Dream": "ATL", "Chicago Sky": "CHI", "Connecticut Sun": "CON", "Dallas Wings": "DAL",
        "Golden State Valkyries": "GS", "Indiana Fever": "IND", "Los Angeles Sparks": "LA",
        "Las Vegas Aces": "LV", "Minnesota Lynx": "MIN", "New York Liberty": "NY",
        "Phoenix Mercury": "PHX", "Portland Fire": "POR", "Seattle Storm": "SEA",
        "Toronto Tempo": "TOR", "Washington Mystics": "WSH"}

def ts(s):
    s = (s or "").replace("Z", "+00:00")
    try:
        d = datetime.datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except Exception: return None

GM = list(csv.DictReader(open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8")))
res = {}
for g in GM:
    try: hs, a = float(g["home_score"]), float(g["away_score"])
    except Exception: continue
    res[(g["home"], g["away"], g["date"])] = (hs, a, ts(g["tip"]))

def am2dec(a):
    a = float(a)
    return 1 + (a / 100 if a > 0 else 100 / -a)

# ---- parse gamelines into per-matchup time series of MAIN lines
raw = collections.defaultdict(list)
meta = {}
for r in csv.DictReader(open(os.path.join(D, "gamelines.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    if not t: continue
    pr = r["prices"].split(",")
    if len(pr) != 2: continue
    try: d1, d2 = am2dec(pr[0]), am2dec(pr[1])
    except Exception: continue
    raw[r["matchup_id"]].append((t, r["type"], r.get("side", ""), r.get("points", ""), d1, d2))
    meta[r["matchup_id"]] = (r["teams"], ts(r["start"]))

def mainpick(cands):
    """main line = the one whose two prices are most balanced"""
    if not cands: return None
    return min(cands, key=lambda c: abs(1 / c[4] - 1 / c[5]))

games = []
for mid, rows in raw.items():
    teams, start = meta[mid]
    try: h, a = [FULL[x] for x in teams.split("|")]
    except Exception: continue
    # gamelines 'teams' is "home|away"?  verify against schedule below
    bytime = collections.defaultdict(list)
    for x in rows: bytime[x[0]].append(x)
    tl = sorted(bytime)
    if len(tl) < 2: continue
    snaps = []
    for t in tl:
        g = bytime[t]
        ml = [x for x in g if x[1] == "moneyline"]
        sp = mainpick([x for x in g if x[1] == "spread"])
        to = mainpick([x for x in g if x[1] == "total"])
        snaps.append(dict(t=t, ml=(ml[0][4], ml[0][5]) if ml else None,
                          sp=(float(sp[3]), sp[4], sp[5]) if sp and sp[3] else None,
                          to=(float(to[3]), to[4], to[5]) if to and to[3] else None))
    games.append(dict(mid=mid, home=h, away=a, start=start, snaps=snaps))

print("matchups parsed: %d" % len(games))
# link to results
linked = []
for g in games:
    st = g["start"]
    key = None
    for dd in ((st - datetime.timedelta(hours=6)).strftime("%Y%m%d"), st.strftime("%Y%m%d")):
        if (g["home"], g["away"], dd) in res: key = (g["home"], g["away"], dd); break
        if (g["away"], g["home"], dd) in res: key = (g["away"], g["home"], dd); break
    if not key: continue
    hs, aw, tip = res[key]
    flip = (key[0] != g["home"])          # gamelines 'teams' order vs schedule home/away
    g["swapped"] = flip
    g["hs"], g["as_"] = (hs, aw) if not flip else (aw, hs)
    g["tip"] = tip
    linked.append(g)
print("linked to a final score: %d" % len(linked))
# orientation sanity: does a negative main spread go with the higher-scoring side?
ok = 0; tot = 0
for g in linked:
    s = [x for x in g["snaps"] if x["sp"]]
    if not s: continue
    tot += 1
    fav_first = s[0]["sp"][0] < 0
    if fav_first == (g["hs"] > g["as_"]): ok += 1
print("orientation check: 'points' on the first-listed team matches winner %.1f%% of games (n=%d)" % (ok / tot * 100, tot))


def near(snaps, tip, hrs, field):
    c = [s for s in snaps if s[field] and s["t"] < tip - datetime.timedelta(hours=hrs)]
    return c[-1] if c else None

def last(snaps, tip, field):
    c = [s for s in snaps if s[field] and s["t"] < tip]
    return c[-1] if c else None

def first(snaps, field):
    c = [s for s in snaps if s[field]]
    return c[0] if c else None

def bboot(v, nb=6000):
    if len(v) < 3: return (float("nan"),) * 3
    ms = []
    for _ in range(nb): ms.append(statistics.mean([random.choice(v) for _ in range(len(v))]))
    ms.sort(); return statistics.mean(v), ms[int(.025 * nb)], ms[int(.975 * nb)]

print("\n=== CAPTURE WINDOW ===")
lag = [(g["tip"] - [s for s in g["snaps"]][-1]["t"]).total_seconds() / 3600 for g in linked]
op = [(g["tip"] - g["snaps"][0]["t"]).total_seconds() / 3600 for g in linked]
print("  first capture median %.1fh before tip; last capture median %.2fh before tip; <1h in %.0f%%" % (
    statistics.median(op), statistics.median(lag), sum(1 for x in lag if x < 1) / len(lag) * 100))

print("\n=== 1) DOES PRE-GAME MOVEMENT PREDICT THE CLOSE? (momentum in the line itself) ===")
for field, name, getter in (("sp", "main spread", lambda s: s["sp"][0]), ("to", "main total", lambda s: s["to"][0])):
    early, mid_, cls, xs, ys = [], [], [], [], []
    for g in linked:
        a = first(g["snaps"], field); b = near(g["snaps"], g["tip"], 6, field); c = last(g["snaps"], g["tip"], field)
        if not (a and b and c): continue
        m1 = getter(b) - getter(a)          # open -> T-6h
        m2 = getter(c) - getter(b)          # T-6h -> close
        xs.append(m1); ys.append(m2)
    if len(xs) < 20: print("  %s: n<20" % name); continue
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((p - mx) * (q - my) for p, q in zip(xs, ys))
    den = math.sqrt(sum((p - mx) ** 2 for p in xs) * sum((q - my) ** 2 for q in ys))
    r = num / den if den else float("nan")
    t = r * math.sqrt((len(xs) - 2) / max(1e-9, 1 - r * r))
    print("  %-12s n=%d games  corr(move open->T-6h, move T-6h->close) = %+.3f  t=%+.2f" % (name, len(xs), r, t))
    print("               mean |open->T-6h| %.2f pts, mean |T-6h->close| %.2f pts" % (
        statistics.mean([abs(x) for x in xs]), statistics.mean([abs(y) for y in ys])))

print("\n=== 2) DOES PRE-GAME MOVEMENT PREDICT THE RESULT? (bet the moving side at the OPEN, grade at real prices) ===")
print("    null: independent games; CI = game bootstrap. breakeven at the captured two-sided prices.")
for field, name in (("sp", "spread"), ("to", "total")):
    buckets = collections.defaultdict(list)
    for g in linked:
        a = first(g["snaps"], field); c = last(g["snaps"], g["tip"], field)
        if not (a and c): continue
        if field == "sp":
            ol, o1, o2 = a["sp"]; cl_ = c["sp"][0]
            margin = g["hs"] - g["as_"]     # first-listed team margin
            mv = cl_ - ol                   # line moved against first team if positive
            # bet the side the line MOVED TOWARD, at the OPEN price
            if abs(mv) < 0.25: continue
            if mv < 0:                       # first team got more favoured
                won = 1 if (margin + ol) > 0 else (0 if (margin + ol) < 0 else None); price = o1
            else:
                won = 1 if (margin + ol) < 0 else (0 if (margin + ol) > 0 else None); price = o2
        else:
            ol, o1, o2 = a["to"]; cl_ = c["to"][0]
            tot = g["hs"] + g["as_"]; mv = cl_ - ol
            if abs(mv) < 0.25: continue
            if mv > 0: won = 1 if tot > ol else (0 if tot < ol else None); price = o1
            else: won = 1 if tot < ol else (0 if tot > ol else None); price = o2
        if won is None: continue
        buckets["move>=0.25"].append((won * price - 1))
        if abs(mv) >= 1.0: buckets["move>=1.0"].append((won * price - 1))
    for k, v in sorted(buckets.items()):
        m, lo, hi = bboot(v)
        print("  %-8s %-11s n=%3d games  ROI %+6.1f%% [%+6.1f,%+6.1f]" % (name, k, len(v), m * 100, lo * 100, hi * 100))

print("\n=== 3) IS THE PINNACLE CLOSE ITSELF WELL CALIBRATED? (baseline: bet every favourite / every over) ===")
for lbl, fn in (("home/first-listed ML", "ml"), ("main total OVER", "to"), ("first-listed spread", "sp")):
    v = []
    for g in linked:
        c = last(g["snaps"], g["tip"], fn)
        if not c: continue
        if fn == "ml":
            p = c["ml"][0]; won = 1 if g["hs"] > g["as_"] else 0
        elif fn == "to":
            ln, p, _ = c["to"]; t_ = g["hs"] + g["as_"]
            if t_ == ln: continue
            won = 1 if t_ > ln else 0
        else:
            ln, p, _ = c["sp"]; m_ = g["hs"] - g["as_"]
            if m_ + ln == 0: continue
            won = 1 if m_ + ln > 0 else 0
        v.append(won * p - 1)
    m, lo, hi = bboot(v)
    print("  %-22s n=%3d  ROI %+6.1f%% [%+6.1f,%+6.1f]" % (lbl, len(v), m * 100, lo * 100, hi * 100))

print("\n=== 4) FAVOURITE STATUS + CLOSING TOTAL: do closes forecast the score? ===")
xs, ys = [], []
for g in linked:
    c = last(g["snaps"], g["tip"], "to")
    if not c: continue
    xs.append(c["to"][0]); ys.append(g["hs"] + g["as_"])
mx, my = statistics.mean(xs), statistics.mean(ys)
num = sum((p - mx) * (q - my) for p, q in zip(xs, ys))
den = math.sqrt(sum((p - mx) ** 2 for p in xs) * sum((q - my) ** 2 for q in ys))
print("  corr(closing total, realised total) = %+.3f  n=%d games; mean close %.1f vs mean realised %.1f" % (
    num / den, len(xs), mx, my))
xs, ys = [], []
for g in linked:
    c = last(g["snaps"], g["tip"], "sp")
    if not c: continue
    xs.append(-c["sp"][0]); ys.append(g["hs"] - g["as_"])
mx, my = statistics.mean(xs), statistics.mean(ys)
num = sum((p - mx) * (q - my) for p, q in zip(xs, ys))
den = math.sqrt(sum((p - mx) ** 2 for p in xs) * sum((q - my) ** 2 for q in ys))
print("  corr(closing spread, realised margin)= %+.3f  n=%d games; mean implied %.1f vs mean realised %.1f" % (
    num / den, len(xs), mx, my))
