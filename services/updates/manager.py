# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""One persisted update state shared by surfaces; background jobs hold admission."""
from contextlib import nullcontext
from copy import deepcopy
import json
import hashlib
import os
from pathlib import Path
import random
import shutil
import secrets
import sys
import threading
import time

from platform_adapters.paths import private_directory
from platform_adapters.private_files import atomic_json, read_json, require_directory, descriptor, replace_file
from .policy import CHANNELS, installed_identity, select_release, version, canonical_release_url, target_path, HEX, MAX_ARTIFACT

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'augmentor-update-state/1'


class UpdateManager:
    def __init__(self, base, *, root=ROOT, admission=None, clock=time.time, runner=None):
        self.base = require_directory(private_directory(Path(base)))
        self.root, self.admission, self.clock = Path(root), admission, clock
        self.runner = runner or self.run_helper
        self.lock = threading.RLock()
        self.job = None
        self.process = None
        self.cancelled = threading.Event()
        self.stopping = threading.Event()
        self.scheduler = None
        self.current = installed_identity(self.root)
        self.file = self.base / 'state.json'
        if self.file.exists() or self.file.is_symlink():
            self.state = read_json(self.file)
            if (not isinstance(self.state, dict) or self.state.get('schema') != SCHEMA
                    or not isinstance(self.state.get('preferences'), dict)):
                raise ValueError('The update preferences need supported recovery. They were preserved.')
            self.validate_preferences(self.state['preferences'])
            self.validate_state()
            # Observing a dead worker never authorizes replaying installation.
            if self.state.get('phase') in ('checking', 'downloading', 'installing'):
                installing=self.state.get('phase')=='installing'
                if installing:self.state['installationBlocked']=True
                self.state.update(phase='interrupted', error=(
                    'The independent installation outcome is unknown. Preserve its pending record and use recovery.' if installing else
                    'The previous update operation was interrupted. Check again to continue.'))
        else:
            self.state = {'schema': SCHEMA, 'revision': 0, 'preferences': {
                'automaticChecks': self.current['installType'] != 'development' and self.current['channel'] in CHANNELS, 'intervalHours': 24,
                'automaticDownload': False, 'automaticInstall': False, 'channel': self.current['channel'] if self.current['channel'] in CHANNELS else 'preview'},
                'phase': 'idle', 'candidate': None, 'authenticated': False, 'error': None,
                'lastAttempt': None, 'lastSuccessfulCheck': None, 'nextCheck': 0,
                'notifiedRelease': None, 'skippedRelease': None, 'postponedUntil': 0, 'downloads': []}
        self.state['revision'] = self.state.get('revision', 0)
        identity = {k: self.current[k] for k in ('version', 'build', 'target', 'installType', 'sourceCommit', 'component', 'releaseId')}
        observed = self.state.get('observedInstallation')
        if observed is not None and observed != identity:
            # A new running payload starts a new observation, never replays the
            # previous payload's selected download or installation intention.
            self.state.update(candidate=None, downloads=[], phase='idle', authenticated=False,
                              error=None, nextCheck=0, notifiedRelease=None, skippedRelease=None,installationBlocked=False)
        self.state['observedInstallation'] = identity
        self.state.setdefault('installAttempt',None)
        self.state.setdefault('installationBlocked',False)
        self.state.setdefault('nextInstallAttempt',0)
        self.state.setdefault('lastInstallationResult',None)
        self.collect_installation_result()
        self.save()

    def save(self):
        self.state['revision'] += 1
        atomic_json(self.file, self.state)

    @staticmethod
    def validate_preferences(values):
        expected = {'automaticChecks', 'intervalHours', 'automaticDownload', 'automaticInstall', 'channel'}
        if set(values) != expected or any(type(values[k]) is not bool for k in expected - {'intervalHours', 'channel'}):
            raise ValueError('Invalid update preferences.')
        if type(values['intervalHours']) is not int or values['intervalHours'] not in (24, 48) or values['channel'] not in CHANNELS:
            raise ValueError('Choose daily or every two days and a supported update channel.')
        if values['automaticInstall'] and not values['automaticDownload']:
            raise ValueError('Automatic installation also needs automatic downloads enabled.')

    def automatic_capability(self):
        configuration = self.root / 'release/updates.json'
        enabled = configuration.is_file() and json.loads(configuration.read_text()).get('enabled') is True
        return (enabled and self.current['automaticInstallQualified'] and self.installer_available()
                and not self.state.get('installationBlocked',False))

    def installer_available(self):
        if sys.platform=='darwin' and self.current['installType']=='macos-app' and self.current['component']=='desktop':
            from .macos_bootstrap import locations
            try:
                bundle,base,transactions=locations(self.root)
                return (self.base==base/'data/augmentor/updates' and os.access(bundle.parent,os.W_OK|os.X_OK)
                    and all((self.root/name).is_file() for name in ('scripts/macos-update-bootstrap.py','scripts/macos-update-observer.py')))
            except (OSError,ValueError):return False
        if sys.platform!='win32' or self.current['installType']!='windows-inno':return False
        from platform_adapters.windows_identity import local_app_data
        base=local_app_data()/'Augmentor'
        # Source checkouts, custom data/installation locations and older bridge
        # builds retain manual downloads until their adapter is qualified.
        return (self.root==local_app_data()/'Programs/Augmentor Agent/current' and
                self.base==base/'data/augmentor/updates' and
                all((self.root/name).is_file() for name in ('scripts/windows-update-bootstrap.py',
                    'scripts/windows-update-observer.py','scripts/windows-update-coordinator.py')))

    def installation_directory(self):
        if sys.platform=='darwin':
            from lifecycle.posix_pending import transaction_directory
            return transaction_directory()
        if sys.platform!='win32':return None
        from platform_adapters.windows_identity import local_app_data
        return local_app_data()/'Augmentor/updates'

    def launch_installer(self):
        if not self.installer_available():raise ValueError('No qualified installer adapter is available.')
        if sys.platform=='darwin':
            from .macos_bootstrap import launch
            return launch(self.root)
        import windows_supervisor
        return windows_supervisor.request('start-update',root=self.root)['update']

    def attempt_install(self):
        # Called after discovery/download has left maintenance work admission;
        # the independent coordinator must be able to reserve this service.
        with self.lock:
            candidate=self.state.get('candidate')
            if (self.stopping.is_set() or self.cancelled.is_set() or self.state['phase']!='ready' or
                    self.state['installationBlocked'] or
                    not candidate or self.state.get('authenticated') is not True or
                    len(self.state['downloads'])!=len(candidate['artifacts']) or
                    candidate.get('automaticInstallQualified') is not True or
                    not self.state['preferences']['automaticInstall'] or
                    not self.state['preferences']['automaticDownload'] or not self.automatic_capability() or
                    self.release_id()==self.state['skippedRelease'] or self.clock()<self.state['postponedUntil'] or
                    self.clock()<self.state['nextInstallAttempt']):return False
            if self.admission:
                status=self.admission.control('host.maintenance.status',{})
                if status['phase']!='ready' or status['active']:
                    self.state['nextInstallAttempt']=self.clock()+300;self.save();return False
            self.state.update(phase='installing',error=None,installAttempt=None);self.save()
        try:
            result=self.launch_installer()
            from .attempt import attempt_id
            if not isinstance(result,dict) or set(result)!={'started','attempt'} or result['started'] is not True:
                raise ValueError('The independent update launch was not confirmed.')
            id_=attempt_id(result['attempt'])
            with self.lock:self.state['installAttempt']=id_;self.save()
            return True
        except Exception as error:
            # Even a lost RPC answer is an unknown launch, not proof of failure
            # before dispatch. Do not submit another installer automatically.
            with self.lock:
                self.state.update(phase='failed',installationBlocked=True,error=str(error)[:2000]);self.save()
            return False

    def collect_installation_result(self):
        from .attempt import read_result,release_id
        with self.lock:
            id_=self.state.get('installAttempt')
            if not id_:return
            if self.state.get('installationBlocked') and self.state['phase']=='failed':return
            directory=self.installation_directory()
            if directory is None:return
            try:result=read_result(directory,id_)
            except (ValueError,OSError) as error:
                self.state.update(phase='failed',installationBlocked=True,
                    error='The independent update result could not be verified. Recover the preserved attempt. '+str(error)[:1000])
                self.save();return
            if result is None:return
            self.state.update(lastInstallationResult=result,installAttempt=None,error=result['error'])
            if result['outcome']=='deferred':
                self.state.update(phase='ready',installationBlocked=False,nextInstallAttempt=self.clock()+300)
            elif result['outcome']=='failed':
                self.state.update(phase='failed',installationBlocked=True)
            else:
                # A receipt describes completion. It cannot update this running
                # process's cached identity or authorize app/recovery commands.
                self.state.update(phase='idle' if result['releaseId']==release_id(self.current) else 'installed',
                                  installationBlocked=False)
            self.save()

    def validate_state(self):
        value = self.state
        phases = ('idle', 'checking', 'downloading', 'installing', 'interrupted', 'available',
                  'current', 'cancelled', 'failed', 'ready', 'installed')
        if (type(value.get('revision')) is not int or value['revision'] < 0
                or value.get('phase') not in phases or type(value.get('authenticated')) is not bool
                or not isinstance(value.get('downloads'), list) or len(value['downloads']) > 8):
            raise ValueError('The update state needs supported recovery. It was preserved.')
        for key in ('nextCheck', 'postponedUntil', 'lastAttempt', 'lastSuccessfulCheck'):
            number = value.get(key)
            if number is None and key.startswith('last'): continue
            if type(number) not in (int, float) or not 0 <= number < 2**53:
                raise ValueError('Invalid persisted update schedule. It was preserved.')
        for key in ('notifiedRelease', 'skippedRelease'):
            if value.get(key) is not None and (not isinstance(value[key], str) or len(value[key]) > 256):
                raise ValueError('Invalid persisted update notification. It was preserved.')
        from .attempt import attempt_id,validate_result
        if value.get('installAttempt') is not None:attempt_id(value['installAttempt'])
        if type(value.get('installationBlocked',False)) is not bool:
            raise ValueError('Invalid persisted installation recovery state.')
        retry=value.get('nextInstallAttempt',0)
        if type(retry) not in (int,float) or not 0<=retry<2**53:raise ValueError('Invalid installation retry time.')
        previous=value.get('lastInstallationResult')
        if previous is not None:validate_result(previous,previous.get('attempt') if isinstance(previous,dict) else None)
        candidate = value.get('candidate')
        if candidate is not None:
            if value['authenticated']:
                from .policy import validate_release
                validate_release(candidate)
            else:
                self.validate_public_release(candidate, value['preferences']['channel'])
        if value['downloads'] and not candidate:
            raise ValueError('The saved download has no release identity. Check again.')
        for row in value['downloads']:
            if (not isinstance(row, dict) or set(row) != {'role', 'targetPath', 'bytes', 'sha256', 'file'}
                    or {k: v for k, v in row.items() if k != 'file'} not in candidate['artifacts']
                    or row['file'] != str(self.base / 'repository' / (row['sha256'] + '.download'))):
                raise ValueError('Invalid persisted update download. It was preserved.')

    def snapshot(self):
        self.collect_installation_result()
        with self.lock:
            value = deepcopy(self.state)
            value['installed'] = deepcopy(self.current)
            value['automaticInstallAvailable'] = self.automatic_capability()
            value['busy'] = self.state['phase']=='installing' or self.job is not None and self.job.is_alive()
            # Local paths are returned only to a requested download/open action.
            value['downloads'] = [{k: v for k, v in row.items() if k != 'file'} for row in value['downloads']]
            return value

    def release_id(self):
        candidate = self.state.get('candidate')
        return ':'.join(str(candidate[k]) for k in ('channel', 'target', 'version', 'build')) if candidate else None

    def configure(self, params):
        if set(params) != {'revision', 'preferences'}:
            raise ValueError('Save update preferences with their current revision.')
        values = params['preferences']; self.validate_preferences(values)
        with self.lock:
            if params['revision'] != self.state['revision']:
                raise ValueError('Update settings changed elsewhere. Reload before saving.')
            if values['automaticInstall'] and not self.automatic_capability():
                raise ValueError('Automatic installation is not qualified for this installed build yet.')
            channel_changed = values['channel'] != self.state['preferences']['channel']
            if channel_changed and self.state['phase']=='installing':
                raise ValueError('Wait for the observed installation result before changing channels.')
            self.state['preferences'] = deepcopy(values)
            self.state['nextCheck'] = 0
            if channel_changed:
                self.state.update(candidate=None, authenticated=False, downloads=[], phase='idle',
                                  skippedRelease=None, notifiedRelease=None)
            self.save()
        return self.snapshot()

    def call(self, method, params):
        action = method.removeprefix('updates.')
        if action == 'configure':
            return self.configure(params)
        if action in ('status', 'check', 'download', 'cancel', 'notification', 'skip', 'reveal') and params:
            raise ValueError('This update action accepts no caller-provided release, URL or command.')
        if action == 'status':
            return self.snapshot()
        if action == 'reveal':
            with self.lock:
                if self.state['phase'] != 'ready' or not self.state['downloads']:
                    raise ValueError('Finish downloading the update first.')
                return {'folder': str(require_directory(self.ready_directory()))}
        if action == 'check':
            self.start('checking', self.check)
        elif action == 'download':
            with self.lock:
                if not self.state['candidate']:
                    raise ValueError('Check for a compatible release first.')
                self.start('downloading', self.download)
        elif action == 'cancel':
            with self.lock:
                if self.state['phase']=='installing':
                    raise ValueError('The independent installation must finish or be recovered. This action cancels downloads only.')
            self.cancelled.set()
            with self.lock:
                if self.process and self.process.poll() is None:
                    self.process.terminate()
        elif action == 'notification':
            with self.lock:
                identity = self.release_id()
                if (not identity or identity in (self.state['notifiedRelease'], self.state['skippedRelease'])
                        or self.clock() < self.state['postponedUntil']):
                    return None
                self.state['notifiedRelease'] = identity
                self.save()
                return deepcopy(self.state['candidate'])
        elif action == 'skip':
            with self.lock:
                self.state['skippedRelease'] = self.release_id(); self.save()
        elif action == 'postpone':
            if set(params) != {'hours'} or type(params['hours']) is not int or params['hours'] not in (24, 48):
                raise ValueError('Choose a one-day or two-day reminder.')
            with self.lock:
                self.state.update(postponedUntil=self.clock() + params['hours'] * 3600, notifiedRelease=None); self.save()
        else:
            raise ValueError('Unsupported update operation.')
        return self.snapshot()

    def start(self, phase, operation):
        with self.lock:
            if self.job and self.job.is_alive():
                raise ValueError('An update operation is already running.')
            if self.stopping.is_set():
                raise ValueError('The update service is closing.')
            if self.state['phase']=='installing':raise ValueError('An independent installation is being observed.')
            self.cancelled.clear()
            self.state.update(phase=phase, error=None, bytesDownloaded=0)
            self.save()
            self.job = threading.Thread(target=self.work, args=(operation,), name='augmentor-update-' + phase, daemon=False)
            self.job.start()

    def work(self, operation):
        try:
            with self.admission.work() if self.admission else nullcontext():
                operation()
            self.attempt_install()
        except Exception as error:
            with self.lock:
                self.state.update(phase='cancelled' if self.cancelled.is_set() else 'failed',
                                  error='Update download cancelled.' if self.cancelled.is_set() else str(error)[:2000])
                self.state['failures'] = min(8, self.state.get('failures', 0) + 1)
                self.state['nextCheck'] = self.clock() + min(3600 * 6, 300 * 2 ** self.state['failures'])
                self.save()
        finally:
            with self.lock:
                self.process = None

    def check(self):
        with self.lock:
            channel = self.state['preferences']['channel']; self.state['lastAttempt'] = self.clock(); self.save()
        result = self.runner({'operation': 'discover', 'channel': channel, 'target': self.current['target'], 'component':self.current['component']})
        authenticated = result.get('authenticated') is True
        if authenticated:
            os_version = self.os_version()
            if not os_version: raise ValueError('The operating system version could not be verified for this signed release.')
            candidate = select_release(result['catalog'], self.current, channel, os_version=os_version, distribution=self.distribution())
        else:
            candidates = []
            for release in result.get('releases', []):
                self.validate_public_release(release, channel)
                if (version(release['version']) > version(self.current['version']) or
                        self.current.get('buildKnown') and (version(release['version']), release['build']) > (version(self.current['version']), self.current['build'])):
                    candidates.append(release)
            candidate = max(candidates, key=lambda r: (version(r['version']), r['build'])) if candidates else None
        with self.lock:
            if channel != self.state['preferences']['channel']:
                return  # A reply for an old preference cannot overwrite its replacement.
            identity = self.release_id()
            self.state.update(candidate=candidate, authenticated=authenticated, error=None,
                              lastSuccessfulCheck=self.clock(), failures=0, phase='available' if candidate else 'current')
            if identity != self.release_id():
                self.state['downloads'] = []
            delay = self.state['preferences']['intervalHours'] * 3600
            self.state['nextCheck'] = self.clock() + delay + random.uniform(0, 900)
            self.save()
            automatic = candidate and self.state['preferences']['automaticDownload']
        if automatic:
            self.download()

    def validate_public_release(self, value, channel):
        if (not isinstance(value, dict) or set(value) != {'version', 'build', 'channel', 'target', 'releaseUrl', 'artifacts', 'authenticated'}
                or value['authenticated'] is not False or value['channel'] != channel or value['target'] != self.current['target'] or self.current['component']!='desktop'
                or type(value['build']) is not int or not 1 <= value['build'] <= 2**31 - 1):
            raise ValueError('Invalid public release discovery.')
        version(value['version']); canonical_release_url(value['releaseUrl'])
        if not isinstance(value['artifacts'], list) or not 1 <= len(value['artifacts']) <= 8:
            raise ValueError('Invalid public artifact list.')
        roles = set()
        for artifact in value['artifacts']:
            if (not isinstance(artifact, dict) or set(artifact) != {'role', 'targetPath', 'bytes', 'sha256'} or artifact['role'] not in ('runtime', 'desktop', 'browser', 'installer', 'bundle')
                    or artifact['role'] in roles
                    or type(artifact['bytes']) is not int or not 0 < artifact['bytes'] <= MAX_ARTIFACT
                    or not isinstance(artifact['sha256'], str) or not HEX.fullmatch(artifact['sha256'])):
                raise ValueError('Invalid public release artifact.')
            target_path(artifact['targetPath'])
            roles.add(artifact['role'])

    def os_version(self):
        import platform
        if sys.platform == 'darwin': return platform.mac_ver()[0]
        if sys.platform == 'win32': return str(sys.getwindowsversion().build)
        import re
        match = re.match(r'^[0-9]+(?:\.[0-9]+){0,2}', platform.release())
        return match[0] if match else None

    def distribution(self):
        import platform,re
        if sys.platform != 'linux': return None
        try:
            value = platform.freedesktop_os_release()
            number = value['VERSION_ID']
            return (value['ID'],number) if re.fullmatch(r'[0-9]{1,6}(?:\.[0-9]{1,6}){0,2}',number) else None
        except (OSError, KeyError): return None

    def download(self):
        with self.lock:
            candidate = deepcopy(self.state['candidate']); identity = self.release_id()
            authenticated = self.state['authenticated']
            if not candidate:
                raise ValueError('No compatible update is selected.')
            self.state.update(phase='downloading', bytesDownloaded=0); self.save()
        roles = {'debian': ('runtime', 'desktop', 'browser'), 'windows-inno': ('installer',),
                 'macos-app': ('bundle',), 'managed-linux': ('bundle',), 'fedora': ('bundle',), 'development': ('bundle', 'installer')}[self.current['installType']]
        artifacts = [a for a in candidate['artifacts'] if a['role'] in roles]
        if not artifacts:
            raise ValueError('The selected release has no artifact for this installation.')
        if shutil.disk_usage(self.base).free < 2 * sum(a['bytes'] for a in artifacts) + 64 * 1024**2:
            raise ValueError('There is not enough free disk space for this update download.')
        downloads = []
        for artifact in artifacts:
            if self.cancelled.is_set(): raise InterruptedError('Update download cancelled.')
            result = self.runner({'operation': 'download', 'artifact': artifact})
            if authenticated and result.get('authenticated') is not True:
                raise ValueError('Signed delivery became unavailable. Nothing was installed.')
            file = Path(result['file'])
            # A helper reply cannot introduce an arbitrary path into later apply.
            expected = self.base / 'repository' / (artifact['sha256'] + '.download')
            if file != expected:
                raise ValueError('The download helper returned an unexpected cache path.')
            if sys.platform=='win32':
                from platform_adapters.windows_identity import protect_inherited_download
                protect_inherited_download(file)
            self.publish_download(candidate, artifact, file)
            downloads.append({**artifact, 'file': str(file)})
        with self.lock:
            if identity != self.release_id(): return
            self.state.update(downloads=downloads, phase='ready', error=None); self.save()

    def ready_directory(self, candidate=None):
        candidate = candidate or self.state['candidate']
        name = '-'.join(str(candidate[k]) for k in ('channel', 'target', 'version', 'build'))
        return self.base / 'ready' / name

    def publish_download(self, candidate, artifact, source):
        # Give the manual download its original .exe/.dmg/.deb extension in a
        # dedicated private directory. Opening that folder never executes it.
        require_directory(private_directory(self.base / 'ready'))
        folder = require_directory(private_directory(self.ready_directory(candidate)))
        output = folder / artifact['targetPath'].rsplit('/', 1)[1]
        temporary = folder / (artifact['sha256'] + '.' + secrets.token_hex(16) + '.part')
        digest = hashlib.sha256(); count = 0
        fd = descriptor(temporary, writable=True, exclusive=True)
        try:
            with os.fdopen(fd, 'wb') as target, os.fdopen(descriptor(source), 'rb') as original:
                while chunk := original.read(1024**2):
                    if self.cancelled.is_set(): raise InterruptedError('Update download cancelled.')
                    count += len(chunk)
                    if count > artifact['bytes']: raise ValueError('The cached download size changed.')
                    digest.update(chunk); target.write(chunk)
                if count != artifact['bytes'] or digest.hexdigest() != artifact['sha256']:
                    raise ValueError('The cached download does not match its selected release.')
                target.flush(); os.fsync(target.fileno())
            if output.exists() or output.is_symlink(): os.close(descriptor(output))
            replace_file(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)

    def run_helper(self, request):
        from .client import repository_request
        def observed(process):
            with self.lock:self.process=process
        def progress(bytes_):
            with self.lock:self.state['bytesDownloaded']=bytes_
        return repository_request(self.root,self.base/'repository',request,node=self.node_executable(),
            cancelled=self.cancelled,progress=progress,observed=observed)

    def node_executable(self):
        from .client import node_executable
        return node_executable(self.root,development=self.current['installType'] in ('development','managed-linux'))

    def start_scheduler(self):
        if self.scheduler: return
        def schedule():
            # A short startup delay avoids competing with first-run rendering.
            if self.stopping.wait(30): return
            while not self.stopping.is_set():
                try:
                    self.collect_installation_result()
                    with self.lock:
                        due = (self.state['preferences']['automaticChecks'] and self.clock() >= self.state['nextCheck']
                               and self.state['phase'] not in ('installing','installed') and not (self.job and self.job.is_alive()))
                        install=(self.state['phase']=='ready' and self.state['preferences']['automaticInstall'] and
                                 self.state['preferences']['automaticDownload'] and self.state.get('authenticated') is True and
                                 self.state.get('candidate',{}).get('automaticInstallQualified') is True and
                                 self.release_id()!=self.state['skippedRelease'] and self.clock()>=self.state['postponedUntil'] and
                                 self.automatic_capability() and
                                 self.clock()>=self.state['nextInstallAttempt'] and not (self.job and self.job.is_alive()))
                    if install:self.start('ready',lambda:None)
                    elif due: self.start('checking', self.check)
                except Exception:
                    pass  # Maintenance admission stays authoritative.
                # Retain failed-result age and back off instead of busy polling.
                if self.stopping.wait(300): break
        self.scheduler = threading.Thread(target=schedule, name='augmentor-update-schedule', daemon=True)
        self.scheduler.start()

    def close(self):
        self.stopping.set(); self.cancelled.set()
        with self.lock:
            if self.process and self.process.poll() is None: self.process.terminate()
        if self.job: self.job.join(timeout=10)
        if self.scheduler: self.scheduler.join(timeout=2)
