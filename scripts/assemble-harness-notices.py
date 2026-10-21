#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Complete an unselected private preview's notices; public binary gates stay separate."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != 'linux':
    raise SystemExit('Private Harness notice assembly currently requires Linux qualification.')
spec = importlib.util.spec_from_file_location('harness_notice_inventory', ROOT / 'scripts/desktop-deployment.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def native_files(root):
    result = {}
    for part in ('node', 'node_modules'):
        for path in (root / part).rglob('*'):
            if not path.is_file() or path.is_symlink():
                continue
            with path.open('rb') as stream:
                magic = stream.read(4)
            if magic in (b'\x7fELF', b'\0asm'):
                result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def assemble(app, baseline, node_notice_baseline=None):
    app, baseline = Path(app).resolve(), Path(baseline).resolve()
    if (app / 'desktop-release.json').exists():
        raise ValueError('Never change a staged release; use an unselected assembly.')
    if app == baseline or app.is_relative_to(baseline) or baseline.is_relative_to(app):
        raise ValueError('Keep the assembly separate from its baseline.')
    previous = inventory.verify(baseline)
    current_native = native_files(app)
    if current_native != native_files(baseline):
        raise ValueError('Dependency/Node native bytes differ; review their source and notices before assembly.')
    # An explicit second sealed artifact may supply the Node notice when the
    # main private baseline lacks it. Its exact Node binary must still match;
    # it supplies no dependency, source or other native notice authority.
    node_baseline = Path(node_notice_baseline).resolve() if node_notice_baseline is not None else baseline
    node_release = previous if node_baseline == baseline else inventory.verify(node_baseline)
    node_sha256 = current_native.get('node/bin/node')
    if not node_sha256 or node_release['files'].get('node/bin/node') != node_sha256:
        raise ValueError('Node notice baseline does not contain the exact bundled Node binary.')
    web = app / 'dist/harness-web'
    provenance = json.loads((web / 'SOURCE.json').read_text())
    closure = {}
    def require(destination, source):
        source = Path(source)
        if not source.is_file() or source.is_symlink():
            raise ValueError('Missing regular notice input: ' + str(source))
        closure[destination] = source.read_bytes()
    for relative in previous['files']:
        if relative.startswith('licenses/') and not (app / relative).exists():
            require(relative, baseline / relative)
    require('licenses/node.txt', node_baseline / 'licenses/node.txt')
    require('licenses/dsh-gui/THIRD-PARTY-NOTICES.txt', web / 'THIRD-PARTY-NOTICES.txt')
    require('licenses/dsh-gui/SOURCE.json', web / 'SOURCE.json')
    for name, key in (('dsh', None), ('dsh-context', 'dshContext'), ('dsh-metafolder', 'dshMetafolder'), ('augmentor-brand', 'augmentorBrand')):
        seat = 'dsh-gui' if name == 'dsh' else name
        vendor = app / 'apps/harness/vendor' / name
        require('licenses/' + seat + '/LICENSE', vendor / 'LICENSE')
        if key:
            selected = json.loads((vendor / 'SOURCE.json').read_text())
            if selected != provenance[key]:
                raise ValueError('Compiled supplier provenance differs from its selected source: ' + name)
            require('licenses/' + seat + '/SOURCE.json', vendor / 'SOURCE.json')
    for name in ('dsh-attachment', 'dsh-file-reference', 'dsh-preview', 'dsh-model-discovery', 'dsh-office', 'dsh-plugin-wiki-tools', 'dsh-plugin-wiki-skills', 'dsh-session-log-export'):
        # Office's TypeScript is compiled by tsc; its notice inputs stay in
        # preferred source, unlike the copied JavaScript vendor directories.
        vendor = app / ('packages/runtime/vendor' if name == 'dsh-office' else 'dist/runtime/vendor') / name
        for filename in ('LICENSE', 'SOURCE.json'):
            require('licenses/' + name + '/' + filename, vendor / filename)
        for filename in ('SOURCE.md', 'ORIGINAL_LICENSE'):
            if (vendor / filename).exists():
                require('licenses/' + name + '/' + filename, vendor / filename)
    search_records = 0
    def search_selection(vendor, seat, expected=None, *, notices=('LICENSE',), count=True):
        nonlocal search_records
        if vendor.is_symlink() or not vendor.resolve().is_relative_to(app):
            raise ValueError('Search source escapes its unselected assembly.')
        metadata = vendor / 'SOURCE.json'
        if metadata.is_symlink() or not metadata.resolve().is_relative_to(vendor.resolve()):
            raise ValueError('Search source escapes its selected directory.')
        selected = json.loads(metadata.read_text())
        if expected is not None and selected != expected:
            raise ValueError('Compiled search provenance differs from its selected source.')
        records = selected.get('files')
        if not isinstance(records, list) or not records or not set(notices).issubset({row['path'] for row in records}):
            raise ValueError('Search source selection is missing.')
        for row in records:
            relative = Path(row['path'])
            source = vendor / relative
            if relative.is_absolute() or '..' in relative.parts or source.is_symlink() or not source.resolve().is_relative_to(vendor.resolve()):
                raise ValueError('Search source escapes its selected directory.')
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Selected search source changed: ' + str(relative))
        if count:
            search_records += len(records)
        for filename in ('SOURCE.json', *notices):
            require('licenses/' + seat + '/' + filename, vendor / filename)
        for filename in ('SOURCE.md', 'SELECTION.json'):
            if (vendor / filename).exists():
                require('licenses/' + seat + '/' + filename, vendor / filename)
        return selected
    for name in ('dsh-web-search-free', 'keyless-search', 'dsh-keyless-fetch'):
        preferred = app / 'packages/runtime/vendor' / name
        compiled = app / 'dist/runtime/vendor' / name
        notices = ('LICENSE-dddmuc', 'LICENSE-shinjiyu') if name == 'keyless-search' else ('LICENSE',)
        # Validate both trees before any destination is changed; only count the
        # selection once, while preserving the original supplier notices.
        selected = search_selection(preferred, name + '/runtime', notices=notices)
        search_selection(compiled, name + '/runtime', selected, notices=notices, count=False)
        if (preferred / 'SOURCE.json').read_bytes() != (compiled / 'SOURCE.json').read_bytes():
            raise ValueError('Compiled search selection differs from its preferred source.')
    search_selection(app / 'apps/harness/vendor/dsh-web-search-free', 'dsh-web-search-free/client', provenance.get('dshFreeSearch', {}))
    for relative in closure:
        target = app / relative
        if target.is_symlink() or not target.resolve().is_relative_to(app):
            raise ValueError('Notice destination escapes its unselected assembly.')
    # Validate every input before changing even the unselected destination.
    for relative, content in closure.items():
        target = app / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return {'baselineArtifactSha256': previous['artifactSha256'], 'dependencyNativeFiles': len(current_native),
            'nodeNoticeBaselineArtifactSha256': node_release['artifactSha256'], 'nodeNoticeBinarySha256': node_sha256,
            'writtenNoticeFiles': len(closure), 'verifiedSearchSourceRecords': search_records,
            'publicBinaryRedistributionQualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--node-notice-baseline', type=Path, help='Optional verified sealed artifact with the identical Node binary and its original notice.')
    args = parser.parse_args()
    print(json.dumps(assemble(args.app, args.baseline, args.node_notice_baseline), indent=2))
