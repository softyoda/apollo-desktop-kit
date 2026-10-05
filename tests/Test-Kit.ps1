$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$failures=@()
Get-ChildItem $root -Filter *.ps1 -Recurse | ForEach-Object {
    $tokens=$null;$errors=$null
    [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors)
    $failures += $errors
}
if($failures.Count){$failures;throw 'PowerShell parse errors'}
Add-Type -Path (Join-Path $root 'lib\DisplayControl.cs')
Add-Type -Path (Join-Path $root 'lib\MoonlightWindows.cs')
. (Join-Path $root 'windows\Common.ps1')
. (Join-Path $root 'windows\Layout.ps1')
function Assert($condition,[string]$message){if(!$condition){throw $message}}
$p=Read-Profile (Join-Path $root 'examples\two-screens.json')
$positions=@(Get-HostPositions $p Screen1)
Assert ($positions[0].x -eq -1920 -and $positions[1].x -eq 0) 'Mixed-scale horizontal layout must touch at x=0'
Assert ($positions[0].x+$positions[0].width -eq $positions[1].x) 'No gap or overlap at common edge'
$p.streams[0].clientBounds.y=-1080;$p.streams[1].clientBounds.y=0
$vertical=@(Get-HostPositions $p Screen1 Vertical)
Assert ($vertical[0].y -eq -1008 -and $vertical[1].y -eq 0) 'Vertical layout uses stream heights'
$tmp=Join-Path ([IO.Path]::GetTempPath()) ('apollo-kit-test-'+[guid]::NewGuid()+'.json')
try {
    $p.streams[0].width=1919
    $p|ConvertTo-Json -Depth 15|Set-Content $tmp
    $rejected=$false
    try{Read-Profile $tmp|Out-Null}catch{$rejected=$true}
    Assert $rejected 'Odd stream widths must be rejected'
    $p.streams[0].width=1920;$p.streams[0].host=$p.streams[1].host
    $p|ConvertTo-Json -Depth 15|Set-Content $tmp
    $rejected=$false
    try{Read-Profile $tmp|Out-Null}catch{$rejected=$true}
    Assert $rejected 'Duplicate hosts must be rejected'
} finally {Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue}
$packages=Get-Content (Join-Path $root 'packages.json') -Raw|ConvertFrom-Json
foreach($entry in $packages.PSObject.Properties){Assert ($entry.Value.sha256 -match '^[a-f0-9]{64}$') 'Every package needs a SHA256 pin'}
Write-Host 'PASS: scripts, native compilation, profile validation and layout calculations.'
