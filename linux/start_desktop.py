#!/usr/bin/env python3
"""X11 placement of independent Moonlight sessions. Native Wayland is deliberately unsupported."""
import argparse, json, os, pathlib, re, shutil, subprocess, time

def monitors(text):
    result = {}
    for line in text.splitlines():
        match = re.search(r'\d+:\s+([+*]*)(\S+)\s+(\d+)/(?:\d+)x(\d+)/(?:\d+)([+-]\d+)([+-]\d+)', line)
        if match:
            flags, name, w, h, x, y = match.groups()
            result[name] = dict(x=int(x), y=int(y), width=int(w), height=int(h), primary='*' in flags)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('profile')
    args = parser.parse_args()
    if os.environ.get('XDG_SESSION_TYPE') != 'x11':
        raise SystemExit('Automatic placement requires X11. On Wayland use compositor-specific window rules; see docs/linux-client.md.')
    for command in ('xrandr', 'wmctrl', 'xdotool'):
        if not shutil.which(command): raise SystemExit('Missing command: ' + command)
    p = json.loads(pathlib.Path(args.profile).read_text(encoding='utf-8-sig'))
    screens = monitors(subprocess.check_output(['xrandr','--listmonitors'], text=True))
    if not screens: raise SystemExit('No X11 monitors detected')
    command = ['moonlight'] if shutil.which('moonlight') else ['flatpak','run','com.moonlight_stream.Moonlight']
    used = set()
    for stream in p['streams']:
        name = stream['monitor']
        if name == 'left': name = min(screens, key=lambda n: screens[n]['x'])
        if name == 'right': name = max(screens, key=lambda n: screens[n]['x'])
        if name == 'primary': name = next((n for n in screens if screens[n]['primary']), '')
        if name not in screens or name in used: raise SystemExit('Missing/duplicate monitor: ' + name)
        used.add(name)
        b = screens[name]
        before = set(subprocess.check_output(['wmctrl','-l'],text=True).splitlines())
        subprocess.Popen(command + ['stream',stream['host'],stream.get('app','Desktop'),'--resolution',f"{stream['width']}x{stream['height']}",'--fps',str(stream.get('fps',60)),'--display-mode','windowed','--absolute-mouse','--capture-system-keys','always'])
        window = None
        for _ in range(150):
            current = subprocess.check_output(['wmctrl','-lx'],text=True).splitlines()
            old_ids = {line.split()[0] for line in before}
            candidates = [line.split()[0] for line in current if line.split()[0] not in old_ids and 'sdl' in line.lower()]
            if len(candidates) == 1: window=candidates[0]; break
            time.sleep(.5)
        if not window: raise SystemExit('Stream window not found. Check pairing and connection.')
        width = b['width'] if stream['mode']=='borderless' else min(b['width']-16,stream['width'])
        height = b['height'] if stream['mode']=='borderless' else min(b['height']-60,stream['height'])
        subprocess.run(['wmctrl','-ir',window,'-b','remove,maximized_vert,maximized_horz,fullscreen'],check=True)
        subprocess.run(['wmctrl','-ir',window,'-e',f"0,{b['x']},{b['y']},{width},{height}"],check=True)
        if stream['mode']=='borderless':
            subprocess.run(['wmctrl','-ir',window,'-b','add,fullscreen'],check=True)

if __name__ == '__main__': main()
