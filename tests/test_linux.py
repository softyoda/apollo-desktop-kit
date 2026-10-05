import importlib.util
import pathlib
import unittest

spec=importlib.util.spec_from_file_location('launcher',pathlib.Path(__file__).resolve().parents[1]/'linux/start_desktop.py')
launcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

class MonitorTests(unittest.TestCase):
    def test_negative_coordinates_and_portrait(self):
        text='Monitors: 2\n 0: +*eDP-1 1920/300x1080/170+0+0 eDP-1\n 1: +DP-1 1080/170x1920/300-1080-420 DP-1\n'
        result=launcher.monitors(text)
        self.assertTrue(result['eDP-1']['primary'])
        self.assertEqual(result['DP-1']['x'],-1080)
        self.assertEqual(result['DP-1']['y'],-420)
        self.assertEqual(result['DP-1']['height'],1920)
    def test_empty_output(self):
        self.assertEqual(launcher.monitors('Monitors: 0'),{})

if __name__=='__main__':unittest.main()
