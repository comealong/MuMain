"""Source staging for the Dark Wizard Class01 character workflows."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[5]
WORKSPACE = ROOT / 'tools/art_pipeline/workspace'
PARTS = ('HelmClass01', 'ArmorClass01', 'PantClass01', 'GloveClass01', 'BootClass01')
RESTORATION_MODE = 'separate_parts_shared_armature'


def stage_sources(source: Path, output: Path) -> dict:
    names = ['player.bmd', *(name + '.bmd' for name in PARTS), 'skin_barbarian_01.OZJ']
    for name in names:
        if not (source / name).is_file():
            raise FileNotFoundError(source / name)
    staged = output / 'sources'
    staged.mkdir(parents=True)
    hashes = {}
    for name in names:
        shutil.copy2(source / name, staged / name)
        hashes[name] = hashlib.sha256((staged / name).read_bytes()).hexdigest()
    return hashes
