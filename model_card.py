# model_card.py - the over-model card, generated and pinged from THIS LAPTOP. No git, no GitHub.
# ---------------------------------------------------------------------------------------------
# WHY THIS FILE EXISTS SEPARATELY. run_local.py calls `git pull --rebase --autostash` every hour.
# That has twice stashed the working tree, hit a conflict on the pop, and left files deleted plus
# two bot state files in a conflicted state. This script therefore does NOT touch git at all. It
# reads local CSVs, writes two local files, and posts to Discord. If the network is down it still
# writes the card to disk.
#
# THE MODEL (backtest n=108, 67.6%, +25.38u, ROI +23.5%, alpha +16.1pp, z=+3.36):
#   1 OVER side only. Not because unders are cursed - the profitable side actually rotates by
#     half-month - but because our under SELECTION was worse than random even in the months when
#     unders were the better side (blind -4.5%, ours -14.5%). We are bad at picking them.
#   2 SIGNAL must be flip, hotover or overshoot. flip_paper and cascade are the two biggest
#     sources by volume and both are dead, which is why most nights are silent.
#   3 SKIP if the book RAISED her number 0.5+ since her previous game - already repriced.
#     This is the gate. Unstarred bets run -7.0% ROI on 127.
#   4 DRIFT is displayed, NOT used. Stacking it costs ~12u to buy nothing.
#   5 markets pra / pr / pts only - pa ran -14.1%
#   6 one bet per player-market, and same-player multi-market flagged as ONE position
#   Full reasoning, evidence and weak points: MODEL.md
#
# Run it any time. It is idempotent per slate: it will not re-ping a slate it has already sent.
import csv, os, sys, json, math, statistics, datetime, collections, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
NOW = datetime.datetime.now(datetime.timezone.utc)
WINDOW_H = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0    # how far ahead to look for tips
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
BET_MKTS = ("pra", "pr", "pts")
SENT = os.path.join(D, "model_card_sent.json")
FWD  = os.path.join(D, "model_forward.csv")

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def send(msg):
    p = os.path.join(D, "webhook.txt")
    wh = open(p).read().strip() if os.path.exists(p) else ""
    if not wh:
        print("[no webhook - card printed only]"); return False
    try:
        urllib.request.urlopen(urllib.request.Request(
            wh, data=json.dumps({"content": msg[:1900]}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "wnba-bot"}), timeout=15)
        return True
    except Exception as e:
        print("  discord failed:", e); return False

# ---- tonight's games -----------------------------------------------------------------------------
tips, opp = {}, {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if not t or not (0 < (t-NOW).total_seconds() < WINDOW_H*3600): continue
    tips[g["home"]] = t; tips[g["away"]] = t
    opp[g["home"]] = g["away"]; opp[g["away"]] = g["home"]
if not tips:
    print(f"no tips in the next {WINDOW_H:.0f}h - nothing to do"); raise SystemExit
slate = min(tips.values()).strftime("%Y-%m-%d")
print(f"slate {slate}: {len(tips)//2} games, first tip "
      f"{min(tips.values()).strftime('%H:%M')}Z")

# ---- player history ------------------------------------------------------------------------------
gm = {g.get("game_id"): (g.get("date",""), ts(g.get("tip"))) for g in load("data/games_2026.csv")}
plog = collections.defaultdict(list); teamnow = {}
for r in load("data/box_2026.csv"):
    dt, tp = gm.get(r.get("game_id"), ("", None))
    if not dt: continue
    pts, reb, ast = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    pl = (r.get("player") or "").lower()
    plog[pl].append(dict(date=dt, pts=pts, reb=reb, ast=ast, pra=pts+reb+ast,
                         pr=pts+reb, pa=pts+ast, ra=reb+ast))
    teamnow[pl] = r.get("team")
for v in plog.values(): v.sort(key=lambda x: x["date"])
def med(pl, mk, n=10):
    v = plog.get(pl, [])[-n:]
    return statistics.median(x[mk] for x in v) if len(v) >= 6 else None

# ---- the board, split into nights ----------------------------------------------------------------
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
nights = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a, b_ in zip(v, v[1:]):
        if (b_[0]-a[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
    blocks.append(cur)
    for blk in blocks:
        if blk: nights[(pl, mk)].append((blk[0][0], ln, blk))
for v in nights.values(): v.sort()

# ---- candidates: the engine's own over signals for this slate -------------------------------------
# THE SIGNAL MUST BE FROM THIS SLATE. bets_log holds every signal the engine has ever fired, and
# a player's team playing tonight does NOT mean her signal is current - Onyenwere's PR signal last
# fired on 2026-06-24. Without this filter the card silently rebuilds itself out of weeks-old rows.
# If the engine has not run for this slate yet, the right answer is "no card", not "old card".
BL = load("bets_log.csv")
newest = max(((b.get("date") or "")[:10] for b in BL if b.get("date")), default="")
print(f"newest signal in bets_log: {newest or 'none'} | slate: {slate}")
if newest and newest < slate:
    print(f"  NOTE: the engine has not run for {slate} yet (daily_picks fires 14:00 UTC).")
    print(f"  Anything below is built from the {newest} run and may not cover this slate.")

seen, rows = set(), []
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    bd = (b.get("date") or "").replace("-", "")[:8]
    try:
        age = (datetime.datetime.strptime(slate.replace("-", ""), "%Y%m%d")
               - datetime.datetime.strptime(bd, "%Y%m%d")).days
    except Exception:
        continue
    if not (0 <= age <= 1): continue                              # stale signal, ignore
    pl, mk, ln = (b.get("player") or "").lower(), b.get("market"), f(b.get("line"))
    if mk not in MKTS or ln is None: continue
    tm = teamnow.get(pl)
    if tm not in tips: continue                                   # not playing this slate
    if (pl, mk) in seen: continue
    tn = [x for x in nights.get((pl, mk), []) if (tips[tm] - x[0]).total_seconds() < 30*3600
          and x[0] <= tips[tm]]
    if not tn: continue
    seen.add((pl, mk))
    _, line_now, series = max(tn, key=lambda x: len(x[2]))
    prev = [x for x in nights.get((pl, mk), []) if (tips[tm] - x[0]).total_seconds() >= 30*3600]
    pv = prev[-1][1] if prev else None
    drift = series[-1][1]/series[0][1] - 1 if len(series) >= 2 else 0.0
    rows.append(dict(pl=pl, name=b.get("player"), mk=mk, src=b.get("src") or "?", team=tm,
                     opp=opp.get(tm), tip=tips[tm], line=line_now, price=series[-1][1],
                     drift=drift, prev=pv, med=med(pl, mk),
                     raised=(pv is not None and line_now - pv >= 0.5)))
print(f"{len(rows)} over candidates on this slate's teams")

# SELECTION, rebuilt 2026-08-14, then CORRECTED the same day. Read the correction - it is the
# most instructive mistake in this file.
#
#   THE MISTAKE. The first version of this rule ranked signals on their RAW numbers (flip +19.6%,
#   hotover +7.1%, overshoot +4.0%, flip_paper +5.0%, cascade -5.7%), kept the top two, and only
#   THEN discovered the star. I applied the star to the two signals I had already kept and never
#   re-tested the ones I had discarded. overshoot RAW is mediocre because it is half a good signal
#   and half a dead one averaged together - which is precisely what the star exists to separate:
#       overshoot RAW      n=163  57.1%   +4.0% ROI  alpha  +5.3pp
#       overshoot STARRED  n=86   61.6%  +11.6% ROI  alpha +10.0pp   <- in
#       overshoot raised   n=77   51.9%   -4.4% ROI  alpha  +0.2pp   <- out
#
#   THE LIST  = flip + hotover + overshoot, STARRED ONLY. n=108, 67.6%, +25.38u, +23.5% ROI,
#               alpha +16.1pp, z=+3.36. The three groups are disjoint - overshoot fires on
#               different player-nights, so these are extra bets, not relabels.
#   THE LADDER, i.e. which filter earns its keep:
#     raw over menu (all srcs, all mkts) n=596 +3.1% | +markets n=545 +2.8% (-0.3pp, ~nothing)
#     +drop dead signals n=213 +8.7% (+5.9pp) | +THE STAR n=108 +23.5% (+14.8pp) <- the star IS it
#   THE STAR  = the book did NOT raise her number 0.5+ since her last game. It is a GATE, not a
#               tier: the 105 unstarred bets run -6.86u, -6.5% ROI, alpha -0.9pp. Shown on the
#               card so you can see what was rejected. Do not bet them.
#   OUT OF SAMPLE, split 20260718:  IN n=40 +28.6%  ->  OUT n=68 +20.5%. Both halves readable.
#   PRICE      = first 1.818 +22.3% | last 1.820 +22.0%. My earlier 'close is best' number was a
#               BUG: the close price was read at the book's main line, which for 63 of 134 bets
#               was a different line than the bet settled on. On the 71 clean ones first and close
#               are a wash (1.832 +11.6% vs 1.839 +11.5%). Overshoot is bet slightly shorter than
#               flip (median 1.80 vs 1.83) and still clears break-even at a flat 1.70.
#   TIMING     = BET ON THE ALERT. Same 134 selections, priced as whole bets:
#                 on the alert  line 20.49  price 1.818  67.2%  +29.86u  +22.3%
#                 at the close  line 20.87  price 1.851  63.4%  +23.58u  +17.6%
#               Waiting costs 4.7pp. The line RISES on 38.8% of bets and falls on 8.2% - you gain
#               3.3 cents and pay 0.38 of line for it. The rise afterwards IS the CLV, and you
#               capture it by being early, not by waiting for it.
#   DRIFT IS NOT USED. Stacking it on top of not-raised costs ~12u to buy nothing. Displayed only.
TOP_SRC = ("flip", "hotover", "overshoot")
cand = [r for r in rows if r["mk"] in BET_MKTS and r["src"] in TOP_SRC]
PASS = [r for r in cand if not r["raised"]]
SECOND = [r for r in cand if r["raised"]]
PASS.sort(key=lambda r: r["tip"]); SECOND.sort(key=lambda r: r["tip"])
WIB = lambda t: (t + datetime.timedelta(hours=7)).strftime("%H:%M")

def fmt(r, star):
    mv = (f"book cut {r['prev']:.1f}→{r['line']:.1f}" if r["prev"] is not None and r["prev"] > r["line"]
          else (f"line held {r['line']:.1f}" if r["prev"] is not None
                else (f"book RAISED {r['prev']:.1f}→{r['line']:.1f}" if r["prev"] is not None
                      else "no previous line")))
    if r["prev"] is not None and r["line"] - r["prev"] >= 0.5:
        mv = f"book RAISED {r['prev']:.1f}→{r['line']:.1f}"
    head = ("⭐ " if star else "· ") + f"**{r['name']}** {r['mk'].upper()} Over {r['line']} @ {r['price']:.2f}"
    out = [f"{head} · {r['team']} v {r['opp']} · {WIB(r['tip'])} WIB"]
    tail = f"   {mv}"
    if r["med"] is not None: tail += f" · 10-game median {r['med']:.1f}"
    tail += f" · price {100*r['drift']:+.1f}% · _{r['src']}_"
    out.append(tail)
    return out

lines = [f"**🎯 OVER MODEL · {slate}** · {len(PASS)} bet{'s' if len(PASS)!=1 else ''} · flat 1u"]
for r in PASS: lines += fmt(r, True)
if SECOND:
    lines.append(f"_— below: {len(SECOND)} the book has already repriced (raised her 0.5+). "
                 f"Historically n=127, 50.4%, −8.84u, ROI −7.0%. DO NOT BET. Shown so you can "
                 f"see what was rejected. —_")
    for r in SECOND: lines += fmt(r, False)
dbl = [p for p, c in collections.Counter(r["pl"] for r in PASS).items() if c > 1]
for p in dbl:
    nm = next(r["name"] for r in PASS if r["pl"] == p)
    lines.append(f"⚠️ {nm} appears twice — same player, same night. Treat as ONE position.")
rej = [r for r in rows if r not in PASS]
if rej:
    lines.append(f"_skipped {len(rej)}: "
                 + ", ".join(f"{r['name'].split()[-1]} ("
                             + ("book raised" if r["raised"] else
                                ("drifted" if r["drift"] >= 0.01 else r["mk"])) + ")"
                             for r in rej[:6]) + "_")
card = "\n".join(lines) if PASS else f"**🎯 OVER MODEL · {slate}** · no qualifying bets tonight."
print("\n" + card + "\n")

# ---- idempotent send, and log the picks so tomorrow can grade them --------------------------------
sent = json.load(open(SENT)) if os.path.exists(SENT) else {}
if not PASS:
    # SILENCE ON EMPTY. At ~0.8 starred bets a night most slates have nothing, and a nightly
    # "no qualifying bets" ping trains you to ignore the channel - which is exactly when you
    # miss the one that matters. No bet, no message. The card is still written to the log.
    print("no qualifying bets - staying silent (card is in the log)")
    sent[slate] = 0
    tmp = SENT + ".tmp"; json.dump(sent, open(tmp, "w")); os.replace(tmp, SENT)
elif sent.get(slate) == len(PASS):
    print("already sent this slate with the same count - not re-pinging")
else:
    if send(card):
        print("pinged Discord")
        sent[slate] = len(PASS)
        tmp = SENT + ".tmp"
        json.dump(sent, open(tmp, "w")); os.replace(tmp, SENT)    # atomic, never a half-written file
    # THE TRACKER MUST MATCH THE CARD, NOT ACCUMULATE IT.
    # The loop reruns every 30 min. A pick can qualify at 21:00 and then fail at 22:00 because the
    # book raised her number or the price drifted. Appending each time left 3 pending rows for a
    # slate whose card showed 2 - a record of bets we would NOT have placed. So while the slate is
    # still PRE-TIP, replace this slate's pending rows with the current card. Once the first tip
    # has passed the card is frozen and never rewritten, because by then the bet is real.
    sk = slate.replace("-", "")
    first_tip = min(tips.values())
    rows_all = load("model_forward.csv")
    hdr = ["slate","player","market","side","line","odds","src","prev_line",
           "result","actual","pnl","note"]
    if NOW < first_tip:
        keep = [r for r in rows_all
                if not (r["slate"] == sk and r.get("result") not in ("WIN", "loss", "push"))]
        for r in PASS:
            keep.append({"slate": sk, "player": r["name"], "market": r["mk"], "side": "Over",
                         "line": r["line"], "odds": r["price"], "src": r["src"],
                         "prev_line": r["prev"] if r["prev"] is not None else "",
                         "result": "", "actual": "", "pnl": "", "note": "pending"})
        tmp = FWD + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader(); w.writerows(keep)
        os.replace(tmp, FWD)                       # atomic - never a half-written tracker
        print(f"tracker now holds exactly the {len(PASS)} picks on this card (pre-tip, rewritable)")
    else:
        print("first tip has passed - card frozen, tracker left untouched")
