param([string[]]$Hosts = @(), [double]$RenderScale = 1.0, [string]$OutFile = "$PSScriptRoot\..\profile.local.json")
. "$PSScriptRoot\Common.ps1"
Initialize-Native
if ($RenderScale -lt 0.5 -or $RenderScale -gt 2) { throw 'RenderScale must be in [0.5,2].' }
$screens = @([System.Windows.Forms.Screen]::AllScreens | Sort-Object { $_.Bounds.Left },{ $_.Bounds.Top })
if ($Hosts.Count -and $Hosts.Count -ne $screens.Count) { throw 'Provide one host per monitor, ordered left-to-right/top-to-bottom.' }
$streams = @()
for ($i=0; $i -lt $screens.Count; $i++) {
    $s=$screens[$i]; $b=$s.Bounds
    $streamHost = if ($Hosts.Count) { $Hosts[$i] } else { 'Screen' + ($i+1) }
    $streams += [ordered]@{ host=$streamHost; app='Desktop'; monitor=$s.DeviceName; mode='borderless'; width=2*[int][Math]::Floor($b.Width*$RenderScale/2); height=2*[int][Math]::Floor($b.Height*$RenderScale/2); fps=60; renderScale=$RenderScale; clientBounds=@{x=$b.X;y=$b.Y;width=$b.Width;height=$b.Height}; clientPrimary=$s.Primary }
}
@{ version=1; streams=$streams; clipboard=$true } | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Profile written: $OutFile. Edit host names to match Moonlight paired hosts."
