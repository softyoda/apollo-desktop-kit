$ErrorActionPreference = 'Stop'
$KitRoot = Split-Path $PSScriptRoot -Parent
function Initialize-Native {
    if (!('MoonlightWindows' -as [type])) { Add-Type -Path (Join-Path $KitRoot 'lib\MoonlightWindows.cs') }
    Add-Type -AssemblyName System.Windows.Forms
    [void][MoonlightWindows]::SetThreadDpiAwarenessContext([IntPtr](-4))
}
function Get-VerifiedAsset([string]$Package) {
    $manifest = Get-Content (Join-Path $KitRoot 'packages.json') -Raw | ConvertFrom-Json
    $asset = $manifest.$Package
    if (!$asset -or $asset.sha256 -notmatch '^[a-fA-F0-9]{64}$') { throw "Unknown/unpinned package $Package" }
    $cache = Join-Path $KitRoot 'downloads'
    New-Item -ItemType Directory -Path $cache -Force | Out-Null
    $path = Join-Path $cache $asset.file
    if (!(Test-Path -LiteralPath $path) -or (Get-FileHash $path -Algorithm SHA256).Hash -ne $asset.sha256) {
        Invoke-WebRequest -UseBasicParsing $asset.url -OutFile $path
    }
    if ((Get-FileHash $path -Algorithm SHA256).Hash -ne $asset.sha256) { throw "SHA256 mismatch: $Package" }
    return $path
}
function Get-CrossPasteCli([string]$InstallRoot) {
    $candidates = @((Join-Path $InstallRoot 'CrossPaste\app\bin\crosspaste-cli.exe'))
    return $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
function Install-CrossPaste([string]$InstallRoot) {
    $exe = Join-Path $InstallRoot 'CrossPaste\bin\CrossPaste.exe'
    if (!(Test-Path -LiteralPath $exe)) {
        $zip = Get-VerifiedAsset 'crosspasteWindows'
        Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $InstallRoot 'CrossPaste') -Force
    }
    $cli = Get-CrossPasteCli $InstallRoot
    & $cli status *> $null
    if ($LASTEXITCODE -ne 0) { Start-Process -FilePath $exe -WindowStyle Hidden | Out-Null }
    $ready = $false
    for ($i=0; $i -lt 40; $i++) {
        & $cli status *> $null
        if ($LASTEXITCODE -eq 0) { $ready=$true; break }
        Start-Sleep -Milliseconds 500
    }
    if (!$ready) { throw 'CrossPaste did not start. Open its window to inspect the error.' }
    foreach ($setting in @(@('enableEncryptSync','true'),@('pastePrimaryTypeOnly','false'),@('enableAutoStartUp','true'),@('enableSyncText','true'),@('enableSyncHtml','true'),@('enableSyncRtf','true'),@('enableSyncFile','true'),@('enableSyncImage','true'))) {
        & $cli config set $setting[0] $setting[1]
        if ($LASTEXITCODE -ne 0) { throw "CrossPaste setting failed: $($setting[0])" }
    }
    return $cli
}
function Read-Profile([string]$Path) {
    $profile = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if ($profile.version -ne 1 -or @($profile.streams).Count -eq 0) { throw 'Profile needs version=1 and at least one stream.' }
    $seen = @{}
    foreach ($stream in $profile.streams) {
        if (!$stream.host -or $stream.host -match '["\r\n]' -or !$stream.app -or $stream.app -match '["\r\n]') { throw 'Invalid host/app.' }
        if ($seen.ContainsKey($stream.host)) { throw 'Use distinct Apollo hosts for each stream.' }; $seen[$stream.host]=$true
        if ($stream.mode -notin @('windowed','borderless')) { throw 'mode must be windowed or borderless.' }
        if ($stream.width -lt 320 -or $stream.width -gt 16384 -or $stream.height -lt 200 -or $stream.height -gt 16384 -or $stream.width % 2 -or $stream.height % 2) { throw 'Stream dimensions must be even, between 320x200 and 16384x16384.' }
        if ($stream.fps -lt 10 -or $stream.fps -gt 240) { throw 'FPS must be between 10 and 240.' }
    }
    return $profile
}
