# THE OVER MODEL — what it is, why each rule is there, and what it is worth

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

## 1. The rule, in one box

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

Volume: **~2.6 starred bets per night**, roughly 78 a month. Many nights are still silent -
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

This is a **gate, not a tier**. The 127 unstarred bets across all three signals run
**−8.84u, ROI −7.0%, alpha −1.2pp**. They are printed on the card so you can see what was
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
flip only                        n=33   81.8%  +16.27u  ROI +49.3%  alpha +30.4pp  z=+3.49
flip + hotover                   n=48   77.1%  +19.87u  ROI +41.4%  alpha +25.8pp  z=+3.58
flip + hotover + overshoot  LIVE n=134  67.2%  +29.86u  ROI +22.3%  alpha +15.6pp  z=+3.62
```

Adding overshoot halves ROI-per-bet and raises total profit from +19.87u to +29.86u. That is
the trade, stated plainly: less edge per bet, ~50% more money, 3x the volume.

**Out of sample** (split at 2026-07-18, 60/40 on match-days):

```
flip + hotover              IN n=14 unmeasurable      OUT n=34  +40.1%  z=+2.94
overshoot starred           IN n=35  +14.1%           OUT n=51   +9.9%  z=+1.31
flip + hotover + overshoot  IN n=49  +22.8%           OUT n=85  +22.0%  z=+2.87
```

**+22.8% in, +22.0% out.** The combined model is the only configuration with a holdout big
enough on *both* sides to mean anything - flip+hotover alone has n=14 in sample, so its
out-of-sample number has nothing to be compared against.

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
