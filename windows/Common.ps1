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
function Get-StoreCrossPaste {
    # Only use a registered Store-signed package. Never trust/import the ZIP's certificate.
    if (!(Get-Command Get-AppxPackage -ErrorAction SilentlyContinue)) { return $null }
    $packages=@(Get-AppxPackage -ErrorAction SilentlyContinue | Where-Object { $_.SignatureKind -eq 'Store' -and $_.Name -match 'CrossPaste' })
    if (!$packages.Count -and (Get-Command Get-StartApps -ErrorAction SilentlyContinue)) {
        $app=Get-StartApps | Where-Object Name -eq 'CrossPaste' | Select-Object -First 1
        if($app){$family=($app.AppID -split '!')[0];$packages=@(Get-AppxPackage | Where-Object { $_.SignatureKind -eq 'Store' -and $_.PackageFamilyName -eq $family })}
    }
    foreach($package in ($packages | Sort-Object Version -Descending)){
        $cli=Join-Path $package.InstallLocation 'app\bin\crosspaste-cli.exe'
        $exe=Join-Path $package.InstallLocation 'bin\CrossPaste.exe'
        # The real Store 2.2.0 package ships the GUI but omits the optional CLI.
        # A missing CLI is not a missing installation.
        if(Test-Path -LiteralPath $exe){
            if(!(Test-Path -LiteralPath $cli)){$cli=$null}
            return [pscustomobject]@{cli=$cli;exe=$exe;source='store'}
        }
    }
    return $null
}
function Get-CrossPasteInstallation([string]$InstallRoot) {
    $store=Get-StoreCrossPaste
    if($store){return $store}
    $cli=Join-Path $InstallRoot 'CrossPaste\app\bin\crosspaste-cli.exe'
    $exe=Join-Path $InstallRoot 'CrossPaste\bin\CrossPaste.exe'
    if((Test-Path -LiteralPath $cli) -and (Test-Path -LiteralPath $exe)){return [pscustomobject]@{cli=$cli;exe=$exe;source='portable'}}
    return $null
}
function Get-CrossPasteCli([string]$InstallRoot) {
    $installation=Get-CrossPasteInstallation $InstallRoot
    if($installation){return $installation.cli}
    return $null
}
function Test-CrossPasteStatus([string]$Cli) {
    # Launch failures (including application-control policy) must not abort the whole installer.
    try { & $Cli status *> $null; return [pscustomobject]@{launched=$true;running=($LASTEXITCODE -eq 0);error=''} }
    catch { return [pscustomobject]@{launched=$false;running=$false;error=$_.Exception.Message} }
}
function Install-CrossPasteStore {
    $store=Get-StoreCrossPaste
    if($store){return $store}
    if(Get-Command winget.exe -ErrorAction SilentlyContinue){
        try { & winget.exe install --id 9P6X7D7DMCCR --source msstore --exact --accept-package-agreements --accept-source-agreements --disable-interactivity | Out-Host }
        catch { Write-Warning 'L installation Store automatique est indisponible. Ouverture de sa page officielle.' }
        $store=Get-StoreCrossPaste
        if($store){return $store}
    }
    # Let Windows/the Store enforce the policy. Do not sideload, unblock, or change security settings.
    Start-Process 'ms-windows-store://pdp/?ProductId=9P6X7D7DMCCR'
    throw 'Installe CrossPaste depuis la page Microsoft Store ouverte, puis relance ce meme fichier. Si le Store refuse aussi, utilise le support Windows ou l administrateur du PC.'
}
function Install-CrossPaste([string]$InstallRoot) {
    $installation=Get-CrossPasteInstallation $InstallRoot
    if($installation){
        if(!$installation.cli -and $installation.source -eq 'store'){
            if(!(Get-Process CrossPaste -ErrorAction SilentlyContinue)){Start-Process -FilePath $installation.exe -WindowStyle Hidden | Out-Null}
            return $installation
        }
        $status=Test-CrossPasteStatus $installation.cli
        if(!$status.launched){
            if($installation.source -eq 'store'){throw ('La version Store de CrossPaste est aussi bloquee. La politique Windows reste inchangee. '+$status.error)}
            Write-Host 'Le programme portable ne peut pas demarrer. Installation de la distribution officielle Microsoft Store.'
            $installation=$null
        }
    }
    if(!$installation){$installation=Install-CrossPasteStore}
    $cli=$installation.cli
    if(!$cli -and $installation.source -eq 'store'){
        if(!(Get-Process CrossPaste -ErrorAction SilentlyContinue)){Start-Process -FilePath $installation.exe -WindowStyle Hidden | Out-Null}
        return $installation
    }
    $status=Test-CrossPasteStatus $cli
    if(!$status.launched){throw ('Windows refuse CrossPaste. Aucun reglage de securite ne sera desactive. '+$status.error)}
    if(!$status.running){Start-Process -FilePath $installation.exe -WindowStyle Hidden | Out-Null}
    $ready = $false
    for ($i=0; $i -lt 40; $i++) {
        $status=Test-CrossPasteStatus $cli
        if(!$status.launched){throw $status.error}
        if ($status.running) { $ready=$true; break }
        Start-Sleep -Milliseconds 500
    }
    if (!$ready) { throw 'CrossPaste did not start. Open its window to inspect the error.' }
    foreach ($setting in @(@('enableEncryptSync','true'),@('pastePrimaryTypeOnly','false'),@('enableAutoStartUp','true'),@('enableSyncText','true'),@('enableSyncHtml','true'),@('enableSyncRtf','true'),@('enableSyncFile','true'),@('enableSyncImage','true'))) {
        & $cli config set $setting[0] $setting[1]
        if ($LASTEXITCODE -ne 0) { throw "CrossPaste setting failed: $($setting[0])" }
    }
    return $installation
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
