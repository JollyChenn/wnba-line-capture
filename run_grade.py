# run_grade.py - the whole grading suite, on this laptop. Was GitHub-Actions-only until now.
# ---------------------------------------------------------------------------------------------
# grade-bets.yml ran seven scripts on a dozen crons. grade_trigger.bat on the laptop contained no
# python at all, so with the cloud workflows disabled NOTHING would grade a bet, refresh CLV, or
# run the regression audit. This file is that workflow, locally, in the same order.
#
# Deliberately does no git. If a step fails the rest still run - a broken CLV reader should never
# stop bets being graded.
import os, sys, subprocess, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("refresh box scores for finished games", "daily_picks.py"),
    ("grade bets vs results (record, ROI, odds-CLV, sharp-CLV)", "grade_bets.py"),
    ("drift tracker", "drift_tracker.py"),
    ("fade paper grading", "fade_grade.py"),
    ("CLV reader", "clv_reader.py"),
    ("signal report", "signal_report.py"),
    ("strategy audit (fails loudly on a regression)", "audit_strategy.py"),
    ("health check", "health_check.py"),
    ("grade the over-model forward record", "grade_forward.py"),
    ("ping last night's result (notification 2 of 2)", "ping_results.py"),
    ("dashboard", "build_dashboard.py"),
]

print(f"=== local grading run {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
ok = fail = skip = 0
for name, script in STEPS:
    path = os.path.join(D, script)
    if not os.path.exists(path):
        print(f"  SKIP  {name}  ({script} not present)"); skip += 1; continue
    try:
        # WINDOWS ONLY PROBLEM, AND IT WAS SILENTLY FATAL. These scripts print star and chart
        # characters. On the GitHub runner stdout is UTF-8 so it worked; on this laptop Python
        # defaults to cp1252, the print raises UnicodeEncodeError, and the script dies with
        # exit 1 - meaning grade_bets.py would never actually grade anything. Force UTF-8.
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        r = subprocess.run([sys.executable, path], cwd=D, capture_output=True, text=True,
                           timeout=900, env=env, errors="replace")
        tail = (r.stdout or "").strip().splitlines()[-2:]
        if r.returncode == 0:
            print(f"  ok    {name}")
            for t in tail: print(f"          {t[:110]}")
            ok += 1
        else:
            print(f"  FAIL  {name}  (exit {r.returncode})")
            for t in (r.stderr or "").strip().splitlines()[-3:]: print(f"          {t[:110]}")
            fail += 1
    except Exception as e:
        print(f"  FAIL  {name}: {e}"); fail += 1
print(f"=== {ok} ok, {fail} failed, {skip} skipped ===")
