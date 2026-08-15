# run_fast.py - the SHORT loop. Board capture + card only, every 10 minutes.
# ---------------------------------------------------------------------------------------------
# WHY SPLIT THE CADENCE. Only two things need to be fresh: the board (prices and lines move) and
# the card (which reads the board). Everything else in run_local.py - injuries, game lines, the
# dashboard, the drift gate - changes on the scale of hours and does not need a 10-minute loop.
#
# THE NUMBER THAT JUSTIFIES IT. Of the line cuts that later revert, 26.3% are gone inside 30
# minutes; p25 of their lifetime is 20 minutes. A 30-minute loop is blind to a quarter of the
# transient ones. Worse, we cannot even measure how many we miss: xbet_board.csv logs only
# CHANGES, so a cut that opens and closes between two scrapes is absent from the file entirely.
# Sampling faster is the only way to find out, which makes this an experiment, not a tuning.
#
# WHY IT DOES NOT MEAN MORE LOAD ON 1XBET. cloud_xbet.py now ROTATES between 1x-bet.com and
# melbet.com, which run the same LineFeed engine and quote the same board:
#     before  1x-bet every 30 min          = 2 requests/hr, all on one host
#     after   alternating every 10 min     = 3 requests/hr, split across two hosts
# Each host is actually hit LESS often than before while we sample the board 3x more.
#
# Silent apart from the card, which is notification 1 of 2 and only speaks when there is a bet.
import os, sys, subprocess, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("board", "cloud_xbet.py", {"CAPTURE_ROLE": "all", "XBET_WINDOW_MIN": "2880"}),
    ("card",  "model_card.py", {}),                 # NOTIFICATION 1 of 2 - silent when no bet
    ("shadow", "shadow_log.py", {}),                # decision-time log of every rejected filter
]

stamp = datetime.datetime.now().strftime("%H:%M")
out = []
for name, script, env in STEPS:
    path = os.path.join(D, script)
    if not os.path.exists(path):
        out.append(f"{name}:missing"); continue
    try:
        # cp1252 is fatal for anything printing a star or an emoji, and these all do.
        e = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", **env)
        r = subprocess.run([sys.executable, path], cwd=D, capture_output=True, text=True,
                           timeout=300, env=e, errors="replace")
        txt = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            out.append(f"{name}:FAIL")
            for l in txt.strip().splitlines()[-2:]: print(f"    {name}: {l[:120]}")
            continue
        # surface only what matters, so a 10-minute loop does not flood the window overnight
        for l in txt.splitlines():
            if any(k in l for k in ("MODEL S", "pinged", "FULL BOARD", "BLOCKED",
                                    "mirror order", "shadow ", "fell back")):
                print(f"    {l.strip()[:140]}")
        out.append(f"{name}:ok")
    except subprocess.TimeoutExpired:
        out.append(f"{name}:timeout")
    except Exception as ex:
        out.append(f"{name}:{str(ex)[:40]}")
print(f"  fast {stamp}  " + "  ".join(out))
