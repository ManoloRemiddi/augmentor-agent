# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Observe a Unix socket's actual peer without adopting a saved PID.

Linux obtains a pidfd directly from the connected socket. macOS binds a process
event to its kernel audit token and confirms that token after registration.
This grants observation only; it cannot stop work or authorize installation.
"""
import ctypes
import math
import os
from pathlib import Path
import select
import socket
import struct
import sys

from platform_support import require_same_user
from .transport import LocalSocket


def _credentials(connection):
    require_same_user(connection)
    if sys.platform=='linux':
        pid,uid,_gid=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid!=os.getuid() or pid<=0:raise PermissionError('The socket has no live same-user process identity.')
        return pid,None
    if sys.platform=='darwin':
        # Apple's public sys/un.h: SOL_LOCAL=0, LOCAL_PEERPID=2,
        # LOCAL_PEERTOKEN=6. Opaque audit bytes distinguish PID generations.
        pid=struct.unpack('i',connection.getsockopt(0,2,4))[0]
        token=connection.getsockopt(0,6,32)
        if pid<=0 or len(token)!=32:raise PermissionError('The socket has no kernel process audit identity.')
        return pid,token
    raise RuntimeError('Unix process observation requires Linux or macOS.')


def _executable(pid):
    if sys.platform=='linux':return Path(os.readlink('/proc/'+str(pid)+'/exe'))
    library=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
    query=library.proc_pidpath
    query.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32];query.restype=ctypes.c_int
    buffer=ctypes.create_string_buffer(4096)
    if query(pid,buffer,len(buffer))<=0:
        error=ctypes.get_errno();raise OSError(error,'The socket peer executable could not be observed.')
    return Path(os.fsdecode(buffer.value))


class PeerProcess:
    def __init__(self, connection, executable):
        self.fd=None;self.queue=None;self.closed=False;self.finished=False
        expected=Path(executable)
        if not expected.is_absolute():raise ValueError('Use an independently identified absolute executable.')
        try:
            self.pid,self.token=_credentials(connection)
            if sys.platform=='linux':
                # Linux's public socket ABI supplies the peer's actual pidfd;
                # opening a reported/recycled PID would not provide this binding.
                self.fd=struct.unpack('i',connection.getsockopt(socket.SOL_SOCKET,getattr(socket,'SO_PEERPIDFD',77),4))[0]
                if self.fd<0:raise ValueError('The socket did not supply a process observation.')
                os.set_inheritable(self.fd,False)
            else:
                self.queue=select.kqueue()
                event=select.kevent(self.pid,filter=select.KQ_FILTER_PROC,
                    flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE|select.KQ_EV_ONESHOT,fflags=select.KQ_NOTE_EXIT)
                self.queue.control([event],0,0)
                # A second kernel handshake closes the PID-reuse race between
                # the original audit token and registering the process event.
                with LocalSocket() as confirmation:
                    confirmation.settimeout(5);confirmation.connect(connection.getpeername())
                    if _credentials(confirmation)!=(self.pid,self.token):
                        raise ValueError('The socket owner changed during process observation.')
            if self.exited() or _executable(self.pid).resolve()!=expected.resolve() or self.exited():
                raise ValueError('The socket belongs to another executable or an exited process.')
        except BaseException:self.close();raise

    def verify(self, connection):
        if self.closed or self.exited() or _credentials(connection)!=(self.pid,self.token):
            raise ValueError('The observed socket process exited or changed. No request was replayed.')

    def exited(self, timeout=0):
        if self.closed:raise ValueError('The process observation is closed.')
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<=timeout<=60:
            raise ValueError('Use a bounded process observation timeout.')
        if self.finished:return True
        if self.fd is not None:
            poll=select.poll();poll.register(self.fd,select.POLLIN|select.POLLHUP|select.POLLERR)
            self.finished=bool(poll.poll(math.ceil(timeout*1000)))
        elif self.queue is not None:self.finished=bool(self.queue.control(None,1,timeout))
        else:raise ValueError('The process observation is unavailable.')
        return self.finished

    def close(self):
        self.closed=True
        if self.fd is not None:os.close(self.fd);self.fd=None
        if self.queue is not None:self.queue.close();self.queue=None

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
