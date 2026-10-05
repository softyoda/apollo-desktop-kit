param([string]$InstallRoot="$env:LOCALAPPDATA\ApolloDesktopKit",[switch]$ResetSetup)
$ErrorActionPreference='Stop'
$kitSource=Split-Path $PSScriptRoot -Parent
$profilePath=Join-Path $InstallRoot 'profile.local.json'
$stamp=Join-Path $InstallRoot 'setup-version.txt'
$version='0.2.0'
try {
    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
    $settingsPath=Join-Path $InstallRoot 'setup-options.json'
    $options=@{}
    if(Test-Path -LiteralPath $settingsPath){$options=Get-Content -LiteralPath $settingsPath -Raw|ConvertFrom-Json}
    $needsSetup=$ResetSetup -or !(Test-Path -LiteralPath $stamp)
    if(!$needsSetup){$needsSetup=(Get-Content -LiteralPath $stamp -Raw).Trim() -ne $version}
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
    $cli=Get-CrossPasteCli $InstallRoot
    if(!$cli){throw 'CrossPaste manque. Relancer avec -ResetSetup.'}
    & $cli status *> $null
    if($LASTEXITCODE -ne 0){
        Start-Process -FilePath (Join-Path $InstallRoot 'CrossPaste\bin\CrossPaste.exe') -WindowStyle Hidden
        for($i=0;$i -lt 40;$i++){
            Start-Sleep -Milliseconds 500
            & $cli status *> $null
            if($LASTEXITCODE -eq 0){break}
        }
    }
    $raw=& $cli --json devices
    if($LASTEXITCODE -ne 0){throw 'CrossPaste ne repond pas.'}
    $devices=@($raw|ConvertFrom-Json)
    if($options.clipboardTarget){$devices=@($devices|Where-Object appInstanceId -eq $options.clipboardTarget)}
    $paired=@($devices|Where-Object { $_.allowSend -and $_.allowReceive -and $_.connectState -ne 4 })
    $streamsStarted=$false
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
    # The desktop entry reuses this exact setup/launch flow, including pairing retries.
    $entry=Join-Path $InstallRoot 'kit\windows\Setup-And-Start.ps1'
    $link=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Apollo - Mes ecrans.lnk'))
    $link.TargetPath="$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $link.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$entry+'"'
    $link.WorkingDirectory=$InstallRoot
    $link.Save()
    Write-Host 'Presse-papiers associe. Le raccourci Apollo - Mes ecrans est pret.'
    if(!$streamsStarted){& (Join-Path $InstallRoot 'kit\windows\Start-Desktop.ps1') -ProfilePath $profilePath}
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Appuie sur Entree pour fermer. Tu peux relancer le meme fichier pour reprendre'
    exit 1
}
