# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Session-owned PipeWire echo cancellation, without changing desktop defaults.

Both Resonant playback and capture must use this route. Creating the module is
not an acoustic qualification: speaker placement and volume still affect AEC.
"""
import atexit
from contextlib import contextmanager
import json
import os
import re
import subprocess
import threading
import time
import uuid


_OPEN_LOCK = threading.Lock()


class EchoRouteError(RuntimeError):
    pass


def _pactl(*args):
    try:
        result = subprocess.run(['pactl', *args], capture_output=True, text=True,
                                timeout=5, check=True,
                                env={**os.environ, 'LC_ALL': 'C.UTF-8'})
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise EchoRouteError('Hands-free echo cancellation is unavailable. '
                             'Check the microphone and PipeWire, or use hold-to-talk.') from error


def _listing(kind):
    try:
        value = json.loads(_pactl('-f', 'json', 'list', kind))
        if not isinstance(value, list):
            raise ValueError('Expected a list')
        return value
    except (ValueError, TypeError) as error:
        raise EchoRouteError('Could not verify the hands-free audio route.') from error


@contextmanager
def _pulse_device(key, value):
    # ALSA's pulse plugin reads these when a new stream opens. The temporary
    # environment is local to Augmentor; desktop audio defaults are untouched.
    with _OPEN_LOCK:
        previous = os.environ.get(key)
        os.environ[key] = value
        try:
            yield
        finally:
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


class EchoRoute:
    def __init__(self, module_id, source, sink):
        self.module_id = module_id
        self.source = source
        self.sink = sink
        self.closed = False
        self._close_lock = threading.Lock()
        atexit.register(self.close)

    @classmethod
    def create(cls):
        source = _pactl('get-default-source')
        sink = _pactl('get-default-sink')
        # Never feed playback monitoring (or one of our own AEC nodes) back
        # into a new cancellation module. Do not guess a replacement device.
        valid = re.compile(r'^[A-Za-z0-9_.:-]+$')
        if (not valid.fullmatch(source) or not valid.fullmatch(sink)
                or source.endswith('.monitor') or source.startswith('resonant_aec_')
                or sink.startswith('resonant_aec_')):
            raise EchoRouteError('Select a physical microphone and speaker output '
                                 'in desktop sound settings before using hands-free.')
        name = f'resonant_aec_{os.getpid()}_{uuid.uuid4().hex[:8]}'
        source_name, sink_name = name + '_mic', name + '_speaker'
        module_id = _pactl(
            'load-module', 'module-echo-cancel', 'aec_method=webrtc',
            f'source_master={source}', f'sink_master={sink}',
            f'source_name={source_name}', f'sink_name={sink_name}',
            'rate=48000', 'channels=1', 'channel_map=mono',
            'source_properties=device.description=Resonant-Microphone priority.session=0',
            'sink_properties=device.description=Resonant-Speaker priority.session=0')
        if not module_id.isdecimal():
            raise EchoRouteError('PipeWire did not return a valid echo cancellation module.')
        route = cls(module_id, source_name, sink_name)
        try:
            deadline = time.monotonic() + 2
            while True:
                if (route._device_index('sources', source_name) is not None
                        and route._device_index('sinks', sink_name) is not None):
                    return route
                if time.monotonic() >= deadline:
                    raise EchoRouteError('The hands-free audio devices did not become available.')
                time.sleep(.05)
        except Exception:
            route.close()
            raise

    @staticmethod
    def _device_index(kind, name):
        return next((item['index'] for item in _listing(kind)
                     if item.get('name') == name), None)

    @staticmethod
    def _process_streams(kind):
        return [item for item in _listing(kind)
                if item.get('properties', {}).get('application.process.id') == str(os.getpid())]

    def _open(self, sd, direction, kwargs):
        if self.closed:
            raise EchoRouteError('The hands-free audio route is closed.')
        is_input = direction == 'input'
        name = self.source if is_input else self.sink
        kind = 'source-outputs' if is_input else 'sink-inputs'
        device_kind = 'sources' if is_input else 'sinks'
        relation = 'source' if is_input else 'sink'
        index = self._device_index(device_kind, name)
        if index is None:
            raise EchoRouteError('The hands-free audio route disappeared. Reopen voice.')
        previous = {item['index'] for item in self._process_streams(kind)}
        stream = None
        try:
            with _pulse_device('PULSE_SOURCE' if is_input else 'PULSE_SINK', name):
                constructor = sd.RawInputStream if is_input else sd.RawOutputStream
                stream = constructor(**{**kwargs, 'device': 'pulse'})
            # Pulse stream restoration must not silently reroute the stream to
            # the raw microphone or a different speaker. Fail closed if it does.
            opened = [item for item in self._process_streams(kind) if item['index'] not in previous]
            if not opened or any(item.get(relation) != index for item in opened):
                raise EchoRouteError('Could not confirm echo-cancelled audio routing. '
                                     'Use hold-to-talk or reopen voice.')
            return stream
        except Exception:
            if stream is not None:
                stream.close()
            raise

    def open_input(self, sd, **kwargs):
        return self._open(sd, 'input', kwargs)

    def open_output(self, sd, **kwargs):
        return self._open(sd, 'output', kwargs)

    def close(self):
        """Call after closing streams; never unload another session's module."""
        with self._close_lock:
            if self.closed:
                return
            self.closed = True
            atexit.unregister(self.close)
            try:
                _pactl('unload-module', self.module_id)
            except EchoRouteError:
                # Server exit or module removal already detached this route.
                pass
