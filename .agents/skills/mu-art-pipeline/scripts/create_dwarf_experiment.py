"""Create a Class01 dwarf trial with all Player actions and a rigid Sword01 attachment."""
from pathlib import Path
import argparse
import json
import math
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from dwarf_experiment.paths import ROOT, workspace_path
from create_dark_wizard_group import DEFAULT_BLENDER, stage_group_inputs
from mu_art_pipeline.textures import convert_texture

HELPERS = Path(__file__).with_name('dwarf_experiment')
DEFAULT_PROFILE = HELPERS / 'classic_dwarf_profile.json'


def load_profile(path):
    profile = json.loads(path.read_text(encoding='utf-8'))
    defaults = json.loads(DEFAULT_PROFILE.read_text(encoding='utf-8'))
    if set(profile) != set(defaults):
        raise ValueError('Profile fields must match classic_dwarf_profile.json')
    if not isinstance(profile['name'], str) or not profile['name']:
        raise ValueError('Profile name must be a nonempty string')
    for key, value in profile.items():
        if key == 'name':
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{key} must be a positive number')
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'{key} must be finite and greater than zero')
    return profile


def stage_inputs(output, profile):
    item_source = ROOT / 'src/bin/Data/Item'
    for name in ('Sword01.bmd', 'sword02.OZJ'):
        if not (item_source / name).is_file():
            raise FileNotFoundError(item_source / name)
    stage_group_inputs(ROOT / 'src/bin/Data/Player', output)
    items = output / 'sources/item'
    items.mkdir()
    for name in ('Sword01.bmd', 'sword02.OZJ'):
        shutil.copy2(item_source / name, items / name)
    convert_texture(items / 'sword02.OZJ', output / 'sword02.jpg')
    (output / 'profile.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')


def run_blender(blender, script, arguments, blend=None):
    command = [str(blender), '--background', '--factory-startup']
    if blend is not None:
        command.append(str(blend))
    command += ['--python-exit-code', '1', '--python', str(HELPERS / script)]
    if arguments:
        command += ['--', *arguments]
    subprocess.run(command, check=True)


def create_trial(blender, output):
    arguments = ['--experiment', str(output)]
    run_blender(blender, 'build_experiment.py', arguments)
    subprocess.run([sys.executable, str(HELPERS / 'validate_experiment.py'), *arguments], check=True)
    subprocess.run([sys.executable, str(HELPERS / 'make_contact_sheet.py'), *arguments], check=True)
    blend = output / 'runs/v01/Dwarf_Classic_Experiment.blend'
    run_blender(blender, 'inspect_saved_blend.py', [], blend)
    if not blend.is_file():
        raise RuntimeError('Blender did not create the experiment')
    return blend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New workspace-relative experiment directory')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--blender', type=Path, default=DEFAULT_BLENDER)
    args = parser.parse_args()
    output = workspace_path(args.output)
    if output.exists():
        raise FileExistsError(f'Choose a new experiment directory: {output}')
    if not args.blender.is_file():
        raise FileNotFoundError(args.blender)
    profile = load_profile(args.profile)
    stage_inputs(output, profile)
    blend = create_trial(args.blender, output)
    print(json.dumps({'blend': str(blend), 'installed_to_game': False}))


if __name__ == '__main__':
    main()
