param([ValidateSet('server','client')][string]$Role,[Parameter(Mandatory=$true)][string]$InstallerPath)
$ErrorActionPreference='Stop'
try {
    $expected=if($Role -eq 'server'){'1c984914aec944de19b64eff232421439629699f8138e3ddc29301175bc6d938'}else{'38cad6d4432b52d5bb9409d9ad03b72fdffc4ada4cd3a48fbeca1a2752a8518a'}
    if((Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).Hash -ne $expected){throw 'Driver checksum mismatch'}
    if((Get-AuthenticodeSignature -LiteralPath $InstallerPath).Status -ne 'Valid'){throw 'Driver publisher signature is invalid'}
    if($Role -eq 'server') {
        if(@(Get-NetFirewallProfile -PolicyStore ActiveStore | Where-Object { -not $_.Enabled -or $_.AllowLocalFirewallRules -eq 'False' }).Count){throw 'Windows Firewall and local firewall rules must be enabled'}
        $name='SpaceMouseLink-USB-LocalOnly'
        $ranges=@('0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255','::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')
        if(Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue){Remove-NetFirewallRule -Name $name}
        New-NetFirewallRule -Name $name -DisplayName 'SpaceMouse Link - block non-local USB access' -Direction Inbound -Action Block -Protocol TCP -LocalPort 3240 -RemoteAddress $ranges -Profile Any | Out-Null
        if(-not (Test-Path -LiteralPath (Join-Path $env:ProgramW6432 'usbipd-win\usbipd.exe'))) {
            $p=Start-Process msiexec.exe -ArgumentList ('/i "'+$InstallerPath+'" /qn /norestart REBOOT=ReallySuppress') -Wait -PassThru -WindowStyle Hidden
            if($p.ExitCode -notin @(0,3010)){throw "USB driver installer failed: $($p.ExitCode)"}
        }
        Get-NetFirewallRule -Name usbipd -ErrorAction SilentlyContinue | Disable-NetFirewallRule
        Set-Service usbipd -StartupType Automatic
        Start-Service usbipd
    } elseif(-not (Test-Path -LiteralPath (Join-Path $env:ProgramW6432 'USBip\usbip.exe'))) {
        $p=Start-Process -FilePath $InstallerPath -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCLOSEAPPLICATIONS /SP- /COMPONENTS="main,client" /TASKS=""' -Wait -PassThru -WindowStyle Hidden
        if($p.ExitCode -notin @(0,3010)){throw "USB virtual driver installer failed: $($p.ExitCode)"}
    }
    exit 0
} catch { Write-Error $_.Exception.Message; exit 1 }
