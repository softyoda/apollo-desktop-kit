param([string]$ProfilePath='', [string]$ClipboardTarget='', [string]$OutFile="$PSScriptRoot\..\Apollo-Setup.cmd")
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$buildRoot=Join-Path ([IO.Path]::GetTempPath()) ('apollo-build-'+[guid]::NewGuid())
New-Item -ItemType Directory -Path $buildRoot | Out-Null
foreach($dir in @('windows','lib')){Copy-Item -LiteralPath (Join-Path $root $dir) -Destination $buildRoot -Recurse}
Copy-Item -LiteralPath (Join-Path $root 'packages.json') -Destination $buildRoot
if($ProfilePath){Copy-Item -LiteralPath $ProfilePath -Destination (Join-Path $buildRoot 'seed-profile.json')}
@{clipboardTarget=$ClipboardTarget}|ConvertTo-Json|Set-Content (Join-Path $buildRoot 'setup-options.json') -Encoding UTF8
$zip=Join-Path $buildRoot 'kit.zip'
Compress-Archive -Path (Join-Path $buildRoot 'windows'),(Join-Path $buildRoot 'lib'),(Join-Path $buildRoot '*.json') -DestinationPath $zip
$payload=[Convert]::ToBase64String([IO.File]::ReadAllBytes($zip))
$hash=(Get-FileHash $zip -Algorithm SHA256).Hash
$batch=@'
@echo off
setlocal
set "APOLLO_SETUP_FILE=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=[IO.File]::ReadAllText($env:APOLLO_SETUP_FILE); $m='# APOLLO_'+'POWERSHELL'; & ([scriptblock]::Create($t.Substring($t.IndexOf($m)+$m.Length)))"
exit /b %errorlevel%
# APOLLO_POWERSHELL
'@
$bootstrap=@'
$ErrorActionPreference='Stop'
try {
    $installRoot=Join-Path $env:LOCALAPPDATA 'ApolloDesktopKit'
    $stage=Join-Path $installRoot 'setup-source'
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    $zip=Join-Path $stage 'kit.zip'
    [IO.File]::WriteAllBytes($zip,[Convert]::FromBase64String('__PAYLOAD__'))
    if((Get-FileHash $zip -Algorithm SHA256).Hash -ne '__HASH__'){throw 'Fichier endommage. Telecharge-le a nouveau.'}
    Expand-Archive -LiteralPath $zip -DestinationPath $stage -Force
    Copy-Item -LiteralPath (Join-Path $stage 'setup-options.json') -Destination $installRoot -Force
    & (Join-Path $stage 'windows\Setup-And-Start.ps1') -InstallRoot $installRoot
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Appuie sur Entree pour fermer'
    exit 1
}
'@
$content=$batch+"`r`n"+$bootstrap.Replace('__PAYLOAD__',$payload).Replace('__HASH__',$hash)
[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutFile),$content,(New-Object Text.UTF8Encoding($false)))
Write-Host "Created: $OutFile"
