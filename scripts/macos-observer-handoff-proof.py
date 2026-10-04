#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual source→retained exec and production refusal using only private fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'services'))
from lifecycle.macos_payload import verify_bundle
from platform_adapters.paths import private_directory
from platform_adapters.private_files import require_directory,read_json


def proof(original,retained,home):
    if sys.platform!='darwin':raise RuntimeError('This fixture requires native Mac process identity.')
    original,retained,home=map(lambda path:Path(path).resolve(),(original,retained,home))
    if home.exists() or home.is_symlink():raise ValueError('Use a new private fixture home.')
    require_directory(private_directory(home))
    base=home/'Library/Application Support/Augmentor'
    for part in ('config','data','state'):require_directory(private_directory(base/part))
    updates=require_directory(private_directory(base/'data/augmentor/updates'))
    transactions=require_directory(private_directory(base/'state/augmentor/updates'))
    attempt=secrets.token_hex(24)
    observers=require_directory(private_directory(base/'cache/update-observers'))
    directory=require_directory(private_directory(observers/('mac-'+attempt)))
    observer=directory/'Observer.app'
    release=(retained/'Contents/Resources/app/release.json').read_bytes()
    payload=verify_bundle(retained,release,development=True)
    # This already-verified disposable bundle is no longer executing any code.
    # Moving it avoids another multi-gigabyte copy. The original stays untouched.
    retained.rename(observer)
    if verify_bundle(observer,release,development=True)!=payload:raise ValueError('Relocation changed the observer fixture.')
    source=home/'Applications/Augmentor Agent Desktop.app'
    # Source directory deliberately does not exist: the production guard must
    # refuse this development observer before any source inspection/drain/write.
    environment={key:value for key,value in os.environ.items() if not key.startswith(('XDG_','AUGMENTOR_','PYTHON','NODE_'))}
    environment.update(HOME=str(home),XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),
        XDG_STATE_HOME=str(base/'state'),XDG_RUNTIME_DIR='/tmp/augmentor-'+str(os.getuid()))
    arguments=[str(observer/'Contents/Resources/app/python/bin/python3'),'-I','-B',
        str(observer/'Contents/Resources/app/scripts/macos-update-observer.py'),'--attempt',attempt,
        '--source-bundle',str(source),'--source-release-sha256',hashlib.sha256(release).hexdigest(),
        '--source-payload-sha256',payload['sha256']]
    launcher="""import fcntl,os,sys
fd=os.open(sys.argv[1],os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);os.set_inheritable(fd,True)
args=sys.argv[2:]+['--bootstrap-fd',str(fd)]
os.execv(args[0],args)
"""
    result=subprocess.run([str(original/'Contents/Resources/app/python/bin/python3'),'-I','-B','-c',launcher,
        str(transactions/'bootstrap.lock'),*arguments],env=environment,stdin=subprocess.DEVNULL,capture_output=True,timeout=45)
    record=read_json(transactions/('attempt-'+attempt+'.json'))
    if (result.returncode==0 or record['outcome']!='deferred'
            or record['error']!='Public update inspection requires a signed, notarized release.'
            or record['transactionId'] is not None or (transactions/'active.json').exists() or source.exists()):
        raise ValueError('The actual retained observer did not refuse the development fixture before source work: '+
            str(record.get('error','Unknown fixture result.'))[:512])
    if verify_bundle(observer,release,development=True)!=payload:raise ValueError('The retained exec changed the immutable bundle.')
    return {'actualRetainedExec':True,'inheritedBootstrapLockBound':True,'developmentProductionRefused':True,
        'noSourceDrainOrApply':True,'retainedPayloadPreserved':True,
        'scope':'Private native negative boundary; no signed publisher, qualified forward update or user installation.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('original','retained','home'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(proof(args.original,args.retained,args.home)))
