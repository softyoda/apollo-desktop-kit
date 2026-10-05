param(
    [ValidateSet('Apply','Restore','Probe')][string]$Action='Probe',
    [string]$Display='\\.\DISPLAY1', [uint32]$Width=3200, [uint32]$Height=1350, [uint32]$Fps=60,
    [string]$StateDirectory="$env:ProgramData\ApolloDesktopKit\runtime",
    [switch]$AllowNvidiaCustomMode
)
$ErrorActionPreference='Stop'
$KitRoot=Split-Path $PSScriptRoot -Parent
Add-Type -Path (Join-Path $KitRoot 'lib\DisplayControl.cs')
if ($Action -eq 'Probe') { [DisplayControl]::Current($Display) | Select-Object width,height,freq; exit }
New-Item -ItemType Directory -Path $StateDirectory -Force | Out-Null
$statePath=Join-Path $StateDirectory (($Display -replace '[^a-zA-Z0-9]','') + '-previous.json')
try {
    if ($Action -eq 'Apply') {
        if (!(Test-Path -LiteralPath $statePath)) {
            [DisplayControl]::Current($Display) | Select-Object width,height,freq | ConvertTo-Json | Set-Content -LiteralPath $statePath
        }
        if ($AllowNvidiaCustomMode) { [DisplayControl]::EnsureCustom($Display,$Width,$Height,$Fps) }
        elseif (![DisplayControl]::HasMode($Display,$Width,$Height,$Fps)) { throw 'Mode unavailable. Create it in your GPU panel or explicitly allow NVIDIA custom modes.' }
        [DisplayControl]::Set($Display,$Width,$Height,$Fps)
        $current=[DisplayControl]::Current($Display)
        if ($current.width -ne $Width -or $current.height -ne $Height) { throw 'Applied resolution could not be verified.' }
    } elseif (Test-Path -LiteralPath $statePath) {
        $old=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        [DisplayControl]::Set($Display,$old.width,$old.height,$old.freq)
        Remove-Item -LiteralPath $statePath
    }
} catch {
    if ($Action -eq 'Apply' -and (Test-Path -LiteralPath $statePath)) {
        $old=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        [DisplayControl]::Set($Display,$old.width,$old.height,$old.freq)
        Remove-Item -LiteralPath $statePath
    }
    throw
}
