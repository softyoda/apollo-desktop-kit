# Binary distribution and corresponding sources

The original SpaceMouse Link Python source is MIT-licensed. **The Windows application bundle is distributed under GPL-3.0-or-later terms** because the upstream PyAV wheel includes GPL-enabled FFmpeg, x264 and x265. Do not describe the complete binary bundle as MIT-only. The libraries remain separate DLLs in the installed `_internal` directory.

The app does not use media encoding, but aiortc imports PyAV and these binary dependencies are included. Upstream licenses and package metadata are installed in `licenses/`. GPL version 3 is included there as `GPL-3.0.txt`. The USB driver installers are not redistributed: the optional setup task downloads their official, pinned upstream releases.

Corresponding source and build instructions are available without charge at the links below, alongside the binary download in the release notes:

- **This application:** the GitHub source archive for the same `spacemouse-v0.2.0-beta.1` tag. `build.ps1`, `SpaceMouseLink.spec` and `requirements.lock.txt` define the application build.
- **PyAV 17.1.0:** [source](https://github.com/PyAV-Org/PyAV/tree/v17.1.0), [source archive](https://github.com/PyAV-Org/PyAV/archive/refs/tags/v17.1.0.tar.gz), [Windows wheel workflow](https://github.com/PyAV-Org/PyAV/blob/v17.1.0/.github/workflows/tests.yml).
- **FFmpeg 8.1.1 and bundled codec libraries:** [complete upstream build recipes, patches and source URLs](https://github.com/PyAV-Org/pyav-ffmpeg/tree/8.1.1-2), [recipe archive](https://github.com/PyAV-Org/pyav-ffmpeg/archive/refs/tags/8.1.1-2.tar.gz), [exact source package definitions](https://github.com/PyAV-Org/pyav-ffmpeg/blob/8.1.1-2/scripts/pkg.py). This is the build selected by [PyAV's pinned vendor configuration](https://github.com/PyAV-Org/PyAV/blob/v17.1.0/scripts/ffmpeg-latest.json).
- **FFmpeg source:** https://ffmpeg.org/releases/ffmpeg-8.1.1.tar.xz
- **x264 source:** https://code.videolan.org/videolan/x264/-/archive/b35605ace3ddf7c1a5d67a2eb553f034aef41d55/x264-b35605ace3ddf7c1a5d67a2eb553f034aef41d55.tar.bz2
- **x265 source:** https://bitbucket.org/multicoreware/x265_git/downloads/x265_4.2.tar.gz
- **Other Python dependencies:** exact versions are in `requirements.lock.txt`; the unmodified source distributions are available from their versioned PyPI pages. Their metadata and licenses are included in the installed `licenses/` directory.
- **Python 3.13.16:** [CPython source](https://github.com/python/cpython/tree/v3.13.16), packaged Windows runtime from [python-build-standalone](https://github.com/astral-sh/python-build-standalone).
- **Installer framework:** Inno Setup 7.1.0, [source and license](https://github.com/jrsoftware/issrc/tree/is-7_1_0).

No third-party source has been modified. Rebuilding does not require any signing key or pairing credential. If an upstream corresponding-source link becomes unavailable, report it to the repository owner so equivalent access can be restored.
