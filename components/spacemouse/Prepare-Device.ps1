param([Parameter(Mandatory=$true)][ValidatePattern('^[1-9][0-9]{0,3}-[1-9][0-9]{0,3}$')][string]$BusId)
$ErrorActionPreference='Stop'
try {
    $exe=Join-Path $env:ProgramW6432 'usbipd-win\usbipd.exe'
    $state=& $exe state | ConvertFrom-Json
    if($LASTEXITCODE){throw 'Cannot inspect USB devices'}
    $device=@($state.Devices | Where-Object { $_.BusId -eq $BusId -and $_.InstanceId -match 'VID_256F&PID_C635' })
    if($device.Count -ne 1){throw 'Selected device is not a SpaceMouse Compact'}
    $rule=Get-NetFirewallRule -PolicyStore ActiveStore -Name 'SpaceMouseLink-USB-LocalOnly'
    if($rule.Enabled -ne 'True' -or $rule.Action -ne 'Block'){throw 'Select the USB prerequisite step in Server setup first'}
    Start-Service usbipd
    & $exe bind --busid $BusId
    if($LASTEXITCODE){throw 'USB preparation failed'}
    exit 0
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [Windows.Forms.MessageBox]::Show($_.Exception.Message,'SpaceMouse USB preparation') | Out-Null
    exit 1
}
