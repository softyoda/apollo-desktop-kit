"""Exercise the actual PowerShell guard with synthetic policy, without changing Windows."""
import os
import subprocess
import unittest

from windows_usb import FIREWALL_CHECK


MOCK = r"""
$rule = [pscustomobject]@{
 Name='SpaceMouse Link - block non-local USB access'; Enabled=$true
 Direction=1; Action=0; Protocol=6; LocalPorts='3240'; Profiles=2147483647
 ApplicationName=''; ServiceName=''; LocalAddresses='*'; RemotePorts='*'
 InterfaceTypes='All'; Interfaces=$null
 RemoteAddresses='0.0.0.0-126.255.255.255,128.0.0.0-255.255.255.255,::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'
}
$policy = [pscustomobject]@{LocalPolicyModifyState=0; Rules=@($rule)}
$profiles = @(1,2,4 | ForEach-Object { [pscustomobject]@{Enabled=$true; AllowLocalFirewallRules='True'} })
function Get-NetFirewallProfile { param($PolicyStore) $profiles }
function New-Object { param($ComObject) $policy }
function Get-NetFirewallRule { throw 'Forbidden: elevated ActiveStore rule enumeration' }
"""


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell required')
class FirewallGuard(unittest.TestCase):
    def check(self, mutation=''):
        return subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
             MOCK + '\n' + mutation + '\n' + FIREWALL_CHECK],
            capture_output=True, encoding='utf-8', errors='replace', timeout=30)

    def test_valid_protection_without_privileged_rule_query(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsafe_or_unreadable_policy_is_rejected(self):
        mutations = [
            '$policy.Rules=@()', '$policy.Rules=@($rule,$rule)',
            '$rule.Enabled=$false', '$rule.Action=1', '$rule.Direction=2',
            '$rule.Protocol=17', "$rule.LocalPorts='3241'", '$rule.Profiles=2',
            "$rule.ApplicationName='C:\\limited.exe'", "$rule.ServiceName='other'",
            "$rule.LocalAddresses='127.0.0.1'", "$rule.RemotePorts='1234'",
            "$rule.InterfaceTypes='Lan'", "$rule.Interfaces=@('Ethernet')",
            "$rule.RemoteAddresses='0.0.0.0-126.255.255.255'",
            '$policy.LocalPolicyModifyState=1', '$profiles[0].Enabled=$false',
            "$profiles[0].AllowLocalFirewallRules='False'", '$profiles=@()',
            "function New-Object { throw 'Access denied' }",
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertNotEqual(self.check(mutation).returncode, 0)
