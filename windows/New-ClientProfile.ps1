param([string[]]$Hosts = @(), [double]$RenderScale = 1.0, [string]$OutFile = "$PSScriptRoot\..\profile.local.json")
# Compatibility entry point; implementation lives in its component.
& "$PSScriptRoot\..\components\moonlight\windows\New-ClientProfile.ps1" @PSBoundParameters
