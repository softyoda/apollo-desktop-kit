param([string]$InstallRoot = "$env:LOCALAPPDATA\ApolloDesktopKit", [string]$ProfilePath = '', [switch]$PairClipboard, [switch]$SkipFirewall, [switch]$NoShortcut)
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\moonlight\windows\Install-Client.ps1" @PSBoundParameters
