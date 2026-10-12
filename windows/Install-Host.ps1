param([switch]$ClipboardOnly)
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\apollo-server\windows\Install-Host.ps1" @PSBoundParameters
