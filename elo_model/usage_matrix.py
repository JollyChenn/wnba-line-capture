# usage_matrix.py - USAGE-REDISTRIBUTION MATRIX (per the betting-engine brief: "X out -> who absorbs").
# Built + tested 2026-08-01 on real pregame 1xbet odds, OUT-day games only:
#   baseline 51% -12.3u | matrix-bumped 52% -8.9u | th2.5 53% -3.3u  (breakeven 53.5%)
# The matrix IMPROVES the projection (+1-2pp every cut) but the book already prices outs -> no
# standalone props edge at 1xbet. Asset kept: absorb[(absent,teammate)] deltas power the cascade
# ranking + future full-board repricing. Rebuild by running the inline logic in the session notes /
# PLAN 5b; matrix needs >=3 shared-absence games per pair before it fires.
