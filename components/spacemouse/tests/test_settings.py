import unittest
from unittest.mock import patch, MagicMock
import sys

from identity import new_identity
import settings


@unittest.skipUnless(sys.platform=='win32','Windows integration')
class SettingsTests(unittest.TestCase):
    def test_dpapi_roundtrip_hides_private_key(self):
        from windows_usb import protect, unprotect
        import json
        data=json.dumps(new_identity()).encode()
        encrypted=protect(data)
        self.assertNotIn(data,encrypted)
        self.assertEqual(unprotect(encrypted),data)

    def test_startup_is_current_user_and_quotes_binary(self):
        import winreg
        key=MagicMock()
        key.__enter__.return_value=key
        with patch.object(winreg,'CreateKey',return_value=key) as create, \
             patch.object(winreg,'SetValueEx') as write, \
             patch.object(sys,'frozen',True,create=True), \
             patch.object(sys,'executable',r'C:\Program Files\SpaceMouse Link\Client\SpaceMouseLink.exe'):
            settings.set_startup('client',True)
        self.assertEqual(create.call_args.args[0],winreg.HKEY_CURRENT_USER)
        command=write.call_args.args[-1]
        self.assertTrue(command.startswith('"C:\\Program Files\\'))
        self.assertTrue(command.endswith('--role client --tray'))

    def test_startup_off_removes_only_role_value(self):
        import winreg
        key=MagicMock()
        key.__enter__.return_value=key
        with patch.object(winreg,'CreateKey',return_value=key),patch.object(winreg,'DeleteValue') as delete:
            settings.set_startup('server',False)
        self.assertEqual(delete.call_args.args,(key,'SpaceMouseLink-server'))
