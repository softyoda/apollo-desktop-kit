@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\Install-Client.ps1" -PairClipboard
pause
