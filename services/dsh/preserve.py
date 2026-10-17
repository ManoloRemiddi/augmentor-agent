# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage a bounded custom DSH upgrade without changing or executing its profile."""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
from urllib.parse import unquote, urlsplit

import yaml
from . import setup

SCHEMA='augmentor-dsh-preservation-stage/1'
OWNERSHIP='augmentor-dsh-preserved-ownership/1'
ROLES=set(setup.PRESETS.values())
ADAPTERS={f'adapters/{name}/index.mjs' for name in (
    'dsh-product','dsh-memory','dsh-home-client','dsh-execution',
    'dsh-response-metrics','dsh-desktop','dsh-context-budget')}
STRING='tag:yaml.org,2002:str'
LIMIT=4*1024**2


def sha(value):return hashlib.sha256(value).hexdigest()


def read(path,private=False):
    path=Path(path)
    if not path.is_absolute() or path.resolve()!=path:
        raise ValueError('Choose canonical absolute files without links.')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1 or before.st_size>LIMIT or private and before.st_mode&0o077:
            raise ValueError('Migration input must be a bounded owned regular file.')
        data=bytearray()
        while len(data)<=LIMIT:
            chunk=os.read(fd,min(65536,LIMIT+1-len(data)))
            if not chunk:break
            data.extend(chunk)
        after=os.fstat(fd)
        if len(data)>LIMIT or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError('Migration input changed while reading.')
        return bytes(data)
    finally:os.close(fd)


def document(raw):
    def unique(rows):
        value={}
        for key,item in rows:
            if key in value:raise ValueError('Duplicate metadata keys need manual review.')
            value[key]=item
        return value
    value=json.loads(raw,object_pairs_hook=unique)
    if not isinstance(value,dict):raise ValueError('Expected an integration metadata object.')
    return value


def module_path(node):
    if not isinstance(node,yaml.ScalarNode) or node.tag!=STRING:return None
    value=node.value
    if value.startswith('file:'):
        parsed=urlsplit(value)
        if parsed.netloc or parsed.query or parsed.fragment:raise ValueError('Unsupported module URL.')
        value=unquote(parsed.path)
    path=Path(value)
    return path if path.is_absolute() else None


def composition(raw):
    """Node-only parsing: never construct !!js, resolve YAML 1.1 keys or dump it."""
    text=raw.decode('utf-8');tree=yaml.compose(text)
    if not isinstance(tree,yaml.SequenceNode):raise ValueError('Expected a profile patch list.')
    seen=set();mappings=[]
    def walk(node,depth=0):
        if depth>64 or len(seen)>50000:raise ValueError('Profile structure exceeds migration bounds.')
        if id(node) in seen:raise ValueError('Aliased profile nodes require manual migration review.')
        seen.add(id(node))
        if isinstance(node,yaml.MappingNode):
            fields={}
            for key,value in node.value:
                if not isinstance(key,yaml.ScalarNode):raise ValueError('Complex profile keys need manual review.')
                if key.value in fields:raise ValueError('Duplicate profile keys need manual review.')
                fields[key.value]=value
            mappings.append((node,fields))
            for _,value in node.value:walk(value,depth+1)
        elif isinstance(node,yaml.SequenceNode):
            for value in node.value:walk(value,depth+1)
    walk(tree)
    return text,mappings


def rewrite(raw,incoming,target,inputs):
    text,mappings=composition(raw)
    def identity(fields):
        value=fields.get('id')
        return value.value if isinstance(value,yaml.ScalarNode) and value.tag==STRING else None
    products=[fields for _,fields in mappings if identity(fields)=='augmentor-product' and 'name' in fields]
    browsers=[fields for _,fields in mappings if identity(fields)=='augmentor-product-browser' and 'name' in fields]
    if len(products)!=1 or len(browsers)!=1:raise ValueError('Exactly one active product and Browser module is required.')
    old_product=module_path(products[0]['name']);active_browser=module_path(browsers[0]['name'])
    if old_product is None or old_product.as_posix().endswith('/adapters/dsh-product/index.mjs') is False or active_browser is None:
        raise ValueError('Unknown active integration module needs manual review.')
    oldroot=old_product.parents[2];changes={};roles=set();retained=set()
    def replace(node,path):
        key=(node.start_mark.index,node.end_mark.index)
        if key in changes:raise ValueError('Overlapping integration references need manual review.')
        changes[key]={'before':node.value,'after':str(path),'line':node.start_mark.line+1}
    inputs(old_product)
    inputs(incoming/'adapters/dsh-product/index.mjs')
    replace(products[0]['name'],incoming/'adapters/dsh-product/index.mjs')
    replace(browsers[0]['name'],target/'browser/dist/index.js')
    for _,fields in mappings:
        name=fields.get('name');config=fields.get('config')
        if not isinstance(name,yaml.ScalarNode) or name.tag!=STRING or not isinstance(config,yaml.MappingNode):continue
        if name.value!='@deepseek-ai/dsh-agent-preset' and '/@deepseek-ai/dsh-agent-preset/' not in name.value:continue
        values={k.value:v for k,v in config.value};role=identity(values)
        if role not in ROLES:continue
        if role in roles:raise ValueError('Duplicate owned preset declarations need manual review.')
        roles.add(role);plugins=values.get('plugins')
        if not isinstance(plugins,yaml.SequenceNode):raise ValueError('Owned preset must contain explicit plugin rows.')
        def plugins_walk(node):
            if isinstance(node,yaml.MappingNode):
                f={k.value:v for k,v in node.value};value=f.get('name');path=module_path(value)
                if path is not None and path.is_relative_to(oldroot):
                    relative=path.relative_to(oldroot).as_posix()
                    if relative in ADAPTERS:
                        inputs(path);inputs(incoming/relative);replace(value,incoming/relative)
                    else:retained.add(relative)
                for _,value in node.value:plugins_walk(value)
            elif isinstance(node,yaml.SequenceNode):
                for value in node.value:plugins_walk(value)
        plugins_walk(plugins)
    if roles!=ROLES:raise ValueError('Both existing declarative Augmentor roles must be present.')
    changed=text
    for (start,end),value in sorted(changes.items(),reverse=True):changed=changed[:start]+json.dumps(value['after'],ensure_ascii=False)+changed[end:]
    # Parsing validates our scalar substitutions but never executes expressions.
    composition(changed.encode())
    unchanged=sorted({str(path) for _,fields in mappings if (node:=fields.get('name')) is not None and (path:=module_path(node)) is not None and (node.start_mark.index,node.end_mark.index) not in changes})
    return changed.encode(),oldroot,active_browser,list(changes.values()),sorted(retained),unchanged


def stage(home,incoming,output,cli):
    if setup.sys.platform!='linux':raise ValueError('Preserved DSH migration is Linux-only.')
    home,incoming,output,cli=(Path(value) for value in (home,incoming,output,cli))
    for path in (home,incoming,output,cli):
        if not path.is_absolute() or path.resolve()!=path:raise ValueError('Choose canonical absolute migration paths.')
    if output.exists() or output.is_symlink():raise ValueError('Choose an absent private staging directory.')
    if any(output.is_relative_to(path) or path.is_relative_to(output) for path in (home,incoming)):
        raise ValueError('Migration staging must be outside both the profile and application.')
    snapshots={}
    def snapshot(path,optional=False):
        key=str(path)
        value=None if optional and not path.exists() and not path.is_symlink() else read(path)
        if key in snapshots and snapshots[key]!=value:raise ValueError('Migration input changed during preparation.')
        snapshots[key]=value;return value
    if setup.cli_family(cli)!=setup.MODERN_DSH:raise ValueError('Use the qualified existing modern DSH CLI.')
    modules,packages=setup.modules_directory(cli)
    manifest=next((p/'package.json' for p in (cli,*cli.parents) if (p/'package.json').is_file() and document(read(p/'package.json')).get('name')=='@deepseek-ai/dsh'),None)
    if manifest is None:raise ValueError('Cannot bind the selected CLI manifest.')
    snapshot(manifest)
    for name in packages:snapshot(modules/name/'package.json')
    profile=home/'profiles/web';target=profile/'augmentor-product'
    ownership_raw=snapshot(target/'ownership.json');owner=document(ownership_raw)
    if owner.get('schema') not in (None,OWNERSHIP):raise ValueError('Unknown integration ownership schema.')
    expected_files={'browser/dist/index.js','browser/package.json'}
    if not isinstance(owner.get('files'),dict) or not isinstance(owner.get('presets'),dict) or set(owner['files'])!=expected_files or set(owner['presets'])!=ROLES:
        raise ValueError('Integration ownership is incomplete.')
    owned_js=snapshot(target/'browser/dist/index.js')
    if sha(owned_js)!=owner['files']['browser/dist/index.js']:raise ValueError('Edited integration code requires separate preservation review.')
    owned_package=document(snapshot(target/'browser/package.json'))
    for role,files in owner['presets'].items():
        if not isinstance(files,dict) or set(files)!={'preset.yml','agent.cordis.yml'}:raise ValueError('Preset ownership is incomplete.')
        for name,digest in files.items():
            if sha(snapshot(home/'.agent-presets'/role/name))!=digest:raise ValueError('Edited preset files require separate preservation review.')
    original=snapshot(profile/'cordis.patch.yml')
    patch,oldroot,active_browser,edits,retained,unchanged=rewrite(original,incoming,target,snapshot)
    count=len(edits)
    if sha(snapshot(active_browser))!=owner['files']['browser/dist/index.js']:
        raise ValueError('Active compatibility code differs from the owned code; preserve it separately.')
    active_package=document(snapshot(active_browser.parents[1]/'package.json'))
    if active_package!=owned_package:raise ValueError('Active and owned package edits differ; preserve both explicitly.')
    reference_raw=snapshot(oldroot/'apps/browser/plugin/package.json');reference=document(reference_raw)
    expected_reference=owner.get('preservedMigration',{}).get('sourcePackageSha256',owner['files']['browser/package.json'])
    if sha(reference_raw)!=expected_reference:raise ValueError('Original package provenance does not match ownership.')
    if {k:v for k,v in active_package.items() if k!='peerDependencies'}!={k:v for k,v in reference.items() if k!='peerDependencies'}:
        raise ValueError('Package edits beyond peer dependencies need separate preservation review.')
    new_package_raw=snapshot(incoming/'apps/browser/plugin/package.json');new_package=document(new_package_raw)
    product=document(snapshot(incoming/'release/product.json'))
    if not isinstance(product.get('version'),str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?',product['version']) or new_package.get('name')!=reference.get('name') or new_package.get('version')!=product.get('version'):
        raise ValueError('Incoming product and plugin identity must match.')
    peers=active_package.get('peerDependencies',{})
    required={'@deepseek-ai/cordis':'4.0.4','@deepseek-ai/dsh-tools':setup.MODERN_DSH}
    if set(peers)!=set(required) or set(new_package.get('peerDependencies',{}))!=set(required):
        raise ValueError('Unknown peer dependency edits need separate review.')
    for name,version in required.items():
        if not isinstance(peers[name],str) or version not in [part.strip() for part in peers[name].split('||')]:
            raise ValueError('Preserved peers do not explicitly support the qualified modern SDK.')
    new_package['peerDependencies']=peers
    package_bytes=(json.dumps(new_package,indent=2,ensure_ascii=False)+'\n').encode()
    js=snapshot(incoming/'apps/browser/plugin/dist/index.js')
    for path in (home/'settings.yaml',home/'.credentials.yaml',home/'augmentor-product-token',profile/'cordis.yml',profile/'package.json'):
        snapshot(path,optional=True)
    migration={'sourcePackageSha256':sha(new_package_raw),'previousOwnershipSha256':sha(ownership_raw),
               'compositionBeforeSha256':sha(original),'compositionAfterSha256':sha(patch),
               'editedFieldsPreserved':['browser/package.json:peerDependencies']}
    new_owner={'schema':OWNERSHIP,'version':product['version'],
               'files':{'browser/dist/index.js':sha(js),'browser/package.json':sha(package_bytes)},
               'presets':owner['presets'],'preservedMigration':migration}
    assets={'cordis.patch.yml':patch,'integration/browser/dist/index.js':js,
            'integration/browser/package.json':package_bytes,
            'integration/ownership.json':(json.dumps(new_owner,indent=2)+'\n').encode()}
    plan={'schema':SCHEMA,'home':str(home),'incoming':str(incoming),'target':str(target),
          'previousVersion':owner.get('version'),'candidateVersion':product['version'],
          'cli':str(cli),'sdkPackages':packages,'rewrittenModuleReferences':count,'moduleEdits':edits,
          'retainedOldRootModules':retained,'retainedModulePaths':unchanged,
          'retainedDependenciesRequireSeparateQualification':True,'oldRootMustRemainAvailable':True,
          'ownerInputs':{path:None if value is None else sha(value) for path,value in snapshots.items()},
          'assets':{name:sha(data) for name,data in assets.items()},
          'ownerFilesChanged':False,'activated':False,'requiresColdBackupAndImmutableIncomingForActivation':True}
    # Recheck all source bytes before allocating even an output-only stage.
    for path,value in snapshots.items():
        current=None if value is None and not Path(path).exists() and not Path(path).is_symlink() else read(Path(path))
        if current!=value:raise ValueError('Migration input changed before staging.')
    output.mkdir(mode=0o700);identity=output.stat()
    try:
        for name,data in {**assets,'plan.json':(json.dumps(plan,indent=2)+'\n').encode()}.items():
            path=output/name;path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(data)
        digest=sha(read(output/'plan.json',private=True));verify(output,digest)
        return {'schema':SCHEMA,'planSha256':digest,'rewrittenModuleReferences':count,'candidateVersion':product['version'],'ownerFilesChanged':False,'activated':False}
    except BaseException:
        now=output.lstat()
        if not output.is_symlink() and (now.st_dev,now.st_ino)==(identity.st_dev,identity.st_ino):shutil.rmtree(output)
        raise


def verify(output,expected):
    if setup.sys.platform!='linux':raise ValueError('Preserved DSH migration is Linux-only.')
    output=Path(output);raw=read(output/'plan.json',private=True)
    if sha(raw)!=expected:raise ValueError('The staged plan changed after review.')
    plan=document(raw)
    if plan.get('schema')!=SCHEMA or plan.get('activated') is not False or plan.get('ownerFilesChanged') is not False:
        raise ValueError('Unknown or applied preservation stage.')
    expected_assets={'cordis.patch.yml','integration/browser/dist/index.js','integration/browser/package.json','integration/ownership.json'}
    if set(plan.get('assets',{}))!=expected_assets:raise ValueError('The stage asset inventory changed.')
    for name,digest in plan['assets'].items():
        if sha(read(output/name,private=True))!=digest:raise ValueError('A staged integration asset changed.')
    for path,digest in plan['ownerInputs'].items():
        file=Path(path)
        actual=None if digest is None and not file.exists() and not file.is_symlink() else sha(read(file))
        if actual!=digest:raise ValueError('An owner or supplier input changed; prepare a fresh stage.')
    return {'valid':True,'ownerFilesChanged':False,'activated':False}
