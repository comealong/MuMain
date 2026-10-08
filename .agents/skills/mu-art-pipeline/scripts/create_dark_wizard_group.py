"""Default character recovery: five independent Dark Wizard parts on one animated Player armature."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from mu_art_pipeline.character_sources import ROOT, WORKSPACE, RESTORATION_MODE, stage_sources
from mu_art_pipeline.textures import convert_texture

DEFAULT_BLENDER = Path('D:/Blender/5.2.2/blender-5.2.2-windows-x64/blender.exe')
GROUP_FILENAME = 'DarkWizard_Client_Group.blend'


def stage_group_inputs(source: Path, output: Path) -> None:
    hashes = stage_sources(source, output)
    convert_texture(output / 'sources/skin_barbarian_01.OZJ', output / 'skin_barbarian_01.jpg')
    manifest = {'source_directory': str(source), 'source_sha256': hashes,
                'restoration_mode': RESTORATION_MODE, 'merged_mesh': False,
                'geometry_input': 'original BMD only', 'reference_geometry_read': False}
    (output / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def build_group(blender: Path, output: Path) -> Path:
    builder = Path(__file__).with_name('build_dark_wizard_group_blender.py')
    command = [str(blender), '--background', '--factory-startup', '--python-exit-code', '1',
               '--python', str(builder), '--', str(output)]
    subprocess.run(command, check=True)
    destination = output / GROUP_FILENAME
    if not destination.is_file():
        raise RuntimeError('Blender did not create the character group')
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'src/bin/Data/Player')
    parser.add_argument('--output', type=Path, default=Path('characters/dark_wizard_shared'),
                        help='New workspace-relative directory; existing outputs are preserved')
    parser.add_argument('--blender', type=Path, default=DEFAULT_BLENDER)
    args = parser.parse_args()
    output = (WORKSPACE / args.output).resolve()
    if not output.is_relative_to(WORKSPACE.resolve()):
        raise ValueError('Output must be inside the art workspace')
    if output.exists():
        raise FileExistsError(f'Choose a new output directory: {output}')
    if not args.blender.is_file():
        raise FileNotFoundError(args.blender)
    stage_group_inputs(args.source.resolve(), output)
    destination = build_group(args.blender, output)
    print(json.dumps({'blend': str(destination), 'restoration_mode': RESTORATION_MODE,
                      'report': str(output / 'group_manifest.json')}))


if __name__ == '__main__':
    main()
