"""Resolve the repository and constrain experiment output to the art workspace."""
from pathlib import Path
import sys

ROOT = next(path for path in Path(__file__).resolve().parents
            if (path / 'docs/CODING_RULES.md').is_file())
WORKSPACE = ROOT / 'tools/art_pipeline/workspace'
SCRIPTS = ROOT / '.agents/skills/mu-art-pipeline/scripts'
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))


def workspace_path(value):
    path = (WORKSPACE / value).resolve()
    if path == WORKSPACE.resolve() or not path.is_relative_to(WORKSPACE.resolve()):
        raise ValueError('Choose a subdirectory inside the art workspace')
    return path


def experiment_from_arguments():
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    if '--experiment' not in arguments:
        raise ValueError('--experiment is required')
    return workspace_path(arguments[arguments.index('--experiment') + 1])
