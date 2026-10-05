param([Parameter(Mandatory=$true)][string]$ProfilePath,[Parameter(Mandatory=$true)][hashtable]$DisplayMap,[Parameter(Mandatory=$true)][string]$AnchorHost,[ValidateSet('Horizontal','Vertical')][string]$Layout='Horizontal',[switch]$Apply)
. "$PSScriptRoot\Common.ps1"
. "$PSScriptRoot\Layout.ps1"
Add-Type -Path (Join-Path $KitRoot 'lib\DisplayControl.cs')
$profile=Read-Profile $ProfilePath
$positions=@(Get-HostPositions $profile $AnchorHost $Layout)
$snapshot=@()
foreach($p in $positions) {
    $name=$DisplayMap[$p.host]
    if(!$name){throw "Missing display mapping for $($p.host)"}
    $m=[DisplayControl]::Current($name)
    if($m.width -ne $p.width -or $m.height -ne $p.height){throw "Start all streams first. $($p.host) is $($m.width)x$($m.height), expected $($p.width)x$($p.height)."}
    $snapshot += [pscustomobject]@{display=$name;x=$m.x;y=$m.y}
}
if (@($DisplayMap.Values | Select-Object -Unique).Count -ne $DisplayMap.Count) { throw 'Two hosts map to the same display.' }
$positions | Format-Table host,x,y,width,height
if(!$Apply){Write-Host 'Preview only. Add -Apply to save the layout.';exit}
$backup=Join-Path (Split-Path (Resolve-Path $ProfilePath) -Parent) ('layout-before-'+(Get-Date -Format 'yyyyMMddHHmmss')+'.json')
$snapshot | ConvertTo-Json | Set-Content -LiteralPath $backup
try {
    foreach($p in $positions){[DisplayControl]::Move($DisplayMap[$p.host],$p.x,$p.y)}
    [DisplayControl]::Commit()
} catch {
    foreach($p in $snapshot){[DisplayControl]::Move($p.display,$p.x,$p.y)}
    [DisplayControl]::Commit()
    throw
}
Write-Host "Layout applied; original positions: $backup"
