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

print("syncing state with the cloud...")
git("pull", "--rebase", "--autostash", "-q", "origin", "main")

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
        git("pull", "--rebase", "--autostash", "-q", "origin", "main"); git("push", "-q")
print(f"\ndone {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} local")
