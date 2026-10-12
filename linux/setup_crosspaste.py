import pathlib, runpy
_target = pathlib.Path(__file__).resolve().parents[1] / "components/clipboard/linux/setup_crosspaste.py"
globals().update(runpy.run_path(str(_target), run_name=__name__))
