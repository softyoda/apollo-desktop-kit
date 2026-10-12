param([string]$InstallRoot="$env:LOCALAPPDATA\ApolloDesktopKit",[switch]$ResetSetup)
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\moonlight\windows\Setup-And-Start.ps1" @PSBoundParameters
