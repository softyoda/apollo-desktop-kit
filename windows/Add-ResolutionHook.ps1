param([Parameter(Mandatory=$true)][string]$InstanceName,[string]$Display='\\.\DISPLAY1',[int]$Width=3200,[int]$Height=1350,[int]$Fps=60,[switch]$AllowNvidiaCustomMode)
. "$PSScriptRoot\Common.ps1"
$settings=Get-Content "$env:ProgramData\ApolloFleet\settings.json" -Raw | ConvertFrom-Json
$instances=@($settings.instances | Where-Object name -eq $InstanceName)
if ($instances.Count -ne 1) { throw 'Expected one matching Fleet instance.' }
$target="$env:ProgramData\ApolloDesktopKit"
New-Item -ItemType Directory -Path $target -Force | Out-Null
foreach ($dir in @('windows','lib')) { Copy-Item -LiteralPath (Join-Path $KitRoot $dir) -Destination $target -Recurse -Force }
$appsPath=Join-Path $settings.paths.fleetConfigDirectory $instances[0].appsFileName
$apps=Get-Content -LiteralPath $appsPath -Raw | ConvertFrom-Json
$desktop=@($apps.apps | Where-Object name -eq 'Desktop')
if ($desktop.Count -ne 1) { throw 'Expected one Desktop application.' }
if ($Display -notmatch '^\\\\\.\\DISPLAY\d+$') { throw 'Invalid Windows display name.' }
if ($Width -lt 320 -or $Width -gt 16384 -or $Height -lt 200 -or $Height -gt 16384 -or $Width%2 -or $Height%2 -or $Fps -lt 10 -or $Fps -gt 240) { throw 'Invalid resolution/FPS.' }
Copy-Item -LiteralPath $appsPath -Destination ($appsPath + '.before-resolution-hook-' + (Get-Date -Format 'yyyyMMddHHmmss'))
$command='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + (Join-Path $target 'windows\Set-StreamResolution.ps1') + '" -Display "' + $Display + '"'
$custom=if($AllowNvidiaCustomMode){' -AllowNvidiaCustomMode'}else{''}
$hook=@{do=$command+" -Action Apply -Width $Width -Height $Height -Fps $Fps"+$custom;undo=$command+' -Action Restore';elevated=$true}
$existing=@($desktop[0].'prep-cmd' | Where-Object { $_ -and $_.do -notlike '*Set-StreamResolution.ps1*' })
$desktop[0] | Add-Member -NotePropertyName 'prep-cmd' -NotePropertyValue @($existing+$hook) -Force
[IO.File]::WriteAllText($appsPath,($apps|ConvertTo-Json -Depth 30),(New-Object Text.UTF8Encoding($false)))
Write-Host 'Hook installed. Restart this Apollo instance from its web Troubleshooting page or Fleet to load it.'
