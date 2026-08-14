# THE OVER MODEL — what it is, why each rule is there, and what it is worth

Last updated 2026-08-14. This file is the single source of truth for the live model.
If this file and any older doc disagree, this file wins.

---

## 1. The rule, in one box

```
SIGNAL    the engine flags her with src = flip  OR  hotover
MARKET    pra / pr / pts only
SIDE      Over. Never under.
STAR      the book did NOT raise her number by 0.5+ since her previous game   -> BET
STAKE     flat 1u. one bet per player-market. same player on 2 markets = ONE position.
FRESH     the signal must be from today or yesterday (0-1 days old)
TIMING    place it whenever the alert fires. waiting is worth 0.4 cents. not a real edge.
DRIFT     shown on the card, NOT used as a filter.
```

Volume: **~0.7 starred bets per night**, roughly 21 a month. Most nights are silent.
That is the model working, not the model broken.

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

### flip / hotover only
Every over-source, one bet per player-market-night, scored as **alpha over the matched
per-market blind baseline** (raw win rate is meaningless when one subset is pra and another
is ast):

| source | starred n | win% | ROI | alpha | z |
|---|---|---|---|---|---|
| **flip** | 20 | 75.0% | **+37.9%** | +23.6pp | +2.11 |
| overshoot | 39 | 61.5% | +11.2% | +10.2pp | +1.28 |
| hotover | 9 | — | — | too few | — |
| flip_paper | 59 | 49.2% | −9.7% | −1.4pp | −0.22 |
| cascade | 43 | 46.5% | −14.1% | −4.3pp | −0.56 |

`flip_paper` and `cascade` are the two biggest sources by volume and both are **dead**.
That is why the card ignores them, and it is why there is no bet most nights.

### The star (book did not raise her 0.5+)
This is the single most valuable filter, and it replicates inside each signal independently:

```
flip  RAW       n=34   64.7%   +18.9% ROI
flip  STARRED   n=20   75.0%   +37.9% ROI     <- the whole edge is here
flip  raised    n=14   (loses)
```

The logic: when the book *raises* her line after a good game, it has already priced the thing
our signal is reacting to. When it holds or cuts, it hasn't. We are buying the un-repriced ones.

Unstarred bets are still printed on the card, labelled and not recommended. Across 48 of them
they ran **−5.33u**. Do not take them.

### Drift is displayed, not used
The old model skipped bets whose price had lengthened 1%+. On flip/hotover specifically that
filter **costs 12.1u**. It is on the card as information only.

### pra / pr / pts only
`pa` ran −14.1%. `reb`, `ast`, `ra` have per-market blind baselines so different (ast Over is
44.0%, pr Over is 55.8%) that mixing them makes every pooled number a lie.

---

## 3. What it is worth

**Backtest** (strict universe — both sides quoted, drift computable, one bet per
player-market-night):

```
flip + hotover, STARRED    n=29   21-8   72.4%   +9.39u   ROI +32.4%   alpha +21.2pp   z=+2.28
```

On the looser universe used when the model was first wired: n=42, 78.6%, +18.96u, +45.1% ROI,
alpha +27.2pp, z=3.53, **positive in all three months**.

**The best single piece of evidence** is August. In 2026-08a blind overs returned −11.5% —
the most over-hostile stretch in the data — and the model returned **+16.0% (+3.84u on 24)**.
Roughly 27 points of alpha against a punishing environment. That is the strongest sign it is
reading something real rather than riding an over-friendly season.

**Forward record: 4-3, +0.13u, ROI +1.9% over 7 bets.** Meaningless at this n. Review at 50.

---

## 4. Honest weak points — read before trusting this

1. **hotover barely qualifies.** In the strict universe hotover-starred is n=9. Raw hotover is
   −13.4%. The edge measured above is carried almost entirely by `flip`. Dropping hotover would
   cost ~a third of the volume and probably lose nothing.
2. **overshoot is the strongest thing we are NOT betting.** Starred overshoot is +11.2% on
   n=39 — four times hotover's sample. Adding it gives n=68, 66.2%, +13.76u, alpha +14.9pp,
   **z=+2.46, higher than the live model alone**. This is the first change to consider.
3. **n=29 is small.** ±18pp confidence interval. z=+2.28 is real but not a multiplicity-priced
   result across all the variants that were searched this session.
4. **We are betting a soft book.** 1xbet props sit 7.0% below Pinnacle no-vig fair
   (n=551 time-aligned, t=−42.9). The edge must clear that. It is why the filters are so tight.

---

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
