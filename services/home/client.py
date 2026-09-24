# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Shared local pairing configuration. Never returns the NAS bearer to a UI."""
import json
import fcntl
import os
from pathlib import Path
import tempfile
import urllib.request
from urllib.parse import urlsplit


def config_path():
    return Path(os.environ.get('AUGMENTOR_HOME_CONNECTION',Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'augmentor/home.json'))


def endpoint(value):
    if not isinstance(value,str):raise ValueError('Enter a Home URL')
    u=urlsplit(value)
    if u.username or u.password or u.query or u.fragment or u.path not in ('','/') or not u.hostname or (u.scheme!='https' and not (u.scheme=='http' and u.hostname in ('localhost','127.0.0.1','::1'))):
        raise ValueError('Use the Home HTTPS URL, or loopback through a private tunnel.')
    return value.rstrip('/')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Home redirects are disabled')


def call(method,params):
    path=config_path()
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    # Serialize pairing/revocation across native and Browser callers. Keep the
    # lock file stable; unlinking it would allow concurrent independent locks.
    fd=os.open(str(path)+'.lock',os.O_CREAT|os.O_RDWR,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _call_locked(method,params,path)


def _call_locked(method,params,path):
    saved=json.loads(path.read_text()) if path.exists() else None
    if method=='home.connection.state':
        return {'connected':bool(saved),'url':saved['url'] if saved else '', 'name':saved.get('name','Home') if saved else ''}
    if method=='home.connection.disconnect':
        if saved:
            # Revoke remotely first. A failed revocation must not be reported as success.
            request=urllib.request.Request(endpoint(saved['url'])+'/logout',data=b'{}',headers={'Authorization':'Bearer '+saved['token'],'Content-Type':'application/json'})
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=10) as response:response.read(8192)
        path.unlink(missing_ok=True)
        return {'connected':False}
    if method!='home.connection.pair':raise ValueError('Unknown Home configuration operation')
    url=endpoint(params.get('url'))
    if not isinstance(params.get('code'),str) or len(params['code'])>200:raise ValueError('Enter a one-time pairing code')
    name=params.get('name','Augmentor')
    if not isinstance(name,str) or not name.strip() or len(name)>80:raise ValueError('Enter a device name up to 80 characters')
    if saved:raise ValueError('Disconnect the existing Home connection before replacing it')
    data=json.dumps({'code':params['code'],'name':name,'kind':'api'}).encode()
    request=urllib.request.Request(url+'/pair',data=data,headers={'Content-Type':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=10) as response:result=json.loads(response.read(16384))
    if not isinstance(result.get('token'),str) or len(result['token'])<24:raise ValueError('Invalid Home pairing response')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as file:
            temporary=Path(file.name)
            json.dump({'url':url,'token':result['token'],'name':name},file)
            file.flush();os.fsync(file.fileno())
        temporary.chmod(0o600);temporary.replace(path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)
    return {'connected':True,'url':url,'name':name}
