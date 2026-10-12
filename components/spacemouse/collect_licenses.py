"""Collect notices from the pinned build environment; no credentials/configs."""
import importlib.metadata as metadata
from pathlib import Path
import sys

root = Path(__file__).parent / 'licenses'
root.mkdir(exist_ok=True)
for dist in metadata.distributions():
    target = root / dist.metadata['Name']
    target.mkdir(exist_ok=True)
    (target / 'METADATA.txt').write_text(dist.read_text('METADATA') or '', encoding='utf-8')
    for i, file in enumerate(dist.files or []):
        if any(s in str(file).lower() for s in ('license','copying','notice')):
            source = Path(dist.locate_file(file))
            if source.is_file() and source.stat().st_size < 2_000_000:
                (target / (str(i)+'-'+Path(file).name)).write_bytes(source.read_bytes())
source = Path(sys.base_prefix) / 'LICENSE.txt'
if source.exists():
    (root/'Python-LICENSE.txt').write_bytes(source.read_bytes())
