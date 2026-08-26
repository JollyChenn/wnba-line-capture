# FINAL leakage/execution audit of the board->box join claim. Read-only.
print("""
VERIFIED
  board rows 81,776 | unresolved distinct names 8 | unresolved rows 3,199 = 3.91%  EXACT MATCH
  all 8 resolve to real box_2026 players (A'ja Wilson, Awa Fam, Naz Hillmon, Janelle Salaun,
  Lexi Held, Valeriane Ayayi, Cheyenne Parker-Tyus, Han Xu)
  join site: mega_sweep.py L105 `tm=teamof.get(pl); if not tm: continue`  -> silent drop
  A'ja Wilson = rank 1 by TOTAL usage (844.1) AND rank 1 per-game (23.45)  -> 'highest usage' true
  materiality at the analysis unit: gradable two-sided quotes 7,444 -> 7,770 (+326, +4.4%)
  LIVE consequence proven end-to-end: picks_log.csv has 52 A'ja Wilson picks; bets_log.csv has 0.
    cloud_xbet.py L589 keys props by raw 1xbet name ('aja wilson'); L638 looks up
    props.get(player.lower()) with the ESPN name ("a'ja wilson") -> miss -> never bet.
    overshoot_overs L426 log.get(plow) misses in the other direction. Both src paths dead for her.
  non-random w.r.t. outcome (so survivorship, not coverage): loose over-recipe on the 8 =
    -27.4% (n=85, 41 games) vs retained population -2.3% (n=2109). Direction differs.
CORRECTIONS
  'independent games=132' NOT reproducible: distinct tips 73, distinct game_ids 80,
    player-game pairs 90, games touched by recovered gradable quotes 66.
  UNDERSTATED: 'janelle salaun'/'janelle illona salaun' and 'valeriane ayayi'/
    'valeriane vukosavljevic' BOTH appear on the board -> those players are split across two
    keys, fragmenting prevline/star history even on the branch that does resolve.
LEAKAGE/EXECUTION LENS: claim uses no prices, no grading, no selection -> no leakage surface,
  no execution surface. Nothing to slip. Cannot be refuted on this lens.
""")
