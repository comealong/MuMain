"""Resolve Player action indices from the client's enum and matching BMD count."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from .bmd import parse_bmd

RIDING_MACRO = 'YDG_ADD_SKILL_RIDING_ANIMATIONS'


def enum_rows(header: Path, riding_enabled: bool) -> tuple[list[dict], int]:
    text = header.read_text(encoding='utf-8-sig')
    start = re.search(r'enum\s*\{\s*PLAYER_SET\s*,', text)
    if start is None:
        raise ValueError('Player enum was not found')
    opening = text.index('{', start.start())
    closing = text.index('};', opening)
    body = text[opening + 1:closing]
    rows, values, conditions = [], {}, [True]
    value = -1
    base_line = text[:opening + 1].count('\n')
    for offset, raw in enumerate(body.splitlines(), 1):
        line = raw.split('//', 1)[0].strip()
        if line.startswith('#'):
            update_condition(line, conditions, riding_enabled)
            continue
        if not line or not conditions[-1]:
            continue
        match = re.fullmatch(r'(PLAYER_\w+|MAX_PLAYER_ACTION)(?:\s*=\s*(\w+))?\s*,?', line)
        if match is None:
            raise ValueError(f'Unsupported enum syntax at line {base_line + offset}: {line}')
        name, assignment = match.groups()
        value = resolve_value(assignment, values) if assignment else value + 1
        values[name] = value
        if name != 'MAX_PLAYER_ACTION':
            rows.append({'index': value, 'name': name, 'source_line': base_line + offset})
    if len(conditions) != 1 or 'MAX_PLAYER_ACTION' not in values:
        raise ValueError('Player enum or preprocessing block is incomplete')
    return rows, values['MAX_PLAYER_ACTION']


def update_condition(line: str, stack: list[bool], enabled: bool) -> None:
    fields = line.split()
    directive = fields[0]
    if directive == '#ifdef' and fields[1:] == [RIDING_MACRO]:
        stack.append(stack[-1] and enabled)
    elif directive == '#endif' and len(stack) > 1:
        stack.pop()
    elif directive == '#else' and len(stack) > 1:
        stack[-1] = stack[-2] and not stack[-1]
    else:
        raise ValueError(f'Unsupported Player enum directive: {line}')


def resolve_value(assignment: str, values: dict) -> int:
    if assignment in values:
        return values[assignment]
    try:
        return int(assignment, 0)
    except ValueError as error:
        raise ValueError(f'Unsupported Player enum expression: {assignment}') from error


def canonical_row(rows: list[dict]) -> dict:
    candidates = [row for row in rows if not row['name'].endswith('_END')]
    return candidates[-1] if candidates else rows[-1]


def extract_player_actions(header: Path, model_path: Path) -> dict:
    model = parse_bmd(model_path)
    count = len(model['actions'])
    matching = []
    for enabled in (False, True):
        rows, sentinel = enum_rows(header, enabled)
        if sentinel == count and {row['index'] for row in rows} == set(range(count)):
            matching.append((enabled, rows))
    if len(matching) != 1:
        raise ValueError(f'Cannot uniquely match Player enum profiles to {count} BMD actions')
    enabled, rows = matching[0]
    actions = []
    for index, action in enumerate(model['actions']):
        aliases = [row for row in rows if row['index'] == index]
        canonical = canonical_row(aliases)
        actions.append({'index': index, 'name': canonical['name'],
                        'aliases': [r['name'] for r in aliases if r != canonical],
                        'enum_source_line': canonical['source_line'],
                        'keys': action['keys'], 'root_locked': action['lock_positions']})
    return {'header': str(header.resolve()), 'model': str(model_path.resolve()),
            'source_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in (header, model_path)},
            'action_count': count, 'defines': {RIDING_MACRO: enabled}, 'actions': actions}
