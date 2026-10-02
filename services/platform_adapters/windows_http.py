# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Bind loopback HTTP to its Windows kernel peer before sending credentials.

No proxy discovery, DNS, redirects, request retries or process termination. The
caller additionally verifies ownership in its reserved supervisor's process Job.
"""
import ctypes
import http.client
import json
import math
import os
from pathlib import Path
import socket
import struct
import sys
import time

LIMIT=65536


class HttpRefused(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__('The owned service refused maintenance. Its work was preserved; no request was replayed.')


def connection_pid(connection):
    """Find the server side of this exact established IPv4 loopback connection."""
    if sys.platform!='win32':raise RuntimeError('Kernel TCP observations require Windows.')
    if connection.family!=socket.AF_INET:raise ValueError('An explicit IPv4 loopback connection is required.')
    client,server=connection.getsockname(),connection.getpeername()
    if client[0]!='127.0.0.1' or server[0]!='127.0.0.1':raise ValueError('Maintenance cannot contact a remote service.')
    query=ctypes.WinDLL('iphlpapi',use_last_error=True).GetExtendedTcpTable
    query.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32),ctypes.c_int,
        ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
    query.restype=ctypes.c_uint32
    size=ctypes.c_uint32(4096)
    deadline=time.monotonic()+1
    while True:
        if size.value<4 or size.value>32*1024*1024:raise ValueError('Invalid Windows TCP table size.')
        buffer=ctypes.create_string_buffer(size.value)
        result=query(buffer,ctypes.byref(size),False,socket.AF_INET,4,0)  # TCP_TABLE_OWNER_PID_CONNECTIONS
        if result==122:  # Table grew; no application request has been sent.
            if time.monotonic()>=deadline:raise TimeoutError('The kernel connection table did not settle.')
            continue
        if result:raise ctypes.WinError(result)
        count=struct.unpack_from('<I',buffer)[0]
        if 4+count*24>len(buffer):raise ValueError('Truncated Windows TCP ownership table.')
        owners=set()
        for index in range(count):
            state,local_addr,local_port,remote_addr,remote_port,pid=struct.unpack_from('<6I',buffer,4+index*24)
            address=lambda value:socket.inet_ntoa(struct.pack('<I',value))
            if (state==5 and (address(local_addr),socket.ntohs(local_port&0xffff))==server and
                    (address(remote_addr),socket.ntohs(remote_port&0xffff))==client):owners.add(pid)
        if len(owners)==1 and next(iter(owners))>0:return next(iter(owners))
        if owners or time.monotonic()>=deadline:
            raise ValueError('The connected loopback service has no unique kernel owner.')
        time.sleep(.01)  # Read-only connection observation, never an HTTP retry.


class ObservedHttp:
    def __init__(self, port, executable, *, verify_process, timeout=5):
        if sys.platform!='win32':raise RuntimeError('Observed HTTP requires Windows.')
        if type(port) is not int or not 1024<=port<=65535:raise ValueError('Invalid owned service port.')
        if not math.isfinite(timeout) or not 0<timeout<=30:raise ValueError('Use a bounded HTTP timeout.')
        self.port,self.executable,self.verify_process,self.timeout=port,Path(executable),verify_process,timeout
        self.process=None;self.pid=None;self.closed=False

    def observe(self, connection):
        import win32api,win32con,win32event,win32process,win32security
        from .windows_identity import current_sid
        pid=connection_pid(connection)
        if self.process is None:
            process=win32api.OpenProcess(win32con.SYNCHRONIZE|win32con.PROCESS_QUERY_INFORMATION|
                win32con.PROCESS_VM_READ,False,pid)
            try:
                token=win32security.OpenProcessToken(process,win32con.TOKEN_QUERY)
                try:
                    if win32security.GetTokenInformation(token,win32security.TokenUser)[0]!=current_sid():
                        raise PermissionError('The loopback service belongs to another Windows user.')
                finally:token.Close()
                actual=Path(win32process.GetModuleFileNameEx(process,0)).resolve()
                if os.path.normcase(str(actual))!=os.path.normcase(str(self.executable.resolve())):
                    raise ValueError('The loopback service executable differs. No request was sent.')
                self.verify_process(pid)
                self.process,self.pid=process,pid
                process=None
            finally:
                if process is not None:process.Close()
        else:
            if pid!=self.pid or win32event.WaitForSingleObject(self.process,0)!=win32event.WAIT_TIMEOUT:
                raise ValueError('The observed loopback service exited or changed. No request was sent to a replacement.')
            self.verify_process(pid)

    def request(self, path, payload=None, headers=None):
        if self.closed:raise ValueError('The loopback process observation is closed.')
        if not isinstance(path,str) or not path.startswith('/') or '\r' in path or '\n' in path:
            raise ValueError('Use an explicit local service path.')
        body=None if payload is None else json.dumps(payload,separators=(',',':')).encode('utf-8')
        if body is not None and len(body)>16384:raise ValueError('The maintenance request is too large.')
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=self.timeout)
        try:
            connection.connect()
            # http.client must never silently reopen a socket after verification.
            connection.auto_open=False
            self.observe(connection.sock)
            connection.request('GET' if body is None else 'POST',path,body,
                {'Content-Type':'application/json',**(headers or {})})
            response=connection.getresponse();raw=response.read(LIMIT+1)
            if len(raw)>LIMIT:raise ValueError('The owned service response is too large.')
            try:value=json.loads(raw)
            except (UnicodeError,ValueError):raise ValueError('The owned service response is invalid. No request was replayed.') from None
            if not isinstance(value,dict):raise ValueError('The owned service returned an invalid envelope.')
            if response.status!=200:
                raise HttpRefused(response.status)
            return value
        finally:connection.close()

    def exited(self, timeout=0):
        import win32event
        if not math.isfinite(timeout) or not 0<=timeout<=60:raise ValueError('Use a bounded process observation timeout.')
        if self.process is None:raise ValueError('The process observation is closed.')
        return win32event.WaitForSingleObject(self.process,math.ceil(timeout*1000))==win32event.WAIT_OBJECT_0

    def close(self):
        self.closed=True
        if self.process is not None:self.process.Close();self.process=None
