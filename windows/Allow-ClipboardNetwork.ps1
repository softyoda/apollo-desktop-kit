param([Parameter(Mandatory=$true)][string]$CrossPasteExe, [string[]]$RemoteAddress = @('LocalSubnet'))
$ErrorActionPreference='Stop'
if (!(Test-Path -LiteralPath $CrossPasteExe)) { throw 'CrossPaste executable not found.' }
$exe=(Resolve-Path -LiteralPath $CrossPasteExe).Path
foreach ($rule in @(@('ApolloKit CrossPaste TCP','TCP',13129),@('ApolloKit CrossPaste discovery','UDP',5353))) {
    $existing=Get-NetFirewallRule -DisplayName $rule[0] -ErrorAction SilentlyContinue
    if ($existing) { $existing | Remove-NetFirewallRule }
    New-NetFirewallRule -DisplayName $rule[0] -Direction Inbound -Action Allow -Protocol $rule[1] -LocalPort $rule[2] -Program $exe -RemoteAddress $RemoteAddress -Profile Any | Out-Null
}
Write-Host "CrossPaste rules limited to: $($RemoteAddress -join ', ')"
