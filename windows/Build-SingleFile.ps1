param([string]$ProfilePath='', [string]$ClipboardTarget='', [string]$OutFile="$PSScriptRoot\..\Apollo-Setup.cmd")
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\moonlight\windows\Build-SingleFile.ps1" @PSBoundParameters
