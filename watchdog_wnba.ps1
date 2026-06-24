# watchdog_wnba.ps1 - keeps the WNBA bot healthy while unattended (laptop 24/7).
# Run by Task Scheduler every ~30 min (hidden). Read-mostly; only acts when something is actually wrong.
# ASCII-only on purpose: PowerShell 5.1 misreads non-ASCII in -File scripts.
# Checks + auto-fixes:
#   1. GIT SYNC - the recurring divergence / conflict-marker / stuck-rebase mess -> resync laptop to origin
#      (cloud is the source of truth; laptop is a mirror + capturer). Backs up before any hard reset.
#   2. SCHEDULED TASKS - WNBA-Capture-Real / WNBA-Grade-Trigger enabled (re-enable if Windows disabled them).
#   3. CLOUD LIVENESS - if origin hasn't committed in hours, nudge a grade+capture dispatch; alert if long-dead.
#   4. gh AUTH - if the CLI auth lapses the laptop can't dispatch; alert.
# Pings Discord (webhook.txt) only on a REAL problem. Logs every run to watchdog_wnba.log.
$ErrorActionPreference = 'Continue'
$REPO = 'C:\Users\Axioo\wnba-line-capture'
$GH   = 'C:\Program Files\GitHub CLI\gh.exe'
Set-Location $REPO
$LOG  = Join-Path $REPO 'watchdog_wnba.log'
function log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm') $m" | Out-File -Append -FilePath $LOG -Encoding utf8 }

$hook = ''
if (Test-Path "$REPO\webhook.txt") { $hook = (Get-Content "$REPO\webhook.txt" -Raw).Trim() }
function alert($m) {
    log "ALERT: $m"
    if ($hook) {
        try {
            Invoke-RestMethod -Uri $hook -Method Post -ContentType 'application/json' -TimeoutSec 15 `
                -Headers @{ 'User-Agent' = 'wnba-watchdog' } `
                -Body (@{ content = "WNBA watchdog: $m" } | ConvertTo-Json)
        } catch {}
    }
}

# ---------- 1) GIT SYNC HEALTH ----------
try {
    if ((Test-Path "$REPO\.git\rebase-merge") -or (Test-Path "$REPO\.git\rebase-apply")) {
        git rebase --abort 2>$null
        log "aborted a stuck rebase"
    }
    git fetch origin 2>$null
    $loc = (git rev-parse HEAD 2>$null)
    $org = (git rev-parse origin/main 2>$null)
    if ($loc -and $org -and ($loc.Trim() -ne $org.Trim())) {
        $lr = (git rev-list --left-right --count HEAD...origin/main 2>$null) -split '\s+'
        $ahead = [int]$lr[0]
        $behind = [int]$lr[1]
        $markers = git grep -l '^<<<<<<< ' 2>$null
        if ($markers -or ($ahead -gt 0 -and $behind -gt 0)) {
            git branch -f watchdog-backup HEAD 2>$null
            git reset --hard origin/main 2>$null
            log "git BROKEN/diverged (ahead=$ahead behind=$behind markers=$($markers -join ',')) -> reset to origin (backup: watchdog-backup)"
        } elseif ($behind -gt 0 -and $ahead -eq 0) {
            git pull --ff-only origin main 2>$null
            log "git was behind $behind -> fast-forwarded"
        } elseif ($ahead -gt 0 -and $behind -eq 0) {
            git push 2>$null
            log "git had $ahead un-pushed local commit(s) -> pushed"
        }
    }
    # tidy stray autostashes once synced (this bot repo has no intentional user stashes; they only pile up from failed autostash-pops)
    if ((git rev-parse HEAD 2>$null).Trim() -eq (git rev-parse origin/main 2>$null).Trim()) {
        if (git stash list 2>$null) { git stash clear 2>$null; log "cleared stray stash(es)" }
    }
} catch { log "git-sync error: $($_.Exception.Message)" }

# ---------- 2) SCHEDULED TASKS ----------
foreach ($t in @('WNBA-Capture-Real', 'WNBA-Grade-Trigger')) {
    try {
        $info = schtasks /query /tn "\$t" /v /fo CSV 2>$null | ConvertFrom-Csv | Select-Object -First 1
        if (-not $info) {
            alert "$t task is MISSING - real-money capture/grade won't fire."
            continue
        }
        if ($info.'Scheduled Task State' -ne 'Enabled') {
            schtasks /change /tn "\$t" /enable 2>$null
            log "$t was disabled -> re-enabled"
        }
    } catch { log "task-check error ($t): $($_.Exception.Message)" }
}

# ---------- 3) CLOUD LIVENESS ----------
$cloudAge = '?'
try {
    $iso = (git show -s --format=%cI origin/main 2>$null).Trim()
    $ageH = ([datetime]::UtcNow - ([datetimeoffset]$iso).UtcDateTime).TotalHours
    $cloudAge = [math]::Round($ageH, 1)
    if ($ageH -gt 8) {
        & $GH workflow run grade-bets.yml  --repo JollyChenn/wnba-line-capture 2>$null
        & $GH workflow run capture-xbet.yml --repo JollyChenn/wnba-line-capture 2>$null
        log "cloud stale ${cloudAge}h -> nudged grade+capture dispatch"
        if ($ageH -gt 18) { alert "cloud silent ${cloudAge}h - grading/capture likely DOWN (Actions minutes? 1xbet block?). Check GitHub Actions." }
    }
} catch { log "liveness error: $($_.Exception.Message)" }

# ---------- 4) gh AUTH ----------
try {
    & $GH auth status 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { alert "gh CLI auth FAILED - laptop can't dispatch grading. Fix: run 'gh auth login'." }
} catch {}

$lh = (git rev-parse --short HEAD 2>$null)
$oh = (git rev-parse --short origin/main 2>$null)
log "ok (local $lh = origin $oh; cloud age ${cloudAge}h)"
