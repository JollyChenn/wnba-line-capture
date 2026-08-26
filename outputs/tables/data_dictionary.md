# WNBA line-capture -- DATA DICTIONARY

Generated 2026-08-26T06:26Z by outputs/t1_enum.py (read-only audit).

Scope: every `.csv` in repo root, `data/`, `elo_model/`. `.bak.csv` / `pre-*` files are prior-state
backups kept by the pipeline and are flagged as such -- they are NOT independent data.

| file | rows | cols | date col | date range |
|---|---|---|---|---|
| `bets_log.csv` | 32,273 | 11 | captured_utc | 2026-06-14T13:47:20 .. 2026-08-26T06:23:37 |
| `bets_log.pre-src.bak.csv` (BACKUP) | 41 | 10 | captured_utc | 2026-06-14T13:47:20 .. 2026-06-15T22:59:20 |
| `cascade_log.csv` | 3 | 14 | game_date | 2026-06-17 .. 2026-06-17 |
| `drift_gate_today.csv` | 19 | 17 | date | 2026-08-25 .. 2026-08-25 |
| `drift_log.csv` | 12,813 | 16 | logged_utc | 2026-08-08T09:12:52 .. 2026-08-26T06:23:45 |
| `drift_track.csv` | 1,025 | 13 | date | 2026-06-14 .. 2026-08-25 |
| `fade_graded.csv` | 236 | 12 | logged_utc | 2026-08-03T05:58:29 .. 2026-08-26T00:06:48 |
| `fade_paper.csv` | 237 | 9 | logged_utc | 2026-08-03T05:58:29 .. 2026-08-26T05:21:17 |
| `fam_bets.csv` | 1,025 | 16 | date | 20260614 .. 20260825 |
| `gamelines.csv` | 32,192 | 8 | captured_utc | 2026-07-11T16:40:22 .. 2026-08-26T06:23:44 |
| `graded_bets.csv` | 1,025 | 16 | date | 20260614 .. 20260825 |
| `graded_bets.pre-dedup.bak.csv` (BACKUP) | 13 | 14 | date | 20260614 .. 20260615 |
| `graded_bets.pre-src.bak.csv` (BACKUP) | 4 | 13 | date | 20260614 .. 20260614 |
| `injuries_log.csv` | 958 | 5 | captured_utc | 2026-06-24T20:30:22 .. 2026-08-26T02:11:43 |
| `line_snapshots.csv` | 174 | 11 | captured_utc | 2026-06-13T20:23:17 .. 2026-06-15T23:56:37 |
| `lineups_log.csv` | 2,897 | 5 | captured_utc | 2026-06-24T23:34:39 .. 2026-08-26T02:11:43 |
| `live_lines.csv` | 56,843 | 7 | ts | 2026-07-16T00:09:03 .. 2026-08-11T23:48:45 |
| `live_snapshots.csv` | 1,269 | 15 | ts | 2026-07-16T00:09:03 .. 2026-08-11T23:48:45 |
| `model_forward.csv` | 27 | 13 | slate | 20260811 .. 20260825 |
| `model_forward.pre-slatefix.bak.csv` (BACKUP) | 24 | 13 | slate | 20260811 .. 20260825 |
| `model_forward.pre-void.bak.csv` (BACKUP) | 27 | 13 | slate | 20260811 .. 20260825 |
| `my_bets.csv` | 5 | 14 | date | 20260617 .. 20260620 |
| `parlay_forward.csv` | 39 | 14 | slate | 2026-07-02 .. 2026-08-25 |
| `picks_log.csv` | 2,503 | 12 | pick_date | 2026-06-12 .. 2026-08-25 |
| `pinged_bets.backup.csv` (BACKUP) | 31 | 14 | sent_utc | 2026-08-08T09:46:16 .. 2026-08-08T22:44:32 |
| `pinged_bets.csv` | 101 | 15 | sent_utc | 2026-08-08T09:46:16 .. 2026-08-13T21:00:14 |
| `pinn_board.csv` | 22,824 | 7 | captured_utc | 2026-08-21T13:11:37 .. 2026-08-26T06:23:37 |
| `pinn_snapshots.csv` | 6,814 | 7 | captured_utc | 2026-06-20T15:19:46 .. 2026-08-26T06:23:37 |
| `shadow_forward.csv` | 1,641 | 17 | slate | 2026-06-24 .. 2026-08-25 |
| `shadow_forward.pre-backfill.bak.csv` (BACKUP) | 191 | 16 | slate | 2026-08-15 .. 2026-08-22 |
| `shadow_forward.pre-gap.bak.csv` (BACKUP) | 124 | 14 | slate | 2026-08-15 .. 2026-08-21 |
| `shadow_forward.pre-rank.bak.csv` (BACKUP) | 44 | 14 | slate | 2026-08-15 .. 2026-08-18 |
| `shadow_forward.pre-slatefix.bak.csv` (BACKUP) | 1,594 | 17 | slate | 2026-06-24 .. 2026-08-25 |
| `shadow_forward.pre-void.bak.csv` (BACKUP) | 1,641 | 17 | slate | 2026-06-24 .. 2026-08-25 |
| `xbet_board.csv` | 81,755 | 6 | captured_utc | 2026-06-24T10:26:26 .. 2026-08-26T06:20:22 |
| `xbet_gamelines.csv` | 12,482 | 8 | captured_utc | 2026-08-16T05:00:19 .. 2026-08-26T06:23:39 |
| `xbet_snapshots.csv` | 47,646 | 6 | captured_utc | 2026-06-13T20:07:12 .. 2026-08-26T06:23:37 |
| `data/box_2026.csv` | 5,678 | 11 | - | - |
| `data/box_2026.pre-allstar-purge.bak.csv` (BACKUP) | 5,593 | 11 | - | - |
| `data/games_2026.csv` | 290 | 7 | date | 20260508 .. 20260826 |
| `data/games_2026.pre-allstar-purge.bak.csv` (BACKUP) | 286 | 7 | date | 20260508 .. 20260824 |
| `data/halves_2026.csv` | 2,156 | 6 | date | 20260508 .. 20260622 |
| `elo_model/be_odds.csv` | 1,861 | 15 | - | - |
| `elo_model/betexplorer_ml.csv` | 333 | 6 | - | - |
| `elo_model/box_full.csv` | 37,509 | 22 | - | - |
| `elo_model/elo_forward_log.csv` | 99 | 31 | logged_utc | 2026-07-15T18:41:32 .. 2026-08-03T23:45:03 |
| `elo_model/elo_forward_log_v1.csv` | 19 | 12 | logged_utc | 2026-07-11T16:41:45 .. 2026-07-14T18:43:39 |
| `elo_model/elo_graded.csv` | 99 | 46 | logged_utc | 2026-07-15T18:41:32 .. 2026-08-03T23:45:03 |
| `elo_model/espn_odds.csv` | 185 | 6 | - | - |
| `elo_model/feats_v3.csv` | 1,923 | 21 | - | - |
| `elo_model/feats_v4.csv` | 1,027 | 28 | - | - |
| `elo_model/feats_v5.csv` | 1,027 | 34 | - | - |
| `elo_model/gameinfo.csv` | 1,059 | 4 | - | - |
| `elo_model/games_full.csv` | 2,058 | 7 | date | 20190509 .. 20260802 |
| `elo_model/plays_full.csv` | 415,714 | 8 | - | - |
| `elo_model/plays_text.csv` | 179,895 | 10 | - | - |
| `elo_model/ratings.csv` | 454 | 6 | - | - |
| `elo_model/shots.csv` | 253,303 | 8 | - | - |
| `elo_model/timeouts.csv` | 17,478 | 4 | - | - |
| `elo_model/zone_feats.csv` | 1,046 | 4 | - | - |

---

## Per-file detail

### `bets_log.csv`

Rows: **32,273**  Columns: **11**  Date range (`captured_utc`): **2026-06-14T13:47:20 .. 2026-08-26T06:23:37**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 32,273 (100%) | 1,659 | `2026-06-14T13:47:20+00:00` |
| date | date(YYYY-MM-DD) | 32,273 (100%) | 68 | `2026-06-14` |
| player | str | 32,273 (100%) | 105 | `Shakira Austin` |
| market | str | 32,273 (100%) | 7 | `pts` |
| side | str | 32,273 (100%) | 2 | `Under` |
| line | float | 32,273 (100%) | 34 | `15.5` |
| odds | float | 32,273 (100%) | 65 | `1.9` |
| tier | str | 32,273 (100%) | 4 | `STRONG` |
| ev | float | 32,273 (100%) | 627 | `0.445` |
| pinn | float | 7,113 (22%) | 48 | `15.5` |
| src | str | 32,273 (100%) | 10 | `model` |

Sample row:

```
captured_utc='2026-06-14T13:47:20+00:00', date='2026-06-14', player='Shakira Austin', market='pts', side='Under', line='15.5', odds='1.9', tier='STRONG', ev='0.445', pinn='', src='model'
```

### `bets_log.pre-src.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **41**  Columns: **10**  Date range (`captured_utc`): **2026-06-14T13:47:20 .. 2026-06-15T22:59:20**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 41 (100%) | 8 | `2026-06-14T13:47:20+00:00` |
| date | date(YYYY-MM-DD) | 41 (100%) | 2 | `2026-06-14` |
| player | str | 41 (100%) | 9 | `Shakira Austin` |
| market | str | 41 (100%) | 4 | `pts` |
| side | str | 41 (100%) | 2 | `Under` |
| line | float | 41 (100%) | 12 | `15.5` |
| odds | float | 41 (100%) | 12 | `1.9` |
| tier | str | 41 (100%) | 2 | `STRONG` |
| ev | float | 41 (100%) | 17 | `0.445` |
| pinn | float | 1 (2%) | 2 | `15.5` |

Sample row:

```
captured_utc='2026-06-14T13:47:20+00:00', date='2026-06-14', player='Shakira Austin', market='pts', side='Under', line='15.5', odds='1.9', tier='STRONG', ev='0.445', pinn=''
```

### `cascade_log.csv`

Rows: **3**  Columns: **14**  Date range (`game_date`): **2026-06-17 .. 2026-06-17**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_date | date(YYYY-MM-DD) | 3 (100%) | 1 | `2026-06-17` |
| game_id | int | 3 (100%) | 1 | `401856996` |
| team | str | 3 (100%) | 1 | `WSH` |
| trigger_out | str | 3 (100%) | 1 | `Shakira Austin` |
| player | str | 3 (100%) | 3 | `Michaela Onyenwere` |
| market | str | 3 (100%) | 1 | `pra` |
| side | str | 3 (100%) | 1 | `Over` |
| line | float | 3 (100%) | 3 | `18.5` |
| actual | int | 3 (100%) | 3 | `25` |
| result | bool/enum | 3 (100%) | 2 | `WIN` |
| odds_captured | str | 3 (100%) | 1 | `NOT_CAPTURED` |
| clv | empty | 0 (0%) | 1 | `` |
| illustrative_pnl_at_1.75 | str | 3 (100%) | 2 | `+0.75` |
| note | str | 3 (100%) | 1 | `Austin+Iriafen OUT; LINE is bot median-a...` |

Sample row:

```
game_date='2026-06-17', game_id='401856996', team='WSH', trigger_out='Shakira Austin', player='Michaela Onyenwere', market='pra', side='Over', line='18.5', actual='25', result='WIN', odds_captured='NOT_CAPTURED', clv='NA', illustrative_pnl_at_1.75='+0.75', note='Austin+Iriafen OUT; LINE is bot median-anchor NOT a real 1xbet line; fair ~1.75; real odds+CLV never captured'
```

### `drift_gate_today.csv`

Rows: **19**  Columns: **17**  Date range (`date`): **2026-08-25 .. 2026-08-25**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| date | date(YYYY-MM-DD) | 19 (100%) | 1 | `2026-08-25` |
| player | str | 19 (100%) | 17 | `Azura Stevens` |
| market | str | 19 (100%) | 5 | `pts` |
| side | str | 19 (100%) | 2 | `Under` |
| line | float | 19 (100%) | 12 | `10.5` |
| src | str | 19 (100%) | 6 | `newunder` |
| open_odds | float | 19 (100%) | 8 | `1.73` |
| now_odds | float | 19 (100%) | 7 | `1.73` |
| move_pct | float | 19 (100%) | 3 | `0.0` |
| verdict | str | 19 (100%) | 2 | `BET (steady)` |
| confidence | str | 19 (100%) | 3 | `ok 85%` |
| line_moved | str | 5 (26%) | 5 | `20.5->19.5` |
| fade_side | str | 2 (11%) | 2 | `Under` |
| fade_price | float | 2 (11%) | 3 | `1.8` |
| captures | int | 19 (100%) | 11 | `65` |
| span_h | float | 19 (100%) | 11 | `8.5` |
| last_utc | datetime | 19 (100%) | 7 | `2026-08-25T22:43:06Z` |

Sample row:

```
date='2026-08-25', player='Azura Stevens', market='pts', side='Under', line='10.5', src='newunder', open_odds='1.73', now_odds='1.73', move_pct='0.0', verdict='BET (steady)', confidence='ok 85%', line_moved='', fade_side='', fade_price='', captures='65', span_h='8.5', last_utc='2026-08-25T22:43:06Z'
```

### `drift_log.csv`

Rows: **12,813**  Columns: **16**  Date range (`logged_utc`): **2026-08-08T09:12:52 .. 2026-08-26T06:23:45**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| logged_utc | datetime | 12,813 (100%) | 569 | `2026-08-08T09:12:52Z` |
| date | date(YYYY-MM-DD) | 12,813 (100%) | 18 | `2026-08-08` |
| player | str | 12,813 (100%) | 71 | `Alyssa Thomas` |
| market | str | 12,813 (100%) | 5 | `pts` |
| side | str | 12,813 (100%) | 2 | `Over` |
| line | float | 12,813 (100%) | 32 | `14.5` |
| src | str | 12,813 (100%) | 9 | `flip_paper` |
| open_odds | float | 12,813 (100%) | 42 | `1.88` |
| now_odds | float | 12,813 (100%) | 50 | `1.88` |
| move_pct | float | 12,813 (100%) | 143 | `0.0` |
| verdict | str | 12,813 (100%) | 3 | `BET (steady)` |
| confidence | str | 12,813 (100%) | 5 | `ok 85%` |
| line_moved | str | 1,518 (12%) | 67 | `17.5->18.5` |
| fade_side | str | 2,393 (19%) | 3 | `Over` |
| fade_price | float | 2,393 (19%) | 35 | `1.78` |
| captures | int | 12,813 (100%) | 128 | `4` |

Sample row:

```
logged_utc='2026-08-08T09:12:52Z', date='2026-08-08', player='Alyssa Thomas', market='pts', side='Over', line='14.5', src='flip_paper', open_odds='1.88', now_odds='1.88', move_pct='0.0', verdict='BET (steady)', confidence='ok 85%', line_moved='', fade_side='', fade_price='', captures='4'
```

### `drift_track.csv`

Rows: **1,025**  Columns: **13**  Date range (`date`): **2026-06-14 .. 2026-08-25**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| date | date(YYYY-MM-DD) | 1,025 (100%) | 65 | `2026-06-14` |
| player | str | 1,025 (100%) | 103 | `Angel Reese` |
| market | str | 1,025 (100%) | 5 | `pra` |
| side | str | 1,025 (100%) | 2 | `Over` |
| line | float | 1,025 (100%) | 32 | `30.5` |
| src | str | 1,025 (100%) | 8 | `hotover` |
| result | bool/enum | 1,025 (100%) | 2 | `WIN` |
| odds | float | 1,025 (100%) | 41 | `1.91` |
| odds_clv | float | 955 (93%) | 148 | `0.044` |
| bucket | str | 1,025 (100%) | 4 | `short` |
| as_bet | float | 1,025 (100%) | 35 | `0.91` |
| fade_ret | float | 157 (15%) | 26 | `0.8` |
| skip_drift | float | 780 (76%) | 36 | `0.91` |

Sample row:

```
date='2026-06-14', player='Angel Reese', market='pra', side='Over', line='30.5', src='hotover', result='WIN', odds='1.91', odds_clv='0.044', bucket='short', as_bet='0.91', fade_ret='', skip_drift='0.91'
```

### `fade_graded.csv`

Rows: **236**  Columns: **12**  Date range (`logged_utc`): **2026-08-03T05:58:29 .. 2026-08-26T00:06:48**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| logged_utc | datetime | 236 (100%) | 153 | `2026-08-03T05:58:29Z` |
| date | date(YYYY-MM-DD) | 236 (100%) | 21 | `2026-08-02` |
| player | str | 236 (100%) | 54 | `Chelsea Gray` |
| market | str | 236 (100%) | 4 | `pts` |
| side | str | 236 (100%) | 2 | `Under` |
| line | float | 236 (100%) | 24 | `12.5` |
| price | float | 236 (100%) | 31 | `1.769` |
| orig_src | str | 236 (100%) | 8 | `flip_paper` |
| orig_move | float | 236 (100%) | 94 | `0.0753` |
| actual | float | 230 (97%) | 38 | `17.0` |
| result | bool/enum | 230 (97%) | 3 | `loss` |
| ret | float | 230 (97%) | 29 | `-1.0` |

Sample row:

```
logged_utc='2026-08-03T05:58:29Z', date='2026-08-02', player='Chelsea Gray', market='pts', side='Under', line='12.5', price='1.769', orig_src='flip_paper', orig_move='0.0753', actual='17.0', result='loss', ret='-1.0'
```

### `fade_paper.csv`

Rows: **237**  Columns: **9**  Date range (`logged_utc`): **2026-08-03T05:58:29 .. 2026-08-26T05:21:17**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| logged_utc | datetime | 237 (100%) | 154 | `2026-08-03T05:58:29Z` |
| date | date(YYYY-MM-DD) | 237 (100%) | 21 | `2026-08-02` |
| player | str | 237 (100%) | 54 | `Chelsea Gray` |
| market | str | 237 (100%) | 4 | `pts` |
| side | str | 237 (100%) | 2 | `Under` |
| line | float | 237 (100%) | 24 | `12.5` |
| price | float | 237 (100%) | 31 | `1.769` |
| orig_src | str | 237 (100%) | 8 | `flip_paper` |
| orig_move | float | 237 (100%) | 95 | `0.0753` |

Sample row:

```
logged_utc='2026-08-03T05:58:29Z', date='2026-08-02', player='Chelsea Gray', market='pts', side='Under', line='12.5', price='1.769', orig_src='flip_paper', orig_move='0.0753'
```

### `fam_bets.csv`

Rows: **1,025**  Columns: **16**  Date range (`date`): **20260614 .. 20260825**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| date | date(YYYYMMDD) | 1,025 (100%) | 65 | `20260614` |
| pl | str | 1,025 (100%) | 98 | `angel reese` |
| mk | str | 1,025 (100%) | 5 | `pra` |
| sd | str | 1,025 (100%) | 2 | `Over` |
| ln | float | 1,025 (100%) | 32 | `30.5` |
| od | float | 1,025 (100%) | 41 | `1.91` |
| oppod | float | 725 (71%) | 48 | `1.98` |
| act | float | 1,025 (100%) | 47 | `33.0` |
| over_won | bool/enum | 1,025 (100%) | 2 | `True` |
| won | bool/enum | 1,025 (100%) | 2 | `True` |
| src | str | 1,025 (100%) | 8 | `hotover` |
| tier | str | 1,025 (100%) | 4 | `SOLID` |
| ev | float | 805 (79%) | 354 | `0.146` |
| pinn | float | 250 (24%) | 32 | `19.5` |
| gt | datetime | 1,025 (100%) | 153 | `2026-06-14T19:00:00+00:00` |
| T | datetime | 1,025 (100%) | 292 | `2026-06-14T13:47:20+00:00` |

Sample row:

```
date='20260614', pl='angel reese', mk='pra', sd='Over', ln='30.5', od='1.91', oppod='', act='33.0', over_won='True', won='True', src='hotover', tier='SOLID', ev='0.146', pinn='', gt='2026-06-14T19:00:00+00:00', T='2026-06-14T13:47:20+00:00'
```

### `gamelines.csv`

Rows: **32,192**  Columns: **8**  Date range (`captured_utc`): **2026-07-11T16:40:22 .. 2026-08-26T06:23:44**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 32,192 (100%) | 867 | `2026-07-11T16:40:22Z` |
| matchup_id | int | 32,192 (100%) | 220 | `1632339837` |
| start | datetime | 32,192 (100%) | 123 | `2026-07-11T20:00` |
| teams | str | 32,192 (100%) | 107 | `Atlanta Dream|Portland Fire` |
| type | str | 32,192 (100%) | 4 | `moneyline` |
| side | str | 4,486 (14%) | 3 | `home` |
| points | float | 30,300 (94%) | 337 | `93.0` |
| prices | str | 32,192 (100%) | 2,624 | `-849,622` |

Sample row:

```
captured_utc='2026-07-11T16:40:22Z', matchup_id='1632339837', start='2026-07-11T20:00', teams='Atlanta Dream|Portland Fire', type='moneyline', side='', points='', prices='-849,622'
```

### `graded_bets.csv`

Rows: **1,025**  Columns: **16**  Date range (`date`): **20260614 .. 20260825**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| date | date(YYYYMMDD) | 1,025 (100%) | 65 | `20260614` |
| player | str | 1,025 (100%) | 103 | `Angel Reese` |
| market | str | 1,025 (100%) | 5 | `pra` |
| side | str | 1,025 (100%) | 2 | `Over` |
| line | float | 1,025 (100%) | 32 | `30.5` |
| odds | float | 1,025 (100%) | 41 | `1.91` |
| tier | str | 1,025 (100%) | 4 | `SOLID` |
| actual | float | 1,025 (100%) | 47 | `33.0` |
| result | bool/enum | 1,025 (100%) | 2 | `WIN` |
| pnl | float | 1,025 (100%) | 35 | `0.91` |
| odds_clv | float | 955 (93%) | 148 | `0.044` |
| line_clv | float | 975 (95%) | 13 | `0.0` |
| sharp_clv | float | 334 (33%) | 13 | `0.0` |
| sharp_odds_clv | float | 262 (26%) | 137 | `-0.034` |
| src | str | 1,025 (100%) | 8 | `hotover` |
| opened | date(YYYY-MM-DD) | 1,025 (100%) | 65 | `2026-06-14` |

Sample row:

```
date='20260614', player='Angel Reese', market='pra', side='Over', line='30.5', odds='1.91', tier='SOLID', actual='33.0', result='WIN', pnl='0.91', odds_clv='0.044', line_clv='0.0', sharp_clv='', sharp_odds_clv='', src='hotover', opened='2026-06-14'
```

### `graded_bets.pre-dedup.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **13**  Columns: **14**  Date range (`date`): **20260614 .. 20260615**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| date | date(YYYYMMDD) | 13 (100%) | 2 | `20260614` |
| player | str | 13 (100%) | 9 | `Angel Reese` |
| market | str | 13 (100%) | 4 | `pra` |
| side | str | 13 (100%) | 2 | `Over` |
| line | float | 13 (100%) | 12 | `30.5` |
| odds | float | 13 (100%) | 9 | `1.91` |
| tier | str | 13 (100%) | 2 | `SOLID` |
| actual | float | 13 (100%) | 11 | `33.0` |
| result | bool/enum | 13 (100%) | 2 | `WIN` |
| pnl | float | 13 (100%) | 4 | `0.91` |
| odds_clv | float | 10 (77%) | 6 | `0.044` |
| line_clv | float | 10 (77%) | 2 | `0.0` |
| sharp_clv | empty | 0 (0%) | 1 | `` |
| src | str | 13 (100%) | 3 | `hotover` |

Sample row:

```
date='20260614', player='Angel Reese', market='pra', side='Over', line='30.5', odds='1.91', tier='SOLID', actual='33.0', result='WIN', pnl='0.91', odds_clv='0.044', line_clv='0.0', sharp_clv='', src='hotover'
```

### `graded_bets.pre-src.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **4**  Columns: **13**  Date range (`date`): **20260614 .. 20260614**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| date | date(YYYYMMDD) | 4 (100%) | 1 | `20260614` |
| player | str | 4 (100%) | 4 | `Angel Reese` |
| market | str | 4 (100%) | 2 | `pra` |
| side | str | 4 (100%) | 2 | `Over` |
| line | float | 4 (100%) | 4 | `30.5` |
| odds | float | 4 (100%) | 4 | `1.91` |
| tier | str | 4 (100%) | 2 | `SOLID` |
| actual | float | 4 (100%) | 4 | `33.0` |
| result | bool/enum | 4 (100%) | 1 | `WIN` |
| pnl | float | 4 (100%) | 3 | `0.91` |
| odds_clv | float | 4 (100%) | 4 | `0.044` |
| line_clv | float | 4 (100%) | 1 | `0.0` |
| sharp_clv | empty | 0 (0%) | 1 | `` |

Sample row:

```
date='20260614', player='Angel Reese', market='pra', side='Over', line='30.5', odds='1.91', tier='SOLID', actual='33.0', result='WIN', pnl='0.91', odds_clv='0.044', line_clv='0.0', sharp_clv=''
```

### `injuries_log.csv`

Rows: **958**  Columns: **5**  Date range (`captured_utc`): **2026-06-24T20:30:22 .. 2026-08-26T02:11:43**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 958 (100%) | 334 | `2026-06-24T20:30:22Z` |
| player | str | 958 (100%) | 153 | `Aaliyah Nye` |
| team | str | 958 (100%) | 15 | `Atlanta Dream` |
| status | str | 958 (100%) | 3 | `Out` |
| detail | str | 958 (100%) | 749 | `Nye (Knee) is listed as out for Wednesda...` |

Sample row:

```
captured_utc='2026-06-24T20:30:22Z', player='Aaliyah Nye', team='Atlanta Dream', status='Out', detail="Nye (Knee) is listed as out for Wednesday's game against Golden State."
```

### `line_snapshots.csv`

Rows: **174**  Columns: **11**  Date range (`captured_utc`): **2026-06-13T20:23:17 .. 2026-06-15T23:56:37**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 174 (100%) | 6 | `2026-06-13T20:23:17+00:00` |
| game_id | str | 174 (100%) | 9 | `5bd596e423be0c73cc633d354e6dd1f8` |
| tip | datetime | 174 (100%) | 7 | `2026-06-13T22:00:00Z` |
| away | str | 174 (100%) | 8 | `Indiana Fever` |
| home | str | 174 (100%) | 9 | `Connecticut Sun` |
| market | str | 174 (100%) | 1 | `player_points` |
| player | str | 174 (100%) | 57 | `Aaliyah Edwards` |
| side | str | 174 (100%) | 2 | `Over` |
| line | float | 174 (100%) | 15 | `10.5` |
| price | float | 174 (100%) | 43 | `2.07` |
| book | str | 174 (100%) | 1 | `Pinnacle` |

Sample row:

```
captured_utc='2026-06-13T20:23:17+00:00', game_id='5bd596e423be0c73cc633d354e6dd1f8', tip='2026-06-13T22:00:00Z', away='Indiana Fever', home='Connecticut Sun', market='player_points', player='Aaliyah Edwards', side='Over', line='10.5', price='2.07', book='Pinnacle'
```

### `lineups_log.csv`

Rows: **2,897**  Columns: **5**  Date range (`captured_utc`): **2026-06-24T23:34:39 .. 2026-08-26T02:11:43**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 2,897 (100%) | 96 | `2026-06-24T23:34:39Z` |
| game_id | int | 2,897 (100%) | 120 | `401857018` |
| player | str | 2,897 (100%) | 217 | `Natasha Howard` |
| team | str | 2,897 (100%) | 15 | `MIN` |
| role | str | 2,897 (100%) | 2 | `starter` |

Sample row:

```
captured_utc='2026-06-24T23:34:39Z', game_id='401857018', player='Natasha Howard', team='MIN', role='starter'
```

### `live_lines.csv`

Rows: **56,843**  Columns: **7**  Date range (`ts`): **2026-07-16T00:09:03 .. 2026-08-11T23:48:45**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| ts | datetime | 56,843 (100%) | 766 | `2026-07-16T00:09:03Z` |
| teams | str | 56,843 (100%) | 41 | `Dallas Wings|New York Liberty` |
| type | str | 56,843 (100%) | 4 | `moneyline` |
| side | str | 10,658 (19%) | 3 | `home` |
| points | float | 53,818 (95%) | 294 | `88.5` |
| prices | str | 56,843 (100%) | 1,000 | `-135,111` |
| alt | int | 56,843 (100%) | 2 | `0` |

Sample row:

```
ts='2026-07-16T00:09:03Z', teams='Dallas Wings|New York Liberty', type='moneyline', side='', points='', prices='-135,111', alt='0'
```

### `live_snapshots.csv`

Rows: **1,269**  Columns: **15**  Date range (`ts`): **2026-07-16T00:09:03 .. 2026-08-11T23:48:45**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| ts | datetime | 1,269 (100%) | 779 | `2026-07-16T00:09:03Z` |
| game_id | int | 1,269 (100%) | 27 | `401857070` |
| period | int | 1,269 (100%) | 4 | `1` |
| clock | str | 1,269 (100%) | 468 | `9:21` |
| away | str | 1,269 (100%) | 13 | `GS` |
| home | str | 1,269 (100%) | 11 | `IND` |
| away_score | int | 1,269 (100%) | 97 | `0` |
| home_score | int | 1,269 (100%) | 95 | `0` |
| h_fouls | int | 1,269 (100%) | 19 | `0` |
| a_fouls | int | 1,269 (100%) | 27 | `0` |
| h_to | int | 1,269 (100%) | 23 | `0` |
| a_to | int | 1,269 (100%) | 19 | `1` |
| h_reb | int | 1,269 (100%) | 46 | `1` |
| a_reb | int | 1,269 (100%) | 37 | `0` |
| last_play | str | 1,268 (100%) | 605 | `Caitlin Clark offensive rebound` |

Sample row:

```
ts='2026-07-16T00:09:03Z', game_id='401857070', period='1', clock='9:21', away='GS', home='IND', away_score='0', home_score='0', h_fouls='0', a_fouls='0', h_to='0', a_to='1', h_reb='1', a_reb='0', last_play='Caitlin Clark offensive rebound'
```

### `model_forward.csv`

Rows: **27**  Columns: **13**  Date range (`slate`): **20260811 .. 20260825**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYYMMDD) | 27 (100%) | 12 | `20260811` |
| player | str | 27 (100%) | 21 | `Kelsey Mitchell` |
| market | str | 27 (100%) | 3 | `pts` |
| side | str | 27 (100%) | 1 | `Over` |
| line | float | 27 (100%) | 18 | `24.5` |
| odds | float | 27 (100%) | 13 | `1.86` |
| src | str | 27 (100%) | 4 | `flip` |
| prev_line | float | 27 (100%) | 16 | `25.5` |
| tip | datetime | 27 (100%) | 16 | `2026-08-11T23:30Z` |
| result | str | 27 (100%) | 3 | `WIN` |
| actual | float | 26 (96%) | 21 | `28` |
| pnl | float | 26 (96%) | 12 | `0.86` |
| note | str | 7 (26%) | 7 | `book cut 25.5->24.5` |

Sample row:

```
slate='20260811', player='Kelsey Mitchell', market='pts', side='Over', line='24.5', odds='1.86', src='flip', prev_line='25.5', tip='2026-08-11T23:30Z', result='WIN', actual='28', pnl='0.86', note='book cut 25.5->24.5'
```

### `model_forward.pre-slatefix.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **24**  Columns: **13**  Date range (`slate`): **20260811 .. 20260825**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYYMMDD) | 24 (100%) | 10 | `20260811` |
| player | str | 24 (100%) | 19 | `Kelsey Mitchell` |
| market | str | 24 (100%) | 3 | `pts` |
| side | str | 24 (100%) | 1 | `Over` |
| line | float | 24 (100%) | 17 | `24.5` |
| odds | float | 24 (100%) | 13 | `1.86` |
| src | str | 24 (100%) | 4 | `flip` |
| prev_line | float | 24 (100%) | 16 | `25.5` |
| tip | datetime | 24 (100%) | 14 | `2026-08-11T23:30Z` |
| result | bool/enum | 23 (96%) | 3 | `WIN` |
| actual | float | 23 (96%) | 19 | `28` |
| pnl | float | 23 (96%) | 12 | `0.86` |
| note | str | 7 (29%) | 7 | `book cut 25.5->24.5` |

Sample row:

```
slate='20260811', player='Kelsey Mitchell', market='pts', side='Over', line='24.5', odds='1.86', src='flip', prev_line='25.5', tip='2026-08-11T23:30Z', result='WIN', actual='28', pnl='0.86', note='book cut 25.5->24.5'
```

### `model_forward.pre-void.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **27**  Columns: **13**  Date range (`slate`): **20260811 .. 20260825**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYYMMDD) | 27 (100%) | 12 | `20260811` |
| player | str | 27 (100%) | 21 | `Kelsey Mitchell` |
| market | str | 27 (100%) | 3 | `pts` |
| side | str | 27 (100%) | 1 | `Over` |
| line | float | 27 (100%) | 18 | `24.5` |
| odds | float | 27 (100%) | 13 | `1.86` |
| src | str | 27 (100%) | 4 | `flip` |
| prev_line | float | 27 (100%) | 16 | `25.5` |
| tip | datetime | 27 (100%) | 16 | `2026-08-11T23:30Z` |
| result | bool/enum | 26 (96%) | 3 | `WIN` |
| actual | float | 26 (96%) | 21 | `28` |
| pnl | float | 26 (96%) | 12 | `0.86` |
| note | str | 7 (26%) | 7 | `book cut 25.5->24.5` |

Sample row:

```
slate='20260811', player='Kelsey Mitchell', market='pts', side='Over', line='24.5', odds='1.86', src='flip', prev_line='25.5', tip='2026-08-11T23:30Z', result='WIN', actual='28', pnl='0.86', note='book cut 25.5->24.5'
```

### `my_bets.csv`

Rows: **5**  Columns: **14**  Date range (`date`): **20260617 .. 20260620**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| date | date(YYYYMMDD) | 5 (100%) | 3 | `20260617` |
| player | str | 5 (100%) | 5 | `Kamilla Cardoso` |
| market | str | 5 (100%) | 3 | `pr` |
| side | str | 5 (100%) | 1 | `Under` |
| line | float | 5 (100%) | 5 | `20.5` |
| odds | float | 5 (100%) | 5 | `1.893` |
| stake_u | int | 5 (100%) | 1 | `1` |
| actual | int | 5 (100%) | 5 | `14` |
| result | bool/enum | 5 (100%) | 2 | `WIN` |
| pnl | float | 5 (100%) | 5 | `0.893` |
| entry_odds | float | 5 (100%) | 5 | `1.893` |
| close_odds | float | 5 (100%) | 5 | `1.893` |
| odds_clv | float | 5 (100%) | 4 | `0.0` |
| note | str | 5 (100%) | 5 | `manual; 1xbet PR line dead-flat 1.893 fo...` |

Sample row:

```
date='20260617', player='Kamilla Cardoso', market='pr', side='Under', line='20.5', odds='1.893', stake_u='1', actual='14', result='WIN', pnl='0.893', entry_odds='1.893', close_odds='1.893', odds_clv='0.0', note='manual; 1xbet PR line dead-flat 1.893 for 25h (13 snapshots) -> CLV neutral'
```

### `parlay_forward.csv`

Rows: **39**  Columns: **14**  Date range (`slate`): **2026-07-02 .. 2026-08-25**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYY-MM-DD) | 39 (100%) | 25 | `2026-08-15` |
| leg1 | str | 39 (100%) | 22 | `Dearica Hamby` |
| mk1 | str | 39 (100%) | 3 | `pr` |
| line1 | float | 39 (100%) | 16 | `20.5` |
| odds1 | float | 39 (100%) | 15 | `1.73` |
| leg2 | str | 39 (100%) | 27 | `NaLyssa Smith` |
| mk2 | str | 39 (100%) | 3 | `pr` |
| line2 | float | 39 (100%) | 18 | `17.5` |
| odds2 | float | 39 (100%) | 12 | `1.87` |
| combined_odds | float | 39 (100%) | 33 | `3.2351` |
| same_game | int | 39 (100%) | 2 | `0` |
| logged_utc | datetime | 39 (100%) | 26 | `2026-08-15T23:04:30Z` |
| result | bool/enum | 31 (79%) | 3 | `loss` |
| pnl | float | 31 (79%) | 14 | `-1.0` |

Sample row:

```
slate='2026-08-15', leg1='Dearica Hamby', mk1='pr', line1='20.5', odds1='1.73', leg2='NaLyssa Smith', mk2='pr', line2='17.5', odds2='1.87', combined_odds='3.2351', same_game='0', logged_utc='2026-08-15T23:04:30Z', result='loss', pnl='-1.0'
```

### `picks_log.csv`

Rows: **2,503**  Columns: **12**  Date range (`pick_date`): **2026-06-12 .. 2026-08-25**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| pick_date | date(YYYY-MM-DD) | 2,503 (100%) | 69 | `2026-06-12` |
| game_id | int | 2,503 (100%) | 186 | `401856984` |
| player | str | 2,503 (100%) | 103 | `Kiki Iriafen` |
| team | str | 2,503 (100%) | 15 | `Washington Mystics` |
| opp | str | 2,503 (100%) | 15 | `Toronto Tempo` |
| market | str | 2,503 (100%) | 9 | `pr_under` |
| anchor | float | 2,503 (100%) | 39 | `23.5` |
| signals | str | 2,503 (100%) | 18 | `disrupted+cold` |
| fair_p | float | 2,503 (100%) | 17 | `0.59` |
| fair_odds | float | 2,503 (100%) | 14 | `1.69` |
| proj | float | 2,503 (100%) | 276 | `21.4` |
| sd | float | 2,489 (99%) | 617 | `6.66` |

Sample row:

```
pick_date='2026-06-12', game_id='401856984', player='Kiki Iriafen', team='Washington Mystics', opp='Toronto Tempo', market='pr_under', anchor='23.5', signals='disrupted+cold', fair_p='0.59', fair_odds='1.69', proj='21.4', sd=''
```

### `pinged_bets.backup.csv`

_Backup/prior-state file - not independent data._

Rows: **31**  Columns: **14**  Date range (`sent_utc`): **2026-08-08T09:46:16 .. 2026-08-08T22:44:32**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| sent_utc | datetime | 31 (100%) | 4 | `2026-08-08T09:46:16Z` |
| stage | str | 31 (100%) | 3 | `main` |
| date | date(YYYY-MM-DD) | 31 (100%) | 2 | `2026-08-08` |
| player | str | 31 (100%) | 16 | `Alyssa Thomas` |
| market | str | 31 (100%) | 5 | `pts` |
| side | str | 31 (100%) | 1 | `Over` |
| line | float | 31 (100%) | 13 | `14.5` |
| odds | float | 31 (100%) | 10 | `1.81` |
| stake | str | 31 (100%) | 2 | `1u` |
| src | str | 31 (100%) | 4 | `flip_paper` |
| move_pct | float | 31 (100%) | 6 | `-3.7` |
| captures | int | 31 (100%) | 7 | `5` |
| confidence | str | 31 (100%) | 3 | `BET NOW 93%` |
| pulled_utc | datetime | 1 (3%) | 2 | `2026-08-08T15:24:30Z` |

Sample row:

```
sent_utc='2026-08-08T09:46:16Z', stage='main', date='2026-08-08', player='Alyssa Thomas', market='pts', side='Over', line='14.5', odds='1.81', stake='1u', src='flip_paper', move_pct='-3.7', captures='5', confidence='BET NOW 93%', pulled_utc=''
```

### `pinged_bets.csv`

Rows: **101**  Columns: **15**  Date range (`sent_utc`): **2026-08-08T09:46:16 .. 2026-08-13T21:00:14**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| sent_utc | datetime | 101 (100%) | 15 | `2026-08-08T09:46:16Z` |
| stage | str | 101 (100%) | 4 | `main` |
| date | date(YYYY-MM-DD) | 101 (100%) | 6 | `2026-08-08` |
| player | str | 101 (100%) | 36 | `Alyssa Thomas` |
| market | str | 101 (100%) | 5 | `pts` |
| side | str | 101 (100%) | 1 | `Over` |
| line | float | 101 (100%) | 23 | `14.5` |
| odds | float | 101 (100%) | 22 | `1.81` |
| stake | str | 101 (100%) | 2 | `1u` |
| src | str | 101 (100%) | 4 | `flip_paper` |
| move_pct | float | 101 (100%) | 17 | `-3.7` |
| captures | int | 101 (100%) | 13 | `5` |
| span_h | float | 81 (80%) | 24 | `3.6` |
| confidence | str | 101 (100%) | 3 | `BET NOW 93%` |
| pulled_utc | str | 8 (8%) | 3 | `2026-08-08T15:24:30Z` |

Sample row:

```
sent_utc='2026-08-08T09:46:16Z', stage='main', date='2026-08-08', player='Alyssa Thomas', market='pts', side='Over', line='14.5', odds='1.81', stake='1u', src='flip_paper', move_pct='-3.7', captures='5', span_h='', confidence='BET NOW 93%', pulled_utc=''
```

### `pinn_board.csv`

Rows: **22,824**  Columns: **7**  Date range (`captured_utc`): **2026-08-21T13:11:37 .. 2026-08-26T06:23:37**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 22,824 (100%) | 424 | `2026-08-21T13:11:37+00:00` |
| date | date(YYYY-MM-DD) | 22,824 (100%) | 5 | `2026-08-21` |
| player | str | 22,824 (100%) | 71 | `megan dileo` |
| market | str | 22,824 (100%) | 7 | `reb` |
| pinn_line | float | 22,824 (100%) | 56 | `4.5` |
| fair_over | float | 14,727 (65%) | 183 | `1.9414` |
| fair_under | float | 14,727 (65%) | 183 | `2.0623` |

Sample row:

```
captured_utc='2026-08-21T13:11:37+00:00', date='2026-08-21', player='megan dileo', market='reb', pinn_line='4.5', fair_over='1.9414', fair_under='2.0623'
```

### `pinn_snapshots.csv`

Rows: **6,814**  Columns: **7**  Date range (`captured_utc`): **2026-06-20T15:19:46 .. 2026-08-26T06:23:37**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 6,814 (100%) | 1,209 | `2026-06-20T15:19:46+00:00` |
| date | date(YYYY-MM-DD) | 6,814 (100%) | 58 | `2026-06-20` |
| player | str | 6,814 (100%) | 70 | `Jordin Canada` |
| market | str | 6,814 (100%) | 3 | `pts` |
| side | str | 6,814 (100%) | 2 | `Under` |
| pinn_line | float | 6,814 (100%) | 22 | `12.5` |
| pinn_fair | float | 6,814 (100%) | 250 | `1.8861` |

Sample row:

```
captured_utc='2026-06-20T15:19:46+00:00', date='2026-06-20', player='Jordin Canada', market='pts', side='Under', pinn_line='12.5', pinn_fair='1.8861'
```

### `shadow_forward.csv`

Rows: **1,641**  Columns: **17**  Date range (`slate`): **2026-06-24 .. 2026-08-25**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYY-MM-DD) | 1,641 (100%) | 54 | `2026-08-15` |
| config | str | 1,641 (100%) | 16 | `MODEL_S` |
| player | str | 1,641 (100%) | 77 | `Dearica Hamby` |
| market | str | 1,641 (100%) | 7 | `pr` |
| side | str | 1,524 (93%) | 3 | `Over` |
| line | float | 1,641 (100%) | 34 | `20.5` |
| odds | float | 1,641 (100%) | 45 | `1.73` |
| src | str | 1,641 (100%) | 6 | `flip` |
| prev_line | float | 1,567 (95%) | 32 | `20.5` |
| mv | float | 1,567 (95%) | 14 | `0.0` |
| drift | float | 1,641 (100%) | 162 | `0.0000` |
| gap | float | 447 (27%) | 10 | `-2.0` |
| tip | datetime | 1,604 (98%) | 123 | `2026-08-18T23:00Z` |
| logged_utc | datetime | 1,641 (100%) | 60 | `2026-08-15T23:04:30Z` |
| backfill | int | 1,346 (82%) | 2 | `1` |
| result | str | 1,641 (100%) | 3 | `loss` |
| actual | float | 1,583 (96%) | 47 | `18.0` |

Sample row:

```
slate='2026-08-15', config='MODEL_S', player='Dearica Hamby', market='pr', side='', line='20.5', odds='1.73', src='flip', prev_line='20.5', mv='0.0', drift='0.0000', gap='', tip='', logged_utc='2026-08-15T23:04:30Z', backfill='', result='loss', actual='18.0'
```

### `shadow_forward.pre-backfill.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **191**  Columns: **16**  Date range (`slate`): **2026-08-15 .. 2026-08-22**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYY-MM-DD) | 191 (100%) | 7 | `2026-08-15` |
| config | str | 191 (100%) | 15 | `MODEL_S` |
| player | str | 191 (100%) | 38 | `Dearica Hamby` |
| market | str | 191 (100%) | 5 | `pr` |
| side | str | 67 (35%) | 3 | `Over` |
| line | float | 191 (100%) | 22 | `20.5` |
| odds | float | 191 (100%) | 20 | `1.73` |
| src | str | 191 (100%) | 6 | `flip` |
| prev_line | float | 186 (97%) | 23 | `20.5` |
| mv | float | 186 (97%) | 11 | `0.0` |
| drift | float | 191 (100%) | 42 | `0.0000` |
| gap | float | 28 (15%) | 6 | `-2.0` |
| tip | datetime | 154 (81%) | 13 | `2026-08-18T02:00Z` |
| logged_utc | datetime | 191 (100%) | 12 | `2026-08-15T23:04:30Z` |
| result | bool/enum | 106 (55%) | 3 | `loss` |
| actual | float | 106 (55%) | 25 | `18.0` |

Sample row:

```
slate='2026-08-15', config='MODEL_S', player='Dearica Hamby', market='pr', side='', line='20.5', odds='1.73', src='flip', prev_line='20.5', mv='0.0', drift='0.0000', gap='', tip='', logged_utc='2026-08-15T23:04:30Z', result='loss', actual='18.0'
```

### `shadow_forward.pre-gap.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **124**  Columns: **14**  Date range (`slate`): **2026-08-15 .. 2026-08-21**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYY-MM-DD) | 124 (100%) | 6 | `2026-08-15` |
| config | str | 124 (100%) | 12 | `MODEL_S` |
| player | str | 124 (100%) | 27 | `Dearica Hamby` |
| market | str | 124 (100%) | 4 | `pr` |
| line | float | 124 (100%) | 19 | `20.5` |
| odds | float | 124 (100%) | 15 | `1.73` |
| src | str | 124 (100%) | 5 | `flip` |
| prev_line | float | 120 (97%) | 20 | `20.5` |
| mv | float | 120 (97%) | 9 | `0.0` |
| drift | float | 124 (100%) | 26 | `0.0000` |
| tip | datetime | 87 (70%) | 8 | `2026-08-18T02:00Z` |
| logged_utc | datetime | 124 (100%) | 9 | `2026-08-15T23:04:30Z` |
| result | bool/enum | 41 (33%) | 3 | `loss` |
| actual | float | 41 (33%) | 14 | `18.0` |

Sample row:

```
slate='2026-08-15', config='MODEL_S', player='Dearica Hamby', market='pr', line='20.5', odds='1.73', src='flip', prev_line='20.5', mv='0.0', drift='0.0000', tip='', logged_utc='2026-08-15T23:04:30Z', result='loss', actual='18.0'
```

### `shadow_forward.pre-rank.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **44**  Columns: **14**  Date range (`slate`): **2026-08-15 .. 2026-08-18**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYY-MM-DD) | 44 (100%) | 3 | `2026-08-15` |
| config | str | 44 (100%) | 8 | `MODEL_S` |
| player | str | 44 (100%) | 12 | `Dearica Hamby` |
| market | str | 44 (100%) | 4 | `pr` |
| line | float | 44 (100%) | 8 | `20.5` |
| odds | float | 44 (100%) | 7 | `1.73` |
| src | str | 44 (100%) | 4 | `flip` |
| prev_line | float | 44 (100%) | 9 | `20.5` |
| mv | float | 44 (100%) | 6 | `0.0` |
| drift | float | 44 (100%) | 10 | `0.0000` |
| tip | datetime | 7 (16%) | 2 | `2026-08-18T02:00Z` |
| logged_utc | datetime | 44 (100%) | 4 | `2026-08-15T23:04:30Z` |
| result | bool/enum | 29 (66%) | 3 | `loss` |
| actual | float | 29 (66%) | 11 | `18.0` |

Sample row:

```
slate='2026-08-15', config='MODEL_S', player='Dearica Hamby', market='pr', line='20.5', odds='1.73', src='flip', prev_line='20.5', mv='0.0', drift='0.0000', tip='', logged_utc='2026-08-15T23:04:30Z', result='loss', actual='18.0'
```

### `shadow_forward.pre-slatefix.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **1,594**  Columns: **17**  Date range (`slate`): **2026-06-24 .. 2026-08-25**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYY-MM-DD) | 1,594 (100%) | 45 | `2026-08-15` |
| config | str | 1,594 (100%) | 16 | `MODEL_S` |
| player | str | 1,594 (100%) | 77 | `Dearica Hamby` |
| market | str | 1,594 (100%) | 7 | `pr` |
| side | str | 1,477 (93%) | 3 | `Over` |
| line | float | 1,594 (100%) | 34 | `20.5` |
| odds | float | 1,594 (100%) | 45 | `1.73` |
| src | str | 1,594 (100%) | 6 | `flip` |
| prev_line | float | 1,520 (95%) | 32 | `20.5` |
| mv | float | 1,520 (95%) | 14 | `0.0` |
| drift | float | 1,594 (100%) | 160 | `0.0000` |
| gap | float | 428 (27%) | 10 | `-2.0` |
| tip | datetime | 1,557 (98%) | 120 | `2026-08-18T23:00Z` |
| logged_utc | datetime | 1,594 (100%) | 57 | `2026-08-15T23:04:30Z` |
| backfill | int | 1,346 (84%) | 2 | `1` |
| result | bool/enum | 1,251 (78%) | 3 | `loss` |
| actual | float | 1,251 (78%) | 45 | `18.0` |

Sample row:

```
slate='2026-08-15', config='MODEL_S', player='Dearica Hamby', market='pr', side='', line='20.5', odds='1.73', src='flip', prev_line='20.5', mv='0.0', drift='0.0000', gap='', tip='', logged_utc='2026-08-15T23:04:30Z', backfill='', result='loss', actual='18.0'
```

### `shadow_forward.pre-void.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **1,641**  Columns: **17**  Date range (`slate`): **2026-06-24 .. 2026-08-25**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| slate | date(YYYY-MM-DD) | 1,641 (100%) | 54 | `2026-08-15` |
| config | str | 1,641 (100%) | 16 | `MODEL_S` |
| player | str | 1,641 (100%) | 77 | `Dearica Hamby` |
| market | str | 1,641 (100%) | 7 | `pr` |
| side | str | 1,524 (93%) | 3 | `Over` |
| line | float | 1,641 (100%) | 34 | `20.5` |
| odds | float | 1,641 (100%) | 45 | `1.73` |
| src | str | 1,641 (100%) | 6 | `flip` |
| prev_line | float | 1,567 (95%) | 32 | `20.5` |
| mv | float | 1,567 (95%) | 14 | `0.0` |
| drift | float | 1,641 (100%) | 162 | `0.0000` |
| gap | float | 447 (27%) | 10 | `-2.0` |
| tip | datetime | 1,604 (98%) | 123 | `2026-08-18T23:00Z` |
| logged_utc | datetime | 1,641 (100%) | 60 | `2026-08-15T23:04:30Z` |
| backfill | int | 1,346 (82%) | 2 | `1` |
| result | bool/enum | 1,583 (96%) | 3 | `loss` |
| actual | float | 1,583 (96%) | 47 | `18.0` |

Sample row:

```
slate='2026-08-15', config='MODEL_S', player='Dearica Hamby', market='pr', side='', line='20.5', odds='1.73', src='flip', prev_line='20.5', mv='0.0', drift='0.0000', gap='', tip='', logged_utc='2026-08-15T23:04:30Z', backfill='', result='loss', actual='18.0'
```

### `xbet_board.csv`

Rows: **81,755**  Columns: **6**  Date range (`captured_utc`): **2026-06-24T10:26:26 .. 2026-08-26T06:20:22**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 81,755 (100%) | 1,298 | `2026-06-24T10:26:26+00:00` |
| player | str | 81,755 (100%) | 129 | `dewanna bonner` |
| market | str | 81,755 (100%) | 7 | `pts` |
| side | str | 81,755 (100%) | 2 | `Over` |
| line | float | 81,755 (100%) | 41 | `10.5` |
| odds | float | 81,755 (100%) | 176 | `1.9` |

Sample row:

```
captured_utc='2026-06-24T10:26:26+00:00', player='dewanna bonner', market='pts', side='Over', line='10.5', odds='1.9'
```

### `xbet_gamelines.csv`

Rows: **12,482**  Columns: **8**  Date range (`captured_utc`): **2026-08-16T05:00:19 .. 2026-08-26T06:23:39**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 12,482 (100%) | 660 | `2026-08-16T05:00:19Z` |
| game_id | int | 12,482 (100%) | 76 | `744652201` |
| start | datetime | 12,482 (100%) | 25 | `2026-08-16T21:00Z` |
| teams | str | 12,482 (100%) | 31 | `Atlanta Dream|Indiana Fever` |
| type | str | 12,482 (100%) | 3 | `moneyline` |
| points | float | 8,982 (72%) | 133 | `187.5` |
| p1 | float | 12,482 (100%) | 335 | `1.803` |
| p2 | float | 12,482 (100%) | 334 | `2.053` |

Sample row:

```
captured_utc='2026-08-16T05:00:19Z', game_id='744652201', start='2026-08-16T21:00Z', teams='Atlanta Dream|Indiana Fever', type='moneyline', points='', p1='1.803', p2='2.053'
```

### `xbet_snapshots.csv`

Rows: **47,646**  Columns: **6**  Date range (`captured_utc`): **2026-06-13T20:07:12 .. 2026-08-26T06:23:37**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| captured_utc | datetime | 47,646 (100%) | 1,637 | `2026-06-13T20:07:12+00:00` |
| player | str | 47,646 (100%) | 92 | `Saniya Rivers` |
| market | str | 47,646 (100%) | 7 | `pra` |
| side | str | 47,646 (100%) | 2 | `Over` |
| line | float | 47,646 (100%) | 36 | `15.5` |
| odds | float | 47,646 (100%) | 79 | `2.0` |

Sample row:

```
captured_utc='2026-06-13T20:07:12+00:00', player='Saniya Rivers', market='pra', side='Over', line='15.5', odds='2.0'
```

### `data/box_2026.csv`

Rows: **5,678**  Columns: **11**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 5,678 (100%) | 287 | `401856890` |
| team | str | 5,678 (100%) | 15 | `CON` |
| player | str | 5,678 (100%) | 231 | `Diamond Miller` |
| aid | int | 5,678 (100%) | 229 | `4433635` |
| min | float | 5,678 (100%) | 49 | `25.0` |
| pts | float | 5,678 (100%) | 43 | `16.0` |
| reb | float | 5,678 (100%) | 21 | `3.0` |
| ast | float | 5,678 (100%) | 16 | `1.0` |
| fga | float | 5,678 (100%) | 30 | `16.0` |
| fta | float | 5,678 (100%) | 20 | `5.0` |
| to | float | 5,678 (100%) | 10 | `2.0` |

Sample row:

```
game_id='401856890', team='CON', player='Diamond Miller', aid='4433635', min='25.0', pts='16.0', reb='3.0', ast='1.0', fga='16.0', fta='5.0', to='2.0'
```

### `data/box_2026.pre-allstar-purge.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **5,593**  Columns: **11**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 5,593 (100%) | 283 | `401856890` |
| team | str | 5,593 (100%) | 17 | `CON` |
| player | str | 5,593 (100%) | 231 | `Diamond Miller` |
| aid | int | 5,593 (100%) | 229 | `4433635` |
| min | float | 5,593 (100%) | 49 | `25.0` |
| pts | float | 5,593 (100%) | 43 | `16.0` |
| reb | float | 5,593 (100%) | 20 | `3.0` |
| ast | float | 5,593 (100%) | 16 | `1.0` |
| fga | float | 5,593 (100%) | 30 | `16.0` |
| fta | float | 5,593 (100%) | 20 | `5.0` |
| to | float | 5,593 (100%) | 10 | `2.0` |

Sample row:

```
game_id='401856890', team='CON', player='Diamond Miller', aid='4433635', min='25.0', pts='16.0', reb='3.0', ast='1.0', fga='16.0', fta='5.0', to='2.0'
```

### `data/games_2026.csv`

Rows: **290**  Columns: **7**  Date range (`date`): **20260508 .. 20260826**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 290 (100%) | 290 | `401856890` |
| date | date(YYYYMMDD) | 290 (100%) | 100 | `20260508` |
| home | str | 290 (100%) | 15 | `NY` |
| away | str | 290 (100%) | 15 | `CON` |
| tip | datetime | 290 (100%) | 243 | `2026-05-08T23:30Z` |
| home_score | float | 287 (99%) | 58 | `106.0` |
| away_score | float | 287 (99%) | 57 | `75.0` |

Sample row:

```
game_id='401856890', date='20260508', home='NY', away='CON', tip='2026-05-08T23:30Z', home_score='106.0', away_score='75.0'
```

### `data/games_2026.pre-allstar-purge.bak.csv`

_Backup/prior-state file - not independent data._

Rows: **286**  Columns: **7**  Date range (`date`): **20260508 .. 20260824**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 286 (100%) | 286 | `401856890` |
| date | date(YYYYMMDD) | 286 (100%) | 99 | `20260508` |
| home | str | 286 (100%) | 16 | `NY` |
| away | str | 286 (100%) | 16 | `CON` |
| tip | datetime | 286 (100%) | 239 | `2026-05-08T23:30Z` |
| home_score | float | 283 (99%) | 59 | `106.0` |
| away_score | float | 283 (99%) | 58 | `75.0` |

Sample row:

```
game_id='401856890', date='20260508', home='NY', away='CON', tip='2026-05-08T23:30Z', home_score='106.0', away_score='75.0'
```

### `data/halves_2026.csv`

Rows: **2,156**  Columns: **6**  Date range (`date`): **20260508 .. 20260622**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 2,156 (100%) | 126 | `401856890` |
| date | date(YYYYMMDD) | 2,156 (100%) | 43 | `20260508` |
| player | str | 2,156 (100%) | 200 | `breanna stewart` |
| h1_pts | int | 2,156 (100%) | 24 | `21` |
| h2_pts | int | 2,156 (100%) | 28 | `10` |
| pts | int | 2,156 (100%) | 40 | `31` |

Sample row:

```
game_id='401856890', date='20260508', player='breanna stewart', h1_pts='21', h2_pts='10', pts='31'
```

### `elo_model/be_odds.csv`

Rows: **1,861**  Columns: **15**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| season | int | 1,861 (100%) | 8 | `2019` |
| mid | str | 1,861 (100%) | 1,861 | `x8EBbIuf` |
| slug | str | 1,861 (100%) | 206 | `washington-mystics-connecticut-sun` |
| hscore | int | 1,861 (100%) | 72 | `89` |
| ascore | int | 1,861 (100%) | 71 | `78` |
| ml_h | float | 1,844 (99%) | 407 | `1.31` |
| ml_a | float | 1,844 (99%) | 554 | `3.43` |
| spread | float | 1,845 (99%) | 63 | `-6.5` |
| sp_h | float | 1,845 (99%) | 76 | `1.9` |
| sp_a | float | 1,845 (99%) | 67 | `1.92` |
| total | float | 1,845 (99%) | 52 | `174.5` |
| ou_o | float | 1,845 (99%) | 60 | `1.92` |
| ou_u | float | 1,845 (99%) | 63 | `1.9` |
| n_bk_sp | int | 1,861 (100%) | 13 | `10` |
| n_bk_ou | int | 1,861 (100%) | 14 | `11` |

Sample row:

```
season='2019', mid='x8EBbIuf', slug='washington-mystics-connecticut-sun', hscore='89', ascore='78', ml_h='1.31', ml_a='3.43', spread='-6.5', sp_h='1.9', sp_a='1.92', total='174.5', ou_o='1.92', ou_u='1.9', n_bk_sp='10', n_bk_ou='11'
```

### `elo_model/betexplorer_ml.csv`

Rows: **333**  Columns: **6**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| season | int | 333 (100%) | 8 | `2019` |
| match | str | 333 (100%) | 170 | `washington-mystics-connecticut-sun` |
| hscore | int | 333 (100%) | 61 | `89` |
| ascore | int | 333 (100%) | 57 | `78` |
| odd_home | float | 333 (100%) | 167 | `1.31` |
| odd_away | float | 333 (100%) | 227 | `3.43` |

Sample row:

```
season='2019', match='washington-mystics-connecticut-sun', hscore='89', ascore='78', odd_home='1.31', odd_away='3.43'
```

### `elo_model/box_full.csv`

Rows: **37,509**  Columns: **22**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 37,509 (100%) | 1,949 | `401537457` |
| team | str | 37,509 (100%) | 29 | `WSH` |
| player | str | 37,509 (100%) | 612 | `Elena Delle Donne` |
| aid | int | 37,509 (100%) | 611 | `2491877` |
| starter | int | 37,509 (100%) | 2 | `1` |
| min | float | 37,506 (100%) | 54 | `12.0` |
| pts | float | 37,509 (100%) | 47 | `11.0` |
| fgm | float | 37,509 (100%) | 18 | `2.0` |
| fga | float | 37,509 (100%) | 32 | `8.0` |
| tpm | float | 37,509 (100%) | 11 | `2.0` |
| tpa | float | 37,509 (100%) | 21 | `4.0` |
| ftm | float | 37,509 (100%) | 20 | `5.0` |
| fta | float | 37,509 (100%) | 21 | `5.0` |
| oreb | float | 37,509 (100%) | 12 | `0.0` |
| dreb | float | 37,509 (100%) | 21 | `0.0` |
| reb | float | 37,509 (100%) | 23 | `0.0` |
| ast | float | 37,509 (100%) | 19 | `0.0` |
| to | float | 37,509 (100%) | 12 | `0.0` |
| stl | float | 37,509 (100%) | 9 | `1.0` |
| blk | float | 37,509 (100%) | 9 | `0.0` |
| pf | float | 37,509 (100%) | 7 | `0.0` |
| pm | float | 37,509 (100%) | 93 | `5.0` |

Sample row:

```
game_id='401537457', team='WSH', player='Elena Delle Donne', aid='2491877', starter='1', min='12.0', pts='11.0', fgm='2.0', fga='8.0', tpm='2.0', tpa='4.0', ftm='5.0', fta='5.0', oreb='0.0', dreb='0.0', reb='0.0', ast='0.0', to='0.0', stl='1.0', blk='0.0', pf='0.0', pm='5.0'
```

### `elo_model/elo_forward_log.csv`

Rows: **99**  Columns: **31**  Date range (`logged_utc`): **2026-07-15T18:41:32 .. 2026-08-03T23:45:03**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| logged_utc | datetime | 99 (100%) | 31 | `2026-07-15T18:41:32Z` |
| date | date(YYYY-MM-DD) | 99 (100%) | 15 | `2026-07-16` |
| home | str | 99 (100%) | 14 | `IND` |
| away | str | 99 (100%) | 15 | `GS` |
| tip | str | 99 (100%) | 10 | `00:00` |
| v3_margin | float | 99 (100%) | 41 | `2.16` |
| v5_margin | float | 99 (100%) | 41 | `-0.48` |
| tot_pred | float | 99 (100%) | 92 | `173.4` |
| pin_spread | str | 91 (92%) | 84 | `-3.0@117,-143` |
| pin_total | str | 91 (92%) | 84 | `168.5@102,-128` |
| pin_ml | str | 91 (92%) | 82 | `@-123,105` |
| outs | empty | 0 (0%) | 1 | `` |
| d_pnews | float | 99 (100%) | 41 | `0.055` |
| d_telo | float | 99 (100%) | 41 | `6.3` |
| d_oreb | float | 99 (100%) | 41 | `-0.0272` |
| d_p3ar | float | 99 (100%) | 41 | `-0.0422` |
| d_fluid | float | 99 (100%) | 40 | `0.315` |
| d_drop | float | 99 (100%) | 41 | `0.0592` |
| d_pfr | float | 99 (100%) | 40 | `1.49` |
| s_pace | float | 99 (100%) | 41 | `158.48` |
| s_tov | float | 99 (100%) | 41 | `-0.0085` |
| d_p3pct | float | 99 (100%) | 41 | `0.1008` |
| lg_env | float | 99 (100%) | 29 | `174.75` |
| top2_H | str | 99 (100%) | 30 | `Kelsey Mitchell|Aliyah Boston` |
| top2_A | str | 99 (100%) | 27 | `Veronica Burton|Gabby Williams` |
| proj_min_H | float | 99 (100%) | 1 | `200.0` |
| proj_min_A | float | 99 (100%) | 1 | `200.0` |
| n_outs | int | 99 (100%) | 1 | `0` |
| b3_coef | str | 99 (100%) | 1 | `18.46|0.002796|15.6|11.8|2.055` |
| b5_coef | str | 99 (100%) | 1 | `22.51|13.95|19.85|-7.74|1.352|-0.1885|2....` |
| bt_coef | str | 99 (100%) | 31 | `1.136|25.59|13.65|-182.6` |

Sample row:

```
logged_utc='2026-07-15T18:41:32Z', date='2026-07-16', home='IND', away='GS', tip='00:00', v3_margin='2.16', v5_margin='-0.48', tot_pred='173.4', pin_spread='-3.0@117,-143', pin_total='168.5@102,-128', pin_ml='@-123,105', outs='', d_pnews='0.055', d_telo='6.3', d_oreb='-0.0272', d_p3ar='-0.0422', d_fluid='0.315', d_drop='0.0592', d_pfr='1.49', s_pace='158.48', s_tov='-0.0085', d_p3pct='0.1008', lg_env='174.75', top2_H='Kelsey Mitchell|Aliyah Boston', top2_A='Veronica Burton|Gabby Williams', proj_min_H='200.0', proj_min_A='200.0', n_outs='0', b3_coef='18.46|0.002796|15.6|11.8|2.055', b5_coef='22.51|13.95|19.85|-7.74|1.352|-0.1885|2.055', bt_coef='1.136|25.59|13.65|-182.6'
```

### `elo_model/elo_forward_log_v1.csv`

Rows: **19**  Columns: **12**  Date range (`logged_utc`): **2026-07-11T16:41:45 .. 2026-07-14T18:43:39**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| logged_utc | datetime | 19 (100%) | 9 | `2026-07-11T16:41:45Z` |
| date | date(YYYY-MM-DD) | 19 (100%) | 4 | `2026-07-11` |
| home | str | 19 (100%) | 6 | `MIN` |
| away | str | 19 (100%) | 8 | `NY` |
| tip | str | 19 (100%) | 6 | `17:00` |
| v3_margin | float | 19 (100%) | 10 | `2.51` |
| v5_margin | float | 19 (100%) | 10 | `2.13` |
| tot_pred | float | 19 (100%) | 19 | `164.4` |
| pin_spread | str | 19 (100%) | 13 | `-6.5@114,-138` |
| pin_total | str | 19 (100%) | 13 | `175.0@107,-135` |
| pin_ml | str | 19 (100%) | 13 | `@-199,168` |
| outs | empty | 0 (0%) | 1 | `` |

Sample row:

```
logged_utc='2026-07-11T16:41:45Z', date='2026-07-11', home='MIN', away='NY', tip='17:00', v3_margin='2.51', v5_margin='2.13', tot_pred='164.4', pin_spread='-6.5@114,-138', pin_total='175.0@107,-135', pin_ml='@-199,168', outs=''
```

### `elo_model/elo_graded.csv`

Rows: **99**  Columns: **46**  Date range (`logged_utc`): **2026-07-15T18:41:32 .. 2026-08-03T23:45:03**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| logged_utc | datetime | 99 (100%) | 31 | `2026-07-15T18:41:32Z` |
| date | date(YYYY-MM-DD) | 99 (100%) | 15 | `2026-07-16` |
| home | str | 99 (100%) | 14 | `IND` |
| away | str | 99 (100%) | 15 | `GS` |
| tip | str | 99 (100%) | 10 | `00:00` |
| v3_margin | float | 99 (100%) | 41 | `2.16` |
| v5_margin | float | 99 (100%) | 41 | `-0.48` |
| tot_pred | float | 99 (100%) | 92 | `173.4` |
| pin_spread | str | 91 (92%) | 84 | `-3.0@117,-143` |
| pin_total | str | 91 (92%) | 84 | `168.5@102,-128` |
| pin_ml | str | 91 (92%) | 82 | `@-123,105` |
| outs | empty | 0 (0%) | 1 | `` |
| d_pnews | float | 99 (100%) | 41 | `0.055` |
| d_telo | float | 99 (100%) | 41 | `6.3` |
| d_oreb | float | 99 (100%) | 41 | `-0.0272` |
| d_p3ar | float | 99 (100%) | 41 | `-0.0422` |
| d_fluid | float | 99 (100%) | 40 | `0.315` |
| d_drop | float | 99 (100%) | 41 | `0.0592` |
| d_pfr | float | 99 (100%) | 40 | `1.49` |
| s_pace | float | 99 (100%) | 41 | `158.48` |
| s_tov | float | 99 (100%) | 41 | `-0.0085` |
| d_p3pct | float | 99 (100%) | 41 | `0.1008` |
| lg_env | float | 99 (100%) | 29 | `174.75` |
| top2_H | str | 99 (100%) | 30 | `Kelsey Mitchell|Aliyah Boston` |
| top2_A | str | 99 (100%) | 27 | `Veronica Burton|Gabby Williams` |
| proj_min_H | float | 99 (100%) | 1 | `200.0` |
| proj_min_A | float | 99 (100%) | 1 | `200.0` |
| n_outs | int | 99 (100%) | 1 | `0` |
| b3_coef | str | 99 (100%) | 1 | `18.46|0.002796|15.6|11.8|2.055` |
| b5_coef | str | 99 (100%) | 1 | `22.51|13.95|19.85|-7.74|1.352|-0.1885|2....` |
| bt_coef | str | 99 (100%) | 31 | `1.136|25.59|13.65|-182.6` |
| home_score | float | 31 (31%) | 15 | `56.0` |
| away_score | float | 31 (31%) | 13 | `75.0` |
| margin | float | 31 (31%) | 14 | `-19.0` |
| total | float | 31 (31%) | 17 | `131.0` |
| close_spread | empty | 0 (0%) | 1 | `` |
| close_total | empty | 0 (0%) | 1 | `` |
| close_ml | empty | 0 (0%) | 1 | `` |
| v3_err | float | 31 (31%) | 17 | `-21.36` |
| v5_err | float | 31 (31%) | 17 | `-22.89` |
| tot_err | float | 31 (31%) | 31 | `-51.80000000000001` |
| ats_v3 | str | 29 (29%) | 3 | `W` |
| ats_v5 | str | 29 (29%) | 3 | `W` |
| ou | str | 29 (29%) | 3 | `L` |
| ml_pick_v5 | str | 31 (31%) | 12 | `WSH` |
| ml_correct | str | 31 (31%) | 3 | `L` |

Sample row:

```
logged_utc='2026-07-15T18:41:32Z', date='2026-07-16', home='IND', away='GS', tip='00:00', v3_margin='2.16', v5_margin='-0.48', tot_pred='173.4', pin_spread='-3.0@117,-143', pin_total='168.5@102,-128', pin_ml='@-123,105', outs='', d_pnews='0.055', d_telo='6.3', d_oreb='-0.0272', d_p3ar='-0.0422', d_fluid='0.315', d_drop='0.0592', d_pfr='1.49', s_pace='158.48', s_tov='-0.0085', d_p3pct='0.1008', lg_env='174.75', top2_H='Kelsey Mitchell|Aliyah Boston', top2_A='Veronica Burton|Gabby Williams', proj_min_H='200.0', proj_min_A='200.0', n_outs='0', b3_coef='18.46|0.002796|15.6|11.8|2.055', b5_coef='22.51|13.95|19.85|-7.74|1.352|-0.1885|2.055', bt_coef='1.136|25.59|13.65|-182.6', home_score='', away_score='', margin='', total='', close_spread='', close_total='', close_ml='', v3_err='', v5_err='', tot_err='', ats_v3='', ats_v5='', ou='', ml_pick_v5='', ml_correct=''
```

### `elo_model/espn_odds.csv`

Rows: **185**  Columns: **6**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 185 (100%) | 185 | `401867793` |
| provider | str | 185 (100%) | 1 | `DraftKings` |
| spread | float | 185 (100%) | 29 | `-6.5` |
| overUnder | float | 185 (100%) | 30 | `158.5` |
| homeML | int | 185 (100%) | 93 | `-258` |
| awayML | int | 185 (100%) | 93 | `210` |

Sample row:

```
game_id='401867793', provider='DraftKings', spread='-6.5', overUnder='158.5', homeML='-258', awayML='210'
```

### `elo_model/feats_v3.csv`

Rows: **1,923**  Columns: **21**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 1,923 (100%) | 1,923 | `401129939` |
| season | int | 1,923 (100%) | 8 | `2019` |
| margin | float | 1,923 (100%) | 85 | `5.0` |
| total | float | 1,923 (100%) | 110 | `179.0` |
| pstr | float | 1,923 (100%) | 1,768 | `0.2174` |
| pnews | float | 1,923 (100%) | 1,770 | `0.241` |
| telo | float | 1,923 (100%) | 1,612 | `20.3` |
| zone | float | 1,923 (100%) | 982 | `0` |
| rest | int | 1,923 (100%) | 9 | `0` |
| b2b | int | 1,923 (100%) | 3 | `0` |
| form5 | float | 1,923 (100%) | 1,522 | `32.37` |
| pace_d | float | 1,923 (100%) | 947 | `-3.03` |
| pace_s | float | 1,923 (100%) | 1,012 | `161.43` |
| tov | float | 1,923 (100%) | 880 | `-0.0245` |
| oreb | float | 1,923 (100%) | 1,270 | `0.0156` |
| ftr | float | 1,923 (100%) | 1,318 | `-0.2447` |
| p3ar | float | 1,923 (100%) | 1,428 | `0.1441` |
| p3pct | float | 1,923 (100%) | 1,211 | `-0.0035` |
| stk | float | 1,923 (100%) | 809 | `7.05` |
| bench | float | 1,923 (100%) | 1,750 | `0.4134` |
| drop | float | 1,923 (100%) | 1,780 | `-0.2758` |

Sample row:

```
game_id='401129939', season='2019', margin='5.0', total='179.0', pstr='0.2174', pnews='0.241', telo='20.3', zone='0', rest='0', b2b='0', form5='32.37', pace_d='-3.03', pace_s='161.43', tov='-0.0245', oreb='0.0156', ftr='-0.2447', p3ar='0.1441', p3pct='-0.0035', stk='7.05', bench='0.4134', drop='-0.2758'
```

### `elo_model/feats_v4.csv`

Rows: **1,027**  Columns: **28**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 1,027 (100%) | 1,027 | `401525954` |
| season | int | 1,027 (100%) | 4 | `2023` |
| margin | float | 1,027 (100%) | 82 | `-8.0` |
| total | float | 1,027 (100%) | 99 | `156.0` |
| pstr | float | 1,027 (100%) | 976 | `-0.0847` |
| pnews | float | 1,027 (100%) | 986 | `-0.0839` |
| telo | float | 1,027 (100%) | 908 | `-5.1` |
| zone | float | 1,027 (100%) | 976 | `0.246` |
| rest | int | 1,027 (100%) | 9 | `0` |
| b2b | int | 1,027 (100%) | 3 | `0` |
| form5 | float | 1,027 (100%) | 911 | `-7.79` |
| pace_d | float | 1,027 (100%) | 670 | `5.96` |
| pace_s | float | 1,027 (100%) | 698 | `156.04` |
| tov | float | 1,027 (100%) | 637 | `-0.0173` |
| oreb | float | 1,027 (100%) | 814 | `-0.1021` |
| ftr | float | 1,027 (100%) | 826 | `0.2195` |
| p3ar | float | 1,027 (100%) | 892 | `0.1593` |
| p3pct | float | 1,027 (100%) | 795 | `-0.2695` |
| stk | float | 1,027 (100%) | 600 | `-7.74` |
| bench | float | 1,027 (100%) | 986 | `-0.1073` |
| drop | float | 1,027 (100%) | 984 | `0.0007` |
| fluid | float | 1,027 (100%) | 963 | `-0.0501` |
| pmr | float | 1,027 (100%) | 990 | `-0.0458` |
| pfr | float | 1,027 (100%) | 1,017 | `-3.8421` |
| ftp | float | 1,027 (100%) | 828 | `-0.319` |
| blkr | float | 1,027 (100%) | 1,017 | `-1.5263` |
| q4 | float | 1,027 (100%) | 918 | `0.1594` |
| road | int | 1,027 (100%) | 7 | `0` |

Sample row:

```
game_id='401525954', season='2023', margin='-8.0', total='156.0', pstr='-0.0847', pnews='-0.0839', telo='-5.1', zone='0.246', rest='0', b2b='0', form5='-7.79', pace_d='5.96', pace_s='156.04', tov='-0.0173', oreb='-0.1021', ftr='0.2195', p3ar='0.1593', p3pct='-0.2695', stk='-7.74', bench='-0.1073', drop='0.0007', fluid='-0.0501', pmr='-0.0458', pfr='-3.8421', ftp='-0.319', blkr='-1.5263', q4='0.1594', road='0'
```

### `elo_model/feats_v5.csv`

Rows: **1,027**  Columns: **34**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 1,027 (100%) | 1,027 | `401525954` |
| season | int | 1,027 (100%) | 4 | `2023` |
| margin | float | 1,027 (100%) | 82 | `-8.0` |
| total | float | 1,027 (100%) | 99 | `156.0` |
| pstr | float | 1,027 (100%) | 976 | `-0.0847` |
| pnews | float | 1,027 (100%) | 986 | `-0.0839` |
| telo | float | 1,027 (100%) | 908 | `-5.1` |
| zone | float | 1,027 (100%) | 976 | `0.246` |
| rest | int | 1,027 (100%) | 9 | `0` |
| b2b | int | 1,027 (100%) | 3 | `0` |
| form5 | float | 1,027 (100%) | 911 | `-7.79` |
| pace_d | float | 1,027 (100%) | 670 | `5.96` |
| pace_s | float | 1,027 (100%) | 698 | `156.04` |
| tov | float | 1,027 (100%) | 637 | `-0.0173` |
| oreb | float | 1,027 (100%) | 814 | `-0.1021` |
| ftr | float | 1,027 (100%) | 826 | `0.2195` |
| p3ar | float | 1,027 (100%) | 892 | `0.1593` |
| p3pct | float | 1,027 (100%) | 795 | `-0.2695` |
| stk | float | 1,027 (100%) | 600 | `-7.74` |
| bench | float | 1,027 (100%) | 986 | `-0.1073` |
| drop | float | 1,027 (100%) | 984 | `0.0007` |
| fluid | float | 1,027 (100%) | 963 | `-0.0501` |
| pmr | float | 1,027 (100%) | 990 | `-0.0458` |
| pfr | float | 1,027 (100%) | 1,017 | `-3.8421` |
| ftp | float | 1,027 (100%) | 828 | `-0.319` |
| blkr | float | 1,027 (100%) | 1,017 | `-1.5263` |
| q4 | float | 1,027 (100%) | 918 | `0.1594` |
| road | int | 1,027 (100%) | 7 | `0` |
| m_scdef | float | 1,027 (100%) | 965 | `-0.2127` |
| m_pade | float | 1,027 (100%) | 964 | `-0.2647` |
| m_rb | float | 1,027 (100%) | 944 | `0.002` |
| m_vo | float | 1,027 (100%) | 934 | `-0.0259` |
| m_all5 | float | 1,027 (100%) | 993 | `-0.3` |
| lgenv | float | 1,027 (100%) | 504 | `162` |

Sample row:

```
game_id='401525954', season='2023', margin='-8.0', total='156.0', pstr='-0.0847', pnews='-0.0839', telo='-5.1', zone='0.246', rest='0', b2b='0', form5='-7.79', pace_d='5.96', pace_s='156.04', tov='-0.0173', oreb='-0.1021', ftr='0.2195', p3ar='0.1593', p3pct='-0.2695', stk='-7.74', bench='-0.1073', drop='0.0007', fluid='-0.0501', pmr='-0.0458', pfr='-3.8421', ftp='-0.319', blkr='-1.5263', q4='0.1594', road='0', m_scdef='-0.2127', m_pade='-0.2647', m_rb='0.002', m_vo='-0.0259', m_all5='-0.3', lgenv='162'
```

### `elo_model/gameinfo.csv`

Rows: **1,059**  Columns: **4**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 1,059 (100%) | 1,059 | `401537457` |
| attendance | int | 1,059 (100%) | 762 | `0` |
| venue | str | 1,059 (100%) | 37 | `Target Center` |
| officials | str | 1,055 (100%) | 950 | `Gina Cross|Ashley Gloss|Blanca Burns` |

Sample row:

```
game_id='401537457', attendance='0', venue='Target Center', officials='Gina Cross|Ashley Gloss|Blanca Burns'
```

### `elo_model/games_full.csv`

Rows: **2,058**  Columns: **7**  Date range (`date`): **20190509 .. 20260802**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 2,058 (100%) | 1,954 | `401537457` |
| date | date(YYYYMMDD) | 2,058 (100%) | 778 | `20230505` |
| home | str | 2,058 (100%) | 19 | `MIN` |
| away | str | 2,058 (100%) | 25 | `WSH` |
| home_score | int | 2,058 (100%) | 76 | `72` |
| away_score | int | 2,058 (100%) | 74 | `69` |
| season | int | 2,058 (100%) | 8 | `2023` |

Sample row:

```
game_id='401537457', date='20230505', home='MIN', away='WSH', home_score='72', away_score='69', season='2023'
```

### `elo_model/plays_full.csv`

Rows: **415,714**  Columns: **8**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 415,714 (100%) | 1,058 | `401537457` |
| period | int | 415,714 (100%) | 8 | `1` |
| clock | str | 415,714 (100%) | 1,141 | `10:00` |
| type_id | int | 415,714 (100%) | 128 | `615` |
| team_id | int | 407,144 (98%) | 26 | `8` |
| text | str | 415,713 (100%) | 88,512 | `Amanda Zahui B. vs. Dorka Juhasz (Tiffan...` |
| away | int | 415,714 (100%) | 140 | `0` |
| home | int | 415,714 (100%) | 130 | `0` |

Sample row:

```
game_id='401537457', period='1', clock='10:00', type_id='615', team_id='8', text='Amanda Zahui B. vs. Dorka Juhasz (Tiffany Mitchell gains possession)', away='0', home='0'
```

### `elo_model/plays_text.csv`

Rows: **179,895**  Columns: **10**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 179,895 (100%) | 1,021 | `401537457` |
| period | int | 179,895 (100%) | 8 | `1` |
| kind | str | 179,895 (100%) | 2 | `shot` |
| team_id | int | 168,986 (94%) | 24 | `8` |
| shooter | str | 168,986 (94%) | 460 | `Napheesa Collier` |
| assister | str | 52,050 (29%) | 1,409 | `Lindsay Allen` |
| alley | int | 179,895 (100%) | 2 | `0` |
| dunk | int | 179,895 (100%) | 2 | `0` |
| layup | int | 179,895 (100%) | 2 | `0` |
| made | int | 179,895 (100%) | 2 | `0` |

Sample row:

```
game_id='401537457', period='1', kind='shot', team_id='8', shooter='Napheesa Collier', assister='', alley='0', dunk='0', layup='0', made='0'
```

### `elo_model/ratings.csv`

Rows: **454**  Columns: **6**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| aid | int | 454 (100%) | 454 | `2491877` |
| player | str | 428 (94%) | 429 | `Elena Delle Donne` |
| team | str | 428 (94%) | 20 | `WSH` |
| gp | int | 454 (100%) | 122 | `27` |
| oR | float | 454 (100%) | 320 | `0.08` |
| dR | float | 454 (100%) | 267 | `0.106` |

Sample row:

```
aid='2491877', player='Elena Delle Donne', team='WSH', gp='27', oR='0.08', dR='0.106'
```

### `elo_model/shots.csv`

Rows: **253,303**  Columns: **8**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 253,303 (100%) | 1,947 | `401537457` |
| period | int | 253,303 (100%) | 8 | `1` |
| team_id | int | 253,303 (100%) | 29 | `8` |
| shooter | str | 253,303 (100%) | 608 | `Napheesa Collier` |
| x | int | 253,303 (100%) | 51 | `10` |
| y | int | 253,303 (100%) | 86 | `19` |
| made | int | 253,303 (100%) | 2 | `0` |
| three | int | 253,303 (100%) | 2 | `1` |

Sample row:

```
game_id='401537457', period='1', team_id='8', shooter='Napheesa Collier', x='10', y='19', made='0', three='1'
```

### `elo_model/timeouts.csv`

Rows: **17,478**  Columns: **4**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 17,478 (100%) | 1,721 | `401537457` |
| period | int | 17,478 (100%) | 8 | `1` |
| clock | str | 17,478 (100%) | 1,104 | `4:54` |
| team_txt | str | 17,478 (100%) | 899 | `Official timeout` |

Sample row:

```
game_id='401537457', period='1', clock='4:54', team_txt='Official timeout'
```

### `elo_model/zone_feats.csv`

Rows: **1,046**  Columns: **4**

| column | dtype | non-null | distinct | example |
|---|---|---|---|---|
| game_id | int | 1,046 (100%) | 1,046 | `401537457` |
| matchup_diff | float | 1,046 (100%) | 1,040 | `0.0` |
| margin | float | 1,046 (100%) | 84 | `3.0` |
| season | int | 1,046 (100%) | 4 | `2023` |

Sample row:

```
game_id='401537457', matchup_diff='0.0', margin='3.0', season='2023'
```
