# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Owned DSH composition migration between exact immutable Linux releases.

Reads precede preparation. Writes require the original live APPLY journal and
startup writer, retain exact private backups, and never replay a saved manifest.
Model settings, conversations, tokens and unrelated host composition survive.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import stat
import sys

from lifecycle.payload_integrity import _json,_read
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import artifact
from platform_adapters.private_files import require_directory,atomic_json,read_json,replace_file

HEADER='# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n'
PRESETS=('augmentor-linux-product','augmentor-browser-product')


def ordinary(path):
    info=Path(path).lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1:
        raise ValueError('An owned registration is no longer an ordinary user file.')
    return info


def raw_file(path):
    ordinary(path)
    return _read(Path(path),1024**2)


def generated(root):
    # This fixed generator belongs to the already inspected artifact. Restore
    # import search order after its historical module-level path adjustment.
    path=Path(root)/'services/dsh/setup.py';spec=importlib.util.spec_from_file_location('augmentor_registration_generator',path)
    module=importlib.util.module_from_spec(spec);previous=list(sys.path);bytecode=sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode=True
        spec.loader.exec_module(module)
        if module.ROOT!=Path(root):raise ValueError('The generator belongs to another immutable release.')
        entries=module.personal_agent_entries()
    finally:sys.path[:]=previous;sys.dont_write_bytecode=bytecode
    if not isinstance(entries,list) or not entries:raise ValueError('The immutable preset generator is invalid.')
    return entries


def document(raw):
    # Owned installer output is a copyright comment followed by JSON-as-YAML.
    text=raw.decode('utf-8');meaningful='\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('#'))
    return _json(meaningful.encode(),1024**2)


class RegistrationPlan:
    def __init__(self,home,source,target,source_version,target_version):
        if sys.platform!='linux':raise RuntimeError('Immutable registration migration requires Linux.')
        self.home=require_directory(Path(home).absolute());self.source,self.target=Path(source),Path(target)
        if self.home.resolve()!=self.home:raise ValueError('Use the original canonical private DSH home.')
        self.files=[];self.links=[];self.begun=False;self.applied=False;self.backup=None;self.journal=None
        self.pair=None
        self.anchors={'dsh-home':self.home}
        self.source_version,self.target_version=source_version,target_version
        profile=self.directory(self.home/'profiles/web')
        owned=self.directory(profile/'augmentor-product')
        browser=self.directory(owned/'browser');self.directory(browser/'dist')
        presets=self.directory(self.home/'.agent-presets')
        self.ownership_path=owned/'ownership.json';self.original_ownership=raw_file(self.ownership_path)
        ownership=_json(self.original_ownership,1024**2)
        if (not isinstance(ownership,dict) or set(ownership)!={'version','files','presets','patchEntry'}
                or ownership['version']!=source_version or not isinstance(ownership['files'],dict)
                or set(ownership['files'])!={'browser/dist/index.js','browser/package.json'}
                or not isinstance(ownership['presets'],dict) or set(ownership['presets'])!=set(PRESETS)
                or not isinstance(ownership['patchEntry'],str)):
            raise ValueError('The DSH registration ownership needs an explicit migration.')
        before_entries=generated(self.source);after_entries=generated(self.target)
        updated=deepcopy(ownership);updated['version']=target_version
        for relative in ownership['files']:
            path=owned/relative;before=raw_file(path)
            if hashlib.sha256(before).hexdigest()!=ownership['files'][relative]:raise ValueError('An owned browser integration was edited.')
            payload=raw_file(self.target/('apps/browser/plugin/'+relative.removeprefix('browser/')))
            self.add_file(path,before,payload)
            updated['files'][relative]=hashlib.sha256(payload).hexdigest()
        for name in PRESETS:
            directory=self.directory(presets/name)
            files=ownership['presets'][name]
            if not isinstance(files,dict) or set(files)!={'preset.yml','agent.cordis.yml'}:raise ValueError('Preset ownership is incomplete.')
            for filename in files:
                path=directory/filename;before=raw_file(path)
                if hashlib.sha256(before).hexdigest()!=files[filename]:raise ValueError('An owned preset was edited; preserve it for explicit migration.')
                content=document(before)
                if filename=='agent.cordis.yml':
                    if content!=before_entries:raise ValueError('The current preset differs from the original immutable defaults.')
                    after=(HEADER+json.dumps(after_entries,indent=2)+'\n').encode()
                else:
                    if content!={'name':'Augmentor '+('Linux' if name==PRESETS[0] else 'Browser'),
                            'description':'Augmentor product integration '+source_version}:
                        raise ValueError('The owned preset metadata was customized.')
                    content['description']='Augmentor product integration '+target_version
                    after=(HEADER+json.dumps(content)+'\n').encode()
                self.add_file(path,before,after);updated['presets'][name][filename]=hashlib.sha256(after).hexdigest()
        patch=profile/'cordis.patch.yml';before=raw_file(patch)
        entry=ownership['patchEntry'];text=before.decode('utf-8')
        if not entry.startswith('- insert: ') or '\n' in entry or text.splitlines().count(entry)!=1 or text.count(entry)!=1:
            raise ValueError('The owned host composition entry changed.')
        rows=_json(entry[len('- insert: '):].encode(),1024**2)
        if not isinstance(rows,list) or not 2<=len(rows)<=3:raise ValueError('Unexpected owned host composition.')
        expected={'augmentor-product':str(self.source/'adapters/dsh-product/index.mjs'),
            'augmentor-product-browser':str(browser/'dist/index.js'),
            'augmentor-product-prompts':str(self.source/'adapters/dsh-prompt-library/lib/index.js')}
        ids=set()
        for row in rows:
            if (not isinstance(row,dict) or row.get('id') not in expected or row['id'] in ids
                    or row.get('name')!=expected[row['id']] or set(row)-{'id','name','config'}):
                raise ValueError('The owned host composition differs from this release.')
            ids.add(row['id'])
        if not {'augmentor-product','augmentor-product-browser'}<=ids:raise ValueError('The owned host composition is incomplete.')
        after_rows=deepcopy(rows)
        for row in after_rows:
            if row['id']!='augmentor-product-browser':row['name']=str(self.target)+row['name'][len(str(self.source)):]
        updated['patchEntry']='- insert: '+json.dumps(after_rows)
        self.add_file(patch,before,text.replace(entry,updated['patchEntry'],1).encode())
        # Only the normal owned links are relocated. Unknown copied modules or
        # external CLI dependencies need their own migration, never an unlink.
        self.add_link(profile/'node_modules',self.source/'dsh/node_modules',self.target/'dsh/node_modules')
        dependencies=self.directory(browser/'node_modules');deepseek=self.directory(dependencies/'@deepseek-ai')
        for name in ('dsh-tools','schemastery'):
            self.add_link(deepseek/name,self.source/('dsh/node_modules/@deepseek-ai/'+name),
                self.target/('dsh/node_modules/@deepseek-ai/'+name))
        self.add_link(dependencies/'ws',self.source/'node_modules/ws',self.target/'node_modules/ws')
        self.add_file(self.ownership_path,self.original_ownership,(json.dumps(updated,indent=2)+'\n').encode())
        self.validate()

    def directory(self,path):
        anchor=next((root for root in self.anchors.values() if path.is_relative_to(root)),None)
        if anchor is None:raise ValueError('The registration directory has no inspected ownership anchor.')
        for parent in (path,*path.parents):
            if not parent.is_relative_to(anchor):break
            info=parent.lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid()
                    or anchor!=self.home and info.st_mode&0o022):
                raise ValueError('An owned registration directory changed or was redirected.')
        return path

    def add_external_file(self,name,anchor,path,before,after):
        """Attach an independently checked fixed user registration before binding."""
        anchor,path=Path(anchor),Path(path)
        if (self.pair is not None or self.begun or name in self.anchors or not anchor.is_absolute()
                or anchor.resolve()!=anchor or not path.is_relative_to(anchor)
                or any(row['path']==path for row in self.files) or ordinary(path).st_mode&0o022):
            raise ValueError('Attach only a fresh canonical owned registration.')
        self.anchors[name]=anchor
        self.directory(path.parent);self.add_file(path,before,after)

    def record_name(self,path):
        for name,root in self.anchors.items():
            if path.is_relative_to(root):return name+'/'+path.relative_to(root).as_posix()
        raise ValueError('The owned registration lost its original anchor.')

    def add_file(self,path,before,after):
        if len(after)>1024**2:raise ValueError('The generated registration exceeds its supported size.')
        self.files.append({'path':path,'before':before,'after':after,'mode':stat.S_IMODE(ordinary(path).st_mode)})

    def add_link(self,path,before,after):
        info=path.lstat()
        if not stat.S_ISLNK(info.st_mode) or info.st_uid!=os.getuid() or os.readlink(path)!=str(before):
            raise ValueError('An owned module link differs from the original bundled runtime.')
        if not before.is_dir() or not after.is_dir():raise ValueError('A matching bundled module dependency is absent.')
        self.links.append({'path':path,'before':str(before),'after':str(after)})

    def validate(self,*,applied=False):
        key='after' if applied else 'before'
        for row in self.files:
            self.directory(row['path'].parent)
            if raw_file(row['path'])!=row[key] or stat.S_IMODE(ordinary(row['path']).st_mode)!=row['mode']:
                raise ValueError('The owned registration changed after its original inspection.')
        for row in self.links:
            self.directory(row['path'].parent)
            info=row['path'].lstat()
            if not stat.S_ISLNK(info.st_mode) or info.st_uid!=os.getuid() or os.readlink(row['path'])!=row[key]:
                raise ValueError('An owned module link changed after original inspection.')
        return True

    def write_file(self,row):
        path=row['path'];temporary=path.with_name('.augmentor-update-'+secrets.token_hex(16))
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb') as stream:
                stream.write(row['after']);stream.flush();os.fchmod(stream.fileno(),row['mode']);os.fsync(stream.fileno())
            replace_file(temporary,path)
        finally:temporary.unlink(missing_ok=True)

    def bind_artifacts(self,source,target):
        """Bind once to the independently inspected managed release pair."""
        pair=(artifact(source),artifact(target))
        if (self.pair is not None or self.begun or pair[0]['version']!=self.source_version
                or pair[1]['version']!=self.target_version):
            raise ValueError('Bind a fresh registration to its original inspected release pair.')
        self.pair=pair

    def apply(self,gate,journal):
        if self.begun or self.applied:raise ValueError('Registration apply cannot be retried or reconstructed.')
        if (not isinstance(gate,Startup) or not gate.maintenance or gate.fd is None or journal.fd is None
                or journal.uncertain or gate.transactions!=journal.directory or journal.record['phase']!='apply-intent'
                or read_json(journal.path)!=journal.record
                or self.pair is None or (journal.record['source'],journal.record['target'])!=self.pair):
            raise ValueError('Retain the original live startup writer and exact bound apply intent.')
        self.validate();self.begun=True;self.journal=journal
        self.backup=journal.directory/('registration-'+journal.record['id']);self.backup.mkdir(mode=0o700)
        parent=os.open(journal.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(parent)
        finally:os.close(parent)
        records=[]
        for index,row in enumerate(self.files):
            backup=self.backup/(str(index)+'.before')
            with backup.open('xb') as stream:
                os.chmod(backup,0o600);stream.write(row['before']);stream.flush();os.fsync(stream.fileno())
            records.append({'name':self.record_name(row['path']),'beforeSHA256':hashlib.sha256(row['before']).hexdigest(),
                'afterSHA256':hashlib.sha256(row['after']).hexdigest(),'backup':backup.name,'mode':row['mode']})
        self.backup_record={'schema':'augmentor-linux-registration/1','transactionId':journal.record['id'],
            'sourceRoot':str(self.source),'targetRoot':str(self.target),'files':records,
            'anchors':{name:str(root) for name,root in self.anchors.items()},
            'links':[{'name':self.record_name(row['path']),'before':row['before'],'after':row['after']} for row in self.links]}
        atomic_json(self.backup/'manifest.json',self.backup_record)
        self.validate()
        for row in self.files:self.write_file(row)
        for row in self.links:
            temporary=row['path'].with_name('.augmentor-update-'+secrets.token_hex(16))
            try:temporary.symlink_to(row['after']);replace_file(temporary,row['path'])
            finally:temporary.unlink(missing_ok=True)
        self.validate(applied=True);self.applied=True

    def verify_applied(self):
        if not self.applied or not self.backup or self.journal is None:raise ValueError('Retain the original successfully returned registration apply.')
        if (self.journal.record['source'],self.journal.record['target'])!=self.pair:
            raise ValueError('The original registration release pair changed.')
        self.validate(applied=True)
        if read_json(self.backup/'manifest.json')!=self.backup_record:raise ValueError('The original registration backup manifest changed.')
        for row,record in zip(self.files,self.backup_record['files']):
            if raw_file(self.backup/record['backup'])!=row['before']:raise ValueError('The original private registration backup changed.')
        return True
