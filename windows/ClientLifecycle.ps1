function Test-ClientReady([string]$ProfilePath) {
    # Local installation only: host/network/clipboard availability is not installation state.
    if (!(Test-Path -LiteralPath $ProfilePath)) { return $false }
    try {
        $clientProfile=Get-Content -LiteralPath $ProfilePath -Raw | ConvertFrom-Json
        return [bool]($clientProfile.version -eq 1 -and $clientProfile.streams -and @($clientProfile.streams).Count -gt 0 -and
            $clientProfile.moonlight -and (Test-Path -LiteralPath $clientProfile.moonlight))
    } catch { return $false }
}
function Update-ClientKit([string]$SourceRoot,[string]$InstallRoot) {
    $destination=Join-Path $InstallRoot 'kit'
    if ([IO.Path]::GetFullPath($SourceRoot).TrimEnd('\') -eq [IO.Path]::GetFullPath($destination).TrimEnd('\')) { return }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    foreach($folder in @('windows','lib')) { Copy-Item -LiteralPath (Join-Path $SourceRoot $folder) -Destination $destination -Recurse -Force }
    Copy-Item -LiteralPath (Join-Path $SourceRoot 'packages.json') -Destination $destination -Force
}
function Set-DailyShortcut([string]$InstallRoot,[string]$ProfilePath) {
    $entry=Join-Path $InstallRoot 'kit\windows\Start-Desktop.ps1'
    $link=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Apollo - Mes ecrans.lnk'))
    $link.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $link.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$entry+'" -ProfilePath "'+$ProfilePath+'"'
    $link.WorkingDirectory=$InstallRoot
    $link.Save()
}
