@echo off
REM ===========================================================================
REM WNBA grade trigger (laptop side) - fires grading AND pulls results back.
REM Dispatches the cloud grade-bets workflow via gh (GitHub honors dispatch
REM immediately, unlike its free-tier schedule cron which it delays ~1.5-2h and
REM sometimes drops). Run by Task Scheduler a few times midday/evening local;
REM each call is idempotent (the cloud grade no-ops if nothing new settled).
REM
REM ALSO pulls the cloud results back to the laptop - once BEFORE dispatch
REM (grabs prior runs) and once ~90s AFTER (grabs the run it just fired) - so
REM local dashboard.html / graded_bets.csv never go stale between slates.
REM Mirrors capture_real.bat git usage (cd to repo, bare git, --rebase
REM --autostash to survive a concurrent capture run).
REM Remove anytime:  schtasks /delete /tn "WNBA-Grade-Trigger" /f
REM ===========================================================================
set "GH=C:\Program Files\GitHub CLI\gh.exe"
cd /d "%~dp0"

REM 1) refresh local with whatever the cloud has already graded + pushed
git pull --rebase --autostash origin main >> grade_trigger.log 2>&1

REM 2) fire the cloud grade-bets workflow
"%GH%" workflow run grade-bets.yml --repo JollyChenn/wnba-line-capture >> grade_trigger.log 2>&1
echo [%DATE% %TIME%] dispatch exit=%ERRORLEVEL% >> grade_trigger.log

REM 3) wait for the cloud run to grade + push, then pull its results. ping
REM    (not timeout) because timeout fails with no console under Task Scheduler.
REM    ping -n 91 waits ~90s.
ping -n 91 127.0.0.1 >nul 2>&1
git pull --rebase --autostash origin main >> grade_trigger.log 2>&1
echo [%DATE% %TIME%] post-pull done >> grade_trigger.log
