param(
    [string]$Root = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$ErrorActionPreference = 'Stop'
Set-Location $Root

$lockPath = Join-Path $Root '.leverage-sync.lock'
$logPath = Join-Path $Root 'logs\auto-sync.log'
New-Item -ItemType Directory -Force -Path (Split-Path $logPath) | Out-Null

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $logPath -Value $line
}

if (Test-Path $lockPath) {
    try {
        $age = (Get-Date) - (Get-Item $lockPath).LastWriteTime
        if ($age.TotalMinutes -lt 10) { return }
        Remove-Item $lockPath -Force
    } catch { return }
}

New-Item -ItemType File -Path $lockPath -Force | Out-Null
try {
    Write-Log 'Auto-sync check started.'

    $status = git status --porcelain
    if ($status) {
        Write-Log 'Local changes detected; sync skipped to protect Owner work.'
        return
    }

    git fetch origin main --quiet
    $local = (git rev-parse HEAD).Trim()
    $remote = (git rev-parse origin/main).Trim()
    if ($local -eq $remote) {
        Write-Log "Already current at $local."
        return
    }

    $changed = @(git diff --name-only $local $remote)
    git merge --ff-only origin/main | Out-Null
    Write-Log "Fast-forwarded $local -> $remote. Changed files: $($changed.Count)."

    $serverChanged = $changed | Where-Object { $_ -like 'server/*' -or $_ -eq 'leverage-server.cmd' -or $_ -like 'control_plane/*' }
    if ($serverChanged) {
        $processes = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$Root\server\leverage_api.py*" })
        foreach ($process in $processes) {
            try { Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop; Write-Log "Stopped old API process $($process.ProcessId)." } catch { Write-Log "Could not stop process $($process.ProcessId): $($_.Exception.Message)" }
        }
        $python = (Get-Command python.exe -ErrorAction Stop).Source
        Start-Process -FilePath $python -ArgumentList '-B','server\leverage_api.py' -WorkingDirectory $Root -WindowStyle Hidden
        Write-Log 'Started updated Leverage Local API.'
    }

    Write-Log 'Auto-sync completed successfully.'
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
}
finally {
    Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
