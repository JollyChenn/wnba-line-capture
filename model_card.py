# model_card.py - MODEL S. The card, generated and pinged from THIS LAPTOP. No git, no GitHub.
# S is for STAR: the star filter is the model (raw over menu +3.1% -> +23.5% with it).
# ---------------------------------------------------------------------------------------------
# WHY THIS FILE EXISTS SEPARATELY. run_local.py calls `git pull --rebase --autostash` every hour.
# That has twice stashed the working tree, hit a conflict on the pop, and left files deleted plus
# two bot state files in a conflicted state. This script therefore does NOT touch git at all. It
# reads local CSVs, writes two local files, and posts to Discord. If the network is down it still
# writes the card to disk.
#
# THE MODEL (backtest, ONE POSITION PER PLAYER: n=96, 59.4%, ROI +10.3%. The +23.5% often
# quoted elsewhere counts a player twice when she qualifies in two markets - see rule 6.)
#   1 OVER side only. Not because unders are cursed - the profitable side actually rotates by
#     half-month - but because our under SELECTION was worse than random even in the months when
#     unders were the better side (blind -4.5%, ours -14.5%). We are bad at picking them.
#   2 SIGNAL must be flip, hotover or overshoot. flip_paper and cascade are the two biggest
#     sources by volume and both are dead, which is why most nights are silent.
#   3 SKIP if the book RAISED her number 0.5+ since her previous game - already repriced.
#     SKIP ALSO if there is NO previous line: the star IS that comparison, so with nothing to
#     compare the filter was never applied. Those 64 bets ran 48.4% / -10.0% and were dragging
#     the rule from +23.5% to +11.0% until 2026-08-15. Unknown is not starred.
#     raised n=41 ROI -1.1% | no-prev n=64 ROI -10.0% | starred n=108 ROI +23.5%
#   4 DRIFT is displayed, NOT used. Stacking it costs ~12u to buy nothing.
#   5 markets pra / pr / pts only. Re-tested WITH the star 2026-08-16: pa starred is
#     n=24 +4.3% ROI (not the -14.1% an older note claimed, which was a different
#     universe). reb/ast/ra barely fire at all - 2, 1 and 1 signals in the whole
#     season - so there is no volume hiding in the excluded markets.
#   6 ONE POSITION PER PLAYER, enforced not merely warned. Counting a player twice when
#     she qualifies in two markets is what made the backtest read +23.5% instead of
#     +10.3%, and the forward record 6-6 instead of 5-6. The card keeps her best price.
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
# board_seen.json = every (player|market|side|line) key present in the LAST scrape, with its
# timestamp. This is what "is the line still there" actually means. xbet_board.csv only records
# CHANGES, so a line that has sat unmoved all day has no recent row and looks stale when it is in
# fact the most stable number on the board.
SEEN = {}
try:
    SEEN = json.load(open(os.path.join(D, "board_seen.json")))
except Exception:
    pass

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

# ---- the board, anchored to GAMES, not to a fixed hours-before-tip window --------------------------
# THIS WAS A REAL BUG AND IT COST A BET. The old version kept board blocks that started within 30h
# of tip and called everything older "her previous game". But 1xbet posts lines a MEDIAN 29.9h
# before tip (p75 = 40.5h), so roughly half of all CURRENT lines were being thrown into the
# previous-game bucket. On 2026-08-15 Shakira Austin's live 32.5 was first quoted 43.1h out and
# got classified as her previous line, while a dead 31.5 - one quote, gone by 13:13 - was first
# quoted 28.4h out and got shown as the bet. The card advertised a number that no longer existed
# AND computed the star against tonight's own line.
#
# The backtest never had this bug: it anchors each block to the GAME it precedes. The live card
# was therefore not implementing the model that was measured. Now it matches - every block is
# attached to the player's next game within 36h, exactly as audit_signals.py does it.
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))

# every tip this player could be quoted for, so a block can be attached to the game it precedes
tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t:
        tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()

def game_for(team, when):
    """the first tip that starts AFTER this quote and within 60h - i.e. the game it is pricing"""
    for t in tips_of.get(team, []):
        if when <= t and (t - when).total_seconds() <= 60*3600:
            return t
    return None

# per (player, market, game-tip): every quote we hold for that game, newest last
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = None
    v.sort()
    for t, o in v:
        if tm is None: tm = teamnow.get(pl)
        if tm is None: break
        gt = game_for(tm, t)
        if gt is None: continue
        bygame[(pl, mk, gt)].append((t, ln, o))
for v in bygame.values(): v.sort()

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
    tonight = bygame.get((pl, mk, tips[tm]), [])
    if not tonight: continue
    seen.add((pl, mk))
    # THE LINE YOU CAN ACTUALLY BET IS THE MOST RECENT QUOTE, full stop. Not the most-quoted
    # line, which is what this used to pick and which is how a dead 31.5 reached the card while
    # 32.5 was live on the board.
    line_now, price_now = tonight[-1][1], tonight[-1][2]
    # HER PREVIOUS GAME'S LINE = the last quote attached to her PREVIOUS game, by game not by
    # clock. This is the star's reference point and it must not be contaminated by tonight.
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < tips[tm])
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    # drift is measured only across quotes at the line we would actually take
    same = [x for x in tonight if x[1] == line_now]
    drift = same[-1][2]/same[0][2] - 1 if len(same) >= 2 else 0.0
    rows.append(dict(pl=pl, name=b.get("player"), mk=mk, src=b.get("src") or "?", team=tm,
                     opp=opp.get(tm), tip=tips[tm], line=line_now, price=price_now,
                     drift=drift, prev=pv, med=med(pl, mk),
                     seen_utc=tonight[-1][0], noprev=(pv is None),
                     # NO PREVIOUS LINE IS NOT A STAR. The star IS the comparison against her
                     # previous game's number - with no previous number there is nothing to
                     # compare and the filter has not been applied at all. The old code read
                     # `pv is not None and ...`, so a missing previous line produced raised=False
                     # and the card BET it. Those 64 bets ran 48.4% / -10.0% ROI and dragged the
                     # rule from +23.5% down to +11.0%. Unknown is not starred; unknown is out.
                     raised=(pv is None or line_now - pv >= 0.5)))
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
# ONE POSITION PER PLAYER, ENFORCED - not merely warned about. The rule has always said a player
# qualifying in two markets is ONE bet, but the card used to list both and leave the choice to
# you, and the tracker logged both. That flattered every number: on 2026-08-11 Dearica Hamby went
# in as pts 13.5 AND pra 22.5, both won, and one good night was counted twice. The backtest has
# the same split - +23.5% counting both against +10.3% under this rule - so the card now picks
# her best-priced leg and that is the bet.
_bestleg = {}
for _r in sorted(PASS, key=lambda x: -x["price"]):
    _bestleg.setdefault(_r["pl"], _r)
_dropped = [r for r in PASS if _bestleg.get(r["pl"]) is not r]
PASS = sorted(_bestleg.values(), key=lambda r: r["tip"])
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
    # HOW OLD IS THIS NUMBER. The line shown is the most recent quote we hold, but the board is
    # only sampled every 10 min and you may read the ping later. A quote from 4 hours ago is not
    # a bet, it is a suggestion - so say how stale it is rather than let you find out at the book.
    # CONFIRMED = the line was in the most recent scrape of the board, whether or not the price
    # moved. That is the question you actually care about: is this number still buyable?
    conf = SEEN.get(f"{r['pl']}|{r['mk']}|Over|{r['line']}")
    ct = ts(conf) if conf else None
    if ct is not None:
        mins = (NOW - ct).total_seconds()/60
        tail += (f" · ✓ on the board {mins:.0f}m ago" if mins < 45
                 else f" · ⚠️ not seen for {mins/60:.1f}h — RECHECK THE BOARD")
    else:
        tail += " · ⚠️ not in the last scrape — RECHECK THE BOARD"
    out.append(tail)
    return out

lines = [f"**🎯 MODEL S · {slate}** · {len(PASS)} bet{'s' if len(PASS)!=1 else ''} · flat 1u"]
for r in PASS: lines += fmt(r, True)
if SECOND:
    lines.append(f"_— below: {len(SECOND)} rejected — the book already repriced her (raised 0.5+, "
                 f"n=41, ROI −1.1%) or she has no previous line to compare (n=64, ROI −10.0%). "
                 f"DO NOT BET. Shown so you can see what was screened out. —_")
    for r in SECOND: lines += fmt(r, False)
# ---- the parlay line ------------------------------------------------------------------------------
# Whenever 2+ bets qualify on a slate, pair them off and show the accumulator alongside. This is a
# STAKING choice, not a selection one - the picks are identical either way.
#
# WHY IT IS SHOWN AT ALL. 1xbet pays the straight product on a 2-leg accumulator (verified at the
# book: 1.87 x 1.73 = 3.2351, quoted 3.235), so a parlay is pure leverage with the SAME break-even
# as the singles - a single breaks even at p = 1/o, a pair at p^2 = 1/o^2, the same p. Backtest of
# singles-plus-pairs: risk 128u, +29.72u, ROI +23.2% against singles-only +14.9%.
#
# WHY IT IS LABELLED OPTIONAL. Both rest on the same single-leg edge, which has fewer than 50
# forward bets behind it. Leverage before proof only makes being wrong more expensive. Pairing is
# by tip time, consecutive, no reuse - a bet is in at most one parlay.
if len(PASS) >= 2:
    par = []
    for i in range(0, len(PASS)-1, 2):
        a, b2 = PASS[i], PASS[i+1]
        par.append((a, b2, a["price"] * b2["price"]))
    lines.append(f"_— optional parlay layer, 1u each. Same picks, leverage only. —_")
    for a, b2, od in par:
        lines.append(f"💰 **{a['name'].split()[-1]} + {b2['name'].split()[-1]}** "
                     f"{a['mk'].upper()} {a['line']} & {b2['mk'].upper()} {b2['line']} "
                     f"@ **{od:.2f}** · 1u")
    if len(PASS) % 2:
        lines.append(f"_({PASS[-1]['name'].split()[-1]} has no partner tonight — single only)_")

for _d in _dropped:
    lines.append(f"_· also qualified: {_d['name']} {_d['mk'].upper()} {_d['line']} @ {_d['price']:.2f} "
                 f"— NOT a second bet, one position per player. Kept her better price above._")
rej = [r for r in rows if r not in PASS]
if rej:
    lines.append(f"_skipped {len(rej)}: "
                 + ", ".join(f"{r['name'].split()[-1]} ("
                             + ("dead signal" if r["src"] not in TOP_SRC else
                                r["mk"] if r["mk"] not in BET_MKTS else
                                "no prev line" if r.get("noprev") else
                                "book raised") + ")"
                             for r in rej[:6]) + "_")
card = "\n".join(lines) if PASS else f"**🎯 MODEL S · {slate}** · no qualifying bets tonight."
print("\n" + card + "\n")

# ---- idempotent send, and log the picks so tomorrow can grade them --------------------------------
sent = json.load(open(SENT)) if os.path.exists(SENT) else {}
if not PASS:
    # SILENCE ON EMPTY. At ~0.8 starred bets a night most slates have nothing, and a nightly
    # "no qualifying bets" ping trains you to ignore the channel - which is exactly when you
    # miss the one that matters. No bet, no message. The card is still written to the log.
    print("no qualifying bets - staying silent (card is in the log)")
    sent[slate] = []
    tmp = SENT + ".tmp"; json.dump(sent, open(tmp, "w")); os.replace(tmp, SENT)
elif sent.get(slate) == [f"{r['pl']}|{r['mk']}|{r['line']}" for r in PASS] or all(
        any(f"{r['pl']}|{r['mk']}|{r['line']}" in v for v in sent.values() if isinstance(v, list))
        for r in PASS):
    # KEY ON THE PICKS, NOT THE COUNT. On 2026-08-15 a line-classification bug put Shakira Austin
    # on the card at a dead 31.5; the fix replaced her with Dearica Hamby - still two bets, so a
    # count-based check would have stayed silent and left you holding the wrong card. Any change
    # to WHO or WHAT LINE re-sends.
    print("already sent this slate with the same picks - not re-pinging")
else:
    if send(card):
        print("pinged Discord")
        sent[slate] = [f"{r['pl']}|{r['mk']}|{r['line']}" for r in PASS]
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
    hdr = ["slate","player","market","side","line","odds","src","prev_line","tip",
           "result","actual","pnl","note"]
    # A BET IS IDENTIFIED BY HER GAME, NOT BY THE SLATE LABEL. `slate` is min(tip) among games
    # inside the 16h window, so it MOVES as earlier games tip and drop out. On 2026-08-15 the
    # window held LA@WSH (23:30Z) and MIN@LV (00:00Z) and the slate read 2026-08-15; once WSH
    # tipped, MIN@LV was the only game left and the slate flipped to 2026-08-16. NaLyssa Smith's
    # single bet was therefore logged twice under two labels - and pinged twice. Dedup on
    # (player, market, tip) so the same game can never be recorded under two slates.
    if NOW < first_tip:
        keep = [r for r in rows_all
                if not (r["slate"] == sk and r.get("result") not in ("WIN", "loss", "push"))]
        # DEDUP AGAINST WHAT SURVIVES THE REWRITE, NOT AGAINST rows_all. The pre-tip rewrite has
        # just dropped this slate's pending rows so they can be rebuilt from the current board;
        # if the dedup set were built from rows_all it would contain those very rows and refuse
        # to re-add them, silently emptying the tracker on every run after the first.
        have_games = {(r.get("player"), r.get("market"), r.get("tip")) for r in keep if r.get("tip")}
        for r in PASS:
            tipkey = r["tip"].strftime("%Y-%m-%dT%H:%MZ")
            if (r["name"], r["mk"], tipkey) in have_games:
                print(f"  already tracked {r['name']} {r['mk']} for this game - not duplicating")
                continue
            keep.append({"slate": sk, "player": r["name"], "market": r["mk"], "side": "Over",
                         "line": r["line"], "odds": r["price"], "src": r["src"],
                         "prev_line": r["prev"] if r["prev"] is not None else "",
                         "tip": tipkey,
                         "result": "", "actual": "", "pnl": "", "note": "pending"})
        tmp = FWD + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader(); w.writerows(keep)
        os.replace(tmp, FWD)                       # atomic - never a half-written tracker
        print(f"tracker now holds exactly the {len(PASS)} picks on this card (pre-tip, rewritable)")
    else:
        print("first tip has passed - card frozen, tracker left untouched")
