param([Parameter(Mandatory=$true)][string]$InstanceName,[string]$Display='\\.\DISPLAY1',[int]$Width=3200,[int]$Height=1350,[int]$Fps=60,[switch]$AllowNvidiaCustomMode)
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\apollo-server\windows\Add-ResolutionHook.ps1" @PSBoundParameters
