param(
    [Parameter(Mandatory=$true)][string]$Root,
    [Parameter(Mandatory=$true)][string]$Runner
)

$ErrorActionPreference = 'Stop'
$TaskName = 'Leverage Auto Sync'
$Root = (Resolve-Path $Root).Path
$Runner = (Resolve-Path $Runner).Path

$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "{0}"' -f $Runner) -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType InteractiveToken -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$info = Get-ScheduledTaskInfo -TaskName $TaskName
if ($info.LastTaskResult -ne 0) {
    $log = Join-Path $Root 'logs\auto-sync.log'
    if (Test-Path $log) {
        Write-Host (Get-Content $log -Tail 20 | Out-String)
    }
    throw "Leverage Auto Sync test run failed with result $($info.LastTaskResult)."
}

Write-Host "Leverage Auto Sync registered and test run succeeded."
Write-Host "Next run: $($info.NextRunTime)"
