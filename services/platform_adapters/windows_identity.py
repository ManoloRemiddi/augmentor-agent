# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Windows token identity and private filesystem objects (pywin32, both CPUs)."""
import hashlib
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
    if descriptor.GetSecurityDescriptorOwner() != current_sid():
        raise PermissionError('The Augmentor directory belongs to another Windows identity.')
    acl = descriptor.GetSecurityDescriptorDacl()
    if acl is None:
        raise PermissionError('The Augmentor directory has no access restrictions.')
    control, _revision = descriptor.GetSecurityDescriptorControl()
    if not control & win32security.SE_DACL_PROTECTED:
        raise PermissionError('The Augmentor directory must not inherit broader access from its parent.')
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


def private_file_descriptor(path, *, writable=False, create=False, exclusive=False):
    """Read or create a protected ordinary file; validate the opened object."""
    import msvcrt
    path = reject_reparse_ancestors(path)
    private_directory(path.parent)
    disposition = win32con.CREATE_NEW if exclusive else win32con.OPEN_ALWAYS if create else win32con.OPEN_EXISTING
    access = win32con.GENERIC_READ | (win32con.GENERIC_WRITE if writable else 0)
    handle = win32file.CreateFile(str(path), access,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE, security_attributes(),
        disposition, win32file.FILE_FLAG_OPEN_REPARSE_POINT, None)
    try:
        info = win32file.GetFileInformationByHandle(handle)
        if info[0] & (stat.FILE_ATTRIBUTE_REPARSE_POINT | stat.FILE_ATTRIBUTE_DIRECTORY) or info[7] != 1:
            raise PermissionError('The private file must be an ordinary single-link file.')
        descriptor = win32security.GetSecurityInfo(handle, win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
        require_private_descriptor(descriptor)
        return msvcrt.open_osfhandle(handle.Detach(), (os.O_RDWR if writable else os.O_RDONLY) | os.O_BINARY)
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
