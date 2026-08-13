# run_local.py - run the WHOLE pipeline on this laptop, independent of GitHub Actions.
# ---------------------------------------------------------------------------------------------
# WHY THIS EXISTS: GitHub's cron skipped the 09:13 run on 2026-08-08 (next scheduled was 12:13, so
# the T-8h alert never fired) and again skipped 15:13 that evening. Two missed pings in one day on a
# schedule that is supposed to be unattended. The cloud stays primary, but this gives a local path
# that answers to nobody but the laptop.
#
#   python run_local.py            refresh box -> capture 1xbet -> drift gate -> guard -> Discord
#   python run_local.py --dry      everything except sending
#
# Safe to run alongside the cloud: every writer here appends or rewrites atomically, and the alert
# dedups on alert_state.json, so a bet already pinged by the cloud will not be sent twice.
import platform
platform._wmi = None          # MUST precede any pandas import on this box - a wedged WMI hangs pandas
import os, sys, runpy, datetime, csv

D = os.path.dirname(os.path.abspath(__file__))
os.chdir(D)
DRY = "--dry" in sys.argv


def step(name, script, env=None):
    """Run one pipeline script in-process. A failure is reported and skipped, never fatal - a bad
    1xbet response must not stop the drift gate from re-reading what we already have."""
    print(f"\n{'='*70}\n  {name}\n{'='*70}")
    old = dict(os.environ)
    if env: os.environ.update(env)
    try:
        runpy.run_path(os.path.join(D, script), run_name="__main__")
    except SystemExit:
        pass
    except Exception as e:
        import traceback
        print(f"  !! {script} failed: {e}")
        traceback.print_exc(limit=3)
    finally:
        os.environ.clear(); os.environ.update(old)


def git(*args):
    """Share state with the cloud. alert_state.json records which stages have fired for a slate, so
    if the laptop and the runner keep SEPARATE copies they will each think nothing was sent and you
    get every ping twice. Pull before, push after - then whichever one runs first wins and the other
    correctly stays quiet."""
    import subprocess
    try:
        r = subprocess.run(["git"] + list(args), cwd=D, capture_output=True, text=True, timeout=120)
        return r.returncode == 0
    except Exception as e:
        print("  git failed (continuing local-only):", e); return False

def git_out(*args):
    import subprocess
    try:
        r = subprocess.run(["git"] + list(args), cwd=D, capture_output=True, text=True, timeout=120)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""

# WHY THIS IS NO LONGER `git pull --rebase --autostash`.
# That command rebases the WHOLE repo on every hourly run. Twice it dropped local commits and
# deleted their files from the working tree, and twice its autostash hit a conflict on the pop and
# left board_last.json / health_state.json full of merge markers - which then blocks every later
# commit. The repo is not what needs syncing. Exactly ONE file does: alert_state.json, which
# records what has already been pinged so the laptop and the cloud do not both alert.
# So fetch, take that single file, and touch nothing else. This cannot delete a file, cannot
# rewrite history, and cannot leave a conflict behind.
print("syncing ping state with the cloud (alert_state.json only)...")
if git("fetch", "-q", "origin", "main"):
    if git("checkout", "origin/main", "--", "alert_state.json"):
        print("  pulled alert_state.json from origin")
    else:
        print("  no alert_state.json on origin yet - continuing local-only")
else:
    print("  fetch failed - continuing local-only")
unmerged = git_out("diff", "--name-only", "--diff-filter=U")
if unmerged:
    print(f"  WARNING unresolved merge left in: {unmerged.splitlines()} - fix before this can push")

step("1/5  refresh box scores + rebuild signals from the latest games", "daily_picks.py")
step("2/5  capture 1xbet board (both sides, 48h window)", "cloud_xbet.py",
     {"CAPTURE_ROLE": "all", "XBET_WINDOW_MIN": "2880"})
step("3/5  drift gate (skip-drift verdicts + fade paper)", "drift_gate.py")

# ---- 4) show exactly what the guard would send, BEFORE sending it -----------------------------
print(f"\n{'='*70}\n  4/5  guard - what passes the strategy right now\n{'='*70}")
sys.path.insert(0, D)
import alert_bets as A
rows = list(csv.DictReader(open(os.path.join(D, "drift_gate_today.csv"), encoding="utf-8")))
ok = A.guard(rows)
if not ok:
    print("  nothing passes the guard right now.")
else:
    u = sum(0.5 if A.stake(r).startswith("½") else 1.0 for r in ok)
    print(f"  {len(ok)} bets, {u:g}u total exposure\n")
    for r in sorted(ok, key=lambda x: (x["src"], x["player"])):
        print("   " + A.fmt(r))

if DRY:
    print("\n--dry: not sending.")
else:
    step("5/5  Discord alert (respects the stage timing + dedup)", "alert_bets.py")
    step("dashboard", "build_dashboard.py")
    # push the record back so the cloud sees what was already sent
    for fn in ("alert_state.json", "pinged_bets.csv", "drift_gate_today.csv", "drift_log.csv",
               "fade_paper.csv", "bets_log.csv", "xbet_board.csv", "xbet_snapshots.csv",
               "dashboard.html", "data/box_2026.csv", "data/games_2026.csv"):
        if os.path.exists(os.path.join(D, fn)): git("add", "-f", fn)
    if git("commit", "-q", "-m", f"local run {datetime.datetime.now().strftime('%F %H:%M')}"):
        # push only. If origin has moved on, the push is simply rejected and we try again next
        # hour - that is harmless. The old code rebased first, which is what kept destroying the
        # working tree for the sake of a push that does not matter to tonight's betting.
        if not git("push", "-q"):
            print("  push rejected (origin moved on) - local record is intact, will retry next run")
print(f"\ndone {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} local")
