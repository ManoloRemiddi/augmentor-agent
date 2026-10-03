# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Live managed-Linux selection transaction from retained updater code.

Compatibility is checked while the original DSH integration is still running.
After drain only exact immutable artifacts, selection and offline imports are
checked. Owned presets are migrated through their separately bound backup plan;
package-manager trees and service definitions remain outside this controller.
"""
from copy import deepcopy
import hashlib
import importlib.util
import os
from pathlib import Path
import sys

from lifecycle.macos_payload import snapshot
from lifecycle.payload_integrity import _json,_read,MAX_INVENTORY,MAX_ENTRIES
from lifecycle.posix_startup import Startup
from lifecycle.update_journal import artifact
from platform_adapters import locks
from platform_adapters.private_files import descriptor,read_json,require_directory,atomic_json
from .policy import installed_identity


def selection_bytes(path):
    with os.fdopen(descriptor(path),'rb') as stream:raw=stream.read(65537)
    value=_json(raw,65536)
    if not isinstance(value,dict):raise ValueError('The managed selection is invalid.')
    return raw,value


def load_deployment(data):
    script=Path(__file__).resolve().parents[2]/'scripts/desktop-deployment.py'
    spec=importlib.util.spec_from_file_location('augmentor_retained_linux_selection',script)
    tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    tool.DATA=data
    return tool


class ManagedPlan:
    def __init__(self,data,source,target,*,development=False,registration=None):
        if sys.platform!='linux':raise RuntimeError('Managed selection requires Linux.')
        if type(development) is not bool:raise ValueError('Choose an explicit qualification policy.')
        self.data=require_directory(Path(data).absolute())
        self.source,self.target=Path(source).absolute(),Path(target).absolute()
        self.development=development;self.fd=None;self.entered=False;self.closed=False
        self.applied=False;self.started=False;self.backend=None
        self.registration=registration

    def __enter__(self):
        if self.entered or self.closed:raise ValueError('Use a fresh managed selection plan.')
        self.entered=True
        try:
            for root in (self.source,self.target):
                require_directory(root)
                if root.resolve()!=root:raise ValueError('Use canonical immutable release paths.')
                if Path(__file__).resolve().is_relative_to(root):
                    raise ValueError('Run the coordinator from retained code outside both releases.')
            if self.source==self.target:raise ValueError('Stage a separate target release.')
            if not self.development and any(root.parent!=self.data/'releases' for root in (self.source,self.target)):
                raise ValueError('Use the canonical immutable managed release store.')
            self.fd=descriptor(self.data/'deployment.lock',writable=True,create=True)
            locks.flock(self.fd,locks.LOCK_EX|locks.LOCK_NB)
            self.raw,self.previous=selection_bytes(self.data/'desktop.json')
            if self.previous.get('root')!=str(self.source):raise ValueError('The selected source changed.')
            self.tool=load_deployment(self.data)
            # Bound metadata before the legacy deployment verifier parses it.
            # Whole-tree inspection adds modes, directories and ordinary-file
            # checks to that verifier's original content inventory.
            for root in (self.source,self.target):
                manifest=_json(_read(root/'desktop-release.json',MAX_INVENTORY),MAX_INVENTORY)
                if (not isinstance(manifest,dict) or set(manifest)!={'deployment','files','artifactSha256'}
                        or not isinstance(manifest['deployment'],dict) or not isinstance(manifest['files'],dict)
                        or len(manifest['files'])>MAX_ENTRIES):raise ValueError('Invalid bounded managed release descriptor.')
                _json(_read(root/'release.json',65536),65536)
                _json(_read(root/'release/product.json',65536),65536)
            self.source_payload,self.target_payload=snapshot(self.source),snapshot(self.target)
            self.source_manifest=self.tool.verify(self.source)
            self.target_manifest=self.tool.verify(self.target)
            self.proposed=deepcopy(self.target_manifest['deployment'])
            if self.source_manifest['deployment']!=self.previous or self.proposed.get('root')!=str(self.target):
                raise ValueError('The staged descriptor differs from its final selection.')
            # These values own live services and user configuration. A publisher
            # cannot replace them by putting fields in a downloaded descriptor.
            owned={'root','releaseId','sourceRef','artifactSha256','python','node','version'}
            if ({k:v for k,v in self.previous.items() if k not in owned}
                    !={k:v for k,v in self.proposed.items() if k not in owned}):
                raise ValueError('This update needs an explicit runtime/profile migration.')
            self.identities=[]
            for root,config in ((self.source,self.previous),(self.target,self.proposed)):
                identity=installed_identity(root)
                if identity['installType']!='managed-linux' or identity['component']!='desktop':
                    raise ValueError('Use the managed Desktop installation path.')
                if not self.development and (not identity['automaticInstallQualified'] or not identity['buildKnown']):
                    raise ValueError('This release has not qualified automatic managed installation.')
                if not self.development and any(not Path(config[key]).is_relative_to(root) for key in ('python','node')):
                    raise ValueError('Automatic managed updates require retained bundled interpreters.')
                self.identities.append(identity)
            if any(self.identities[0][key]!=self.identities[1][key] for key in ('target','channel','protocols')):
                raise ValueError('This update needs a coordinated product integration migration.')
            from .linux_registration import RegistrationPlan
            if self.registration is None and not self.development and self.previous.get('dshService'):
                if not self.previous.get('dshHome'):raise ValueError('The owned DSH home is missing from this deployment.')
                self.registration=RegistrationPlan(self.previous['dshHome'],self.source,self.target,
                    self.identities[0]['version'],self.identities[1]['version'])
            if self.registration is not None:
                if (not isinstance(self.registration,RegistrationPlan) or self.registration.source!=self.source
                        or self.registration.target!=self.target or str(self.registration.home)!=self.previous.get('dshHome')
                        or self.registration.source_version!=self.identities[0]['version']
                        or self.registration.target_version!=self.identities[1]['version']):
                    raise ValueError('Use the original registration plan for this exact managed release pair.')
                self.registration.validate()
                self.registration.bind_artifacts(*self.pair())
            # Crucially this check precedes preparation/shutdown. Existing
            # DshAdapter enforces exact product identity against the live server.
            if self.registration is not None:
                self.tool.check(self.previous,connected=True)
                self.tool.check(self.proposed,connected=False)
            else:self.tool.check(self.proposed,connected=True)
            self.validate(offline=False)
            return self
        except BaseException:self.close();raise

    def pair(self):
        return tuple(artifact({**{k:identity[k] for k in ('version','sourceCommit','target','channel','dataSchema','readableDataSchemas')},
            'sha256':payload['sha256']}) for identity,payload in zip(self.identities,(self.source_payload,self.target_payload)))

    def validate(self,*,offline=True):
        if self.fd is None or self.closed or self.started:
            raise ValueError('The original managed preflight is no longer live.')
        if selection_bytes(self.data/'desktop.json')[0]!=self.raw:
            raise ValueError('The original selected bytes changed before promotion.')
        if self.registration is not None:self.registration.validate()
        for root,expected,manifest in ((self.source,self.source_payload,self.source_manifest),
                (self.target,self.target_payload,self.target_manifest)):
            if self.tool.verify(root)!=manifest or snapshot(root)!=expected:
                raise ValueError('An immutable managed artifact changed after preflight.')
        if offline:
            self.tool.check(self.proposed,connected=False)
            if snapshot(self.target)!=self.target_payload:raise ValueError('The offline import changed the target.')

    def close(self):
        self.closed=True
        if self.fd is not None:os.close(self.fd);self.fd=None

    def __exit__(self,*_):self.close()


class ManagedBackend:
    def __init__(self,plan,gate,journal):
        if not isinstance(plan,ManagedPlan) or plan.closed or plan.fd is None or plan.backend is not None:
            raise ValueError('Retain the original one-shot managed preflight.')
        if not isinstance(gate,Startup) or not gate.maintenance or gate.fd is None or gate.transactions!=journal.directory:
            raise ValueError('Retain startup exclusion and this live update journal.')
        if not plan.development:
            from lifecycle.posix_pending import transaction_directory
            if gate.transactions!=transaction_directory():raise ValueError('Use the ordinary persistent startup barrier.')
        self.plan,self.gate,self.journal=plan,gate,journal
        self.fd=None;self.ready=False;self.closed=False;self.record_sha256=None
        plan.backend=self

    def __enter__(self):return self

    def wait_ready(self):
        if self.closed or self.ready:raise ValueError('Managed readiness cannot be repeated.')
        self.plan.validate()
        fd=descriptor(self.gate.path.parent/'installation.lock',writable=True,create=True)
        try:locks.flock(fd,locks.LOCK_EX|locks.LOCK_NB)
        except BaseException:os.close(fd);raise
        self.fd=fd;self.ready=True

    def authorize(self):
        if self.closed or not self.ready or self.fd is None or self.plan.started:
            raise ValueError('Managed apply is not ready or was already attempted.')
        journal=self.journal
        if (journal.fd is None or journal.uncertain or journal.record['phase']!='apply-intent'
                or read_json(journal.path)!=journal.record
                or (journal.record['source'],journal.record['target'])!=self.plan.pair()):
            raise ValueError('The live apply intent differs from the original managed pair.')
        self.plan.validate()
        self.plan.started=True  # A failed namespace flush must never permit retry.
        if self.plan.registration is not None:self.plan.registration.apply(self.gate,journal)
        atomic_json(self.plan.data/'desktop.previous.json',self.plan.previous)
        atomic_json(self.plan.data/'desktop.json',self.plan.proposed)
        self.plan.applied=True

    def observe_acknowledgement(self):
        journal=self.journal
        if (not self.plan.applied or self.record_sha256 is not None or journal.fd is None or journal.uncertain
                or journal.record['phase']!='apply-acknowledged' or read_json(journal.path)!=journal.record):
            raise ValueError('Only the original successful selection can retain its acknowledgement.')
        self.record_sha256=hashlib.sha256(selection_bytes(journal.path)[0]).hexdigest()

    def close(self):
        self.closed=True
        if self.fd is not None:os.close(self.fd);self.fd=None

    def __exit__(self,*_):self.close()
