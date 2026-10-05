$ErrorActionPreference='Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'windows\Common.ps1')
$fixture=Join-Path ([IO.Path]::GetTempPath()) ('crosspaste-store-test-'+[guid]::NewGuid())
New-Item -ItemType Directory -Path (Join-Path $fixture 'bin'),(Join-Path $fixture 'app\bin') -Force | Out-Null
$exe=Join-Path $fixture 'bin\CrossPaste.exe'
$cli=Join-Path $fixture 'app\bin\crosspaste-cli.exe'
New-Item -ItemType File -Path $exe | Out-Null
$script:package=[pscustomobject]@{Name='ShenzhenCompileFutureTech.CrossPaste';SignatureKind='Store';Version=[version]'2.2.0.0';InstallLocation=$fixture;PackageFamilyName='CrossPaste_test'}
function Get-AppxPackage {return $script:package}
function Get-StartApps {return [pscustomobject]@{Name='CrossPaste';AppID='CrossPaste_test!Crosspaste'}}
try {
    $guiOnly=Get-StoreCrossPaste
    if(!$guiOnly -or $guiOnly.cli -or $guiOnly.exe -ne $exe){throw 'Store GUI without CLI must be detected as installed.'}
    New-Item -ItemType File -Path $cli | Out-Null
    $withCli=Get-StoreCrossPaste
    if($withCli.cli -ne $cli){throw 'Optional Store CLI should be detected when present.'}
    $script:package.Name='Publisher.NumericIdentity'
    if(!(Get-StoreCrossPaste)){throw 'Start menu identity fallback should detect registered package.'}
    $script:package.SignatureKind='Developer'
    if(Get-StoreCrossPaste){throw 'Untrusted/sideloaded package must not be treated as Store-signed.'}
    Write-Host 'PASS: actual Store 2.2 layout (GUI-only), optional CLI and package identity/signature checks.'
} finally {
    Remove-Item -LiteralPath $exe,$cli -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $fixture 'app\bin'),(Join-Path $fixture 'app'),(Join-Path $fixture 'bin'),$fixture -ErrorAction SilentlyContinue
}
