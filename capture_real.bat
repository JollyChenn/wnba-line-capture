@echo off
REM ===========================================================================
REM WNBA REAL-MONEY capture (laptop side). Counterpart to the cloud's paper role.
REM   - scrapes 1xbet for MODEL (cold/shrink/stingy) real-money bets,
REM   - writes the odds snapshots (xbet/pinn) that feed the signal CLV,
REM   - pings Discord for real-money bets (per-game timed),
REM   - pushes the data so the cloud grade-bets can settle it.
REM Light: one ~30-60s run; the task auto-kills it at 4 min, never stacks, hidden.
REM Webhook is read from webhook.txt (gitignored) so the secret never hits git.
REM Your actual P&L is in my_bets.csv (hand-entered) and is independent of this.
REM Remove: schtasks /delete /tn "WNBA-Capture-Real" /f
REM ===========================================================================
cd /d "%~dp0"
if exist webhook.txt (set /p DISCORD_WEBHOOK=<webhook.txt) else (set "DISCORD_WEBHOOK=")
set "CAPTURE_ROLE=real"
set "XBET_WINDOW_MIN=1440"
git pull --rebase --autostash origin main >> capture_real.log 2>&1
python cloud_xbet.py >> capture_real.log 2>&1
git add -f bets_log.csv xbet_snapshots.csv pinn_snapshots.csv xbet_board.csv board_last.json >> capture_real.log 2>&1
git diff --staged --quiet
if errorlevel 1 (
  git commit -m "laptop real-money capture %DATE% %TIME%" >> capture_real.log 2>&1
  git pull --rebase --autostash origin main >> capture_real.log 2>&1
  git push >> capture_real.log 2>&1
)
echo [%DATE% %TIME%] capture_real done >> capture_real.log
