# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Refuse altered copies of actual signed source metadata; no network or installation."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    tool = Path(__file__).with_name('acquire-ubuntu-toolchain-sources.py')
    spec = importlib.util.spec_from_file_location('source_auth_refusal', tool)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    records = module.authenticate(policy, args.root)
    module.dsc_crosscheck(records, args.root / 'objects')
    cases = {}
    def refuse(name, changed, root, required=None):
        try:
            module.authenticate(changed, root)
        except (ValueError, KeyError) as error:
            if required and required not in str(error):
                raise
            cases[name] = {'refused': True, 'error': str(error)}
        else:
            raise RuntimeError(name + ' unexpectedly accepted')
    mutations = [
        ('wrong-reference-pin', lambda p: p['binaryLock'].update(sha256='0' * 64)),
        ('wrong-keyring', lambda p: p['keyring'].update(sha256='0' * 64)),
        ('changed-signed-release', lambda p: p['releases'][0].update(sha256='0' * 64)),
        ('changed-compressed-index', lambda p: p['indexes'][0].update(sha256='0' * 64)),
        ('changed-plain-index', lambda p: p['indexes'][0].update(plainSha256='0' * 64)),
        ('wrong-source-version', lambda p: p['sources'][0].update(sourceVersion='unverified')),
        ('duplicate-source', lambda p: p['sources'].append(p['sources'][0])),
        ('wrong-source-object-hash', lambda p: p['objects'][0].update(sha256='0' * 64)),
        ('unapproved-download', lambda p: p['objects'][0].update(urls=['https://example.com/unverified'])),
        ('escaping-source-path', lambda p: p['objects'][0].update(path='../escape'))]
    for name, mutate in mutations:
        changed = copy.deepcopy(policy); mutate(changed); refuse(name, changed, args.root)
        print(name + ': refused', flush=True)
    with tempfile.TemporaryDirectory(prefix='augmentor-source-signature-refusal-') as directory:
        root = Path(directory)
        for dirname in ('metadata', 'references'):
            shutil.copytree(args.root / dirname, root / dirname)
        changed = copy.deepcopy(policy); name = changed['releases'][0]['path']
        original = (root / name).read_bytes()
        if b'Origin: Ubuntu' not in original:
            raise ValueError('Unexpected original Ubuntu release.')
        data = original.replace(b'Origin: Ubuntu', b'Origin: Changed', 1)
        (root / name).write_bytes(data)
        changed['releases'][0].update(sha256=hashlib.sha256(data).hexdigest(), size=len(data))
        refuse('invalid-signature-with-updated-local-hash', changed, root, 'signature')
    with tempfile.TemporaryDirectory(prefix='augmentor-source-object-refusal-') as directory:
        root = Path(directory); row = next(r for r in policy['objects'] if r['path'].endswith('.dsc'))
        original = args.root / 'objects' / row['path']
        if module.sha(original) != row['sha256']:
            raise ValueError('Original source control object changed.')
        target = root / row['path']; target.parent.mkdir(parents=True)
        target.write_bytes(b'X' + original.read_bytes()[1:])
        try:
            module.acquire(row, root)
        except ValueError as error:
            cases['changed-existing-source-object'] = {'refused': True, 'error': str(error)}
        else:
            raise RuntimeError('Changed source object unexpectedly accepted')
    report = {'format': 'augmentor-toolchain-source-authentication-refusal/1',
        'toolSha256': module.sha(tool), 'probeSha256': module.sha(Path(__file__)),
        'policySha256': module.sha(args.policy), 'cases': cases,
        'originalMetadataMutated': False, 'originalSourceObjectsMutated': False,
        'sourceObjectsExecuted': False, 'packagesInstalled': False, 'networkUsed': False}
    with (args.root / 'source-authentication-probe-result.json').open('x') as output:
        json.dump(report, output, indent=2); output.write('\n')
    print(str(len(cases)) + ' actual source authentication refusals passed.', flush=True)


if __name__ == '__main__':
    main()
