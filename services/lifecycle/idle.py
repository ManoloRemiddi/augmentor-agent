# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bound detached companions without tying a shared service to its first parent."""
import os
from pathlib import Path
import threading
import time


class Lifetime:
    def __init__(self, lock, endpoint=None, *, timeout=300, clock=time.monotonic):
        self.lock = threading.RLock()
        self.clock, self.timeout = clock, timeout
        self.last_used = clock()
        self.active = 0
        self.closing = False
        self.files = [(Path(lock.name), self.identity(os.fstat(lock.fileno())))]
        if endpoint is not None and os.name != 'nt':
            path = Path(endpoint)
            self.files.append((path, self.identity(path.stat())))

    @staticmethod
    def identity(info):
        return info.st_dev, info.st_ino

    def reachable(self):
        for path, identity in self.files:
            try:
                if self.identity(path.stat()) != identity:
                    return False
            except FileNotFoundError:
                return False
        return True

    def enter(self):
        with self.lock:
            if self.closing:
                return False
            self.active += 1
            self.last_used = self.clock()
            return True

    def leave(self):
        with self.lock:
            self.active -= 1
            self.last_used = self.clock()

    def retire(self, ready=lambda: True):
        """Claim shutdown before another transport request can be admitted."""
        with self.lock:
            if self.closing or self.active:
                return False
            if self.reachable() and self.clock() - self.last_used < self.timeout:
                return False
            if not ready():
                return False
            self.closing = True
            return True

    def cleanup(self, endpoint):
        # A deleted/replaced state tree can have a new service already listening.
        # Never unlink its endpoint from the retiring process's finally block.
        path = Path(endpoint)
        expected = next((identity for owned, identity in self.files if owned == path), None)
        if expected is None:
            return
        try:
            if self.identity(path.stat()) == expected:
                path.unlink()
        except FileNotFoundError:
            pass


class IdleServerMixin:
    """Count accepted transports before launching handler threads on every OS."""
    def process_request(self, request, address):
        if not self.lifetime.enter():
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.lifetime.leave()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.lifetime.leave()

    def watch_idle(self, lock, endpoint, stop, ready=lambda: True):
        self.lifetime = Lifetime(lock, endpoint)
        self.idle_stopped = threading.Event()
        def watch():
            while not self.idle_stopped.wait(1):
                if self.lifetime.retire(ready):
                    stop()
                    return
        threading.Thread(target=watch, daemon=True).start()
