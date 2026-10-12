param([Parameter(Mandatory=$true)][string]$CrossPasteExe, [string[]]$RemoteAddress = @('LocalSubnet'))
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\clipboard\windows\Allow-ClipboardNetwork.ps1" @PSBoundParameters
