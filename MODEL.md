# MODEL S — what it is, why each rule is there, and what it is worth

**S is for STAR.** The star filter is the model — see the ladder in §2. Everything
else in the rule is signal hygiene; the star is the edge.

Last updated 2026-08-14. This file is the single source of truth for the live model.
If this file and any older doc disagree, this file wins.


---

## 0. What "alpha" means in this file

Every table here reports **alpha**, not just win rate, because raw win rate is not comparable
across markets. The blind Over hit rate on this board differs a lot by market:

```
pra Over  50.9%      pr Over  52.6%      pts Over  50.7%      ast Over  44.0%
```

So a 50% win rate is *good* on ast (+6.0pp) and *bad* on pr (−2.6pp). **Alpha = our win rate
minus the blind win rate of the same market and side**, weighted across whatever mix of markets
that group happens to contain. It answers the only question that matters: did the signal beat
what you would have got picking that same market and side at random?

`z` is that alpha divided by its standard error - how many standard deviations from luck.
Roughly: |z| under 2 is suggestive, over 2 is interesting, and none of it means anything until
the multiplicity correction in §4.4.

---

## 1. MODEL S, in one box

```
SIGNAL    the engine flags her with src = flip  OR  hotover  OR  overshoot
MARKET    pra / pr / pts only
SIDE      Over. Never under.
STAR      the book did NOT raise her number by 0.5+ since her previous game   -> BET
STAKE     flat 1u. one bet per player-market. same player on 2 markets = ONE position.
FRESH     the signal must be from today or yesterday (0-1 days old)
TIMING    BET ON THE ALERT. waiting until close costs 4.7pp of ROI - see §3.
DRIFT     shown on the card, NOT used as a filter.
```

Volume: **~2.1 starred bets per night**, roughly 62 a month. Many nights are still silent -
the two biggest signals by volume (`flip_paper`, `cascade`) are dead and never make the card.

---

## 2. Why each rule exists

### OVER only
Our unders lost **−95.61u** while our overs made **+62.69u**. For a long time I called this
structural. That was over-stated, and the seasonal check corrected it:

| half-month | blind over ROI | blind under ROI | better side |
|---|---|---|---|
| 2026-06b | −9.5% | −4.5% | **under** |
| 2026-07a | −3.4% | −10.3% | over |
| 2026-07b | −2.8% | −10.9% | over |
| 2026-08a | −11.5% | −2.9% | **under** |

The profitable *side* rotates. The pooled "unders are −13%" number was dominated by July,
which is 56% of the sample and happened to be over-heavy.

**But we still never bet unders**, for a reason that survives the correction: our under
*selection* was worse than random even when unders were the good side. In 2026-06b blind unders
returned −4.5% and ours returned −14.5%. In 2026-08a blind −2.9%, ours −15.9%. We are not
being punished by the environment, we are just bad at picking unders. Different problem, and
"don't bet them" solves it.

### flip / hotover / overshoot only

**This list was wrong for half a day and the correction is the most instructive thing here.**
The first version ranked signals on their RAW numbers, kept the top two, and only *then*
discovered the star filter - which was applied to the two survivors and never re-run on the
signals already discarded. `overshoot` looked mediocre raw because it is half a good signal
and half a dead one averaged together, which is exactly what the star exists to separate:

| source | starred n | win% | ROI | alpha | z | verdict |
|---|---|---|---|---|---|---|
| **flip** | 33 | 81.8% | **+49.3%** | +30.4pp | +3.49 | in |
| **overshoot** | 86 | 61.6% | **+11.6%** | +10.0pp | +1.85 | in |
| hotover | 15 | 66.7% | +24.0% | +15.7pp | +1.22 | in (audited, kept) |
| flip_paper | 84 | 56.0% | +3.6% | +5.3pp | +0.97 | out |
| cascade | 63 | 49.2% | −12.1% | −1.7pp | −0.27 | out |

The three kept groups are **disjoint** - zero shared player-market-nights - so overshoot is 86
genuinely extra bets, not relabels of ones we already take.

`flip_paper` and `cascade` are the two biggest sources by volume and both are dead. That is why
there is still no bet on plenty of nights.

### What the three signals actually ARE

All three are generated in `cloud_xbet.py`. They are not variants of one idea:

**`flip`** — the under-model found a cold/shrink candidate, but the book's *over* line came in so
low (2+ below her anchor, and below our projection) that the over is the +EV side. The model
literally flips its own under into an over. It only gets the `flip` tag if the underlying signal
is a proven one; on an experimental signal it is tagged `flip_paper` instead, which is why
`flip_paper` is a different and dead animal.

**`overshoot`** — a board-wide sweep, independent of the player model. It looks for any 1xbet
over line sitting **3+ below the player's trailing median**, then guards it hard: confirmed-active
only (injury-first), current-team games only so a trade cannot blend the median, skip if minutes
are shrinking (role cut), skip if she is cold, **skip if Pinnacle agrees with the low line** (then
*our* median is the stale one, not the book's), and drop pts/pra in low-total games. It is the
most mechanically explicit of the three: *the book's number is far below what she actually does.*

**`hotover`** — the `else` branch. Any over that is not flip / newunder / usgshock / fragile /
model / starout falls here. It is a catch-all, not a designed signal, and in practice it fires
**only on pra** (all 15 starred bets are pra).

### The ladder - which filter is actually doing the work

Start from every over the engine has ever fired and add one restriction at a time:

```
0. every OVER signal, every market  (the raw menu)   n=596  56.7%  +18.63u  ROI  +3.1%  alpha +5.6pp
1. + markets pra / pr / pts only                     n=545  56.5%  +15.13u  ROI  +2.8%  alpha +5.5pp
2. + drop flip_paper, cascade and the rest           n=213  59.2%  +18.52u  ROI  +8.7%  alpha +7.7pp
3. + THE STAR                              <- LIVE   n=108  67.6%  +25.38u  ROI +23.5%  alpha +16.1pp

   restricting markets      +3.1% ->  +2.8%   ( -0.3pp)   kept 545/596
   dropping dead signals    +2.8% ->  +8.7%   ( +5.9pp)   kept 213/545
   THE STAR                 +8.7% -> +23.5%   (+14.8pp)   kept 108/213
```

**The star is the model.** It is worth more than twice what signal-selection is worth, and the
market filter is worth roughly nothing on its own (it stays because `pa` was clearly bad and
because mixing markets with 44-53% blind rates makes every pooled number unreadable).

Worth noticing: the raw over menu was already **+3.1%, alpha +5.6pp, z=+2.73**. The overs were
never the problem. The -32.92u came from the unders bolted onto the same menu.

### The star (book did not raise her 0.5+)
The single most valuable filter, and it replicates inside each signal independently — which is
what makes it a mechanism rather than a lucky cut:

```
             RAW                    STARRED                 RAISED
flip     n=60  65.0%  +19.6%    n=33  81.8%  +49.3%    n=27  44.4%  −16.8%
overshoot n=163 57.1%  +4.0%    n=86  61.6%  +11.6%    n=77  51.9%   −4.4%
```

The logic: when the book *raises* her line after a good game, it has already priced the thing
our signal is reacting to. When it holds or cuts, it hasn't. We buy the un-repriced ones.

This is a **gate, not a tier**. The 105 unstarred bets across all three signals run
**−6.86u, ROI −6.5%, alpha −0.9pp**. They are printed on the card so you can see what was
rejected. Do not bet them.


### Should we FADE the raised ones? No - tested, it still loses

The obvious idea: if the raised group returns −7.0% on the over, bet the under instead. It
does not work, and the reason is worth keeping:

```
RAISED  n=47   BET THE OVER   48.9%  avg 1.865   -4.54u  ROI  -9.7%   alpha -2.2pp
               FADE (under)   51.1%  avg 1.883   -2.33u  ROI  -5.0%   alpha +2.2pp
```

The two alphas are **mirror images by construction** - if the over is X above its baseline the
under is exactly X below its. Fading never creates information; it buys the other side of the
same coin at the other side's price and pays the vig a second time.

The raised group hits 48.9% on the over. That is a coin flip, and **the book's cut on those 47
lines averages 7.1%.** Either side of a coin flip loses that, every time. A signal that is *bad*
is not the same as a signal that is *reverse-good* - raised bets are not wrong, they are
uninformative, and there is nothing in an uninformative bet to fade.

Split by signal, the fade does not rescue itself either:

```
ALL raised, pooled       n=94   under hits 51.1%   break-even 53.2%   ROI  -4.7%
  raised flip            n=14   under hits 50.0%   break-even 53.0%   ROI  -5.8%
  raised hotover         n=12   under hits 66.7%   break-even 53.4%   ROI +24.3%   <- n=12. NOISE.
  raised overshoot       n=21   under hits 42.9%   break-even 53.0%   ROI -21.1%
```

Two of three lose; the one that "wins" is **twelve bets**, which is exactly what splitting a
coin-flip group three ways produces. That cell is the precise shape of the thing that has
burned this project over and over. Do not build on it.

### Drift is displayed, not used
The old model skipped bets whose price had lengthened 1%+. On flip/hotover specifically that
filter **costs 12.1u**. It is on the card as information only.

### pra / pr / pts only
`pa` ran −14.1%. `reb`, `ast`, `ra` have per-market blind baselines so different (ast Over is
44.0%, pr Over is 55.8%) that mixing them makes every pooled number a lie.

---

## 3. What it is worth

**Backtest**, one bet per player-market-night, priced at the first logged odds:

```
flip only                        n=25   84.0%  +13.69u  ROI +54.8%  alpha +32.4pp  z=+3.24
flip + hotover                   n=40   77.5%  +17.30u  ROI +43.2%  alpha +26.1pp  z=+3.31
flip + hotover + overshoot  LIVE n=108  67.6%  +25.38u  ROI +23.5%  alpha +16.1pp  z=+3.36
```

(Earlier drafts of this file quoted n=134 / +29.86u. That was the same rule **without** the
pra/pr/pts market filter, which the card does apply. n=108 is what the card actually bets.)

Adding overshoot cuts ROI-per-bet from 43.2% to 23.5% and raises total profit from +17.30u to
+25.38u. That is the trade: less edge per bet, ~47% more money, 2.7x the volume.

**Out of sample** (split at 2026-07-18, 60/40 on match-days):

```
LIVE  IN   n=40  70.0%  +11.44u  ROI +28.6%  alpha +18.6pp  z=+2.35
LIVE  OUT  n=68  66.2%  +13.94u  ROI +20.5%  alpha +14.7pp  z=+2.42
```

Both halves are big enough to read and both clear +20%. Month by month: July +24.8% (n=72),
August +15.5% (n=33). Decaying slightly, but positive throughout.

**Price basis, and a bug I had to back out.** I first reported that the board close was the
*best* price (+24.7% vs +22.3%). That was wrong. The close price was being read at the book's
**main line**, which for 63 of 134 bets was a *different* line from the one the bet was settled
against - and 52 of those had moved up, where a higher line naturally quotes longer odds. I was
crediting one line's price to another line's outcome. On the 71 bets where the close is quoted
at the same line, first and close are a wash:

```
CLEAN subset (close quoted at the same line)   first 1.832 +11.6%   close 1.839 +11.5%
```

**Price timing is worth nothing. Line timing is worth a lot** - see below.

**WHEN TO BET: on the alert.** The honest comparison is not two prices for one line, it is two
whole bets - the line-and-price you can have now, against the line-and-price at close:

```
BET ON THE ALERT   avg line 20.49   avg price 1.818   67.2%   +29.86u   ROI +22.3%
BET AT CLOSE       avg line 20.87   avg price 1.851   63.4%   +23.58u   ROI +17.6%
                                          waiting costs 6.28u = 4.7pp of ROI
```

Why: after the alert the line **rises on 38.8% of bets and falls on only 8.2%**. You gain about
3.3 cents of price by waiting and pay about 0.38 of line for it. That is a bad trade.

```
line ROSE after we saw it   n=52  (38.8%)  won 75.0%  ROI +33.9%
line held                   n=71  (53.0%)  won 60.6%  ROI +11.6%
line FELL                   n=11  ( 8.2%)  won 72.7%  ROI +36.2%
```

That top row is the CLV: the market moving toward us afterwards is the confirmation the signal
is real. **You capture that by betting early. Waiting for close means you are the one paying it.**

**Stress test** - the combined model stays profitable even if every bet were flat 1.70
(break-even 58.8% vs 67.2% actual, +19.00u).

**The best single piece of evidence** is August. In 2026-08a blind overs returned −11.5% - the
most over-hostile stretch in the data - and the model returned **+16.0%**. Roughly 27 points of
alpha against a punishing environment.

**Forward record: 4-3, +0.13u, ROI +1.9% over 7 bets.** Meaningless at this n. Review at 50,
which at ~2.6 bets a night is about three weeks away rather than three months.

## 4. Honest weak points - read before trusting this

1. **overshoot's cushion is thin, and its `pts` leg is the weak cell.** Overall it hits 61.6%
   against a break-even of 55.6% at its median price of 1.80 - six points of margin on n=86,
   where the CI is about ±10pp. Broken down:
   ```
   overshoot starred  pra   n=26  73.1%  ROI +33.5%  alpha +22.1pp  z=+2.26
   overshoot starred  pr    n=26  61.5%  ROI +10.4%  alpha  +9.0pp  z=+0.92
   overshoot starred  pts   n=16  43.8%  ROI -20.6%  alpha  -6.9pp  z=-0.55   <- watch this
   ```
   I did NOT cut pts, because pooled across all three signals pts is **+6.3%, alpha +7.7pp** -
   so the weakness lives in one 16-bet cell, and cutting a market on 16 bets is exactly the
   curve-fitting that has killed every previous version of this model. Flag it, watch it
   forward, do not act on it yet.
2. **overshoot is bet slightly shorter than flip** - median 1.80 vs 1.83, p25 1.73 vs 1.80.
   Not fatal, but it is why the margin is thinner.
3. **hotover: audited, and KEPT** - reversing what this file said earlier. I had called it
   unmeasurable because n=15 fell below my n>=20 reporting threshold. Measured, it is
   66.7%, +3.60u, ROI +24.0%, **alpha +15.7pp - the same alpha as the model overall.**
   Dropping it changes nothing and costs 15 bets:
   ```
   flip + overshoot  (drop)   n=119  67.2%  +26.25u  ROI +22.1%  z=+3.41   OOS 23.9 -> 21.0
   flip + hot + over (keep)   n=134  67.2%  +29.86u  ROI +22.3%  z=+3.62   OOS 22.8 -> 22.0
   ```
   It is small and it is a catch-all, but it is not dragging. Keep.
4. **MULTIPLICITY - the most important caveat in this file, now measured.** I simulated every
   outcome from that line's own de-vigged book probability (a world with no edge, same lines,
   same prices, same sample sizes) and re-ran the entire 558-cell search on each fake world:

   ```
   ASKING "is the BEST cell of my search significant?"
     min n=25   real +32.4%   null median +22.3%   p=0.193
     min n=40   real +20.2%   null median +15.1%   p=0.237
     min n=60   real +20.2%   null median +10.3%   p=0.077
     min n=80   real +12.8%   null median  +6.2%   p=0.213      -> NOT significant

   ASKING "is OUR cell significant?" (flip+hotover+overshoot x pra/pr/pts x starred)
     n=68   real +20.2%   null median -6.5%   p95 +12.3%        -> p=0.0095
   ```

   **Both numbers are true and they mean different things.** Cherry-picking the best of 558
   cells produces +22% ROI in a *no-edge* world about half the time - so the maximum of my
   search proves nothing. But our config is not that maximum (the max was +32.4% on n=29; ours
   is +20.2% on n=68), and tested as a stated rule it clears the null at p=0.0095.

   The honest position is between the two: our rule was chosen after looking at the data, so
   0.0095 is optimistic; it was chosen by a *mechanism* rather than by maximising ROI, so 0.19
   is pessimistic. **Probably real, not proven. The forward record settles it, nothing else.**
5. **We are betting a soft book.** 1xbet props sit 7.0% below Pinnacle no-vig fair
   (n=551 time-aligned, t=−42.9). The edge must clear that. It is why the filters are tight.
6. **The methodological lesson, kept deliberately:** when a new filter is discovered, re-run it
   across *every* candidate that was previously rejected. Ranking on raw performance and then
   filtering the survivors nearly cost this model two thirds of its bets.

## 5. Notifications — exactly two, by design

| # | when | script | silent if |
|---|---|---|---|
| 1 | evening, ~30 min after the board refresh | `model_card.py` | no starred bets |
| 2 | morning, after the last game settles | `ping_results.py` | nothing newly settled |

Everything else is muted. `health_check.py` prints to `wnba_loop.log` instead of pinging.
`cascade_watch.py` and `lineup_check.py` run with `NO_PING=1`. `alert_bets.py` is retired to
`_retired_alert_bets.py.txt`.

Both pingers are idempotent — `model_card_sent.json` and `results_sent.json` — so the 30-minute
loop cannot repeat a message.

---

## 6. Operating it

Everything runs on this laptop. **No GitHub, no git in the hot path** — `git pull --rebase
--autostash` destroyed local commits three times, which is why the card generator touches git
at all.

```powershell
cd C:\Users\Axioo\wnba-line-capture
.\wnba_loop.ps1        # leave this window open. Ctrl+C stops it.
```

- pipeline `run_local.py` every 30 min (board prices move continuously)
- grading `run_grade.py` every 2 h (games finish 09:00–12:00 WIB; late finals get swept up)
- `PYTHONIOENCODING=utf-8` is mandatory — cp1252 kills any script that prints ★ or 📊, and that
  silently stopped grading entirely once.

**Never auto-bet 1xbet.** Bets are placed by hand. `webhook.txt` is gitignored and must stay
that way.

---

## 6. The shadow log - every rejected filter, tracked forward

`shadow_log.py` records, **at decision time**, what each competing rule would have bet tonight.
`grade_shadow.py` settles them and prints a head-to-head scoreboard. Both are silent.

| config | rule |
|---|---|
| **MODEL_S** | flip/hotover/overshoot, pra/pr/pts, **starred** — LIVE |
| S_prev | flip+hotover only, starred (the model before overshoot went in) |
| S_drift | drift gate INSTEAD of the star |
| S_filterx | star AND drift stacked |
| S_nostar | same signals, no star at all |
| S_raised | only the ones the star rejects (should lose) |
| OLD_MENU | every over signal, any market, no filter |

**Why this exists.** Over four nights in August the drift gate showed **3-0, +81% ROI** and
MODEL_S showed **5-4, −1.2%**. On the full sample the drift gate is worth nothing (+8.3% versus
+8.7% for no filter at all) — it simply held no ticket on the one bad night. Four nights cannot
choose between rules and neither can forty bets. This log is how the choice eventually gets made
by forward data instead of by whichever backtest was run most recently.

**Decision-time only, never backfilled.** Reconstructing history from `xbet_board.csv` would use
the *final* board state, which is not what we could have acted on — the same contamination that
produced three withdrawn findings this week. Historical reconstruction lives in
`config_compare.py` and is kept separate on purpose.


## 2026-08-18 - the definitive feature sweep (mega_sweep.py)

One grid, every feature family, both sides, on all 6,077 two-sided board quotes. Box score
(usage share, usage trend, minutes trend, form vs line, trailing-median gap), momentum (streak of
games she beat her own line, rest days, team win/loss last game), line (the star, line move,
price), and game markets (Pinnacle total, spread, moneyline). 74 cells at n>=120.

    best real cell   rank 4 [under]  +5.1%
    shuffled best-of-grid   median +1.4%   p95 +4.2%   max +9.5%
    GLOBAL p = 0.0207

Two cells cleared the ceiling: `rank 4 [under]` and `over-streak 2 [over]`.

**over-streak 2 is dead.** It looked like the better of the two - not cherry-picked, and rising
with the streak (0: -8.3%, 1: -2.2%, 2: +4.4%). It failed everything after that:

    OOS         IN n=313 +8.7%  ->  OUT n=230 -1.5%
    streak 3+   -1.3%          the effect reverses instead of continuing
    by market   pr +15.2% (n=170) carries it; pts +0.4, pra -1.7, pa +0.2, ast -14.9
    form split  streak2 & form BELOW median +21.2%, ABOVE -3.4%   backwards

It was NOT the star filter in disguise (starred-streak2 +7.1% vs raised-streak2 +0.4%, only 38%
overlap), which is the one thing it had going for it. Not enough.

**What survived the whole sweep - two cells, both non-monotonic:**

    rank 2 OVER    +3.2% (n=1471)   IN +1.8% -> OUT +4.5%
    rank 4 UNDER   +5.1% (n=901)    IN +6.5% -> OUT +4.2%

Mechanism, if real: the book prices the STAR carefully because everyone bets her, and pays less
attention to the second option. Same inattention the star filter exploits, on a different axis.

Against both: rank 2 is a spike between negative neighbours (rank 1 -4.6%, rank 3 -5.0%), rank 4
likewise, and "fade the low ranks" is explicitly false - rank 5+ returns -5.4%. The alternating
shape (over good at 2, under good at 4 and 6) is what noise looks like cut fourteen ways. And the
p=0.0207 prices only the 74 cells in that grid, not the forty-odd scripts run before it.

Neither is live. `S_rank2` and `RANK2_ANY` are now in shadow_log.py so forward data settles it.
The rank-4 UNDER cannot be tracked there - every candidate row in that file is an over, and an
under-side ledger does not exist yet. That is the open build item.

**Game markets contributed nothing again.** Total, spread and moneyline made neither end of the
table (best: `game total HIGH [over]` +1.4%). That is the twelfth cross-market test to come back
empty, and it is consistent with the season's central finding: 1xbet's prop LINES match
Pinnacle's on 64% of quotes exactly - the 7% softness is in the PRICE, not the number. Tests that
look sideways at another market keep failing because there is nothing there to see. The star, and
possibly rank, look BACKWARDS IN TIME at the book's own previous number, which is the only
dimension where this book has been shown to be inattentive.

## 2026-08-18 (later) - the re-audit. Two corrections to what I reported earlier today.

### CORRECTION 1: the rank p-value was computed against the wrong null

mega_sweep permuted outcomes quote-by-quote. Rank is not a property of a quote, it is a property
of a PLAYER for most of a season, so that null could not have produced the data.

    rank 2 OVER   1466 quotes -> 58 players, 256 player-GAMES (5.7 correlated quotes each)
    rank 4 UNDER   891 quotes -> 52 players, 194 player-games

    player-block bootstrap (the honest interval):
      rank 2 OVER   +2.5%   95% CI [-5.6%, +10.6%]   INCLUDES 0
      rank 4 UNDER  +5.0%   95% CI [-3.3%, +13.1%]   INCLUDES 0

In their favour: leave-one-player-out never turns either non-positive (0 of 58, 0 of 52), so this
is a broad weak effect rather than one good season. But `p=0.0207` should not have been quoted.
Effective n is ~250 player-games and a +2.5% edge is invisible at that size. Both stay on paper.
(reaudit_rank.py test C is malformed - assigning a player's whole season to her modal rank
invents a rank6-under cell at +27.8% that is +2.1% in the real data. Ignore its p=0.0000.)

### CORRECTION 2: the star filter alone LOSES. The engine's signal is doing the work.

passcount.py built the universe the way the card bets - unraised, BET_MKTS, one position per
player, best price - across the whole board:

    ALL Model-S-shaped   n=838   50.7%   ROI -4.4%   95% CI [-11.1%, +2.1%]

That is the star filter with NO `src in (flip, hotover, overshoot)` condition, because
xbet_board.csv does not carry which signal fired. It loses. So the +11% headline is NOT the star
- it is the engine's signal selection, which the star then filters. The season's summary line
("the star is the only surviving edge") is wrong as written. Correct version: the star is the
only surviving FILTER; the signals select the population it filters, and if they are noise the
star has nothing to improve. Testing that is the open question.

### TEAMMATES: a real pattern, not a bettable one

Anchored on the PASS (known at bet time), not on the pick hitting (knowable only after).

    teammate of a pass, OVER   -8.5%  [-16.4, +0.1]     vs baseline -4.9%
    teammate ast OVER         -16.3%  [-32.6, -0.8]     excludes 0
    teammate ra  OVER         -17.4%  [-33.2, -0.8]     excludes 0
    teammate ast UNDER         -0.2%  [-13.5, +14.1]    fading returns nothing
    teammate ra  UNDER         +3.8%  [-12.9, +20.9]
    block permutation over the whole teammate grid      p = 0.324

The anti-correlation is real in DIRECTION - teammates' assist and reb+ast overs underperform when
S fires on a scorer - and the under price already absorbs it. Same wall as every other fade.

THE STAR INVERTS ON TEAMMATES:

    teammate ALSO unraised, OVER  -15.3%  [-29.7, -1.9]   excludes 0, WRONG WAY
    teammate WAS raised,    OVER   -5.4%  [-15.1,  +4.8]

The game-level inattention story is false. The filter works on the player it fires on and
reverses next to her. Independent support for one-position-per-player and against same-game
stacking.

### PASS-COUNT PER TEAM-GAME: dead

An undeduped seven-market cut showed -29.3% / -9.7% / +3.6% across 1/2/3 passes. Rebuilt with
dedup and BET_MKTS it goes 1:-19.0, 2:-13.0, 3:+0.0, 4:-2.4, 5:-5.9 - peaks and falls. Never
positive in either time-half. Confounded with roster coverage (few-quote team-games +5.9%,
many-quote -7.3%). Block permutation p = 0.7432.

### METHOD NOTE - adopt for everything from here

Prop quotes cluster by player and by game. A quote-level bootstrap or permutation is roughly
sqrt(quotes-per-player) too tight and manufactures significance. Bootstrap and permute at the
level the LABEL lives at: player-block for player attributes (rank, role), game-block for
game attributes (pass count, total). This is the same bug class as every other one this season -
two identifiers treated as interchangeable, here "a quote" and "an independent observation".

## 2026-08-18 (final) - IS THE MODEL GOOD? The honest answer, with the right nulls.

### The backtest edge does not survive the correct null

    MODEL S (signal fired)          n=99   61.6%  +13.7%  95CI [-5.0, +31.2]
    same star filter, NO signal     n=822  50.4%   -5.2%  95CI [-11.2, +0.5]
    gap +18.9pp

That gap looks decisive until you ask what null it beats. Two permutations:

    BETWEEN players (does the engine pick good PLAYERS?)          p = 0.0568
    WITHIN players  (does the engine pick good NIGHTS?)           p = 0.3280

The second is the one that matters, because picking nights is what the signals claim to do. Take
the same 44 players, the same number of bets each, and choose their nights AT RANDOM from their
star-filtered games: median +10.0%, p95 +23.4%, against the engine's +13.7%. The engine's timing
is worth +3.7pp over a coin flip and cannot be told apart from one.

So whatever Model S has is in WHICH PLAYERS it concentrates on and how often, not in when it
fires. And the player-level test is only borderline.

### The forward record - the only data not fitted to anything

    MODEL S forward (star-filtered, deduped)  n=13   53.8%   -0.13u   -1.0%
    three SIGS (flip/hotover/overshoot)       n=221  55.2%   +4.40u   +2.0%  95CI [-10.7, +13.7]
      flip family (flip + flip_paper)         n=141  56.7%   +7.40u   +5.2%  95CI [ -8.3, +17.2]
      overshoot                               n=144  54.2%   -0.63u   -0.4%
    ENTIRE PING MENU                          n=869  51.1%  -55.91u   -6.4%  95CI [-12.1, -1.0]

The last line is the only statistically solid result in the whole file: the menu as a whole is
losing, and its interval EXCLUDES ZERO. newunder (-45.27u over 303 bets) and cascade (-8.47u over
199) are where it goes.

### CLV says no edge, and CLV is our own stated proof standard

    odds_clv   three SIGS -0.001 | flip family +0.005 | overshoot +0.003 | entire menu -0.001
    sharp_clv  three SIGS -0.188 (n=32) | flip -0.190 (n=21) | flip_paper +0.020 (n=50)

Flat against our own closing number, and negative against Pinnacle on the signals with enough
sharp coverage to read. The NBA cousin ran -6% on the same metric and was shelved for it. A model
that genuinely beat a soft book would show positive odds_clv long before it showed profit.

### VERDICT

Not good, not proven bad, and the weight is negative. Nothing here clears a bar we set ourselves.
The one component with any forward support is the FLIP FAMILY: n=141, 56.7%, +5.2%, the only
group with non-negative CLV on both measures. Its interval still spans zero.

Everything hunted today died under clustered nulls: rank2 over, rank4 under, over-streak-2,
teammate correlation, pass-count, and every game-market test. No new profitable filter was found.

The correct posture is the one already in place - paper/track, never auto-bet, and let the
forward column decide. What would change the verdict is odds_clv turning positive on the flip
family over another 100+ bets. What would end it is the menu's -6.4% continuing.

## 2026-08-18 - QUALIFICATION AUDIT: how a bet actually becomes a Model S bet

Four gates, in order:

    1  src in (flip, hotover, overshoot)          set by cloud_xbet at capture time
    2  mk  in (pra, pr, pts)                      BET_MKTS in model_card
    3  not raised                                 book has not moved her line up 0.5+ since her
                                                  PREVIOUS GAME (not previous quote)
    4  one position per player, best price         _bestleg dedup

### Gate 1 - what the three signals actually are

`flip` (cloud_xbet ~665) fires only on a player who ALREADY carries an UNDER signal: her 1xbet
OVER line has overshot to at least 2 below her anchor AND below our projection, at a price above
our fair. It is a contrarian read on our own under - the book has run the number so far down that
the other side became free. `flip_paper` is the same shape on an unproven underlying signal.

`hotover` is the residual tag for an over that is not a flip and not new/usgshock. In practice it
is 100% pra (521 of 521 rows).

`overshoot` (overshoot_overs, ~389) is a genuine SEPARATE board-wide scan, not a fallback: any
over line >=3 below the player's trailing 10-game median, gated by injury status, current-team-only
history, a MINUTES-SHRINK check on disjoint 5v5 windows, a cold-form skip, a period/live-prop
guard, a game-total trap, a PINNACLE CONFIRM (if the sharp agrees with 1xbet's low line then OUR
median is the stale one - drop), EV>0, and one bet per player.

### FINDING 1 - a latent mislabelling bug in the grader

grade_bets.py:28 writes

    src = b.get("src", "") or ("model" if b["side"] == "Under" else "overshoot")

So ANY row reaching the grader with a blank src is silently filed as `overshoot` (if an over) or
`model` (if an under) - the two most consequential buckets in the project. Current exposure is
small: all 19,295 bets_log rows carry a src, so only the 41-row pre-src era is affected. But it is
live, and if cloud_xbet ever emits a blank src those bets are absorbed into a proven bucket with
no trace. The same fallback is repeated at clv_reader.py:12, build_dashboard.py:72 and
bet_timing_study.py:22. Not fixed here - changing it alters the meaning of historical rows and
should be a deliberate decision.

### FINDING 2 - BET_MKTS contradicts overshoot's own design note, and the DATA backs BET_MKTS

cloud_xbet:56 records the June-15 lesson: "POINTS crater (so pts/PRA overshoot-overs are TRAPS)
... keep pa/pr/ra, drop pts/pra". BET_MKTS does the exact opposite - it keeps pra and pts and
discards pa and ra. That silently drops 23% of overshoot's output (pa 365, ra 5 of 1577) and 21%
of flip's.

Forward evidence (graded_bets, player-block CIs) says BET_MKTS is the right config and the
comment is stale:

    overshoot pts/pra  ("its trap set")   n=68   57.4%   +6.2%  CI [-13.8, +26.5]  clv +0.008
    overshoot pa/pr/ra ("its safe set")   n=76   51.3%   -6.3%  CI [-27.0, +14.5]  clv -0.002

    BET_MKTS  (what we bet)               n=280  56.1%   +3.8%  CI [ -6.1, +14.2]  clv +0.005
    pa + ra   (what we discard)           n=39   51.3%   -6.3%  CI [-35.6, +19.9]  clv -0.009

Inverted relative to the comment. Both CIs span zero and n=39 on the discarded group is thin, so
this is not proof - but nothing supports re-admitting pa/ra, and the comment should not be left
where it will mislead the next change. Best single market is pra (n=75, 60.0%, +11.8%), which is
also the only market hotover ever fires in.

### Gate 3 is sound

model_card:187 selects the previous line BY GAME (`g < tips[tm]`), not by clock - the fix for the
30h bucketing bug that once showed a dead 31.5 while 32.5 was live. And `raised=(pv is None or
line_now - pv >= 0.5)` correctly treats a missing previous line as NOT starred. Both verified
against the current source.
