# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise real signed-kit refusal paths without changing original metadata.

Run after successful separate package acquisition. All altered inputs are local
copies or in-memory policies; no network, package installation or trust changes.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',required=True,type=Path);parser.add_argument('--root',required=True,type=Path)
    args=parser.parse_args();policy=json.loads(args.policy.read_text())
    tool=Path(__file__).with_name('acquire-ubuntu-toolchain.py')
    spec=importlib.util.spec_from_file_location('toolchain_acquisition_probe',tool)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.authenticate(policy,args.root)
    cases={}
    for name,mutate in [
        ('wrong-keyring',lambda p:p['keyring'].update(sha256='0'*64)),
        ('changed-signed-release',lambda p:p['releases'][0].update(sha256='0'*64)),
        ('changed-full-index',lambda p:p['indexes'][0].update(sha256='0'*64)),
        ('wrong-binary-hash',lambda p:p['packages'][0].update(sha256='0'*64)),
        ('wrong-source-version',lambda p:p['packages'][0].update(sourceVersion='unverified')),
        ('duplicate-package',lambda p:p['packages'].append(p['packages'][0])),
        ('unapproved-download',lambda p:p['packages'][0].update(urls=['https://example.com/'+p['packages'][0]['filename']])),
        ('escaping-metadata',lambda p:p['keyring'].update(path='../keyring'))]:
        changed=copy.deepcopy(policy);mutate(changed)
        try:module.authenticate(changed,args.root)
        except (ValueError,KeyError) as error:cases[name]={'refused':True,'error':str(error)}
        else:raise AssertionError(name+' unexpectedly accepted')
    with tempfile.TemporaryDirectory(prefix='augmentor-toolchain-signature-refusal-') as directory:
        root=Path(directory);(root/'metadata').mkdir()
        shutil.copyfile(args.root/policy['keyring']['path'],root/policy['keyring']['path'])
        changed=copy.deepcopy(policy);name=changed['releases'][0]['path'];data=(args.root/name).read_bytes()
        if b'Origin: Ubuntu' not in data:raise ValueError('Unexpected original Ubuntu release.')
        data=data.replace(b'Origin: Ubuntu',b'Origin: Changed',1);(root/name).write_bytes(data)
        changed['releases'][0]['sha256']=hashlib.sha256(data).hexdigest()
        try:module.authenticate(changed,root)
        except ValueError as error:
            if 'signature' not in str(error):raise
            cases['invalid-signature-with-updated-local-hash']={'refused':True,'error':str(error)}
        else:raise AssertionError('Invalid signature accepted')
    with tempfile.TemporaryDirectory(prefix='augmentor-toolchain-package-refusal-') as directory:
        root=Path(directory);row=policy['packages'][0];name=Path(row['filename']).name
        data=(args.root/'debs'/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Original package was changed.')
        (root/name).write_bytes(b'X'+data[1:])
        try:module.acquire(row,root)
        except ValueError as error:cases['changed-existing-package-body']={'refused':True,'error':str(error)}
        else:raise AssertionError('Changed package accepted')
    report={'format':'augmentor-toolchain-authentication-refusal/1',
        'toolSha256':hashlib.sha256(tool.read_bytes()).hexdigest(),
        'probeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'policySha256':hashlib.sha256(args.policy.read_bytes()).hexdigest(),
        'cases':cases,'signedMetadataMutated':False,'packagesInstalled':False}
    with (args.root/'authentication-probe-result.json').open('x') as output:output.write(json.dumps(report,indent=2)+'\n')
    print('Ten actual metadata/signature/package refusal cases pass.')


if __name__=='__main__':main()
