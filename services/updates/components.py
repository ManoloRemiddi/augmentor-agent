# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Component consent for a compatible release; never executes an upstream updater.

Bundled harness identities are publisher-declared inputs to the complete release.
An external prerequisite is never treated as an application-owned installation.
"""
import hashlib
import json
from pathlib import Path
import re

from lifecycle.payload_integrity import _read, _json

NAMES = {'augmentor': 'Augmentor Agent', 'dsh': 'DSH', 'pi': 'Pi', 'codex': 'Codex'}
HARNESS_IDS = ('dsh', 'pi', 'codex')
SCHEMA = 'augmentor-update-components/1'


def defaults():
    return {key: key == 'augmentor' for key in NAMES}


def validate_choices(value):
    if (not isinstance(value, dict) or set(value) != set(NAMES)
            or any(type(enabled) is not bool for enabled in value.values())):
        raise ValueError('Choose automatic updates separately for each supported component.')
    return value


def validate_contract(value):
    if not isinstance(value, dict) or set(value) != set(HARNESS_IDS):
        raise ValueError('The release needs complete harness update identities.')
    for key, row in value.items():
        if (not isinstance(row, dict) or set(row) != {'version', 'sha256', 'ownership'}
                or not isinstance(row['version'], str)
                or not re.fullmatch(r'[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}(?:[-+][A-Za-z0-9.+-]{1,96})?', row['version'])
                or not isinstance(row['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', row['sha256'])
                or row['ownership'] != ('external' if key == 'codex' else 'bundled')):
            raise ValueError('Invalid harness update identity or installation ownership.')
    return value


def installed(root):
    path = Path(root)/'release/update-components.json'
    if not path.exists() and not path.is_symlink():
        return None
    value = _json(_read(path, 65536), 65536)
    if not isinstance(value, dict) or set(value) != {'schema', 'components'} or value['schema'] != SCHEMA:
        raise ValueError('Repair the installed harness update identities.')
    return validate_contract(value['components'])


def build_contract(source):
    """Public build inputs only, including the complete pinned DSH/plugin lock."""
    source = Path(source)
    package = _json(_read(source/'package.json', 65536), 65536)
    lock_raw = _read(source/'package-lock.json', 8*1024**2)
    lock = _json(lock_raw, 8*1024**2)
    pi = {}
    for name in ('pi-ai', 'pi-agent-core', 'pi-coding-agent'):
        full = '@earendil-works/'+name
        row = lock['packages']['node_modules/'+full]
        if row['version'] != package['dependencies'][full] or not isinstance(row.get('integrity'), str):
            raise ValueError('The pinned Pi packages disagree with their build lock.')
        pi[full] = {key: row[key] for key in ('version', 'integrity')}
    # Include the locked runtime dependency closure, not only package names or
    # versions: changing a transitive engine dependency is also a harness update.
    packages=lock['packages']; queue=['node_modules/'+name for name in pi]; closure={}
    while queue:
        path=queue.pop()
        if path in closure:continue
        row=packages[path]
        integrity=row.get('integrity')
        if integrity is None:
            # npm's duplicate nested lock rows can omit integrity. Accept only
            # a unique hashed record for the identical name/version/tarball in
            # this same reviewed lock; never query the registry to fill it.
            name=path.rsplit('/node_modules/',1)[-1].removeprefix('node_modules/')
            matches={other['integrity'] for location,other in packages.items()
                if location.rsplit('/node_modules/',1)[-1].removeprefix('node_modules/')==name
                and other.get('version')==row.get('version') and other.get('resolved')==row.get('resolved')
                and isinstance(other.get('integrity'),str)}
            if len(matches)==1:integrity=matches.pop()
        if not isinstance(row.get('version'),str):
            raise ValueError('The Pi runtime closure needs explicit package versions.')
        if isinstance(integrity,str):
            closure[path]={'version':row['version'],'integrity':integrity}
        else:
            # An unhashed lock row is not an upstream-byte attestation. Bind
            # the entire reviewed input lock conservatively for consent; the
            # separately signed full artifact/payload inventory authenticates
            # actual installed bytes. Never fetch an identity during checking.
            closure[path]={'version':row['version'],'sourceLockSHA256':hashlib.sha256(lock_raw).hexdigest()}

        for dependency in {**row.get('dependencies',{}), **row.get('optionalDependencies',{})}:
            folder=path;locations=[folder+'/node_modules/'+dependency]
            while '/node_modules/' in folder:
                folder=folder.rsplit('/node_modules/',1)[0]
                locations.append(folder+'/node_modules/'+dependency)
            locations.append('node_modules/'+dependency)
            resolved=next((location for location in locations if location in packages),None)
            if resolved is None:
                if dependency not in row.get('optionalDependencies',{}):
                    raise ValueError('The Pi build lock omits a required runtime dependency.')
            else:queue.append(resolved)
    dsh_raw = _read(source/'release/dsh/package-lock.json', 8*1024**2)
    dsh = _json(dsh_raw, 8*1024**2)['packages']['node_modules/@deepseek-ai/dsh']
    dsh_package=_json(_read(source/'release/dsh/package.json',65536),65536)
    if dsh['version']!=dsh_package['dependencies']['@deepseek-ai/dsh']:
        raise ValueError('The pinned DSH runtime disagrees with its build lock.')
    codex_raw = _read(source/'release/codex/source-pin.json', 65536)
    codex = _json(codex_raw, 65536)
    if codex['version'] != package['devDependencies']['@openai/codex']:
        raise ValueError('The separate Codex prerequisite disagrees with the tested build.')
    contract = {
        'pi': {'version': pi['@earendil-works/pi-coding-agent']['version'], 'ownership': 'bundled',
               'sha256': hashlib.sha256(json.dumps(closure, sort_keys=True, separators=(',', ':')).encode()).hexdigest()},
        'dsh': {'version': dsh['version'], 'ownership': 'bundled', 'sha256': hashlib.sha256(dsh_raw).hexdigest()},
        'codex': {'version': codex['version'], 'ownership': 'external', 'sha256': hashlib.sha256(codex_raw).hexdigest()},
    }
    return validate_contract(contract)


def refusal(root, candidate, choices):
    """Whole-bundle updates may not replace a component whose consent is off."""
    try:
        validate_choices(choices)
        if not choices['augmentor']:
            return 'Automatic Augmentor Agent updates are turned off.'
        current = installed(root)
        if current is None:
            return 'Install the manual bridge release before using component update controls.'
        target = validate_contract(candidate.get('updateComponents'))
        for key in HARNESS_IDS:
            if current[key] != target[key]:
                if not choices[key]:
                    return f'This release also changes {NAMES[key]}; its automatic updates are turned off.'
                if current[key]['ownership'] == 'external':
                    return f'This release requires a separately verified {NAMES[key]} update.'
    except (OSError, ValueError, KeyError, TypeError):
        return 'The component update identities or consent are unavailable. Use manual installation.'
    return None


def rows(root, current):
    contract = installed(root) or {}
    result = []
    for key, name in NAMES.items():
        row = contract.get(key)
        result.append({'id': key, 'name': name,
            'version': current['version'] if key == 'augmentor' else row['version'] if row and key != 'codex' else None,
            'requiredVersion': row['version'] if row and key == 'codex' else None,
            'ownership': 'application' if key == 'augmentor' else row['ownership'] if row else 'unknown'})
    return result


def verify_target(root, candidate):
    target = installed(root)
    if target is None or target != validate_contract(candidate.get('updateComponents')):
        raise ValueError('The staged harness identities differ from the signed release.')
    return True
