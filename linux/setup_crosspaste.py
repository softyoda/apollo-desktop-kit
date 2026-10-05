#!/usr/bin/env python3
"""Install the pinned official x86-64 CrossPaste AppImage in the user's home."""
import hashlib, json, os, pathlib, platform, subprocess, time, urllib.request

def main():
    if platform.machine() not in ('x86_64', 'AMD64'):
        raise SystemExit('This package pins x86-64. Obtain the official ARM64 release for other machines.')
    kit = pathlib.Path(__file__).resolve().parents[1]
    asset = json.loads((kit / 'packages.json').read_text(encoding='utf-8-sig'))['crosspasteLinux']
    root = pathlib.Path.home() / '.local/share/apollo-desktop-kit/crosspaste'
    root.mkdir(parents=True, exist_ok=True)
    archive = root / asset['file']
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != asset['sha256']:
        urllib.request.urlretrieve(asset['url'], archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != asset['sha256']:
        raise SystemExit('CrossPaste SHA256 mismatch')
    archive.chmod(0o755)
    # Extract to avoid depending on FUSE. All content comes from the verified release.
    subprocess.run([str(archive), '--appimage-extract'], cwd=root, check=True, stdout=subprocess.DEVNULL)
    app = root / 'squashfs-root/AppRun'
    app.chmod(0o755)
    subprocess.Popen([str(app)], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cli = next((p for p in (root / 'squashfs-root').rglob('crosspaste-cli') if p.is_file()), None)
    if cli:
        cli.chmod(0o755)
        for _ in range(40):
            if subprocess.run([str(cli), 'status'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(.5)
        else:
            raise SystemExit('CrossPaste did not start. Launch AppRun in your desktop session and inspect its output.')
        for key, value in [('enableEncryptSync','true'), ('pastePrimaryTypeOnly','false'), ('enableAutoStartUp','true')]:
            subprocess.run([str(cli), 'config', 'set', key, value], check=True)
    else:
        raise SystemExit('CLI missing: enable encryption and all clipboard formats in CrossPaste Settings manually.')
    print('CrossPaste installed. Pair the host from Devices; allow sending and receiving.')

if __name__ == '__main__':
    main()
