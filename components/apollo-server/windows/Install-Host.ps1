param([switch]$ClipboardOnly)
. "$PSScriptRoot\Common.ps1"
if (!$ClipboardOnly) {
    if (!(Test-Path 'C:\Program Files\Apollo\sunshine.exe')) {
        $setup=Get-VerifiedAsset 'apolloWindows'
        # Interactive installer: the operator sees driver choices and the elevation prompt.
        Start-Process -FilePath $setup -Wait
        if (!(Test-Path 'C:\Program Files\Apollo\sunshine.exe')) { throw 'Apollo installation not completed.' }
    }
    if (!(Test-Path 'C:\Program Files\Apollo Fleet Launcher\ApolloFleet.App.exe')) {
        $setup=Get-VerifiedAsset 'fleetWindows'
        Start-Process -FilePath $setup -Wait
    }
}
$clipboardInstallation = @(Install-CrossPaste "$env:LOCALAPPDATA\ApolloDesktopKit")[-1]
if($clipboardInstallation.cli){& $clipboardInstallation.cli status}
else{Write-Host 'CrossPaste Store installe. Associez le client dans son interface graphique.'}
Write-Host 'Configure one Fleet instance per client display; then follow docs/windows-host.md.'
