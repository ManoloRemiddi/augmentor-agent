# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared voice provider configuration. Secrets stay in the native OS vault."""
import json
import math
import os
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path
from .instances import scoped_path, current_name

PROVIDERS = ('local', 'openai-live')
VOICES = ('marin', 'quartz', 'ripple', 'vesper', 'willow', 'stone', 'gleam', 'meridian', 'bossa', 'tempo', 'beacon', 'delta', 'cinder')
LIVE_URL = 'wss://api.openai.com/v1/live/sessions'
SERVICE = 'Augmentor Agent Voice'


def config_path():
    home = Path(os.environ.get('AUGMENTOR_PI_CONFIG', Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'augmentor-pi'))
    return scoped_path(home / 'voice-providers.json')


def load_config():
    defaults = {'provider': 'local', 'cloudVoice': 'marin', 'cloudConsent': False, 'cloudVerified': False}
    try:
        value = json.loads(config_path().read_text())
        if not isinstance(value, dict): return defaults
        for key, default in defaults.items():
            if type(value.get(key)) is type(default):
                defaults[key] = value[key]
    except (OSError, ValueError, TypeError):
        pass
    if defaults['provider'] not in PROVIDERS:
        defaults['provider'] = 'local'
    if defaults['cloudVoice'] not in VOICES:
        defaults['cloudVoice'] = 'marin'
    return defaults


def save_config(value):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        json.dump(value, stream)
        temporary = stream.name
    try:
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def credential_store():
    # Select the OS backend explicitly; never use a plaintext fallback/chainer.
    if sys.platform == 'darwin':
        from keyring.backends.macOS import Keyring
    elif sys.platform == 'win32':
        # pywin32 is already pinned in Windows releases. Use Credential Manager
        # directly so this path does not depend on an absent keyring wheel.
        import win32cred
        class WindowsVault:
            def target(self, service, account): return service + '/' + account
            def get_password(self, service, account):
                try: value = win32cred.CredRead(self.target(service, account), win32cred.CRED_TYPE_GENERIC)
                except Exception as error:
                    if getattr(error, 'winerror', None) == 1168: return None
                    raise
                return value['CredentialBlob'].decode('utf-16-le')
            def set_password(self, service, account, password):
                win32cred.CredWrite({'Type': win32cred.CRED_TYPE_GENERIC,
                    'TargetName': self.target(service, account), 'UserName': account,
                    'CredentialBlob': password.encode('utf-16-le'),
                    'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE}, 0)
            def delete_password(self, service, account):
                win32cred.CredDelete(self.target(service, account), win32cred.CRED_TYPE_GENERIC, 0)
        return WindowsVault()
    else:
        from keyring.backends.SecretService import Keyring
    return Keyring()


def cloud_key():
    try:
        key = credential_store().get_password(SERVICE, current_name())
        if not key: raise ValueError('Missing key')
        return key
    except Exception:
        raise RuntimeError('OpenAI Voice needs setup. Unlock the credential vault and configure your API key.') from None


def local_configured():
    home = Path(os.environ.get('RESONANT_VOICE_HOME', Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'resonant-voice'))
    try:
        value = json.loads((home / 'config.json').read_text())
        token = (home / 'token').read_text().strip()
        if not isinstance(value, dict) or len(token) != 64 or not all(c in 'abcdef0123456789' for c in token): return False
        # Optional speech installation initializes a config even before models
        # exist. A non-inference TTS health check distinguishes that from readiness.
        tts = value.get('tts', {})
        if not isinstance(tts, dict): return False
        endpoint = tts.get('url', 'http://127.0.0.1:8878')
        if not isinstance(endpoint, str): return False
        parsed = urlsplit(endpoint)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
            return False
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs): return None
        with urllib.request.build_opener(NoRedirect).open(endpoint.rstrip('/') + '/health', timeout=1) as response:
            health = json.loads(response.read(8192))
        if not isinstance(health, dict) or health.get('status') != 'ok' or health.get('sample_rate') != 24000:return False
        port=value.get('port',8877)
        if type(port) is not int or not 1024<=port<=65535:return False
        with urllib.request.build_opener(NoRedirect).open(f'http://127.0.0.1:{port}/health',timeout=1) as response:
            companion=json.loads(response.read(8192))
        return isinstance(companion,dict) and companion.get('protocol')=='resonant-voice/1' and isinstance(companion.get('capabilities'),dict) and companion['capabilities'].get('scopedHarnessBridge',0)>=1
    except (OSError, ValueError, TypeError):
        return False


def audio_available():
    import importlib
    try:
        audio=importlib.import_module('sounddevice')
        core=importlib.import_module('PySide6.QtCore')
        return hasattr(audio,'RawInputStream') and hasattr(audio,'RawOutputStream') and hasattr(core,'QCoreApplication')
    except (ImportError,OSError,ValueError):return False


def usage_path():
    path=config_path()
    return path.with_name(path.name.replace('voice-providers','voice-usage'))


def usage_receipt():
    try:
        value=json.loads(usage_path().read_text())
        seconds=value.get('seconds')
        if type(value.get('confirmed')) is not bool:return None
        if seconds is not None and (type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0):return None
        return {'seconds':seconds,'confirmed':value['confirmed']}
    except (OSError,ValueError,AttributeError):return None


def snapshot():
    config = load_config()
    local = local_configured()
    cloud = False
    if config['cloudConsent'] and config['cloudVerified']:
        try: cloud = bool(cloud_key())
        except RuntimeError: pass
    audio=audio_available()
    configured = audio and (local if config['provider'] == 'local' else cloud)
    return {**config, 'configured': configured, 'status': 'ready' if configured else 'needs-setup',
            'lastUsage':usage_receipt(), 'audioAvailable':audio, 'audioError': '' if audio else 'Install the Augmentor Desktop audio runtime to use Voice. Local speech models are optional.',
            'providers': {'local': {'configured': local}, 'openai-live': {'configured': cloud}},
            'cloudVoices': [{'id': v, 'name': v.capitalize()} for v in VOICES]}


def record_usage(seconds, confirmed):
    """Keep only the latest duration receipt, without audio or conversation data."""
    path = usage_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        json.dump({'seconds': seconds, 'confirmed': confirmed}, stream)
        temporary = stream.name
    try: os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def verify_cloud(key, voice, connect=None):
    """Verify actual Live access without microphone capture. Always close the test."""
    if connect is None:
        import websocket
        connect = websocket.create_connection
    socket = None
    deadline=time.monotonic()+20
    try:
        socket = connect(LIVE_URL, timeout=10, header={'Authorization': 'Bearer ' + key}, suppress_origin=True, redirect_limit=0)
        socket.send(json.dumps({'type': 'session.start', 'session': {'model': 'gpt-live-1',
            'instructions': 'This is a connection test. Remain silent. Delegate all requests to the application.',
            'audio': {'format': {'type': 'audio/pcm', 'rate': 24000}, 'output': {'voice': voice}},
            'delegation': {'type': 'client'}, 'store': False}}))
        for _ in range(32):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('Test timed out')
            socket.settimeout(remaining)
            event = json.loads(socket.recv())
            if event.get('type') == 'error': raise ValueError('Rejected')
            if event.get('type') == 'session.started': break
        else: raise ValueError('No startup confirmation')
        socket.send(json.dumps({'type': 'session.close'}))
        for _ in range(32):
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('Test timed out')
            socket.settimeout(remaining)
            event = json.loads(socket.recv())
            if event.get('type') == 'session.closed': return
            if event.get('type') == 'error': raise ValueError('Close rejected')
        raise ValueError('No closure confirmation')
    except Exception:
        raise RuntimeError('OpenAI GPT-Live could not confirm access and session closure. Check your API key, project billing and network, then retry.') from None
    finally:
        if socket is not None: socket.close()


def configure_cloud(key, voice, consent, verify=verify_cloud):
    if not isinstance(key, str) or not 16 <= len(key) <= 4096 or any(c.isspace() for c in key):
        raise ValueError('Enter a valid OpenAI project API key.')
    if voice not in VOICES or consent is not True:
        raise ValueError('Choose a voice and acknowledge cloud processing and duration charges.')
    verify(key, voice)
    try:
        store = credential_store()
        previous = store.get_password(SERVICE, current_name())
        store.set_password(SERVICE, current_name(), key)
    except Exception:
        raise RuntimeError('The credential vault is unavailable or locked. Unlock it and retry; the key was not saved to a file.') from None
    config = load_config()
    config.update(provider='openai-live', cloudVoice=voice, cloudConsent=True, cloudVerified=True)
    try: save_config(config)
    except OSError:
        try:
            if previous: store.set_password(SERVICE, current_name(), previous)
            else: store.delete_password(SERVICE, current_name())
        except Exception:
            raise RuntimeError('Voice settings could not be saved or rolled back. Remove the saved key and retry setup.') from None
        raise RuntimeError('Voice settings could not be saved. The previous API key was restored.') from None
    return snapshot()


def select_provider(provider):
    if provider not in PROVIDERS: raise ValueError('Choose local or OpenAI GPT-Live voice.')
    config = load_config(); config['provider'] = provider; save_config(config)
    return snapshot()


def remove_cloud():
    try:
        store = credential_store()
        if store.get_password(SERVICE, current_name()): store.delete_password(SERVICE, current_name())
    except Exception:
        raise RuntimeError('Unlock the credential vault before removing the OpenAI Voice key.') from None
    config = load_config(); config.update(cloudConsent=False, cloudVerified=False); save_config(config)
    return snapshot()


def cloud_ticket(session_id):
    config = snapshot()
    if config['provider'] != 'openai-live' or not config['configured']:
        raise RuntimeError('Configure OpenAI GPT-Live in Voice settings first.')
    return {'protocol': 'augmentor-live/1', 'provider': 'openai-live', 'sessionId': session_id}


class VoicePreferences:
    """Read only voice fields; browser settings need no Qt appearance decoder."""
    def __init__(self):
        base=config_path().with_name('appearance.json')
        self.path=scoped_path(base)
        fresh=current_name()!='main' and not self.path.exists()
        try:
            self.data=json.loads((base if fresh else self.path).read_text())
            if not isinstance(self.data,dict):self.data={}
        except (OSError,ValueError):self.data={}
        self.values={'resonant_voice':True,'voice_mode':'manual','voice_pause_ms':800}
        for key,default in self.values.copy().items():
            if type(self.data.get(key)) is type(default):self.values[key]=self.data[key]
        if self.values['voice_mode'] not in ('manual','hands-free'):self.values['voice_mode']='manual'
        self.values['voice_pause_ms']=max(400,min(2000,self.values['voice_pause_ms']))
        if fresh:
            self.data['placement']={}
            self.save()

    def save(self):
        # Merge the latest appearance data so a concurrent appearance edit is
        # not overwritten by a long-running voice access test.
        try:
            latest=json.loads(self.path.read_text())
            if isinstance(latest,dict):self.data=latest
        except (OSError,ValueError):pass
        self.data.update(self.values)
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as stream:
            json.dump(self.data,stream);temporary=stream.name
        try:os.replace(temporary,self.path)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)


def provider_settings(value, preferences=None, local_request=None):
    preferences = preferences or VoicePreferences()
    action = value.get('action', 'get')
    if action == 'cloud-configure':
        configure_cloud(value.get('apiKey'), value.get('voice'), value.get('consent'))
    elif action == 'cloud-remove': remove_cloud()
    elif action == 'select': select_provider(value.get('provider'))
    elif action == 'save':
        settings = value.get('settings', {})
        if type(settings.get('enabled')) is not bool: raise ValueError('Invalid voice On/Off setting')
        if settings.get('mode') not in ('manual', 'hands-free'): raise ValueError('Choose a conversation mode')
        if type(settings.get('pauseMs')) is not int or not 400 <= settings['pauseMs'] <= 2000:
            raise ValueError('Invalid pause duration')
        if settings.get('provider', load_config()['provider']) not in PROVIDERS: raise ValueError('Choose a voice provider')
        if settings.get('provider', load_config()['provider']) == 'local' and settings.get('voiceId'):
            if local_request is None:
                from .voice_settings import voice_request
                local_request = voice_request
            local_request('preferences', {'values': {k: settings[k] for k in ('voiceId', 'speed', 'volume')}})
        if 'provider' in settings: select_provider(settings['provider'])
        preferences.values.update(resonant_voice=settings['enabled'], voice_mode=settings['mode'], voice_pause_ms=settings['pauseMs'])
        preferences.save()
    elif action not in ('get', 'status'):
        raise ValueError('Unsupported Voice settings action')
    state = snapshot()
    state.update(enabled=preferences.values['resonant_voice'], mode=preferences.values['voice_mode'], pauseMs=preferences.values['voice_pause_ms'])
    if action == 'status': return state
    state.update(voices=[], values={'voiceId': '', 'speed': 1, 'volume': 1})
    if state['providers']['local']['configured'] and state['provider']=='local':
        try:
            if local_request is None:
                from .voice_settings import voice_request
                local_request = voice_request
            result = local_request('preferences')
            state.update(voices=result['voices'], values=result['values'])
        except Exception:
            state['localError'] = 'The local speech service is unavailable. Start it or complete local setup.'
    return state
