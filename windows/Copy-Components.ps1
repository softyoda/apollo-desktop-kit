function Copy-KitComponents([string]$SourceRoot,[string]$Destination) {
    $modules=Join-Path $Destination 'components'
    New-Item -ItemType Directory -Path $modules -Force | Out-Null
    # SpaceMouse has its own installer/build; never bundle its local runtime or keys.
    foreach($name in @('apollo-server','moonlight','clipboard')) {
        Copy-Item -LiteralPath (Join-Path $SourceRoot ('components\'+$name)) -Destination $modules -Recurse -Force
    }
}
