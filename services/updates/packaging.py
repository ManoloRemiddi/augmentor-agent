# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared release-build identity and public updater inputs for every packager."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

SCHEMA = 'augmentor-update-receipt/1'
REPOSITORY_KEYS = {'schema', 'enabled', 'metadataBaseUrl', 'catalogBaseUrl', 'artifactBaseUrl', 'rootFile'}


def source_revision(root, *, build=0, declared=None):
    if type(build) is not int or not 0 <= build <= 2**31-1:
        raise ValueError('Invalid reviewed release build sequence.')
    root = Path(root).resolve()
    command=['git','-c','safe.directory='+str(root)]
    environment={key:value for key,value in os.environ.items() if not key.startswith('GIT_')}
    revision=subprocess.check_output([*command,'rev-parse','HEAD'],cwd=root,text=True,timeout=10,env=environment).strip()
    dirty=bool(subprocess.check_output([*command,'status','--porcelain'],cwd=root,text=True,timeout=10,env=environment).strip())
    if not re.fullmatch('[a-f0-9]{40}',revision) or declared is not None and declared != revision:
        raise ValueError('The declared release source differs from the actual checkout.')
    if build and dirty:
        raise ValueError('A numbered release requires a clean reviewed source checkout.')
    return {'commit':revision,'dirty':dirty}


def build_receipt(*, version, source_commit, target, channel, build=0, component='desktop'):
    if (not isinstance(version, str) or not re.fullmatch(r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', version)
            or not isinstance(source_commit, str) or not re.fullmatch('[a-f0-9]{40}', source_commit)
            or target not in {'linux-x64', 'linux-arm64', 'macos-x64', 'macos-arm64', 'windows-x64', 'windows-arm64'}
            or channel not in {'stable', 'preview', 'development'}
            or component not in {'desktop', 'companion'} or (component=='companion' and not target.startswith('macos-'))
            or type(build) is not int or not 0 <= build <= 2**31-1):
        raise ValueError('Invalid release-build identity.')
    # Zero is an unnumbered test candidate. Only a reviewed publisher-assigned
    # positive value establishes ordering between builds of one product version.
    values = {'version': version, 'sourceCommit': source_commit, 'target': target, 'channel': channel, 'build': build, 'component':component}
    identity = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'schema': SCHEMA, 'build': build, 'releaseId': identity, 'automaticInstallQualified': False}


def stage_repository(source, destination, *, node):
    """Copy exactly the reviewed config and public root, never a key directory."""
    source, destination = Path(source), Path(destination)
    config_file = source/'release/updates.json'
    if config_file.is_symlink() or not config_file.is_file() or config_file.stat().st_size > 65536:
        raise ValueError('The updater configuration must be an ordinary bounded file.')
    config = json.loads(config_file.read_text(encoding='utf-8'))
    if (not isinstance(config, dict) or set(config) != REPOSITORY_KEYS
            or config['schema'] != 'augmentor-update-repository/1' or type(config['enabled']) is not bool
            or config['artifactBaseUrl'] != 'https://github.com/ManoloRemiddi/augmentor-agent/'
            or config['rootFile'] != 'updates/root.json'
            or any(not isinstance(config[key], str) or not re.fullmatch(r'https://augmentoragent\.com/updates/[A-Za-z0-9/_-]+/', config[key])
                   for key in ('metadataBaseUrl', 'catalogBaseUrl'))):
        raise ValueError('Unsupported packaged update repository.')
    root = source/'release/updates/root.json'
    root_bytes = None
    if root.exists() or root.is_symlink():
        if root.is_symlink() or root.parent.is_symlink() or not root.is_file() or root.stat().st_size > 2*1024**2:
            raise ValueError('The public update root must be an ordinary bounded file.')
        root_bytes = root.read_bytes()
        # Verify the actual signatures with the same pinned model as consumers.
        models=(Path(__file__).resolve().parents[2]/'node_modules/@tufjs/models/dist/index.js').as_uri()
        code = 'import {Metadata} from '+json.dumps(models)+';\n'+"""
let input='';for await(const chunk of process.stdin)input+=chunk;
const root=Metadata.fromJSON('root',JSON.parse(input));root.verifyDelegate('root',root);
if(root.signed.version<1||!root.signed.consistentSnapshot||root.signed.roles.root.threshold!==2||root.signed.roles.root.keyIDs.length!==3||Date.parse(root.signed.expires)<=Date.now())throw Error('Invalid publisher root');
for(const role of ['targets','snapshot','timestamp'])if(root.signed.roles[role].threshold!==1||root.signed.roles[role].keyIDs.length!==1)throw Error('Invalid online role');
"""
        result = subprocess.run([str(node), '--input-type=module', '-e', code], input=root_bytes,
                                cwd=source, capture_output=True, timeout=15,
                                env={key:value for key,value in os.environ.items() if not key.startswith('NODE_')})
        if result.returncode:
            raise ValueError('The packaged publisher root failed signature/policy verification.')
    elif config['enabled']:
        raise ValueError('An enabled updater needs its verified public trust root.')
    target = destination/'release/updates.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config_file, target)
    if root_bytes is not None:
        target = destination/'release/updates/root.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(root_bytes)

    if (source/'package.json').is_file():
        from .components import SCHEMA as COMPONENT_SCHEMA, build_contract
        contract = {'schema': COMPONENT_SCHEMA, 'components': build_contract(source)}
        (destination/'release/update-components.json').write_text(
            json.dumps(contract, sort_keys=True, indent=2)+'\n', encoding='utf-8')
