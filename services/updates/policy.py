# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exact installed identity and release eligibility; never imports candidate code."""
import json
import platform
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = 'augmentor-update-catalog/1'
CHANNELS = ('stable', 'preview')
INSTALL_TYPES = ('managed-linux', 'debian', 'fedora', 'macos-app', 'windows-inno', 'development')
ROLES = ('runtime', 'desktop', 'browser', 'installer', 'bundle')
VERSION = re.compile(r'(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})\Z')
HEX = re.compile(r'[a-f0-9]{64}\Z')
COMMIT = re.compile(r'[a-f0-9]{40}\Z')
MAX_ARTIFACT = 2 * 1024**3


def version(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError('Unsupported product version.')
    return tuple(map(int, value.split('.')))


def canonical_release_url(value):
    if not isinstance(value, str):
        raise ValueError('Invalid release link.')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query or parsed.fragment
            or not re.fullmatch(r'/ManoloRemiddi/augmentor-agent/releases/tag/[A-Za-z0-9._-]{1,128}', parsed.path)):
        raise ValueError('Use the official Augmentor release page.')
    return value


def target_path(value):
    # This is a URL path beneath the canonical artifact host, never a filesystem
    # path, script, arbitrary URL or caller-provided download destination.
    if (not isinstance(value, str) or len(value) > 400 or
            not re.fullmatch(r'releases/download/[A-Za-z0-9._-]{1,128}/[A-Za-z0-9._-]{1,200}', value)
            or any(part in ('.', '..') for part in value.split('/'))):
        raise ValueError('Unsupported release artifact location.')
    return value


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError('Unsupported update metadata fields.')


def _schemas(value):
    current, readable = value.get('dataSchema'), value.get('readableDataSchemas')
    if (type(current) is not int or current < 1 or not isinstance(readable, list)
            or not 1 <= len(readable) <= 16 or any(type(n) is not int or n < 1 for n in readable)
            or len(set(readable)) != len(readable) or current not in readable):
        raise ValueError('Invalid update data compatibility.')


def validate_release(value):
    _keys(value, ('version', 'build', 'sourceCommit', 'channel', 'target', 'installType', 'releaseUrl',
                  'protocols', 'dataSchema', 'readableDataSchemas', 'minimumOS', 'artifacts'),
          ('revoked', 'notes', 'minimumUpdater', 'distributions'))
    version(value['version'])
    if type(value['build']) is not int or not 1 <= value['build'] <= 2**31 - 1:
        raise ValueError('Invalid release build sequence.')
    if not isinstance(value['sourceCommit'], str) or not COMMIT.fullmatch(value['sourceCommit']):
        raise ValueError('Invalid release source identity.')
    if value['channel'] not in CHANNELS or value['installType'] not in INSTALL_TYPES[:-1]:
        raise ValueError('Unsupported update channel or installation method.')
    if value['target'] not in ('linux-x64', 'linux-arm64', 'macos-x64', 'macos-arm64', 'windows-x64', 'windows-arm64'):
        raise ValueError('Unsupported release target.')
    expected_os = {'managed-linux': 'linux', 'debian': 'linux', 'fedora': 'linux',
                   'macos-app': 'macos', 'windows-inno': 'windows'}[value['installType']]
    if not value['target'].startswith(expected_os + '-'):
        raise ValueError('Release installation method and target disagree.')
    distributions = value.get('distributions')
    if expected_os == 'linux':
        if (not isinstance(distributions, dict) or not 1 <= len(distributions) <= 8
                or any(name not in ('debian', 'ubuntu', 'fedora') or not isinstance(floor, str)
                       or not re.fullmatch(r'[0-9]{1,6}(?:\.[0-9]{1,6}){0,2}', floor)
                       for name, floor in distributions.items())):
            raise ValueError('Linux updates require explicit supported distribution versions.')
    elif distributions is not None:
        raise ValueError('Distribution requirements only apply to Linux updates.')
    canonical_release_url(value['releaseUrl'])
    protocols = value['protocols']
    if (not isinstance(protocols, dict) or not 1 <= len(protocols) <= 16 or
            any(not isinstance(k, str) or not re.fullmatch('[a-z][a-zA-Z0-9]{0,31}', k)
                or not isinstance(v, str) or not re.fullmatch('[a-zA-Z0-9-]{1,64}/[1-9][0-9]{0,3}', v)
                for k, v in protocols.items())):
        raise ValueError('Invalid release protocol requirements.')
    _schemas(value)
    if not isinstance(value['minimumOS'], str) or not re.fullmatch(r'[0-9]{1,6}(?:\.[0-9]{1,6}){0,2}', value['minimumOS']):
        raise ValueError('Invalid minimum operating system.')
    if 'revoked' in value and type(value['revoked']) is not bool:
        raise ValueError('Invalid release revocation.')
    if 'notes' in value and (not isinstance(value['notes'], str) or len(value['notes']) > 4000):
        raise ValueError('Invalid release notes.')
    if 'minimumUpdater' in value and (type(value['minimumUpdater']) is not int or not 1 <= value['minimumUpdater'] <= 1000):
        raise ValueError('Invalid updater requirement.')
    artifacts = value['artifacts']
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 8:
        raise ValueError('Invalid update artifact set.')
    roles = set(); paths = set()
    for item in artifacts:
        _keys(item, ('role', 'targetPath', 'bytes', 'sha256'))
        if item['role'] not in ROLES or item['role'] in roles or item['targetPath'] in paths:
            raise ValueError('Duplicate or unsupported update component.')
        roles.add(item['role'])
        paths.add(item['targetPath'])
        target_path(item['targetPath'])
        if type(item['bytes']) is not int or not 0 < item['bytes'] <= MAX_ARTIFACT:
            raise ValueError('Invalid update artifact size.')
        if not isinstance(item['sha256'], str) or not HEX.fullmatch(item['sha256']):
            raise ValueError('Invalid update artifact digest.')
    needed = {'debian': {'runtime', 'desktop', 'browser'}, 'macos-app': {'bundle'},
              'windows-inno': {'installer'}, 'managed-linux': {'bundle'}, 'fedora': {'bundle'}}[value['installType']]
    if not needed <= roles:
        raise ValueError('The release is missing a required update component.')
    return value


def validate_catalog(value):
    _keys(value, ('schema', 'releases'))
    if value['schema'] != SCHEMA or not isinstance(value['releases'], list) or len(value['releases']) > 256:
        raise ValueError('Unsupported update catalog.')
    identities = set()
    for item in value['releases']:
        validate_release(item)
        identity = (item['channel'], item['target'], item['installType'], item['version'], item['build'])
        if identity in identities:
            raise ValueError('The update catalog has ambiguous release identities.')
        identities.add(identity)
    return value


def machine_target(os_name=None, machine=None):
    os_name = os_name or sys.platform
    machine = (machine or platform.machine()).lower()
    arch = {'x86_64': 'x64', 'amd64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}.get(machine)
    operating_system = {'linux': 'linux', 'darwin': 'macos', 'win32': 'windows'}.get(os_name)
    return operating_system + '-' + arch if operating_system and arch else None


def installed_identity(root, *, target=None):
    root = Path(root)
    product = json.loads((root / 'release/product.json').read_text())
    receipt = json.loads((root / 'release.json').read_text()) if (root / 'release.json').is_file() else {}
    managed = json.loads((root / 'desktop-release.json').read_text()) if (root / 'desktop-release.json').is_file() else {}
    raw_target = receipt.get('target', '')
    target = target or machine_target()
    method = 'development'
    if managed:
        method = 'managed-linux' if target and target.startswith('linux-') else 'development'
    elif raw_target.startswith('debian'):
        method = 'debian'
    elif (root / 'fedora-package.json').is_file():
        method = 'fedora'
    elif raw_target.startswith('macos-'):
        method = 'macos-app'
    elif raw_target.startswith('windows-'):
        method = 'windows-inno'
    stamp = receipt.get('update', {})
    if not isinstance(stamp, dict) or type(stamp.get('build', 0)) is not int or not 0 <= stamp.get('build', 0) <= 2**31-1:
        raise ValueError('The installed release build identity is invalid. Repair the installed application.')
    # Legacy managed overlays do not assert that their compatible product version
    # is an unmodified public build. They need an explicit migration before auto.
    return {'version': receipt.get('version', product['version']), 'build': stamp.get('build', 0),
            'buildKnown': stamp.get('build', 0) > 0,
            'sourceCommit': receipt.get('sourceCommit', receipt.get('source', {}).get('commit')),
            'target': target, 'installType': method, 'channel': receipt.get('channel', product['channel']),
            'protocols': receipt.get('protocols', product['protocols']),
            'dataSchema': receipt.get('dataSchema', product['dataSchema']),
            'readableDataSchemas': receipt.get('readableDataSchemas', product['readableDataSchemas']),
            'releaseId': stamp.get('releaseId', managed.get('deployment', {}).get('releaseId')),
            'automaticInstallQualified': stamp.get('automaticInstallQualified') is True,
            'updaterVersion': 1}


def eligibility(current, release, channel, *, os_version=None, distribution=None):
    validate_release(release)
    if release.get('revoked'):
        return 'This release was withdrawn.'
    if release['channel'] != channel or release['target'] != current['target']:
        return 'This release targets another channel or processor.'
    if release['installType'] != current['installType']:
        return 'This release uses another installation method.'
    if release['version'] == current['version'] and not current.get('buildKnown', True):
        return 'The installed build identity is missing. Install the supported updater bridge first.'
    if (version(release['version']), release['build']) <= (version(current['version']), current['build']):
        return 'This release is already installed or older.'
    if release.get('minimumUpdater', 1) > current.get('updaterVersion', 1):
        return 'Install the supported updater bridge release first.'
    if release['protocols'] != current['protocols']:
        return 'This release requires a supported component migration.'
    if (current['dataSchema'] not in release['readableDataSchemas'] or
            release['dataSchema'] not in current['readableDataSchemas']):
        return 'This release requires a supported data migration.'
    numbers = lambda value: tuple(int(p) for p in value.split('.')) + (0,) * (3 - len(value.split('.')))
    if release['target'].startswith('linux-'):
        if not distribution or distribution[0] not in release['distributions']:
            return 'This release is not qualified for this Linux distribution.'
        if numbers(distribution[1]) < numbers(release['distributions'][distribution[0]]):
            return 'This release requires a newer Linux distribution.'
    if os_version is not None:
        if numbers(os_version) < numbers(release['minimumOS']):
            return 'This release requires a newer operating system.'
    return None


def select_release(catalog, current, channel, *, os_version=None, distribution=None):
    validate_catalog(catalog)
    releases = [r for r in catalog['releases'] if eligibility(current, r, channel, os_version=os_version, distribution=distribution) is None]
    return max(releases, key=lambda r: (version(r['version']), r['build'])) if releases else None
