param([string]$InstallRoot = "$env:LOCALAPPDATA\ApolloDesktopKit", [string]$ProfilePath = '', [switch]$PairClipboard, [switch]$SkipFirewall, [switch]$NoShortcut)
. "$PSScriptRoot\Common.ps1"
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
$moonlight = Join-Path $InstallRoot 'Moonlight\Moonlight.exe'
if (!(Test-Path -LiteralPath $moonlight)) {
    # Prefer an existing normal installation, preserving its paired hosts.
    $existing = "$env:ProgramFiles\Moonlight Game Streaming\Moonlight.exe"
    if (Test-Path -LiteralPath $existing) { $moonlight = $existing }
    else { Expand-Archive -LiteralPath (Get-VerifiedAsset 'moonlightWindows') -DestinationPath (Join-Path $InstallRoot 'Moonlight') -Force }
}
$cli=$null
$clipboardInstallation=$null
$clipboardError=Join-Path $InstallRoot 'clipboard-setup-error.txt'
try {
    $clipboardInstallation = @(Install-CrossPaste $InstallRoot)[-1]
    $cli=$clipboardInstallation.cli
    if(Test-Path -LiteralPath $clipboardError){Remove-Item -LiteralPath $clipboardError}
} catch {
    $_.Exception.Message | Set-Content -LiteralPath $clipboardError -Encoding UTF8
    Write-Warning ('Les ecrans restent disponibles. Presse-papiers non configure : '+$_.Exception.Message)
}
if (!$ProfilePath) { $ProfilePath = Join-Path $InstallRoot 'profile.local.json' }
if (!(Test-Path -LiteralPath $ProfilePath)) {
    & "$PSScriptRoot\New-ClientProfile.ps1" -OutFile $ProfilePath
}
$profile = Read-Profile $ProfilePath
$profile | Add-Member -NotePropertyName moonlight -NotePropertyValue $moonlight -Force
$crosspastePath=''
if($clipboardInstallation){$crosspastePath=$clipboardInstallation.exe}
$profile | Add-Member -NotePropertyName crosspaste -NotePropertyValue $crosspastePath -Force
$profile | Add-Member -NotePropertyName clipboard -NotePropertyValue ([bool]$clipboardInstallation) -Force
$profile | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ProfilePath -Encoding UTF8
# Copy only runnable kit files; do not install downloads, credentials, logs or source checkouts.
$kit = Join-Path $InstallRoot 'kit'
New-Item -ItemType Directory -Path $kit -Force | Out-Null
foreach ($folder in @('windows','lib')) { Copy-Item -LiteralPath (Join-Path $KitRoot $folder) -Destination $kit -Recurse -Force }
Copy-Item -LiteralPath (Join-Path $KitRoot 'packages.json') -Destination $kit -Force
if (!$NoShortcut) {
    $link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Apollo - My screens.lnk'))
    $link.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $link.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $kit 'windows\Start-Desktop.ps1') + '" -ProfilePath "' + $ProfilePath + '"'
    $link.WorkingDirectory = $InstallRoot
    $link.Save()
}
if (!$SkipFirewall -and $clipboardInstallation) {
    Write-Host 'Windows may request administrator approval for the LAN-only CrossPaste firewall rules.'
    $firewallArgs='-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $kit 'windows\Allow-ClipboardNetwork.ps1') + '" -CrossPasteExe "' + $crosspastePath + '"'
    try {
        $ruleProcess=Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $firewallArgs -Wait -PassThru
        if ($ruleProcess.ExitCode -ne 0) { Write-Warning 'Firewall setup failed; see docs/clipboard.md.' }
    } catch { Write-Warning 'Firewall setup was not completed; see docs/clipboard.md.' }
}
Write-Host "Installed. Profile: $ProfilePath"
Write-Host 'Pair the Moonlight hosts once if needed. Pair CrossPaste once with the host; subsequent clipboard sync is automatic.'
if ($PairClipboard -and $cli) { & $cli pair }
if ($cli) { & $cli status }
elseif($clipboardInstallation){Write-Host 'CrossPaste Store est installe. Association et preferences dans son interface graphique.'}
