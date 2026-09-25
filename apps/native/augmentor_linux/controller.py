# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
from .instances import scoped_path, load_session
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import uuid
import json
import os
import re
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from .pi_client import PiClient, EventStream, ContractError


class Controller(QObject):
    queue_changed = Signal(list)
    queue_result = Signal(dict)
    queue_action_result = Signal(dict)
    status = Signal(str)
    models = Signal(dict)
    selection_changed = Signal(dict)
    session_info = Signal(dict)
    sessions = Signal(list)
    page = Signal(list, bool, bool)
    busy = Signal(bool)
    event = Signal(dict)
    problem = Signal(str)
    interaction = Signal(dict)
    sent = Signal(str)
    submission_failed = Signal(str)
    history = Signal(list)
    recovered = Signal(list, bool)
    connection = Signal(bool)
    repair_progress = Signal(str)
    repair_finished = Signal(bool, str)

    def __init__(self, parent=None, client=None, harness="pi"):
        super().__init__(parent)
        if harness not in ('pi','dsh'):
            raise ValueError('Choose DSH or Pi. OpenCode support has been retired; its saved data is retained.')
        if client is None and harness=='dsh':
            from .adapters.dsh import DshAdapter
            self.client=DshAdapter()
        else:self.client=client or PiClient()
        self.harness=getattr(self.client,'harness',harness)
        self.preset=getattr(self.client,'preset','augmentor-linux-pi')
        self.capabilities=getattr(self.client,'capabilities',{'branch':True,'edit':True})
        self.session = None
        self.stream = None
        self.running = False
        self.lock = threading.Lock()
        self.cancel_requested = threading.Event()
        self.closed = False
        self.connected = False
        self.online = False
        self.repairing = False
        self.last_connection_error = ""
        self.unavailable_session = None
        self.session_restore_error = ""
        self.monitor_started = False
        self.shutdown = threading.Event()
        self.recovery_lock = threading.Lock()
        self.events_lock = threading.RLock()
        self.recover_buffer = None
        self.stream_generation = None
        self.queue_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='augmentor-submit')
        self.preparing = False
        self.generation = None
        self.selection = None
        self.read_only = False
        self.saved_ids = set()
        self.loaded_events = []
        self.has_more = False
        self.loading_page = False
        self.navigating = False
        self.state_file = None if client is not None else Path(os.environ.get('AUGMENTOR_PI_STATE', Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'augmentor-pi')) / 'session.json'
        if client is None and hasattr(self.client,'state_path'):self.state_file=self.client.state_path()
        if self.state_file:
            self.state_file = scoped_path(self.state_file)
            try:
                state = load_session(self.state_file)
                if state.get('endpoint') == self.client.base and (state.get('session') is None or isinstance(state.get('session'),str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', state['session'])):
                    self.session = state['session']
                    self.selection = state.get('selection')
            except (OSError, ValueError, TypeError):
                pass

    def save_session(self):
        if not self.state_file:
            return
        self.state_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=self.state_file.parent, delete=False) as file:
            json.dump({'endpoint': self.client.base, 'session': self.session, 'selection':self.selection}, file)
            temporary = file.name
        os.replace(temporary, self.state_file)

    def new_chat(self):
        if self.running or self.navigating or self.repairing or self.recovery_lock.locked():
            return False
        self.stream_generation=None
        if self.stream:
            self.stream.close()
        self.stream, self.session, self.connected = None, None, False
        self.unavailable_session = None
        self.session_restore_error = ''
        self.read_only = False
        self.loaded_events = []
        self.save_session()
        self.session_info.emit({'sessionId':None,'title':'Augmentor Agent','saved':False,'readOnly':False})
        return True

    def refresh_models(self):
        def work():
            self.models.emit(self.client.refresh_catalog() if hasattr(self.client,'refresh_catalog') else self.client.model_catalog())
            if self.selection:self.selection_changed.emit(self.selection)
        self.task(work)

    def choose_model(self, selection):
        if self.running or self.read_only:return
        self.selection = selection
        self.save_session()

    def list_sessions(self):
        self.task(lambda:self.sessions.emit(self.client.session_rows()))

    def load_page(self, older=False):
        sid = self.session
        if not sid:return
        payload={'sessionId':sid,'maxMessages':12}
        if older and self.loaded_events:payload['beforeSeq']=min(e['seq'] for e in self.loaded_events)
        result=self.client.call('session.history',payload)
        if self.session != sid:return
        events=[row['event'] for row in result.get('events',[])]
        with self.events_lock:
            self.loaded_events=self.merge_events(events,self.loaded_events) if older else events
            self.has_more=result.get('hasMore',False)
            self.page.emit(list(self.loaded_events), self.has_more, older)

    def load_older(self):
        if not self.has_more or self.loading_page:return
        self.loading_page=True
        def work():
            try:self.load_page(True)
            finally:self.loading_page=False
        self.task(work)

    def open_session(self, row):
        if self.running:return
        def work():
            if self.stream:self.stream.close()
            self.stream=None;self.connected=False
            self.session=row['sessionId']
            self.read_only=not getattr(self.client,'owns_preset',lambda preset:preset==self.preset)(row.get('agentPreset'))
            if row.get('saved'):self.saved_ids.add(self.session)
            else:self.saved_ids.discard(self.session)
            if not self.read_only:self.client.call('session.create',{'sessionId':self.session,'cwd':row['cwd'],'agentPreset':row['agentPreset']})
            self.session_info.emit(dict(row, readOnly=self.read_only))
            self.load_page()
            if not self.read_only:
                self.selection=self.client.call('session.models',{'sessionId':self.session}).get('current')
                if self.selection:self.selection_changed.emit(self.selection)
                self.save_session()
                sid=self.session
                self.subscribe(sid)
            live=getattr(self.stream,'running',None)
            self.running=(live if type(live) is bool else self.history_running(bool(row.get('running')))) and not self.read_only
            self.busy.emit(self.running)
        self.navigate(work)

    def attach_branch(self,row):
        self.stream_generation=None
        if self.stream:self.stream.close()
        self.stream=None;self.connected=False
        self.session=row['sessionId'];self.read_only=False
        self.loaded_events=[];self.has_more=False
        self.selection=row['selection'];self.save_session()
        self.session_info.emit(dict(row,readOnly=False))
        self.selection_changed.emit(self.selection)
        self.load_page();self.subscribe(self.session)

    def branch(self,seq):
        if not self.session or self.read_only or not self.online:return
        source=self.session;target='augmentor-linux-pi-'+uuid.uuid4().hex
        def work():
            row=self.client.call('session.branch',{'sessionId':source,'newSessionId':target,'messageSeq':seq,'mode':'reply'})
            self.attach_branch(row)
            self.status.emit('Branched into a new chat')
        self.navigate(work)

    def toggle_saved(self):
        sid=self.session
        if not sid or self.read_only:return
        action='unsave' if sid in self.saved_ids else 'save'
        def work():
            self.saved_ids=set(self.client.saved_chats(action,sid))
            if sid==self.session:self.session_info.emit({'sessionId':sid,'saved':sid in self.saved_ids})
        self.task(work)

    def rename(self, title):
        sid=self.session
        if not sid:return
        def work():
            result=self.client.call('session.rename',{'sessionId':sid,'title':title})
            if sid==self.session:self.session_info.emit({'sessionId':sid,'title':result['title']})
        self.task(work)

    def navigate(self, fn):
        if self.navigating or self.running or self.repairing or self.recovery_lock.locked():return
        self.navigating=True
        self.busy.emit(False)
        def work():
            try:fn()
            finally:
                self.navigating=False
                if not self.closed:self.busy.emit(self.running)
        self.task(work)

    def task(self, fn):
        def run():
            try:
                fn()
            except Exception as exc:
                if not self.closed:
                    self.problem.emit(str(exc))
        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def merge_events(*groups):
        # Session sequences are durable: history and the live stream overlap.
        rows={event['seq']:event for group in groups for event in group if 'seq' in event}
        return [rows[seq] for seq in sorted(rows)]

    def history_running(self, fallback=False):
        for event in reversed(self.loaded_events):
            if event.get('type') == 'turn/end':return False
            if event.get('type') == 'turn/start':return True
        return fallback

    def subscribe(self, sid):
        generation=object();self.stream_generation=generation
        if self.stream:self.stream.close()
        self.connected=False
        stream=getattr(self.client,'stream_type',EventStream)(self.client,sid,
            lambda f:self.frame(f) if self.stream_generation is generation else None,
            lambda error:self.disconnected(error) if self.stream_generation is generation else None)
        self.stream=stream;stream.start()
        if stream.failure:raise ContractError(stream.failure)
        self.connected=True

    def start_monitor(self):
        if self.monitor_started:return
        self.monitor_started=True
        self.task(self.monitor)

    def monitor(self):
        delay=1
        while not self.shutdown.is_set():
            if self.navigating or self.preparing or self.repairing:
                self.shutdown.wait(.25);continue
            try:
                if not self.connected:
                    self.recover_connection()
                else:self.client.call('host.describe')
                delay=1
                self.shutdown.wait(3)
            except Exception as exc:
                self.online=False;self.connected=False
                if self.closed:return
                self.connection.emit(False)
                self.last_connection_error = str(exc)
                self.status.emit('Reconnecting… '+str(exc)[:240]+' · Settings → Recover connection')
                self.shutdown.wait(delay)
                delay=min(15,delay*2)

    def repair_connection(self):
        with self.lock:
            if self.repairing or self.navigating or self.preparing or (self.running and self.online) or self.closed:
                return False
            self.repairing = True
        self.connection.emit(self.online)
        self.status.emit("Recovering connection…")
        def work():
            ok = False
            message = ''
            runtime_checked = False
            try:
                # Wait for an in-flight health check, then exclude automatic recovery.
                if not self.recovery_lock.acquire(timeout=25):
                    raise ContractError('A connection check is still finishing. Please retry recovery shortly.')
                try:
                    import sys
                    services = str(Path(__file__).resolve().parents[3]/'services')
                    if services not in sys.path: sys.path.insert(0, services)
                    from recovery import recover
                    recover(self.client, self.harness, self.repair_progress.emit)
                    runtime_checked = True
                    if self.harness == 'dsh':
                        from recovery import recover_saved_session
                        target = self.unavailable_session or self.session
                        recover_saved_session(self.client, target, self.repair_progress.emit)
                        if target:
                            self.session = target
                            self.unavailable_session = None
                            self.session_restore_error = ''
                finally:
                    self.recovery_lock.release()
                if self.closed: return
                self.recover_connection(manual=True)
                ok = self.online and not self.unavailable_session
                message = 'Connected. Your conversation is ready.' if ok else self.session_restore_error or 'The runtime did not finish reconnecting.'
            except Exception as exc:
                if not (runtime_checked and self.unavailable_session and self.online):
                    self.online = False
                    self.connected = False
                self.last_connection_error = str(exc)
                message = 'Recovery could not finish: '+str(exc)
                self.status.emit('Recovery needs attention · Settings → Recover connection')
            finally:
                self.repairing = False
                if not self.closed:
                    self.connection.emit(self.online)
                    self.repair_finished.emit(ok, message)
        self.task(work)
        return True

    def recover_connection(self, manual=False):
        try:
            self._recover_connection(manual)
        except Exception as exc:
            # A refused stored chat is not a dead server. Preserve its durable
            # pointer and history, but keep New Chat and recovery accessible.
            if not self.session or not any(text in str(exc) for text in (
                    'unknown to this harness', 'SessionPersistenceCorruptionError', ' is corrupt:',
                    'uses log format v', 'older than the supported v')):
                raise
            self.unavailable_session = self.session
            self.session_restore_error = str(exc)
            self.session = None
            self.loaded_events = []
            self.read_only = False
            self.running = False
            self._recover_connection(manual)
            self.problem.emit('Connected, but the previous chat could not be reopened. Its history is preserved. '
                              'Use Settings → Recover connection to repair it, or start a new chat. '+str(exc))

    def _recover_connection(self, manual=False):
        if not self.recovery_lock.acquire(blocking=False):return
        try:
            if self.repairing and not manual:return
            try:
                self.client.call('host.describe')
            except Exception as error:
                import urllib.error
                refused = isinstance(error, ConnectionRefusedError) or (
                    isinstance(error, urllib.error.URLError) and isinstance(error.reason, ConnectionRefusedError))
                if self.harness != 'dsh' or not refused: raise
                from recovery import start_dsh
                start_dsh(self.client, self.status.emit)
                self.client.call('host.describe')
            sid=self.session
            row=None
            if sid:
                row=next((r for r in self.client.session_rows() if r['sessionId']==sid),None)
                if row is None:
                    # A deleted session must not cause an endless reconnect loop.
                    self.session=None;self.loaded_events=[];self.save_session()
                    self.problem.emit('The previous chat is unavailable. Choose a conversation from History or start a new one.')
                    sid=None
                else:
                    self.read_only=not getattr(self.client,'owns_preset',lambda preset:preset==self.preset)(row.get('agentPreset'))
                    if not self.read_only:self.client.call('session.create',{'sessionId':sid,'cwd':row['cwd'],'agentPreset':row['agentPreset']})
            with self.events_lock:self.recover_buffer=[]
            self.subscribe(sid)
            if sid:
                previous=list(self.loaded_events)
                result=self.client.call('session.history',{'sessionId':sid,'maxMessages':12})
                fetched=[r['event'] for r in result.get('events',[])]
                # Page backwards through a long outage until the old window overlaps.
                oldest=min((e['seq'] for e in previous),default=None)
                more=result.get('hasMore',False)
                while oldest is not None and more and fetched and min(e['seq'] for e in fetched)>oldest:
                    page=self.client.call('session.history',{'sessionId':sid,'maxMessages':12,'beforeSeq':min(e['seq'] for e in fetched)})
                    earlier=[r['event'] for r in page.get('events',[])]
                    if not earlier:break
                    fetched=earlier+fetched;more=page.get('hasMore',False)
                if sid!=self.session or self.closed:return
                current=self.client.call('session.models',{'sessionId':sid}).get('current') if not self.read_only else None
                if self.selection is None:self.selection=current
                self.session_info.emit(dict(row,readOnly=self.read_only))
                self.running=self.history_running(bool(row.get('running'))) and not self.read_only
                with self.events_lock:
                    buffered=self.recover_buffer or []
                    self.loaded_events=self.merge_events(previous,fetched,[f['payload']['event'] for f in buffered if f.get('method')=='session/event'])
                    self.has_more=more
                    self.running=self.history_running(self.running) and not self.read_only
                    if previous:self.recovered.emit(list(self.loaded_events),more)
                    else:self.page.emit(list(self.loaded_events),more,False)
                    self.recover_buffer=None
                    for frame in buffered:self.frame(frame)
                # Stop requested during an outage is the only cancellation retried.
                if self.cancel_requested.is_set() and self.running and not self.read_only:
                    self.client.call('session.cancel',{'sessionId':sid})
            else:
                with self.events_lock:self.recover_buffer=None
            self.models.emit(self.client.model_catalog())
            if self.selection:self.selection_changed.emit(self.selection)
            try:self.saved_ids=set(self.client.saved_chats())
            except ContractError:pass
            self.session_info.emit({'sessionId':sid,'saved':sid in self.saved_ids,'readOnly':self.read_only})
            self.last_connection_error='';self.online=True;self.connection.emit(True);self.busy.emit(self.running)
            self.status.emit('Working…' if self.running else 'Ready')
        finally:
            with self.events_lock:self.recover_buffer=None
            self.recovery_lock.release()

    def prepare_voice(self, selection):
        with self.lock:
            if self.running or self.navigating or self.repairing or self.closed or self.read_only or not self.online:
                raise ContractError('Open an idle, connected DSH conversation first.')
            if not hasattr(self.client,'voice_ticket'):raise ContractError('Voice requires the DSH integration.')
            self.navigating=True
        try:
            self.client.validate_model(selection)
            if not self.session:
                session=self.preset+'-'+uuid.uuid4().hex
                cwd=self.client.workspace();cwd.mkdir(mode=0o700,exist_ok=True)
                self.client.call('session.create',{'sessionId':session,'cwd':str(cwd),'agentPreset':self.preset})
                self.session=session
                self.save_session()
                self.session_info.emit({'sessionId':session,'saved':False,'readOnly':False})
            self.client.call('session.selectModel',{'sessionId':self.session,**selection})
            self.selection=selection;self.save_session()
            if not self.connected or not self.stream or self.stream.session!=self.session:self.subscribe(self.session)
            return self.client.voice_ticket(self.session)
        finally:self.navigating=False

    def send(self, text, selection, edit_from=None, request_id=None):
        with self.lock:
            if self.running or self.navigating or self.repairing or self.recovery_lock.locked() or self.closed or self.read_only:
                return False
            self.running = True
            self.preparing = True
            generation = object()
            self.generation = generation
        cancelled = threading.Event()
        self.cancel_requested = cancelled
        self.busy.emit(True)
        def work():
            accepted = False
            try:
                self.client.validate_model(selection)
                if cancelled.is_set():
                    return
                if edit_from:
                    if edit_from['sessionId']!=self.session:raise ContractError('The conversation changed. Choose Edit again.')
                    row=self.client.call('session.branch',{'sessionId':self.session,'newSessionId':self.preset+'-'+uuid.uuid4().hex,'messageSeq':edit_from['seq'],'mode':'edit'})
                    self.attach_branch(row)
                    if cancelled.is_set():return
                if not self.session:
                    session = self.preset+'-' + uuid.uuid4().hex
                    cwd = self.client.workspace() if hasattr(self.client,'workspace') else Path(os.environ.get('AUGMENTOR_PI_WORKSPACE',Path.home() / 'Augmentor Linux Pi'))
                    cwd.mkdir(mode=0o700, exist_ok=True)
                    self.client.call('session.create', {'sessionId': session, 'cwd': str(cwd), 'agentPreset': self.preset, 'selection': selection})
                    self.session = session
                    self.save_session()
                    self.session_info.emit({'sessionId':session,'saved':False,'readOnly':False})
                self.client.call('session.selectModel', {'sessionId': self.session, 'provider': selection['provider'], 'model': selection['model']})
                self.selection=selection
                if edit_from:self.selection_changed.emit(selection)
                self.save_session()
                if not self.connected or not self.stream or self.stream.session!=self.session:self.subscribe(self.session)
                if cancelled.is_set():
                    return
                response = self.client.call('session.prompt', {'sessionId': self.session, 'mode': 'queue', 'requestId': request_id or str(uuid.uuid4()), 'content': [{'type': 'text', 'text': text}]})
                if response.get('accepted') is not True:
                    raise ContractError('The harness did not accept the message.')
                accepted = True
                self.sent.emit(text)
                if response.get('command'):
                    with self.events_lock:
                        if not self.history_running():self.set_idle(generation)
                if cancelled.is_set():
                    self.client.call('session.cancel', {'sessionId': self.session})
            except Exception:
                self.set_idle(generation)
                raise
            finally:
                if not accepted and not self.closed:
                    self.submission_failed.emit(text)
                if self.generation is generation:
                    self.preparing = False
                if cancelled.is_set():
                    self.set_idle(generation)
        self.task(work)
        return True

    def queue_prompt(self, text, request_id, mode='queue'):
        if not getattr(self.client,'supports_queue',False) or not self.running or self.navigating or self.read_only or not self.online:return False
        generation=self.generation;sid=self.session
        def work():
            try:
                # Preserve order behind the first prompt while a new chat is being prepared.
                while self.preparing and not self.closed:
                    if self.generation is not generation:raise ContractError('The conversation changed before the prompt could be queued.')
                    time.sleep(.03)
                target=sid or self.session
                if self.closed or self.generation is not generation or target!=self.session or not target or self.cancel_requested.is_set():raise ContractError('Prompt was not queued; the active response stopped or changed.')
                result=self.client.call('session.prompt',{'sessionId':target,'requestId':request_id,'mode':mode,'content':[{'type':'text','text':text}]})
                self.queue_result.emit({'id':request_id,'accepted':result.get('accepted') is True,'command':bool(result.get('command'))})
            except Exception as exc:
                self.queue_result.emit({'id':request_id,'accepted':False,'error':str(exc)})
        self.queue_executor.submit(work);return True

    def update_queue(self, item_id, action):
        sid=self.session
        if not sid or self.read_only or not self.online or action not in ('steer','remove'):return
        def work():
            try:
                result=self.client.call('session.updateQueue',{'sessionId':sid,'itemId':item_id,'action':{'kind':action}})
                self.queue_action_result.emit({'id':item_id,'accepted':result.get('accepted') is True})
            except Exception as exc:
                self.queue_action_result.emit({'id':item_id,'error':str(exc)})
                self.status.emit(str(exc))
        self.task(work)

    def set_idle(self, generation=None):
        with self.lock:
            if generation is not None and generation is not self.generation:
                return
            self.running = False
        if not self.closed:
            self.busy.emit(False)

    def reconcile_turn(self, sid, stream_generation):
        """Commit the saved reply even if its final live frame was incomplete."""
        def current():
            return not self.closed and self.session == sid and self.stream_generation is stream_generation
        if not current():return
        result = self.client.call('session.history', {'sessionId':sid, 'maxMessages':12})
        with self.events_lock:
            if not current():return
            # History replaces overlapping live frames; keep older pages and
            # any newer turn that arrived while this read was in flight.
            self.loaded_events = self.merge_events(self.loaded_events, [r['event'] for r in result.get('events', [])])
            self.recovered.emit(list(self.loaded_events), self.has_more)

    def frame(self, frame):
        if self.closed:return
        with self.events_lock:
            if self.recover_buffer is not None:
                self.recover_buffer.append(frame);return
            method, payload = frame.get('method'), frame.get('payload', {})
            if method in ('host/session-status','host/session-error'):
                if payload.get('sessionId')!=self.session:return
                if method=='host/session-error':
                    self.problem.emit(payload.get('message','The DSH task stopped. Check the conversation before retrying.'))
                    self.set_idle()
                elif type(payload.get('running')) is bool:
                    was_running=self.running
                    # A new subscription reports the idle baseline before prompt
                    # submission. Keep our locally reserved turn busy until then.
                    self.running=(payload['running'] or self.preparing) and not self.read_only
                    self.busy.emit(self.running)
                    if was_running and not self.running and self.online and self.session:
                        sid,generation=self.session,self.stream_generation
                        self.task(lambda:self.reconcile_turn(sid,generation))
            elif method == 'session/queue':
                if payload.get('sessionId')==self.session:self.queue_changed.emit(payload.get('items',[]))
            elif method == 'session/event':
                event = payload.get('event', {})
                self.loaded_events=self.merge_events(self.loaded_events,[event])
                self.event.emit(event)
                if event.get('type') == 'runtime/error':self.problem.emit(event.get('data',{}).get('message','Pi runtime error'))
                if event.get('type') == 'turn/end':
                    self.set_idle()
                    if self.online and self.session:
                        sid, generation = self.session, self.stream_generation
                        self.task(lambda:self.reconcile_turn(sid, generation))
                elif event.get('type')=='turn/start':self.running=True;self.busy.emit(True)
            elif method == 'notification':self.status.emit(payload.get('message',''))
            elif method in ('approval/requested', 'question/requested', 'interaction/resolved'):
                self.interaction.emit(frame)

    def disconnected(self, error):
        self.connected=False;self.online=False
        if not self.closed:
            self.connection.emit(False)
            self.status.emit('Reconnecting…')

    def stop(self):
        self.cancel_requested.set()
        if self.session and not self.read_only:
            def work():
                response = self.client.call('session.cancel', {'sessionId': self.session})
                self.status.emit('Cancellation requested')
                live=getattr(self.client,'running_state',lambda _session:None)(self.session)
                if not self.preparing and (live is False or response.get('accepted') is not True):
                    self.set_idle()
            self.task(work)
        else:
            if not self.preparing:
                self.set_idle()

    def answer(self, frame, value):
        self.task(lambda: self.client.respond(frame['rpcId'], value))

    def close(self):
        if self.running:self.stop()
        self.closed = True
        self.queue_executor.shutdown(wait=False,cancel_futures=True)
        self.shutdown.set()
        self.stream_generation=None
        if self.stream:
            self.stream.close()
