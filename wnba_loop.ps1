# wnba_loop.ps1 - the whole bot, in one PowerShell window, forever.
# ---------------------------------------------------------------------------------------------
# Replaces the WNBA-LocalRun / WNBA-ModelCard / WNBA-GradeLocal scheduled tasks. Those are
# disabled while this runs, otherwise both would fire and you would get doubled work.
#
# Cadence, and why:
#   FAST      every 10 min - board capture + the card + the shadow log, and nothing else.
#             Of the line cuts that later revert, 26.3% are gone inside 30 minutes (p25 of their
#             life is 20 min), so a 30-min loop was blind to a quarter of the transient ones.
#             cloud_xbet.py now ROTATES 1x-bet.com <-> melbet.com (same LineFeed engine, same
#             board), so each HOST is hit less than before - 3 req/hr split two ways versus 2
#             req/hr on one - while we sample the board three times as often.
#   PIPELINE  every 30 min - everything that moves on the scale of hours: picks, validate, news,
#             gamelines, drift gate, cascade watch, lineup check, dashboard.
#   GRADING   every 2 h - games finish 09:00-12:00 WIB and late finals need sweeping up.
#             Every grading script is idempotent on already-graded rows, so extra runs are free.
#
# Ctrl+C stops it. Nothing is lost - every script writes as it goes.
$ErrorActionPreference = "Continue"
$repo = "C:\Users\Axioo\wnba-line-capture"
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"   # cp1252 kills grade_bets.py mid-print otherwise
$env:PYTHONUTF8 = "1"

$fastEvery     = 10      # minutes - board + card only
$pipelineEvery = 30      # minutes - the full run
$gradeEvery    = 120     # minutes
$lastFast      = [datetime]::MinValue
$lastPipeline  = [datetime]::MinValue
$lastGrade     = [datetime]::MinValue
$cycle = 0

function Say($msg, $colour = "Gray") {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "MM-dd HH:mm"), $msg) -ForegroundColor $colour
}

Say "WNBA loop started. fast $fastEvery min | pipeline $pipelineEvery min | grading $gradeEvery min." "Cyan"
Say "repo $repo  |  Ctrl+C to stop" "DarkGray"

while ($true) {
    $cycle++
    $now = Get-Date

    if (($now - $lastFast).TotalMinutes -ge $fastEvery) {
        try {
            $out = & python run_fast.py 2>&1
            $out | Out-File -Append -Encoding utf8 "$repo\wnba_loop.log"
            $out | Select-String -Pattern "MODEL S|pinged|BLOCKED|FAIL|fast " |
                ForEach-Object { Say ("   " + $_.ToString().Trim()) "White" }
        } catch { Say "fast error: $_" "Red" }
        $lastFast = $now
    }

    if (($now - $lastPipeline).TotalMinutes -ge $pipelineEvery) {
        Say "pipeline: run_local.py ..." "Yellow"
        try {
            $out = & python run_local.py 2>&1
            $out | Out-File -Append -Encoding utf8 "$repo\wnba_loop.log"
            # surface only the lines that matter, so the window stays readable overnight
            $out | Select-String -Pattern "bets,|nothing passes|no tips|OVER MODEL|pinged|!!|WARNING|rejected" |
                Select-Object -First 6 | ForEach-Object { Say ("   " + $_.ToString().Trim()) "White" }
            Say "pipeline done" "Green"
        } catch { Say "pipeline error: $_" "Red" }
        $lastPipeline = $now
    }

    if (($now - $lastGrade).TotalMinutes -ge $gradeEvery) {
        Say "grading: run_grade.py ..." "Yellow"
        try {
            $out = & python run_grade.py 2>&1
            $out | Out-File -Append -Encoding utf8 "$repo\wnba_loop.log"
            $out | Select-String -Pattern "^\s+(ok|FAIL|SKIP)|forward record|===" |
                Select-Object -Last 4 | ForEach-Object { Say ("   " + $_.ToString().Trim()) "White" }
            Say "grading done" "Green"
        } catch { Say "grading error: $_" "Red" }
        $lastGrade = $now
    }

    Start-Sleep -Seconds 120      # wake every 2 min - the fast loop needs finer granularity
}
