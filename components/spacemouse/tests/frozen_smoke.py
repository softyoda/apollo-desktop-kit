"""Run packaged diagnostics synchronously (Windows GUI executables do not wait in PS)."""
from pathlib import Path
import json
import os
import subprocess

root=Path(__file__).resolve().parents[1]
exe=root/'dist/SpaceMouseLink/SpaceMouseLink.exe'
env=os.environ.copy()
env['SPACEMOUSE_TEST_NO_STUN']='1'
env['SPACEMOUSE_EXPECT_MODE']='DIRECT'
for flag,name in (('--self-check','self'),('--transport-check','direct')):
    report=root/'build'/('frozen-'+name+'.json')
    subprocess.run([str(exe),flag,'--report',str(report)],env=env,check=True,timeout=90)
    result=json.loads(report.read_text())
    assert result['ok']
    print('PASS: packaged '+name+' diagnostic')
