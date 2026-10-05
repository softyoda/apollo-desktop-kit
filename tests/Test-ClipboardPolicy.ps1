$ErrorActionPreference='Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'windows\Common.ps1')
$testRoot=Join-Path ([IO.Path]::GetTempPath()) ('clipboard-test-'+[guid]::NewGuid())
New-Item -ItemType Directory -Path $testRoot | Out-Null
$blocked=Join-Path $testRoot 'blocked.ps1'
$storeCli=Join-Path $testRoot 'store-cli.ps1'
Set-Content -LiteralPath $blocked -Value "throw 'Application control policy blocked execution'"
Set-Content -LiteralPath $storeCli -Value '$global:LASTEXITCODE=0'
try {
    $status=Test-CrossPasteStatus $blocked
    if($status.launched -or $status.running -or !$status.error){throw 'Launch rejection must become a diagnostic result.'}
    $script:storeCalls=0
    function Get-CrossPasteInstallation([string]$InstallRoot){return [pscustomobject]@{source='portable';cli=$blocked;exe='blocked.exe'}}
    function Install-CrossPasteStore {$script:storeCalls++;return [pscustomobject]@{source='store';cli=$storeCli;exe='store.exe'}}
    $result=@(Install-CrossPaste $testRoot)[-1]
    if($result -ne $storeCli -or $script:storeCalls -ne 1){throw 'A rejected portable install must select the official Store distribution.'}
    function Get-CrossPasteInstallation([string]$InstallRoot){return [pscustomobject]@{source='store';cli=$blocked;exe='blocked.exe'}}
    $rejected=$false
    try {Install-CrossPaste $testRoot|Out-Null}catch{$rejected=$true}
    if(!$rejected -or $script:storeCalls -ne 1){throw 'A rejected Store app must stop clipboard setup, not evade the policy.'}
    Write-Host 'PASS: blocked launch handling, Store selection and no retry past Store policy refusal.'
} finally {
    Remove-Item -LiteralPath $blocked,$storeCli -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $testRoot -ErrorAction SilentlyContinue
}
