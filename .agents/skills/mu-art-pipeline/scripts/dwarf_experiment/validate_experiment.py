"""Read-only validation of a generated trial bundle and its original inputs."""
import argparse
import hashlib
import json
import math
import sys

sys.dont_write_bytecode = True
from paths import ROOT, experiment_from_arguments

EXPERIMENT = experiment_from_arguments()
from mu_art_pipeline.bmd import parse_bmd
from mu_art_pipeline.poses import validate_part_bones

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--experiment', required=True)
parser.add_argument('--run', default='runs/v01')
args = parser.parse_args()
OUTPUT = (EXPERIMENT / args.run).resolve()
if not OUTPUT.is_relative_to(EXPERIMENT):
    raise ValueError('Run must be inside the experiment')
PARTS = ('HelmClass01', 'ArmorClass01', 'PantClass01', 'GloveClass01', 'BootClass01')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compare_model(old, new):
    require(len(old['meshes']) == len(new['meshes']), "Validation failed: len(old['meshes']) == len(new['meshes'])")
    require(len(old['bones']) == len(new['bones']), "Validation failed: len(old['bones']) == len(new['bones'])")
    require(len(old['actions']) == len(new['actions']), "Validation failed: len(old['actions']) == len(new['actions'])")
    for source, target in zip(old['bones'], new['bones']):
        require((source['name'], source['parent'], source['dummy']) == (target['name'], target['parent'], target['dummy']), "Validation failed: (source['name'], source['parent'], source['dummy']) == (target['name'], target['parent'], target['dummy'])")
        for old_action, new_action in zip(source['actions'], target['actions']):
            require(old_action['rotations'] == new_action['rotations'], "Validation failed: old_action['rotations'] == new_action['rotations']")
            require(all(math.isfinite(value) for position in new_action['positions'] for value in position), "Validation failed: all(math.isfinite(value) for position in new_action['positions'] for value in position)")
    for source, target in zip(old['actions'], new['actions']):
        require((source['keys'], source['lock_positions']) == (target['keys'], target['lock_positions']), "Validation failed: (source['keys'], source['lock_positions']) == (target['keys'], target['lock_positions'])")
    for source, target in zip(old['meshes'], new['meshes']):
        for field in ('uvs', 'triangles', 'texture', 'texture_index'):
            require(source[field] == target[field], "Validation failed: source[field] == target[field]")
        for field in ('vertices', 'normals'):
            require([item['node'] for item in source[field]] == [item['node'] for item in target[field]], "Validation failed: [item['node'] for item in source[field]] == [item['node'] for item in target[field]]")
        for normal in target['normals']:
            require(abs(math.sqrt(sum(v * v for v in normal['normal'])) - 1.0) < 0.00001, "Validation failed: abs(math.sqrt(sum(v * v for v in normal['normal'])) - 1.0) < 0.00001")


def main():
    report = json.loads((OUTPUT / 'report.json').read_text(encoding='utf-8'))
    for relative, digest in report['source_sha256_before_and_after'].items():
        require(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, "Validation failed: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest")
    for name in ('player', *PARTS):
        old = parse_bmd(EXPERIMENT / 'sources' / (name + '.bmd'))
        new = parse_bmd(OUTPUT / 'generated/Player' / (name + '.bmd'))
        compare_model(old, new)
    source = parse_bmd(EXPERIMENT / 'sources/player.bmd')
    target = parse_bmd(OUTPUT / 'generated/Player/player.bmd')
    for name in PARTS:
        validate_part_bones(parse_bmd(OUTPUT / 'generated/Player' / (name + '.bmd')), target)
    ratios = {}
    profile = report['profile']
    for node, expected in ((4, profile['leg_length']), (5, profile['leg_length']),
                           (27, profile['arm_length']), (28, profile['arm_length'])):
        old = source['bones'][node]['actions'][0]['positions'][0]
        new = target['bones'][node]['actions'][0]['positions'][0]
        ratio = math.sqrt(sum(v * v for v in new) / sum(v * v for v in old))
        require(abs(ratio - expected) < 0.00001, "Validation failed: abs(ratio - expected) < 0.00001")
        ratios[str(node)] = ratio
    for name in ('Sword01.bmd', 'sword02.OZJ'):
        require((EXPERIMENT / 'sources/item' / name).read_bytes() == (OUTPUT / 'generated/Item' / name).read_bytes(), "Validation failed: (EXPERIMENT / 'sources/item' / name).read_bytes() == (OUTPUT / 'generated/Item' / name).read_bytes()")
    result = {'passed': True, 'original_assets_unchanged': True, 'actions': len(target['actions']),
              'rotation_data_unchanged': True, 'topology_uv_node_ids_unchanged': True,
              'unit_normals': True, 'limb_length_ratios': ratios, 'weapon_source_bytes_unchanged': True}
    (OUTPUT / 'bundle_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
