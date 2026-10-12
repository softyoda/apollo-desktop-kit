param(
    [ValidateSet('Apply','Restore','Probe')][string]$Action='Probe',
    [string]$Display='\\.\DISPLAY1', [uint32]$Width=3200, [uint32]$Height=1350, [uint32]$Fps=60,
    [string]$StateDirectory="$env:ProgramData\ApolloDesktopKit\runtime",
    [switch]$AllowNvidiaCustomMode
)
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\apollo-server\windows\Set-StreamResolution.ps1" @PSBoundParameters
