param([string]$InstallRoot="$env:LOCALAPPDATA\ApolloDesktopKit",[switch]$ResetSetup)
$ErrorActionPreference='Stop'
$kitSource=Split-Path $PSScriptRoot -Parent
$profilePath=Join-Path $InstallRoot 'profile.local.json'
$stamp=Join-Path $InstallRoot 'setup-version.txt'
$version='0.2.3'
. "$PSScriptRoot\ClientLifecycle.ps1"
try {
    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
    if (!$ResetSetup -and (Test-ClientReady $profilePath)) {
        # A newer launcher updates its own scripts, never reinstalls dependencies or firewall rules.
        Update-ClientKit $kitSource $InstallRoot
        Set-DailyShortcut $InstallRoot $profilePath
        Write-Host 'Connexion aux ecrans...'
        & (Join-Path $InstallRoot 'kit\windows\Start-Desktop.ps1') -ProfilePath $profilePath
        return
    }
    $settingsPath=Join-Path $InstallRoot 'setup-options.json'
    $options=@{}
    if(Test-Path -LiteralPath $settingsPath){$options=Get-Content -LiteralPath $settingsPath -Raw|ConvertFrom-Json}
    $needsSetup=$true # No usable local profile/Moonlight, or an explicit repair request.
    if($needsSetup){
        Write-Host 'Apollo - preparation automatique du portable' -ForegroundColor Cyan
        if(!(Test-Path -LiteralPath $profilePath)){
            $seed=Join-Path $kitSource 'seed-profile.json'
            if(Test-Path -LiteralPath $seed){Copy-Item -LiteralPath $seed -Destination $profilePath}
            else {
                & "$PSScriptRoot\New-ClientProfile.ps1" -OutFile $profilePath
                $data=Get-Content -LiteralPath $profilePath -Raw|ConvertFrom-Json
                foreach($screen in $data.streams){
                    $name=Read-Host "Nom de l'hote Moonlight pour $($screen.monitor) ($($screen.width)x$($screen.height))"
                    if(!$name){throw 'Un nom Moonlight est necessaire pour chaque ecran.'}
                    $screen.host=$name
                }
                $data|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $profilePath -Encoding UTF8
            }
        }
        Write-Host 'Installation de Moonlight et du presse-papiers. Les premiers telechargements peuvent prendre quelques minutes.'
        $setupLog=Join-Path $InstallRoot 'installation.log'
        & "$PSScriptRoot\Install-Client.ps1" -InstallRoot $InstallRoot -ProfilePath $profilePath -NoShortcut *> $setupLog
        if(!$?){throw "Installation incomplete. Voir $setupLog"}
        Set-Content -LiteralPath $stamp -Value $version
    }
    . "$PSScriptRoot\Common.ps1"
    $streamsStarted=$false
    $clipboardFailure=''
    $clipboardGui=$false
    try {
    $currentProfile=Get-Content -LiteralPath $profilePath -Raw|ConvertFrom-Json
    if(!$currentProfile.clipboard){
        $errorPath=Join-Path $InstallRoot 'clipboard-setup-error.txt'
        if(Test-Path -LiteralPath $errorPath){throw (Get-Content -LiteralPath $errorPath -Raw)}
        throw 'CrossPaste reste a installer depuis le Microsoft Store.'
    }
    $clipboardInstallation=Get-CrossPasteInstallation $InstallRoot
    $cli=$clipboardInstallation.cli
    if(!$cli -and $clipboardInstallation.source -eq 'store'){
        $clipboardGui=$true
    } else {
    if(!$cli){throw 'CrossPaste manque. Relancer avec -ResetSetup.'}
    $status=Test-CrossPasteStatus $cli
    if(!$status.launched){throw $status.error}
    if(!$status.running){
        Start-Process -FilePath (Get-CrossPasteInstallation $InstallRoot).exe -WindowStyle Hidden
        for($i=0;$i -lt 40;$i++){
            Start-Sleep -Milliseconds 500
            $status=Test-CrossPasteStatus $cli
            if(!$status.launched){throw $status.error}
            if($status.running){break}
        }
    }
    $raw=& $cli --json devices
    if($LASTEXITCODE -ne 0){throw 'CrossPaste ne repond pas.'}
    $devices=@($raw|ConvertFrom-Json)
    if($options.clipboardTarget){$devices=@($devices|Where-Object appInstanceId -eq $options.clipboardTarget)}
    $paired=@($devices|Where-Object { $_.allowSend -and $_.allowReceive -and $_.connectState -ne 4 })
    if(!$paired.Count){
        # Open the host desktop first so its pairing popup can be read without TeamViewer.
        Write-Host 'Ouverture des ecrans pour afficher le code du PC hote...'
        & (Join-Path $InstallRoot 'kit\windows\Start-Desktop.ps1') -ProfilePath $profilePath
        $streamsStarted=$true
        $shell=New-Object -ComObject WScript.Shell
        [void]$shell.AppActivate($PID)
        Write-Host 'Une seule association du presse-papiers est necessaire.' -ForegroundColor Cyan
        Write-Host 'Lis le code dans le bureau distant ouvert a droite, puis saisis-le dans cette fenetre.'
        if($options.clipboardTarget){& $cli pair --target $options.clipboardTarget}else{& $cli pair}
        if($LASTEXITCODE -ne 0){throw 'Association non terminee. Relance ce meme fichier pour reprendre.'}
        $raw=& $cli --json devices
        if($LASTEXITCODE -ne 0){throw 'Impossible de verifier l association.'}
        $devices=@($raw|ConvertFrom-Json)
        if($options.clipboardTarget){$devices=@($devices|Where-Object appInstanceId -eq $options.clipboardTarget)}
        if(!@($devices|Where-Object { $_.allowSend -and $_.allowReceive -and $_.connectState -ne 4 }).Count){throw 'Autoriser envoi et reception dans CrossPaste puis relancer.'}
    }
    }
    } catch {
        $clipboardFailure=$_.Exception.Message
        # Do not repeatedly launch a blocked binary from the normal screen launcher.
        $currentProfile=Get-Content -LiteralPath $profilePath -Raw|ConvertFrom-Json
        $currentProfile.clipboard=$false
        $currentProfile|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $profilePath -Encoding UTF8
    }
    Set-DailyShortcut $InstallRoot $profilePath
    if(!$clipboardFailure -and !$clipboardGui){Write-Host 'Presse-papiers associe. Le raccourci Apollo - Mes ecrans est pret.'}
    if(!$streamsStarted){& (Join-Path $InstallRoot 'kit\windows\Start-Desktop.ps1') -ProfilePath $profilePath}
    if($clipboardGui){
        $intro=Join-Path $InstallRoot 'clipboard-gui-intro-shown.txt'
        if(!(Test-Path -LiteralPath $intro)){
            # This is an interactive one-time pairing window, intentionally visible.
            Start-Process -FilePath $clipboardInstallation.exe
            Write-Host 'CrossPaste est installe et ouvert. Une seule fois :' -ForegroundColor Cyan
            Write-Host '1. Dans Appareils / Devices, ajoute le PC hote et saisis le code affiche sur son ecran.'
            Write-Host '2. Dans Parametres, active la synchronisation chiffree et desactive Paste only main type pour conserver les formats enrichis.'
            Write-Host 'Le kit ne peut pas verifier automatiquement cette association car cette version Store ne contient pas la CLI.'
            Read-Host 'Appuie sur Entree pour fermer cet assistant. Le raccourci Apollo - Mes ecrans servira ensuite chaque jour'
            'Instructions shown; pairing is not programmatically verified.'|Set-Content -LiteralPath $intro
        } else {Write-Host 'CrossPaste est lance. L association se gere dans son interface.'}
    }
    if($clipboardFailure){
        Write-Host ('Les ecrans sont lances, mais le presse-papiers n est PAS synchronise : '+$clipboardFailure) -ForegroundColor Yellow
        Read-Host 'Apres installation/autorisation de CrossPaste dans le Store, relance ce meme fichier. Entree pour fermer'
    }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Appuie sur Entree pour fermer. Tu peux relancer le meme fichier pour reprendre'
    exit 1
}
