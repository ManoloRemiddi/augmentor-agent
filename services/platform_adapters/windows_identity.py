# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Windows token identity and private filesystem objects (pywin32, both CPUs)."""
import hashlib
import ctypes
import os
from pathlib import Path
import stat

import ntsecuritycon
import pywintypes
import win32api
import win32con
import win32file
import win32security
from win32com.shell import shell, shellcon


def current_sid():
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    finally:
        token.Close()


def default_owner_sid():
    """The OS token's default owner can be Administrators for elevated Node."""
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return win32security.GetTokenInformation(token, win32security.TokenOwner)
    finally:
        token.Close()


def sid_string():
    return win32security.ConvertSidToStringSid(current_sid())


def identity_key():
    # A name collision cannot confer permission; the ACL authenticates access.
    return hashlib.sha256(sid_string().encode('ascii')).hexdigest()[:24]


def local_app_data():
    # Read the OS known-folder value, not an inherited environment variable that
    # may belong to another user or point inside the replaceable installation.
    return Path(shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, None, 0))


def security_attributes(*, directory=False):
    flags = 'OICI' if directory else ''
    user = sid_string()
    descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        f'O:{user}D:P(A;{flags};FA;;;{user})(A;{flags};FA;;;SY)',
        win32security.SDDL_REVISION_1)
    attributes = pywintypes.SECURITY_ATTRIBUTES()
    attributes.SECURITY_DESCRIPTOR = descriptor
    attributes.bInheritHandle = False
    return attributes


def reject_reparse_ancestors(path):
    # Include junctions/mount-point reparse objects, not just Python symlinks.
    path = Path(os.path.abspath(path))
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise PermissionError('Private Augmentor paths cannot traverse a reparse point.')
    return path


def require_private_directory(path):
    path = reject_reparse_ancestors(path)
    if not path.is_dir():
        raise PermissionError('Augmentor needs an ordinary private directory.')
    descriptor = win32security.GetFileSecurity(str(path), win32security.OWNER_SECURITY_INFORMATION |
                                              win32security.DACL_SECURITY_INFORMATION)
    require_private_descriptor(descriptor)
    return path


def require_private_descriptor(descriptor):
    require_private_grants(descriptor)
    control, _revision = descriptor.GetSecurityDescriptorControl()
    if not control & win32security.SE_DACL_PROTECTED:
        raise PermissionError('The Augmentor directory must not inherit broader access from its parent.')


def require_private_grants(descriptor, *, download_default_owner=False):
    """Validate the exact owner/user/SYSTEM allow-list without changing an ACL."""
    owner = descriptor.GetSecurityDescriptorOwner()
    if owner != current_sid() and not (download_default_owner and owner == default_owner_sid()):
        raise PermissionError('The Augmentor directory belongs to another Windows identity.')
    acl = descriptor.GetSecurityDescriptorDacl()
    if acl is None:
        raise PermissionError('The Augmentor directory has no access restrictions.')
    allowed = {sid_string(), 'S-1-5-18'}
    user_access = False
    for index in range(acl.GetAceCount()):
        ace = acl.GetAce(index)
        (kind, flags), mask, sid = ace
        # Owned directories use a simple protected allow-list, not inherited or
        # object-specific rules that we cannot interpret safely here.
        identity = win32security.ConvertSidToStringSid(sid)
        if kind != win32security.ACCESS_ALLOWED_ACE_TYPE or identity not in allowed:
            raise PermissionError('The Augmentor directory grants an unexpected identity access.')
        if identity == sid_string() and mask & ntsecuritycon.FILE_ALL_ACCESS == ntsecuritycon.FILE_ALL_ACCESS:
            user_access = True
    if not user_access:
        raise PermissionError('The current user cannot maintain this Augmentor directory.')


def private_lock_descriptor(path):
    """Open a private, regular, single-link lease file without following a reparse."""
    return private_file_descriptor(path, writable=True, create=True)


def require_payload_grants(descriptor):
    """Public installed code may be readable broadly, but never writable broadly.

    Inno's per-user payload can inherit the token's Administrators owner and
    ordinary read grants. This is deliberately separate from private state and
    download validation; it never changes an ACL or creates a file.
    """
    trusted={sid_string(),'S-1-5-18','S-1-5-32-544'}
    if win32security.ConvertSidToStringSid(descriptor.GetSecurityDescriptorOwner()) not in trusted:
        raise PermissionError('The installed payload belongs to an unexpected Windows identity.')
    acl=descriptor.GetSecurityDescriptorDacl()
    if acl is None:raise PermissionError('The installed payload has unrestricted access.')
    write=(ntsecuritycon.FILE_WRITE_DATA|ntsecuritycon.FILE_APPEND_DATA|ntsecuritycon.FILE_WRITE_EA|
           ntsecuritycon.FILE_WRITE_ATTRIBUTES|ntsecuritycon.FILE_DELETE_CHILD|ntsecuritycon.DELETE|
           ntsecuritycon.WRITE_DAC|ntsecuritycon.WRITE_OWNER|win32con.GENERIC_WRITE|win32con.GENERIC_ALL)
    for index in range(acl.GetAceCount()):
        (kind,flags),mask,sid=acl.GetAce(index)
        if flags & win32security.INHERIT_ONLY_ACE:continue
        if kind!=win32security.ACCESS_ALLOWED_ACE_TYPE:
            raise PermissionError('The installed payload has unsupported access rules.')
        if mask & write and win32security.ConvertSidToStringSid(sid) not in trusted:
            raise PermissionError('The installed payload is writable by another Windows identity.')


def payload_file_descriptor(path):
    """Pin existing installed code read-only; retain normal installation ACLs."""
    import msvcrt
    path=reject_reparse_ancestors(path)
    security=win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION
    require_payload_grants(win32security.GetFileSecurity(str(path.parent),security))
    try:
        handle=win32file.CreateFile(str(path),win32con.GENERIC_READ,win32con.FILE_SHARE_READ,None,
            win32con.OPEN_EXISTING,win32file.FILE_FLAG_OPEN_REPARSE_POINT,None)
    except pywintypes.error as error:raise ctypes.WinError(error.winerror) from None
    try:
        info=win32file.GetFileInformationByHandle(handle)
        if info[0] & (stat.FILE_ATTRIBUTE_REPARSE_POINT|stat.FILE_ATTRIBUTE_DIRECTORY) or info[7]!=1:
            raise PermissionError('The installed executable must be an ordinary single-link file.')
        require_payload_grants(win32security.GetSecurityInfo(handle,win32security.SE_FILE_OBJECT,security))
        return msvcrt.open_osfhandle(handle.Detach(),os.O_RDONLY|os.O_BINARY)
    except pywintypes.error as error:raise ctypes.WinError(error.winerror) from None
    finally:handle.Close()


def private_file_descriptor(path, *, writable=False, create=False, exclusive=False, private_parent=True, share_write=True):
    """Read or create a protected ordinary file; validate the opened object."""
    import msvcrt
    path = reject_reparse_ancestors(path)
    if private_parent:
        private_directory(path.parent)
    elif not path.parent.is_dir():
        raise FileNotFoundError('The selected data directory does not exist.')
    disposition = win32con.CREATE_NEW if exclusive else win32con.OPEN_ALWAYS if create else win32con.OPEN_EXISTING
    access = win32con.GENERIC_READ | (win32con.GENERIC_WRITE if writable else 0)
    try:
        handle = win32file.CreateFile(str(path), access,
            win32con.FILE_SHARE_READ | (win32con.FILE_SHARE_WRITE if share_write else 0), security_attributes(),
            disposition, win32file.FILE_FLAG_OPEN_REPARSE_POINT, None)
    except pywintypes.error as error:
        # Keep the shared filesystem contract: pywin32's exception type is not
        # an OSError, so map actual kernel failures to Python's standard family.
        raise ctypes.WinError(error.winerror) from None
    try:
        info = win32file.GetFileInformationByHandle(handle)
        if info[0] & (stat.FILE_ATTRIBUTE_REPARSE_POINT | stat.FILE_ATTRIBUTE_DIRECTORY) or info[7] != 1:
            raise PermissionError('The private file must be an ordinary single-link file.')
        descriptor = win32security.GetSecurityInfo(handle, win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
        require_private_descriptor(descriptor)
        return msvcrt.open_osfhandle(handle.Detach(), (os.O_RDWR if writable else os.O_RDONLY) | os.O_BINARY)
    except pywintypes.error as error:
        raise ctypes.WinError(error.winerror) from None
    finally:
        handle.Close()


def private_directory(path):
    path = reject_reparse_ancestors(path)
    if not path.parent.is_dir():
        private_directory(path.parent)
    try:
        win32file.CreateDirectory(str(path), security_attributes(directory=True))
    except pywintypes.error as error:
        if getattr(error, 'winerror', None) != 183:
            raise
    return require_private_directory(path)


def protect_inherited_download(path):
    """Protect a Node-produced file that already has the exact private allow-list.

    The known private download parent and opened single-link file are verified
    first. This cannot repair a public/foreign ACL or follow a reparse object.
    Windows Node inherits safe grants but does not set SE_DACL_PROTECTED on files.
    Elevated Node can use the token's default group owner; only that exact OS
    identity may be normalized to the current user, after the grants check.
    """
    path=reject_reparse_ancestors(path)
    require_private_directory(path.parent)
    try:
        handle=win32file.CreateFile(str(path),win32con.GENERIC_READ|win32con.READ_CONTROL|win32con.WRITE_DAC|win32con.WRITE_OWNER,
            win32con.FILE_SHARE_READ,None,win32con.OPEN_EXISTING,win32file.FILE_FLAG_OPEN_REPARSE_POINT,None)
    except pywintypes.error as error:
        raise ctypes.WinError(error.winerror) from None
    try:
        info=win32file.GetFileInformationByHandle(handle)
        if info[0] & (stat.FILE_ATTRIBUTE_REPARSE_POINT|stat.FILE_ATTRIBUTE_DIRECTORY) or info[7]!=1:
            raise PermissionError('The download must be an ordinary single-link file.')
        observed=win32security.GetSecurityInfo(handle,win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION)
        require_private_grants(observed, download_default_owner=True)
        control,_=observed.GetSecurityDescriptorControl()
        if observed.GetSecurityDescriptorOwner() != current_sid() or not control & win32security.SE_DACL_PROTECTED:
            selected=security_attributes().SECURITY_DESCRIPTOR
            win32security.SetSecurityInfo(handle,win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION|win32security.PROTECTED_DACL_SECURITY_INFORMATION,
                current_sid(),None,selected.GetSecurityDescriptorDacl(),None)
        require_private_descriptor(win32security.GetSecurityInfo(handle,win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION))
    except pywintypes.error as error:
        raise ctypes.WinError(error.winerror) from None
    finally:
        handle.Close()


def process_sid(pid):
    process = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    try:
        token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
        try:
            return win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        finally:
            token.Close()
    finally:
        process.Close()
