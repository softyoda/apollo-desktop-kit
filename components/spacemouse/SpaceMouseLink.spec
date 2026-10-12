from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('wormhole')
datas += [('assets', 'assets')]
hiddenimports += ['twisted.internet.endpoints', 'twisted.internet.tcp', 'twisted.internet.selectreactor',
                  'twisted.internet.ssl', 'twisted.protocols.policies', 'win32api', 'pystray._win32']
a = Analysis(['app.py'], pathex=[], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SpaceMouseLink', debug=False,
          strip=False, upx=False, console=False, icon='assets/spacemouse.ico', uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SpaceMouseLink')
