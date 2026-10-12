param([Parameter(Mandatory=$true)][string]$ProfilePath)
. "$PSScriptRoot\Common.ps1"
$logPath = Join-Path (Split-Path (Resolve-Path $ProfilePath) -Parent) 'desktop-launcher.log'
Start-Transcript -Path $logPath -Force | Out-Null
try {
    Initialize-Native
    $p = Read-Profile $ProfilePath
    if (!(Test-Path -LiteralPath $p.moonlight)) { throw 'Moonlight path missing. Run Install-Client first.' }
    if ($p.clipboard -and $p.crosspaste -and (Test-Path -LiteralPath $p.crosspaste)) {
        try {
            if (!(Get-Process CrossPaste -ErrorAction SilentlyContinue)) { Start-Process -FilePath $p.crosspaste -WindowStyle Hidden | Out-Null }
        } catch { Write-Warning 'CrossPaste ne demarre pas. Connexion aux ecrans poursuivie, sans reinstallation.' }
    }
    $screens = [System.Windows.Forms.Screen]::AllScreens
    # Resolve every output before opening anything.
    $targets = @()
    foreach ($s in $p.streams) {
        $target = switch ($s.monitor) {
            'primary' { $screens | Where-Object Primary }
            'right' { $screens | Sort-Object { $_.Bounds.Right } -Descending | Select-Object -First 1 }
            'left' { $screens | Sort-Object { $_.Bounds.Left } | Select-Object -First 1 }
            default { $screens | Where-Object DeviceName -eq $s.monitor }
        }
        if (@($target).Count -ne 1) { throw "Monitor missing: $($s.monitor)" }
        if ($targets.DeviceName -contains $target.DeviceName) { throw 'Two streams target the same monitor.' }
        $targets += $target
    }
    for ($i=0; $i -lt $p.streams.Count; $i++) {
        $s=$p.streams[$i]; $screen=$targets[$i]
        # SDL sees a windowed session, so it does not lock the pointer on startup.
        $launchArgs = 'stream "{0}" "{1}" --resolution {2}x{3} --fps {4} --display-mode windowed --absolute-mouse --capture-system-keys always' -f $s.host,$s.app,$s.width,$s.height,$s.fps
        $proc=Start-Process -FilePath $p.moonlight -ArgumentList $launchArgs -PassThru
        $deadline=(Get-Date).AddSeconds(75); $handle=[IntPtr]::Zero
        while ((Get-Date) -lt $deadline) {
            $proc.Refresh(); if ($proc.HasExited) { throw "Moonlight exited: $($s.host)" }
            $handle=[MoonlightWindows]::FindStream($proc.Id)
            if ($handle -ne [IntPtr]::Zero) { break }
            Start-Sleep -Milliseconds 250
        }
        if ($handle -eq [IntPtr]::Zero) { throw "Pas de flux pour $($s.host). Si le PC hote redemarre, attends qu'Apollo soit pret puis relance la connexion. Aucune reinstallation n'est necessaire." }
        for ($retry=0; $retry -lt 5; $retry++) {
            Start-Sleep -Milliseconds 800
            $handle=[MoonlightWindows]::FindStream($proc.Id)
            if ($handle -eq [IntPtr]::Zero) { continue }
            if ($s.mode -eq 'borderless') {
                $b=$screen.Bounds
                $ok=[MoonlightWindows]::Borderless($handle,$b.X,$b.Y,$b.Width,$b.Height)
            } else {
                $b=$screen.WorkingArea
                $w=[Math]::Min($s.width+16,$b.Width); $h=[Math]::Min($s.height+39,$b.Height)
                $ok=[MoonlightWindows]::SetWindowPos($handle,[IntPtr]::Zero,$b.X+[int](($b.Width-$w)/2),$b.Y+[int](($b.Height-$h)/2),$w,$h,0x0054)
            }
            if (!$ok) { throw "Window placement failed: $($s.host)" }
        }
        $rect=New-Object MoonlightWindows+Rect
        if (![MoonlightWindows]::GetWindowRect($handle,[ref]$rect)) { throw 'Window disappeared.' }
        if ($rect.Left -lt $screen.Bounds.Left-20 -or $rect.Right -gt $screen.Bounds.Right+20) { throw 'Window not on requested monitor.' }
        if ($s.mode -eq 'borderless' -and ([Math]::Abs($rect.Top-$screen.Bounds.Top) -gt 20 -or [Math]::Abs(($rect.Bottom-$rect.Top)-$screen.Bounds.Height) -gt 20 -or [Math]::Abs(($rect.Right-$rect.Left)-$screen.Bounds.Width) -gt 20)) { throw 'Borderless fullscreen size verification failed.' }
        Write-Host "$($s.host): $($s.width)x$($s.height), $($screen.DeviceName), $($s.mode)"
    }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
} finally { Stop-Transcript | Out-Null }
