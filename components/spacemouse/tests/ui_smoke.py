"""Windows desktop smoke: real tray, hide/restore, explicit quit; no connection."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import time
import tkinter as tk
from app import Window
from identity import new_identity

root=tk.Tk()
root.withdraw()
app=Window(root,{'role':'client',**new_identity(),'close_to_tray':True},preview=True)
app.create_tray()
deadline=time.monotonic()+4
while time.monotonic()<deadline and not (app.tray and app.tray.visible):
    root.update()
    time.sleep(.05)
assert app.tray and app.tray.visible, 'Tray icon did not become visible'
app.close_window()
root.update()
assert root.state()=='withdrawn'
app.show()
root.update()
assert root.state()=='normal'
app.change_close()
app.quit()
print('PASS: actual Windows tray icon created, close hides, Open restores, Quit removes icon')
