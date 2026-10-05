function Get-HostPositions($Profile,[string]$AnchorHost,[ValidateSet('Horizontal','Vertical')][string]$Layout='Horizontal') {
    $streams = if ($Layout -eq 'Horizontal') { @($Profile.streams | Sort-Object { $_.clientBounds.x }) } else { @($Profile.streams | Sort-Object { $_.clientBounds.y }) }
    if (@($streams | Where-Object host -eq $AnchorHost).Count -ne 1) { throw 'AnchorHost must match exactly one profile stream.' }
    $positions=@(); $offset=0; $anchorOffset=0
    foreach ($s in $streams) {
        if (!$s.clientBounds) { throw 'Profile needs clientBounds: generate it on the client.' }
        if ($s.host -eq $AnchorHost) { $anchorOffset=$offset }
        $positions += [pscustomobject]@{host=$s.host;x=$(if($Layout -eq 'Horizontal'){$offset}else{0});y=$(if($Layout -eq 'Vertical'){$offset}else{0});width=$s.width;height=$s.height}
        $offset += $(if($Layout -eq 'Horizontal'){$s.width}else{$s.height})
    }
    foreach($p in $positions) { if($Layout -eq 'Horizontal'){$p.x-=$anchorOffset}else{$p.y-=$anchorOffset} }
    return $positions
}
