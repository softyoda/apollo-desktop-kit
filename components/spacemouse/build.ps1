param([string]$Python='python',[string]$Iscc=$env:INNOSETUP_ISCC)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if(-not $Iscc){$found=Get-Command ISCC.exe -ErrorAction SilentlyContinue;if($found){$Iscc=$found.Source}}
if(-not $Iscc){throw 'Install Inno Setup 7 and pass -Iscc <path to ISCC.exe>, or set INNOSETUP_ISCC.'}
& $Python -m pip install -r requirements.lock.txt
if($LASTEXITCODE){throw 'Dependencies failed'}
& $Python icon_art.py
& $Python -m unittest discover -s tests -v
if($LASTEXITCODE){throw 'Tests failed'}
& $Python -m PyInstaller --noconfirm SpaceMouseLink.spec
if($LASTEXITCODE){throw 'App build failed'}
& $Python collect_licenses.py
Invoke-WebRequest 'https://www.gnu.org/licenses/gpl-3.0.txt' -OutFile licenses\GPL-3.0.txt
foreach($role in @('server','client')) {
    & $Iscc ('/DRole='+$role) installer.iss
    if($LASTEXITCODE){throw 'Installer build failed'}
}
$hashes=Get-ChildItem release\*.exe | ForEach-Object { (Get-FileHash -LiteralPath $_.FullName).Hash.ToLower()+'  '+$_.Name }
$hashes | Set-Content release\SHA256SUMS.txt -Encoding ascii
Write-Output 'Public unpaired installers created. No device identity or pairing key is embedded.'
