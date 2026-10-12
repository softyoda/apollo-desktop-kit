"""Check generated arguments against the installed native client's real CLI."""
import re
import subprocess
import unittest
from unittest.mock import patch

import windows_usb


class InstalledClientContract(unittest.TestCase):
    def test_attach_options_are_supported_by_installed_client(self):
        try:
            exe = windows_usb.executable("client")
        except RuntimeError:
            self.skipTest("Native Windows USB/IP client not installed on this test host")
        help_result = subprocess.run([str(exe), "attach", "--help"], capture_output=True,
                                     text=True, errors="replace", check=True)
        supported = set(re.findall(r"--[a-z][a-z-]*", help_result.stdout))
        with patch.object(windows_usb, "run", return_value="7") as command:
            windows_usb.attach_device("4-1", 43210)
        argv = command.call_args.args[0]
        attach_args = argv[argv.index("attach") + 1:]
        requested = {arg for arg in attach_args if arg.startswith("--")}
        self.assertFalse(requested - supported, "Unsupported USB/IP arguments: " + str(requested - supported))
