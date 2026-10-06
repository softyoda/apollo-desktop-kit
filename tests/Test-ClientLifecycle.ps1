$ErrorActionPreference='Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'windows\ClientLifecycle.ps1')
$root=Join-Path ([IO.Path]::GetTempPath()) ('client-lifecycle-'+[guid]::NewGuid())
New-Item -ItemType Directory -Path $root | Out-Null
$exe=Join-Path $root 'Moonlight.exe'
$profilePath=Join-Path $root 'profile.json'
try {
    if(Test-ClientReady $profilePath){throw 'Missing profile must require installation.'}
    New-Item -ItemType File -Path $exe | Out-Null
    @{version=1;moonlight=$exe;clipboard=$false;streams=@(@{host='offline-host';app='Desktop'})}|ConvertTo-Json -Depth 5|Set-Content $profilePath
    if(!(Test-ClientReady $profilePath)){throw 'Offline host, disabled clipboard and absent version stamp must not reinstall.'}
    'old-version'|Set-Content (Join-Path $root 'setup-version.txt')
    'clipboard failed'|Set-Content (Join-Path $root 'clipboard-setup-error.txt')
    if(!(Test-ClientReady $profilePath)){throw 'Old stamp and clipboard error must not reinstall.'}
    Remove-Item -LiteralPath $exe
    if(Test-ClientReady $profilePath){throw 'Missing Moonlight must require repair.'}
    '{broken'|Set-Content $profilePath
    if(Test-ClientReady $profilePath){throw 'Invalid JSON must require repair.'}
    Write-Host 'PASS: local installation readiness independent of host, clipboard, or version marker.'
} finally {
    Get-ChildItem -LiteralPath $root -File | ForEach-Object { Remove-Item -LiteralPath $_.FullName }
    Remove-Item -LiteralPath $root
}
