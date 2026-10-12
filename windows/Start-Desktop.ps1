param([Parameter(Mandatory=$true)][string]$ProfilePath)
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\moonlight\windows\Start-Desktop.ps1" @PSBoundParameters
