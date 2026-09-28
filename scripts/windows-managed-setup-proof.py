#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual isolated Windows DSH setup/chat/restart using a deterministic model.

Never selects an installed user's profile, modifies login entries, or uses a real
provider secret. Native composer checks use a deterministic model, not a live
provider or physical keyboard/mouse.
"""
import argparse
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import yaml


def prepare_graph(root,work):
    """Known busy refusals may settle in this fixture; lost replies never retry."""
    from lifecycle.windows_preparation import WindowsPreparation
    from platform_adapters.windows_http import HttpRefused
    import windows_supervisor as owner
    deadline=time.monotonic()+10
    while True:
        preparation=WindowsPreparation(root,work/'run',work/'run/shared',owner.managed_directory())
        try:return preparation.__enter__()
        except ValueError as error:
            busy=(isinstance(error,HttpRefused) and error.code==409) or 'active work' in str(error)
            if not busy or time.monotonic()>=deadline:raise
            time.sleep(.1)


def desktop_chat(root, work, out):
    """Actual native GUI, real DSH, Send/Enter and restored rendered history."""
    from platform_adapters.processes import OwnedProcess
    from platform_adapters.transport import LocalSocket
    from augmentor_linux.instances import ipc_basename
    import win32api, win32con, win32job, win32process
    result = {'passed': False, 'scope': 'Native Augmentor.exe and widget input against real DSH with a deterministic model; no physical-input or live-provider claim.'}
    instance = 'windows-chat-proof'
    endpoint = work/'run'/(ipc_basename(instance)+'.sock')
    def exchange(command):
        with LocalSocket() as connection:
            connection.settimeout(8); connection.connect(str(endpoint)); connection.sendall(command.encode()+b'\n')
            with connection.makefile('rb') as stream: raw = stream.readline(1024*1024+1)
        if len(raw)>1024*1024 or not raw.endswith(b'\n'): raise ValueError('The native UI response was lost; no action was replayed.')
        return json.loads(raw)
    def ui(action, **values):
        response = exchange('ui-test:'+json.dumps({'action': action, **values}))
        if not response.get('ok'): raise ValueError(response.get('error', 'Native UI command failed.'))
        return response['result']
    def until(check, child):
        deadline = time.monotonic()+45
        last = None
        while time.monotonic()<deadline:
            if child.poll() is not None: raise AssertionError('The native chat process exited early.')
            try:
                last = ui('inspect')
                if check(last): return last
            except FileNotFoundError: pass
            time.sleep(.2)
        raise AssertionError('The native chat window did not become ready: '+json.dumps(last))
    session = None
    turns = []
    try:
        for index, submission in enumerate(('button','enter')):
            env = {**os.environ, 'QT_QPA_PLATFORM': 'windows', 'QSG_RHI_PREFER_SOFTWARE_RENDERER': '1'}
            # Keep only this disposable GUI and any fixture-started children in
            # a test-owned Job. This is not proof of normal product Quit ownership.
            child = OwnedProcess([str(root/'Augmentor.exe'), '--qualification-root', str(work),
                '--instance', instance, '--harness', 'dsh', '--ui-test-control'], env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                before = until(lambda value: value['online'] and value['visible'] and value['model'] and not value['dialogs'], child)
                assert before['preset'] == 'augmentor-linux-product', before
                assert before['model']['provider'] == 'augmentor-model' and before['model']['model'] == 'fixture', before
                assert not before['draft'] and not before['running'], before
                if index:
                    assert before['session'] == session and 'WINDOWS_UI_BUTTON' in before['transcript'], before
                else: assert before['session'] is None, 'Do not put proof text into another conversation.'
                process = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, before['pid'])
                try:
                    assert win32job.IsProcessInJob(process, child.job), 'An unowned process intercepted the native fixture.'
                    assert Path(win32process.GetModuleFileNameEx(process, 0)).resolve() == root/'Augmentor.exe'
                finally: process.Close()
                status = exchange('maintenance.status'); assert status['buildRoot'] == str(root), status
                marker = 'WINDOWS_UI_BUTTON' if not index else 'WINDOWS_UI_ENTER'
                prompt = 'Reply to '+marker+'. Do not use tools.'
                ui('send', text=prompt, via=submission)
                after = until(lambda value: not value['running'] and value['session'] and
                    value['transcript'].count('Windows managed setup verified.') >= index+1 and
                    prompt in value['transcript'], child)
                assert after['transcript'].count(prompt) == 1 and not after['draft'], after
                session = after['session']
                ui('capture', path=str((out/('native-chat-'+submission+'.png')).resolve()))
                turns.append({'submission': submission, 'pid': after['pid'], 'session': session, 'online': after['online']})
                preparation=prepare_graph(root,work)
                try:
                    assert [item.pid for item in preparation.windows]==[after['pid']]
                    assert preparation.dsh is not None
                    assert {item.name for item in preparation.companions}=={'prompts','memory'}
                    preparation.check()
                finally:preparation.__exit__(*sys.exc_info())
                restored=ui('inspect')
                assert restored['session']==session and restored['transcript']==after['transcript'] and not restored['draft']
                maintenance_token = uuid.uuid4().hex
                def maintenance(action):
                    return exchange('maintenance:'+json.dumps({'method':'host.maintenance.'+action,
                        'params':{'token':maintenance_token}}))
                deadline = time.monotonic()+10
                while True:
                    prepared = maintenance('prepare')
                    if prepared.get('ok'):break
                    if time.monotonic()>=deadline:raise AssertionError('The idle desktop did not prepare: '+str(prepared))
                    time.sleep(.1)
                assert prepared['result']['phase']=='prepared' and prepared['pid']==after['pid'], prepared
                closed = maintenance('commit'); assert closed['ok'] and closed['result']['phase']=='closing', closed
                assert child.wait_graceful(timeout=15) == 0, 'The idle desktop did not close normally.'
            finally:
                child.terminate(); child.wait(timeout=10)
        result.update(passed=True, turns=turns, historyRestored=True, noDuplicateSubmission=True, preparedNormalWindowExit=True,
            graphPreparedAndCancelledWithActualDesktopDshAndCompanions=True)
        return result
    finally:
        (out/'native-chat.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Requires the native Windows runtime.')
    root = args.root.resolve(); args.out.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(root/'services'), str(root/'apps/native')]
    from platform_adapters.paths import private_directory
    from dsh import managed, setup
    import windows_supervisor as owner
    work = private_directory(Path(tempfile.mkdtemp(prefix='augmentor-windows-setup-')).resolve()/'private')
    for name in ('config', 'data', 'state', 'run', 'workspace'): private_directory(work/name)
    os.environ.update(XDG_CONFIG_HOME=str(work/'config'), XDG_DATA_HOME=str(work/'data'),
        XDG_STATE_HOME=str(work/'state'), XDG_RUNTIME_DIR=str(work/'run'),
        AUGMENTOR_SHARED_CONFIG=str(private_directory(work/'config/shared')),
        AUGMENTOR_SHARED_STATE=str(private_directory(work/'run/shared')),
        AUGMENTOR_SHARED_DATA=str(private_directory(work/'data/shared')),
        AUGMENTOR_DSH_WORKSPACE_ROOT=str(work/'workspace'),
        AUGMENTOR_DSH_CLI=str(root/'dsh/node_modules/@deepseek-ai/dsh/lib/bin.js'),
        AUGMENTOR_PYTHON=str(root/'python/python.exe'), AUGMENTOR_PI_NODE=str(root/'node/node.exe'),
        AUGMENTOR_PWSH=str(root/'powershell/pwsh.exe'), PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    os.environ['PATH'] = os.pathsep.join([str(root/'node'), str(root/'python'), str(root/'powershell'), os.environ.get('PATH', os.defpath)])
    calls = []
    model_waiting, release_model = threading.Event(), threading.Event()
    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert self.headers['Authorization'] == 'Bearer fixture-only-key'
            calls.append(body)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream' if body.get('stream') else 'application/json')
            self.end_headers()
            if body.get('stream'):
                latest = next((item for item in reversed(body.get('messages', [])) if item.get('role') == 'user'), {})
                if 'LEASE_HOLD_FIXTURE' in json.dumps(latest):
                    self.wfile.write(b'data: {"choices":[{"index":0,"delta":{"role":"assistant","content":"Waiting"},"finish_reason":null}]}\n\n')
                    self.wfile.flush(); model_waiting.set()
                    release_model.wait(30)
                    return
                for delta, finish in [({'role': 'assistant', 'content': 'Windows managed setup verified.'}, None), ({}, 'stop')]:
                    event = {'id': 'fixture', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'fixture',
                             'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode()); self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n')
            else:
                self.wfile.write(json.dumps({'id': 'fixture', 'object': 'chat.completion', 'created': 1, 'model': 'fixture',
                    'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'OK'}, 'finish_reason': 'stop'}]}).encode())
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Model)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state = owner.managed_directory(); agent = owner.ManagedAgent(root, state)
    report = {'passed': False, 'scope': 'Native bundled DSH and supervisor; deterministic model, isolated state, no installed-user data.'}
    def wait_for(check, seconds=60):
        until = time.monotonic()+seconds
        while time.monotonic() < until:
            try:
                result = check()
                if result: return result
            except (OSError, RuntimeError, ValueError): pass
            time.sleep(.2)
        raise AssertionError('The isolated Windows setup proof timed out.')
    # Retain the exact process handle for the owned crash/restart test.
    def start_supervisor():
        return subprocess.Popen([str(root/'python/python.exe'), '-I', '-Xutf8', '-B',
            str(root/'services/windows_supervisor.py')], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    supervisor = start_supervisor()
    try:
        wait_for(lambda: owner.request('status', root=root))
        from platform_adapters.processes import OwnedProcess
        version = OwnedProcess([str(root/'node/node.exe'), os.environ['AUGMENTOR_DSH_CLI'], '--version'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = version.process.communicate(timeout=20)
            assert version.wait(timeout=5) == 0, stderr.decode('utf-8', errors='replace')
            assert stdout.decode('utf-8').strip() == '0.1.5-rc.1', repr(stdout)
            report['ownedCliVersion'] = '0.1.5-rc.1'
        finally:
            version.terminate(); version.wait(timeout=5)
        result = managed.provision(root, state, {'url': f'http://127.0.0.1:{server.server_port}/v1',
            'model': 'fixture', 'apiKey': 'fixture-only-key', 'context': 32768},
            agent=agent, manager_type='windows-supervisor')
        assert result['saved'] and agent.loaded()
        report['startupCheck'] = managed.private_json(state/'startup-check.json')
        from augmentor_linux.adapters.dsh import DshAdapter
        adapter = DshAdapter(); adapter.call('host.describe'); assert adapter.product
        session = 'windows-setup-'+uuid.uuid4().hex
        adapter.call('session.create', {'sessionId': session, 'agentPreset': 'augmentor-linux-product', 'cwd': str(work/'workspace')})
        adapter.call('session.selectModel', {'sessionId': session, 'provider': 'augmentor-model', 'model': 'fixture'})
        before = len(calls)
        adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
            'content': [{'type': 'text', 'text': 'Reply to the isolated Windows setup fixture.'}]})
        wait_for(lambda: len(calls)>before and not next(row for row in adapter.call('session.list')['items'] if row['sessionId']==session)['running'])
        assert 'Windows managed setup verified.' in json.dumps(adapter.call('session.history', {'sessionId': session}))
        report['nativeDesktop'] = desktop_chat(root, work, args.out)
        spec = importlib.util.spec_from_file_location('windows_browser_proof', Path(__file__).with_name('windows-browser-host-proof.py'))
        browser_proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(browser_proof)
        report['nativeBrowserHost'] = browser_proof.prove(root, work, session)
        # This is the actual DSH writer, not two copies of our adapter. While
        # its model request is active, repair must fail to acquire its lease.
        from dsh.session_lease import session_write_lease
        directories = {path.parent for path in (state/'home/sessions').glob('*/'+session+'/session*.jsonl*')}
        assert len(directories) == 1, 'The actual session artifact directory is ambiguous.'
        lock_path = directories.pop()/'session.lock'
        adapter.call('session.prompt', {'sessionId': session, 'mode': 'queue',
            'content': [{'type': 'text', 'text': 'LEASE_HOLD_FIXTURE'}]})
        assert model_waiting.wait(20), 'The deterministic model did not receive the cancellable turn.'
        spec = importlib.util.spec_from_file_location('dsh_maintenance_proof', Path(__file__).with_name('dsh_maintenance_proof.py'))
        maintenance_proof = importlib.util.module_from_spec(spec); spec.loader.exec_module(maintenance_proof)
        maintenance_proof.refuse_busy(setup.current()['endpoint'], state/'home')
        from lifecycle.windows_preparation import WindowsPreparation
        from platform_adapters.windows_http import HttpRefused
        refused=False
        try:
            with WindowsPreparation(root,work/'run',work/'run/shared',state):pass
        except HttpRefused as error:
            assert error.code==409
            refused=True
        assert refused, 'The component graph accepted an active DSH model request.'
        assert next(row for row in adapter.call('session.list')['items'] if row['sessionId']==session)['running']
        assert owner.request('maintenance',root=root,method='host.maintenance.status',params={})['maintenance']['phase']=='ready'
        report['graphBusyRefusalPreservedModelTurn']=True
        contended = False
        try:
            with session_write_lease(lock_path): pass
        except BlockingIOError: contended = True
        assert contended, 'Recovery lease failed to exclude the actual DSH history writer.'
        adapter.call('session.cancel', {'sessionId': session})
        wait_for(lambda: not next(row for row in adapter.call('session.list')['items'] if row['sessionId']==session)['running'])
        release_model.set()
        report.update(actualHarnessLeaseContention=True, stopCancelledTurn=True)
        with_error = False
        try: agent.stop_failed_setup()
        except ValueError: with_error = True
        assert with_error and agent.loaded(), 'Published runtime must refuse failed-setup cleanup'
        supervisor.kill(); supervisor.wait(timeout=10)
        wait_for(lambda: not agent.loaded())
        def released_history():
            with session_write_lease(lock_path): return True
        wait_for(released_history)
        # Retain the replacement owner's exact handle too. Failure cleanup may
        # terminate this disposable process, never a discovered PID or name.
        supervisor = start_supervisor()
        wait_for(lambda: owner.request('status', root=root))
        exit_marker = work/'natural-dsh-exit.json'
        fixture_patch = state/'home/profiles/web/cordis.patch.yml'
        with fixture_patch.open('a', encoding='utf-8') as stream:
            stream.write(yaml.safe_dump([{'insert':[{'id':'shutdown-observer-proof',
                'name':str(Path(__file__).resolve().parents[1]/'tests/fixtures/dsh-shutdown-observer.mjs'),
                'config':{'path':str(exit_marker)}}]}]))
        agent.start(); wait_for(lambda: adapter.call('host.describe'))
        assert 'Windows managed setup verified.' in json.dumps(adapter.call('session.history', {'sessionId': session}))
        def natural_exit():
            def exited():
                status = owner.request('status', root=root)
                return status if not status['dsh']['running'] else None
            return wait_for(exited)['dsh']['exitCode']
        from lifecycle.windows_components import discover_owner
        from lifecycle.windows_dsh import discover_dsh
        from platform_adapters.windows_http import HttpRefused
        participant=discover_owner(root,Path(os.environ['XDG_RUNTIME_DIR']))
        assert participant is not None, 'The actual background owner was not discovered.'
        token=uuid.uuid4().hex;dsh=None;reserved=False
        try:
            assert participant.control('prepare',token)['phase']=='prepared'
            reserved=True
            dsh=discover_dsh(root,state,participant)
            assert dsh is not None
            def observed_control(action):return dsh.control(action,None if action=='status' else token)
            report['maintenance'] = maintenance_proof.prove(adapter, setup.current()['endpoint'],
                state/'home', session, natural_exit, exit_marker,
                control=observed_control,busy_errors=(HttpRefused,))
            assert dsh.exited(), 'The observed HTTP owner did not exit with the complete DSH Job.'
            report['maintenance']['kernelBoundHttpPeer']=True
        finally:
            if dsh is not None:dsh.close()
            try:
                if reserved:participant.control('cancel',token)
            finally:participant.close()
        agent.start(); wait_for(lambda: adapter.call('host.describe'))
        assert 'Windows managed setup verified.' in json.dumps(adapter.call('session.history', {'sessionId': session}))
        report.update(passed=True, setup=True, conversation=True, crashRestartPreservedHistory=True,
                      selectedRuntimeProtected=True, providerRequests=len(calls))
    except BaseException:
        report['fixtureDiagnostics'] = {}
        for path in (state/'setup-dsh.log', state/'runtime.log', state/'startup-check.json', owner.owner_directory()/'supervisor.log',
                     *list((work/'state/logs').glob('desktop.*.log'))):
            if path.is_file():
                excerpt = path.read_text(encoding='utf-8', errors='replace')[-12000:]
                excerpt = re.sub(r'token=[A-Za-z0-9_-]+', 'token=[redacted]', excerpt)
                report['fixtureDiagnostics'][path.name] = excerpt.replace('fixture-only-key', '[redacted]')
        raise
    finally:
        release_model.set()
        try:
            # This is a disposable synthetic connection, never the user's config.
            setup.configuration().unlink(missing_ok=True)
            if agent.owned(): agent.stop_failed_setup()
            try: owner.request('exit-if-empty', root=root)
            except FileNotFoundError: pass
            except ValueError as error:
                # Companions can still be alive in this bounded fixture. Their
                # global Quit is not being claimed; teardown uses our handle.
                report['fixtureOwnerCleanup'] = str(error)
        except Exception as error:
            report['fixtureCleanupError'] = type(error).__name__+': '+str(error)
        finally:
            if supervisor.poll() is None: supervisor.kill()
            supervisor.wait(timeout=10)
            server.shutdown(); server.server_close()
            report['privateFixtureDirectory'] = str(work)
            (args.out/'managed-setup.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(json.dumps(report), flush=True)


if __name__ == '__main__': main()
