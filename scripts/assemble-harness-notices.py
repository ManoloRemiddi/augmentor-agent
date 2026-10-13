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


def assemble(app, baseline):
    app, baseline = Path(app).resolve(), Path(baseline).resolve()
    if (app / 'desktop-release.json').exists():
        raise ValueError('Never change a staged release; use an unselected assembly.')
    if app == baseline or app.is_relative_to(baseline) or baseline.is_relative_to(app):
        raise ValueError('Keep the assembly separate from its baseline.')
    previous = inventory.verify(baseline)
    if native_files(app) != native_files(baseline):
        raise ValueError('Dependency/Node native bytes differ; review their source and notices before assembly.')
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
    require('licenses/node.txt', baseline / 'licenses/node.txt')
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
    for name in ('dsh-attachment', 'dsh-file-reference', 'dsh-preview', 'dsh-model-discovery', 'dsh-office', 'dsh-plugin-wiki-tools', 'dsh-plugin-wiki-skills'):
        # Office's TypeScript is compiled by tsc; its notice inputs stay in
        # preferred source, unlike the copied JavaScript vendor directories.
        vendor = app / ('packages/runtime/vendor' if name == 'dsh-office' else 'dist/runtime/vendor') / name
        for filename in ('LICENSE', 'SOURCE.json'):
            require('licenses/' + name + '/' + filename, vendor / filename)
        for filename in ('SOURCE.md', 'ORIGINAL_LICENSE'):
            if (vendor / filename).exists():
                require('licenses/' + name + '/' + filename, vendor / filename)
    for relative in closure:
        target = app / relative
        if target.is_symlink() or not target.resolve().is_relative_to(app):
            raise ValueError('Notice destination escapes its unselected assembly.')
    # Validate every input before changing even the unselected destination.
    for relative, content in closure.items():
        target = app / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return {'baselineArtifactSha256': previous['artifactSha256'], 'dependencyNativeFiles': len(native_files(app)),
            'writtenNoticeFiles': len(closure), 'publicBinaryRedistributionQualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assemble(args.app, args.baseline), indent=2))
