param([Parameter(Mandatory=$true)][string]$ProfilePath,[Parameter(Mandatory=$true)][hashtable]$DisplayMap,[Parameter(Mandatory=$true)][string]$AnchorHost,[ValidateSet('Horizontal','Vertical')][string]$Layout='Horizontal',[switch]$Apply)
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\apollo-server\windows\Align-HostScreens.ps1" @PSBoundParameters
