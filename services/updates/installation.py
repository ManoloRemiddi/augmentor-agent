# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live automatic-install authority; no downloaded/state record can replay apply.

An independent coordinator owns this context and passes check to authorize_update.
It retains exact artifact handles, refreshes through the installed TUF helper,
and rereads consent/selection before returning authority. Platform admission,
installed-source inspection, journal ownership and external apply remain separate.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import time

from platform_adapters.private_files import descriptor, read_json, require_directory
from .client import repository_request
from .policy import installed_identity, validate_catalog, validate_release, eligibility


class AutomaticInstallAuthority:
    def __init__(self, root, updates, *, os_version, distribution=None, clock=time.time, repository=None):
        self.root=Path(root);self.base=require_directory(Path(updates))
        self.os_version=os_version;self.distribution=distribution;self.clock=clock
        self.repository=repository or self.refresh
        self.current=None;self.selected=None;self.files=[];self.entered=False;self.closed=False

    def refresh(self):
        return repository_request(self.root,self.base/'repository',{'operation':'discover',
            'channel':self.selected['channel'],'target':self.current['target'],'component':self.current['component']},timeout=30)

    def state(self):
        from .manager import SCHEMA, UpdateManager
        state=read_json(self.base/'state.json')
        if not isinstance(state,dict) or state.get('schema')!=SCHEMA or state.get('authenticated') is not True:
            raise ValueError('Automatic installation requires publisher-verified selection.')
        prefs=state.get('preferences')
        if not isinstance(prefs,dict):raise ValueError('The update consent record is invalid.')
        UpdateManager.validate_preferences(prefs)
        if not prefs['automaticInstall'] or not prefs['automaticDownload']:
            raise ValueError('Automatic installation consent was revoked.')
        selected=state.get('candidate');validate_release(selected)
        if selected.get('automaticInstallQualified') is not True:
            raise ValueError('The publisher offers this release for manual installation only.')
        if self.selected is not None and selected!=self.selected:
            raise ValueError('The selected update changed during authorization.')
        if selected['channel']!=prefs['channel'] or state.get('phase') not in ('ready','installing'):
            raise ValueError('The selected update is not ready for installation.')
        release_id=':'.join(str(selected[key]) for key in ('channel','target','version','build'))
        postponed=state.get('postponedUntil')
        if type(postponed) not in (int,float) or not 0<=postponed<2**53:
            raise ValueError('The update deferral record is invalid.')
        if state.get('skippedRelease')==release_id or postponed>self.clock():
            raise ValueError('The user skipped or postponed this update.')
        return state

    def installed(self):
        current=installed_identity(self.root)
        if (not current['automaticInstallQualified'] or not current['buildKnown'] or current['installType']=='development'
                or current['channel'] not in ('stable','preview') or not current['sourceCommit']):
            raise ValueError('This installed build does not qualify automatic installation.')
        if self.current is not None and current!=self.current:
            raise ValueError('The installed release changed during authorization.')
        return current

    @staticmethod
    def fingerprint(fd):
        value=os.fstat(fd)
        return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns,value.st_nlink)

    @staticmethod
    def digest(fd, length):
        # Do not treat timestamps as immutable bytes on POSIX, nor read beyond
        # the signed length if a cooperating writer grows a damaged cache file.
        hash_=hashlib.sha256()
        with os.fdopen(os.dup(fd),'rb') as stream:
            stream.seek(0);remaining=length
            while remaining:
                chunk=stream.read(min(remaining,1024**2))
                if not chunk:raise ValueError('The retained update bytes changed.')
                remaining-=len(chunk);hash_.update(chunk)
            if stream.read(1):raise ValueError('The retained update bytes changed.')
        os.lseek(fd,0,os.SEEK_SET)
        return hash_.hexdigest()

    def bind_downloads(self, state):
        require_directory(self.base/'repository')
        rows=state.get('downloads');artifacts=self.selected['artifacts']
        if not isinstance(rows,list) or len(rows)!=len(artifacts):raise ValueError('The complete release artifact set is required.')
        remaining=deepcopy(artifacts)
        for row in rows:
            if not isinstance(row,dict) or set(row)!={'role','targetPath','bytes','sha256','file'}:
                raise ValueError('Invalid downloaded installation artifact.')
            item={key:value for key,value in row.items() if key!='file'}
            if item not in remaining:raise ValueError('The downloaded bytes differ from the selected release.')
            expected=self.base/'repository'/(item['sha256']+'.download')
            if row['file']!=str(expected):raise ValueError('The downloaded bytes differ from the selected release.')
            remaining.remove(item)
            if os.name=='nt':
                from platform_adapters.windows_identity import private_file_descriptor
                fd=private_file_descriptor(expected,share_write=False)
            else:fd=descriptor(expected)
            self.files.append({'artifact':item,'path':expected,'fd':fd,'fingerprint':self.fingerprint(fd)})
            if self.files[-1]['fingerprint'][2]!=item['bytes'] or self.digest(fd,item['bytes'])!=item['sha256']:
                raise ValueError('The retained installation artifact is damaged.')
            if self.fingerprint(fd)!=self.files[-1]['fingerprint']:raise ValueError('The installation artifact changed during verification.')
        return deepcopy(rows)

    def __enter__(self):
        if self.entered or self.closed:raise ValueError('Use a new live installation authority; never replay one.')
        self.entered=True
        try:
            self.current=self.installed()
            state=self.state();self.selected=deepcopy(state['candidate'])
            if not self.os_version:raise ValueError('Verify the actual operating system before installation.')
            reason=eligibility(self.current,self.selected,self.selected['channel'],os_version=self.os_version,distribution=self.distribution)
            if reason:raise ValueError(reason)
            self.rows=self.bind_downloads(state)
            self.check('verified')
            return self
        except BaseException:self.close();raise

    def check(self, stage):
        if stage not in ('verified','prepared','installer-ready') or not self.entered or self.closed:
            raise ValueError('Installation authority is not live.')
        self.installed();self.state()
        result=self.repository()
        if not isinstance(result,dict) or result.get('authenticated') is not True:
            raise ValueError('Fresh publisher authority is unavailable; manual downloads cannot authorize install.')
        catalog=validate_catalog(result.get('catalog'))
        if not any(release==self.selected for release in catalog['releases']):
            raise ValueError('The selected release was removed, withdrawn or changed by its publisher.')
        # Consent can change while the bounded network refresh is in flight.
        state=self.state();self.installed()
        if state.get('downloads')!=self.rows:raise ValueError('The selected downloaded artifact set changed.')
        for held in self.files:
            if self.fingerprint(held['fd'])!=held['fingerprint']:raise ValueError('The retained update bytes changed.')
            if os.name!='nt' and self.digest(held['fd'],held['artifact']['bytes'])!=held['artifact']['sha256']:
                raise ValueError('The retained update bytes changed.')
            # A pathname substitution cannot replace a retained descriptor.
            fresh=descriptor(held['path'])
            try:
                if self.fingerprint(fresh)!=held['fingerprint']:raise ValueError('The update download path changed.')
            finally:os.close(fresh)
        self.state();self.installed()
        return True

    def close(self):
        if self.closed:return
        self.closed=True
        for held in self.files:os.close(held['fd'])
        self.files=[]

    def __exit__(self,*_):self.close()
