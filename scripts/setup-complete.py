#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Guided fresh-user setup for the complete, checksummed Debian preview bundle."""
import argparse
import getpass
import hashlib
import importlib.util
import json
import os
import platform
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def run(*args, **kwargs):return subprocess.run([str(a) for a in args],check=True,**kwargs)


def load(path):
    spec=importlib.util.spec_from_file_location(path.stem.replace('-','_'),path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def write(path, text, mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_name(path.name+'.new');temporary.write_text(text);temporary.chmod(mode);temporary.replace(path)


def verify_bundle(bundle):
    manifest=json.loads((bundle/'bundle.json').read_text())
    if manifest.get('format')!='augmentor-complete/1':raise ValueError('Unknown bundle format.')
    for name,expected in manifest['sha256'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe bundle filename.')
        with (bundle/name).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected:raise ValueError('Bundle checksum failed: '+name)
    return manifest


def model_settings(url, model, context):
    parsed=urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a model API URL without credentials, query or fragment.')
    if parsed.scheme=='http' and parsed.hostname not in ('127.0.0.1','::1','localhost'):
        raise ValueError('Remote model APIs require HTTPS.')
    if not model.strip() or context<4096:raise ValueError('Supply the model ID and a context window of at least 4096 tokens.')
    return {'llm-pi-ai':{'providers':{'augmentor-model':{'api':'openai-completions','baseURL':url.rstrip('/'),
             'apiKeyEnv':'AUGMENTOR_MODEL_API_KEY','models':[{'id':model,'name':model,'contextWindow':context,
             'maxTokens':min(4096,context//4),'reasoning':False,'input':['text']}]}}},
             'agent-default-model':{'provider':'augmentor-model','model':model}}


def environment_value(value):
    if any(c in value for c in '\r\n\0'):raise ValueError('API key must be a single line.')
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'


def service(command, home, credentials):
    def field(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
    return ('[Unit]\nDescription=Augmentor DSH runtime\nAfter=network-online.target\n\n[Service]\nType=exec\n'+
            'Environment='+field('DSH_HOME='+str(home))+'\nEnvironment=DSH_TELEMETRY_MODE=DISABLED\n'+
            'EnvironmentFile='+field(credentials)+'\nExecStart='+' '.join(field(v) for v in command)+
            '\nRestart=on-failure\nRestartSec=5\nUMask=0077\n\n[Install]\nWantedBy=default.target\n')


def configure_product(app, cli, home, endpoint, env, state, *, save=True):
    """Compose the product against a temporary owned host; never touch another DSH."""
    sys.path.insert(0,str(app/'services'))
    from dsh.setup import Setup
    from dsh.remote import client
    # The voice bundle needs this fresh secret during its first boot. The
    # checked product installer subsequently validates and reuses it.
    if not (home/'augmentor-product-token').exists():
        write(home/'augmentor-product-token',secrets.token_hex(32)+'\n')
    log_path=state/'setup-dsh.log';process=None
    def stop():
        nonlocal process
        if process and process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        process=None
    def start():
        nonlocal process
        # Truncate only this fresh install's temporary bootstrap log.
        with log_path.open('w') as log:
            process=subprocess.Popen([str(cli),'web','--no-open','--host','127.0.0.1','--port',str(urlsplit(endpoint).port)],
                                     env=env,stdout=log,stderr=log,start_new_session=True)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('The new DSH runtime stopped. Private diagnostic: '+str(log_path))
            matches=re.findall(r'token=([A-Za-z0-9_-]+)',log_path.read_text(errors='replace'))
            if matches:
                try:
                    remote=client(endpoint,home,matches[-1]);remote.call('host.describe');return matches[-1]
                except (OSError,ValueError):pass
            time.sleep(.25)
        raise RuntimeError('The new DSH runtime did not become ready. Private diagnostic: '+str(log_path))
    try:
        token=start();setup=Setup();checked=setup.check({'endpoint':endpoint+'/?token='+token,'home':str(home)})
        if not checked['installed']:
            setup.install(checked['token']);stop();token=start()
            checked=setup.check({'endpoint':endpoint+'/?token='+token,'home':str(home)})
        if save:setup.save(checked['token'])
    finally:stop()


def install(args):
    os.umask(0o077)
    if os.geteuid()==0:raise ValueError('Run this installer as your normal desktop user. It requests sudo only for system packages.')
    bundle=args.bundle.resolve();manifest=verify_bundle(bundle)
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'augmentor'
    config=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))
    state=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'augmentor-install'
    stamp=state/'installation.json'
    record=json.loads(stamp.read_text()) if stamp.exists() else {}
    resumable=record.get('bundle')==manifest['artifactId'] and record.get('status')=='preparing'
    if record.get('bundle')==manifest['artifactId'] and record.get('status')=='installed':return record
    if (data/'desktop.json').exists() and not resumable:raise ValueError('An Augmentor desktop is already installed. Use its documented update/migration workflow; this wizard is for fresh users.')
    if (Path.home()/'.dsh').exists() and any((Path.home()/'.dsh').iterdir()):
        raise ValueError('An existing DSH installation was found. Follow the existing-installation migration guide; no profile or model was changed.')
    if not args.skip_packages:
        info=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        if info.get('ID','').strip('"')!='debian' or info.get('VERSION_ID','').strip('"')!='13' or platform.machine() not in ('x86_64','amd64'):
            raise ValueError('This complete installer is qualified for Debian 13 amd64. Other distributions require separate qualification.')
    if args.plan:return {'bundle':manifest['version'],'components':manifest['components'],'changes':'Fresh private DSH home, desktop/browser, plugins, login recovery and optional local voice/memory.'}
    if not args.model_url:args.model_url=input('Your OpenAI-compatible model API URL (including /v1): ').strip()
    if not args.model:args.model=input('Model ID: ').strip()
    settings=model_settings(args.model_url,args.model,args.context)
    if sys.stdin.isatty() and not args.non_interactive:
        if not args.voice:
            args.voice=input('Set up local voice? Downloads a 2.54 GB model; Breeze research/non-commercial terms apply. [y/N] ').strip().lower()=='y'
        if args.voice and not args.gpu:
            choice=input('Speech device: enter an NVIDIA GPU UUID, or press Enter for CPU (slower): ').strip()
            if choice:args.gpu=choice
        if not args.memory:args.memory=input('Set up dual memory with Docker and this local model? [y/N] ').strip().lower()=='y'
    if args.memory and urlsplit(args.model_url).hostname not in ('127.0.0.1','::1'):
        raise ValueError('The bundled memory setup currently requires a local numeric-loopback model API. Omit memory for a cloud-only setup.')
    secret=os.environ.get(args.api_key_env) if args.api_key_env else getpass.getpass('Model API key (Enter for a local model without authentication): ')
    if args.api_key_env and secret is None:raise ValueError('The requested API-key environment variable is not set.')
    secret=secret or 'local'
    environment_value(secret)
    if not 1024<=args.port<=65535:raise ValueError('Choose a nonprivileged DSH port.')
    with socket.socket() as probe:
        try:probe.bind(('127.0.0.1',args.port))
        except OSError:raise ValueError('The selected DSH port is occupied; no existing service was stopped.') from None
    if stamp.exists() and json.loads(stamp.read_text()).get('bundle')!=manifest['artifactId']:
        raise ValueError('A different partial installation exists; review it before resuming.')
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    write(stamp,json.dumps({'bundle':manifest['artifactId'],'status':'preparing'})+'\n')
    if not args.skip_packages:
        packages=[bundle/name for name in manifest['sha256'] if name.endswith('.deb')]
        run('sudo','apt','install','-y',*packages,'python3-venv','npm','libportaudio2','git','cmake','g++','pkg-config')
    app=args.app_root.resolve();node=app/'node/bin/node'
    runtime=data/'dsh-runtime';runtime.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'PATH':str(node.parent)+':'+os.environ.get('PATH','')}
    for name in ('package.json','package-lock.json'):shutil.copy2(bundle/'dsh'/name,runtime/name)
    run('npm','ci','--prefix',runtime,'--ignore-scripts','--omit=dev','--no-audit','--no-fund',env=env)
    cli=runtime/'node_modules/.bin/dsh';home=data/'dsh-home';home.mkdir(parents=True,exist_ok=True,mode=0o700)
    env.update(DSH_HOME=str(home),DSH_TELEMETRY_MODE='DISABLED',AUGMENTOR_MODEL_API_KEY=secret)
    env['PATH']=str(cli.parent)+':'+env['PATH']
    # Setup's supported-CLI discovery must use this exact freshly installed DSH.
    os.environ['PATH']=env['PATH']
    config_home=Path(os.environ.get('AUGMENTOR_SHARED_CONFIG',config/'augmentor'))
    if (config_home/'harnesses.json').exists():
        saved=json.loads((config_home/'harnesses.json').read_text()).get('dsh',{})
        if not resumable or saved.get('home')!=str(home):raise ValueError('Existing harness settings need a reviewed migration.')
    import yaml
    write(home/'settings.yaml',yaml.safe_dump(settings))
    write(state/'model.env','AUGMENTOR_MODEL_API_KEY='+environment_value(secret)+'\n')
    for name in manifest['plugins']:
        run(cli,'plugin','--profile','web','add',bundle/name,'--ignore-scripts','--config.auto-install-peers=false',env=env,stdout=subprocess.DEVNULL)
    voice=home/'profiles/web/node_modules/dsh-resonant-voice'
    if args.voice:
        command=['/usr/bin/python3',voice/'bin/setup-linux.py','--node',node,'--accept-model-license']
        if args.gpu:
            if not args.skip_packages:run('sudo','apt','install','-y','libvulkan-dev','glslc','spirv-headers')
            command+=['--gpu',args.gpu]
        else:command+=['--cpu']
        if args.no_services:command+=['--no-start']
        run(*command,env=env)
    run(node,voice/'bin/resonant-voice.js','init',env=env)
    endpoint='http://127.0.0.1:'+str(args.port)
    configure_product(app,cli,home,endpoint,env,state)
    python=data/'python/bin/python'
    if not python.exists():run('/usr/bin/python3','-m','venv','--system-site-packages',data/'python')
    run(python,'-m','pip','install','--disable-pip-version-check','sounddevice==0.5.2')
    units=config/'systemd/user';units.mkdir(parents=True,exist_ok=True)
    unit=units/'augmentor-dsh.service'
    content=service([node,cli.resolve(),'web','--no-open','--host','127.0.0.1','--port',str(args.port)],home,state/'model.env')
    if unit.exists() and unit.read_text()!=content:raise ValueError('Existing Augmentor DSH service differs.')
    write(unit,content)
    startup=load(app/'scripts/install-desktop-startup.py')
    startup.install(app,python,node,'augmentor-dsh.service',enable=not args.no_services)
    if not args.no_services:
        run(python,app/'scripts/setup-default-shortcuts.py')
    extension=data/'browser'/manifest['version']
    if extension.exists():shutil.rmtree(extension)
    extension.mkdir(parents=True)
    with zipfile.ZipFile(bundle/manifest['browser']) as archive:
        for name in archive.namelist():
            if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe extension archive member.')
        archive.extractall(extension)
    identity=manifest['extensionId']
    native={'name':'com.augmentor.agent','description':'Augmentor Agent','path':'/usr/bin/augmentor-browser-host','type':'stdio','allowed_origins':['chrome-extension://'+identity+'/']}
    for browser in ('chromium','google-chrome','BraveSoftware/Brave-Browser'):
        write(config/browser/'NativeMessagingHosts/com.augmentor.agent.json',json.dumps(native,indent=2)+'\n')
    if args.memory:
        if not args.skip_packages:run('sudo','apt','install','-y','docker.io')
        docker_ok=subprocess.run(['docker','info'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
        command=[python,app/'scripts/setup-hindsight.py','--model-url',args.model_url,'--model',args.model,'--api-key-env','AUGMENTOR_MODEL_API_KEY']
        if not docker_ok:command+=['--sudo-docker']
        run(*command,env=env)
    if not args.no_services:
        run('systemctl','--user','daemon-reload');run('systemctl','--user','enable','--now','augmentor-dsh.service')
        # Promote a complete copy so future package replacements cannot silently
        # replace the files selected for login.
        deployment=load(app/'scripts/desktop-deployment.py')
        with deployment.locked():
            release=deployment.stage(app,manifest['sourceCommit'],python,node)
            for attempt in range(60):
                try:deployment.activate(release);break
                except (RuntimeError,OSError):
                    if attempt==59:raise
                    time.sleep(1)
        run('systemctl','--user','start','augmentor-desktop.service')
    result={'bundle':manifest['artifactId'],'status':'installed','desktop':True,'browserExtension':str(extension),
            'browserAction':'Load this folder once in chrome://extensions (Developer mode).',
            'voice':'configured' if args.voice else 'plugin installed; speech engine setup deferred',
            'memory':'configured' if args.memory else 'adapter installed; memory engine setup deferred',
            'model':'configured; verify a reply before relying on this setup'}
    write(stamp,json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--model-url');p.add_argument('--model');p.add_argument('--context',type=int,default=32768)
    p.add_argument('--api-key-env');p.add_argument('--port',type=int,default=3080)
    p.add_argument('--voice',action='store_true',help='Accept Breeze research/non-commercial terms and provision local voice.');p.add_argument('--gpu',help='Explicit NVIDIA GPU UUID; otherwise voice uses CPU.')
    p.add_argument('--memory',action='store_true',help='Provision Docker Hindsight using this explicitly chosen local model.')
    p.add_argument('--plan',action='store_true');p.add_argument('--app-root',type=Path,default=Path('/usr/lib/augmentor'))
    p.add_argument('--non-interactive',action='store_true',help='Use supplied model settings and explicit feature flags without questions.')
    p.add_argument('--skip-packages',action='store_true',help=argparse.SUPPRESS);p.add_argument('--no-services',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.gpu and not args.voice:p.error('--gpu requires --voice')
    print(json.dumps(install(args),indent=2))


if __name__=='__main__':
    try:main()
    except Exception as error:raise SystemExit('Setup did not complete: '+str(error))
