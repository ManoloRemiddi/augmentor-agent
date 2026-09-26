#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Inventory actual production npm packages and collect reviewed license texts.

This audits package licensing, not static native-binary dependencies. Run against
the staged release after npm ci and deliberate optional-component exclusions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PERMISSIVE = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', '0BSD', 'BlueOak-1.0.0', 'Unlicense', 'Python-2.0'}
LICENSE_NAME = re.compile(r'^(licen[sc]e|copying)(\.|$|-)', re.I)
NOTICE_NAME = re.compile(r'^(notice|copyright)(\.|$|-)', re.I)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def package_dirs(modules):
    if not modules.is_dir():
        return
    for item in sorted(modules.iterdir()):
        if item.name.startswith('.'):
            continue
        children = sorted(item.iterdir()) if item.name.startswith('@') else [item]
        for package in children:
            if (package / 'package.json').is_file():
                yield package
                yield from package_dirs(package / 'node_modules')


def inventory(tree, catalog_root):
    lock = json.loads((tree / 'package-lock.json').read_text())['packages']
    catalog = json.loads((catalog_root / 'catalog.json').read_text())
    for name, source in catalog['sources'].items():
        if digest((catalog_root / source['file']).read_bytes()) != source['sha256']:
            raise ValueError(f'{name}: reviewed license hash changed')
    components, texts, errors = [], {}, []
    for package in package_dirs(tree / 'node_modules'):
        relative = package.relative_to(tree).as_posix()
        meta = json.loads((package / 'package.json').read_text())
        key = meta['name'] + '@' + meta['version']
        locked = lock.get(relative)
        if locked is None:
            errors.append(f'{relative}: package is not in the lock'); continue
        if locked.get('dev'):
            errors.append(f'{relative}: development package in release tree'); continue
        if locked['version'] != meta['version'] or locked.get('license') != meta.get('license'):
            errors.append(f'{relative}: installed metadata differs from lock'); continue
        effective_license=meta.get('license')
        choice=catalog.get('choices',{}).get(key)
        if choice and choice.get('expression')==effective_license:effective_license=choice.get('selected')
        if effective_license not in PERMISSIVE and catalog.get('additionalLicenses',{}).get(key) != effective_license:
            errors.append(f'{key}: unreviewed license {meta.get("license")}'); continue
        files = [p for p in sorted(package.iterdir()) if p.is_file() and LICENSE_NAME.match(p.name)]
        sources = []
        for file in files:
            content = file.read_bytes(); sha = digest(content); texts[sha] = content
            sources.append({'path': file.relative_to(tree).as_posix(), 'sha256': sha})
        if not files:
            override = catalog['overrides'].get(key)
            if override:
                entry = catalog['sources'][override]
                content = (catalog_root / entry['file']).read_bytes(); sha = digest(content)
                if sha != entry['sha256']:
                    errors.append(f'{key}: reviewed license hash changed'); continue
                texts[sha] = content
                sources.append({'path': 'licenses/' + entry['file'], 'url': entry['url'], 'sha256': sha})
            else:
                # Some packages reproduce the complete MIT grant in README.
                readme = package / 'README.md'
                content = readme.read_bytes() if readme.exists() else b''
                if meta['license'] == 'MIT' and b'Permission is hereby granted' in content and b'copyright' in content.lower() and b'WARRANT' in content:
                    sha = digest(content); texts[sha] = content
                    sources.append({'path': readme.relative_to(tree).as_posix(), 'sha256': sha})
                else:
                    errors.append(f'{key}: missing reviewed license text'); continue
        for file in sorted(package.iterdir()):
            if file.is_file() and NOTICE_NAME.match(file.name):
                content = file.read_bytes(); sha = digest(content); texts[sha] = content
                sources.append({'path': file.relative_to(tree).as_posix(), 'sha256': sha})
        components.append({'name': meta['name'], 'version': meta['version'], 'path': relative,
                           'license': effective_license, 'declaredLicense':meta['license'], 'integrity': locked.get('integrity'), 'notices': sources})
    if errors:
        raise ValueError('\n'.join(errors))
    if not components:
        raise ValueError('No installed production packages found')
    return {'format': 'augmentor-npm-notices/1', 'components': components}, texts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        report, texts = inventory(args.tree.resolve(), ROOT / 'licenses')
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
    args.out.mkdir(parents=True, exist_ok=True)
    text_dir = args.out / 'texts'; text_dir.mkdir(exist_ok=True)
    for sha, content in texts.items():
        (text_dir / (sha + '.txt')).write_bytes(content)
    (args.out / 'npm-components.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Collected notices for {len(report["components"])} production package instances.')


if __name__ == '__main__':
    main()
