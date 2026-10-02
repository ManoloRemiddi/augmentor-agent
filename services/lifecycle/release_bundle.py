# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Verify release metadata and retain exact installer bytes before preparation.

WinSparkle owns Windows download/signature UI. Its handled-download callback may
pass the resulting bundle here, never directly to an installer. This shared
boundary authenticates metadata against an installed trust root and checks local
compatibility independently of the feed. Nothing here closes or executes apps.
"""
import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import struct
import subprocess
import sys
import time
import zipfile

from platform_adapters.paths import private_directory
from platform_adapters.private_files import descriptor, require_directory
from .update_journal import artifact

SCHEMA = 'augmentor-release-bundle/1'
MAX_MANIFEST = 65536
MAX_INSTALLER = 2 * 1024**3 - 1024**2
NAMES = {'manifest.json', 'manifest.sig', 'installer.exe'}


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError('Duplicate release metadata field.')
        value[key] = item
    return value


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:0|[1-9]\d{0,5})\.(?:0|[1-9]\d{0,5})\.(?:0|[1-9]\d{0,5})', value):
        raise ValueError('Use a supported three-part release version.')
    return tuple(map(int, value.split('.')))


def _authenticate_manifest(raw, signature, *, public_key, node):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_MANIFEST or not isinstance(signature, bytes) or len(signature) != 64:
        raise ValueError('Invalid signed release metadata size.')
    try:
        key = base64.b64decode(public_key, validate=True)
        if len(key) != 32 or base64.b64encode(key).decode('ascii') != public_key: raise ValueError()
    except (TypeError, ValueError):
        raise ValueError('An installed Ed25519 release trust root is required.') from None
    node = Path(node)
    if not node.is_absolute() or not node.is_file():
        raise ValueError('Use the explicit bundled Node executable for verification.')
    envelope = {'key': public_key, 'signature': base64.b64encode(signature).decode('ascii'),
                'manifest': base64.b64encode(raw).decode('ascii')}
    # No PATH lookup, shell or inherited Node preload options. The small helper
    # imports only the bundled runtime's crypto module, with no network access.
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith('NODE_')}
    try:
        result = subprocess.run([str(node), str(Path(__file__).with_name('verify-release.mjs'))],
            input=json.dumps(envelope).encode('ascii'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=environment, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError('Release signature verification was unavailable. Nothing was prepared.') from None
    if result.returncode != 0 or result.stdout != b'verified\n':
        raise ValueError('The release signature is not trusted. Nothing was prepared.')
    try: manifest = json.loads(raw.decode('utf-8'), object_pairs_hook=_object)
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError('Invalid signed release metadata.') from None
    fields = {'schema', 'release', 'installerBytes', 'minimumOSBuild', 'protocols', 'issuedAt', 'expiresAt'}
    if not isinstance(manifest, dict) or set(manifest) != fields or manifest['schema'] != SCHEMA:
        raise ValueError('Unsupported signed release metadata.')
    return manifest


def _compatible_manifest(manifest, *, current, protocols, os_build, now):
    """Common trust-independent constraints for delivery and retained recovery."""
    after, before = artifact(manifest['release']), artifact(current)
    _version(after['version']); _version(before['version'])
    if after['target'] not in ('windows-x64', 'windows-arm64') or after['target'] != before['target']:
        raise ValueError('This release targets a different OS or CPU.')
    if after['channel'] != before['channel']:
        raise ValueError('This release targets a different update channel.')
    if before['dataSchema'] not in after['readableDataSchemas'] or after['dataSchema'] not in before['readableDataSchemas']:
        raise ValueError('This release needs an explicit data migration and recovery plan.')
    if not isinstance(protocols, dict) or not protocols or manifest['protocols'] != protocols:
        raise ValueError('This release needs an explicit protocol compatibility plan.')
    if type(manifest['minimumOSBuild']) is not int or not 26200 <= manifest['minimumOSBuild'] <= 0xffffffff:
        raise ValueError('Unsupported minimum Windows build.')
    if type(os_build) is not int or os_build < manifest['minimumOSBuild']:
        raise ValueError('This release needs a newer Windows version.')
    if type(manifest['installerBytes']) is not int or not 1 <= manifest['installerBytes'] <= MAX_INSTALLER:
        raise ValueError('Unsupported installer length.')
    issued, expires = manifest['issuedAt'], manifest['expiresAt']
    if (type(issued) is not int or type(expires) is not int or not 0 < issued < expires or
            expires - issued > 90 * 86400 or issued > now + 300):
        raise ValueError('Release metadata has expired or the system clock needs attention.')
    return after, before


def verify_manifest(raw, signature, *, public_key, node, current, protocols, os_build, now=None):
    """Authenticate exact signed bytes, then enforce forward-delivery policy.

    current/protocols/os_build and public_key come from the verified installation
    and OS, never from an appcast. This entrypoint cannot authorize a downgrade.
    """
    now = time.time() if now is None else now
    manifest = _authenticate_manifest(raw, signature, public_key=public_key, node=node)
    after, before = _compatible_manifest(manifest, current=current, protocols=protocols, os_build=os_build, now=now)
    if _version(after['version']) <= _version(before['version']):
        raise ValueError('An update must be newer than the installed version.')
    if after['sourceCommit'] == before['sourceCommit']:
        raise ValueError('A forward release must identify its reviewed source revision.')
    if manifest['expiresAt'] <= now:
        raise ValueError('Release metadata has expired or the system clock needs attention.')
    return manifest


def _bounded_zip(stream):
    """Bound central-directory allocation before the stdlib parses any entries."""
    length = os.fstat(stream.fileno()).st_size
    if not 22 <= length <= MAX_INSTALLER + MAX_MANIFEST + 8192:
        raise ValueError('Unsupported release bundle length.')
    stream.seek(-22, os.SEEK_END)
    tag, disk, directory_disk, count, total, size, offset, comment = struct.unpack('<4s4H2IH', stream.read(22))
    if (tag != b'PK\x05\x06' or disk or directory_disk or count != 3 or total != 3 or
            not 0 < size <= 4096 or offset + size != length - 22 or comment):
        raise ValueError('Use the bounded three-file release bundle format.')
    stream.seek(0)
    bundle = zipfile.ZipFile(stream)
    try:
        entries = bundle.infolist()
        if len(entries) != 3 or {entry.filename for entry in entries} != NAMES:
            raise ValueError('Unexpected or duplicated release bundle entries.')
        for entry in entries:
            mode = stat.S_IFMT(entry.external_attr >> 16)
            if (entry.is_dir() or entry.compress_type != zipfile.ZIP_STORED or entry.flag_bits & ~0x800 or
                    entry.extra or entry.comment or mode not in (0, stat.S_IFREG) or
                    entry.file_size != entry.compress_size):
                raise ValueError('Unsupported release archive member.')
        if not 0 < bundle.getinfo('manifest.json').file_size <= MAX_MANIFEST or bundle.getinfo('manifest.sig').file_size != 64:
            raise ValueError('Invalid release metadata length.')
        if not 0 < bundle.getinfo('installer.exe').file_size <= MAX_INSTALLER:
            raise ValueError('Invalid bundled installer length.')
        return bundle
    except BaseException:
        bundle.close(); raise


@dataclass
class VerifiedRelease:
    directory: Path
    manifest: dict
    fd: int | None

    @property
    def installer(self): return self.directory/'installer.exe'

    @property
    def identity(self): return artifact(self.manifest['release'])

    def close(self):
        if self.fd is not None: os.close(self.fd); self.fd = None

    def __enter__(self): return self
    def __exit__(self, *_): self.close()


def open_retained_release(directory, *, expected, public_key, node, current, protocols, os_build, now=None):
    """Revalidate an exact recorded local recovery artifact, without executing it.

    expected must be the independently established retained source identity from
    the installed receipt/update journal, never a download's self-description.
    Delivery expiry does not make an already retained recovery artifact unusable;
    signature, exact identity, bytes, OS/channel/schema/protocol checks still apply.
    This does not acquire maintenance, inspect interrupted installation state,
    authorize a downgrade, or find an independent recovery runtime.
    """
    directory = require_directory(Path(directory))
    expected = artifact(expected)
    now = time.time() if now is None else now
    with os.fdopen(descriptor(directory/'manifest.json'), 'rb') as stream:
        raw = stream.read(MAX_MANIFEST+1)
    with os.fdopen(descriptor(directory/'manifest.sig'), 'rb') as stream:
        signature = stream.read(65)
    manifest = _authenticate_manifest(raw, signature, public_key=public_key, node=node)
    after, before = _compatible_manifest(manifest, current=current, protocols=protocols, os_build=os_build, now=now)
    if after != expected:
        raise ValueError('The retained release differs from the recorded recovery identity.')
    if _version(after['version']) > _version(before['version']):
        raise ValueError('A future release is not the recorded previous installation.')
    pinned = None
    try:
        if sys.platform == 'win32':
            from platform_adapters.windows_identity import private_file_descriptor
            pinned = private_file_descriptor(directory/'installer.exe', share_write=False)
        else: pinned = descriptor(directory/'installer.exe')
        with os.fdopen(os.dup(pinned), 'rb') as stream:
            if (os.fstat(stream.fileno()).st_size != manifest['installerBytes'] or
                    hashlib.file_digest(stream, 'sha256').hexdigest() != after['sha256']):
                raise ValueError('The retained installer differs from its signed bytes.')
        result = VerifiedRelease(directory, manifest, pinned)
        pinned = None
        return result
    finally:
        if pinned is not None: os.close(pinned)


def stage_bundle(download, cache, **policy):
    """Retain a verified download in private storage; never extract supplied paths.

    The returned handle denies writes/deletion on Windows until it is closed.
    WindowsApply independently checks the same signed digest when launching.
    Signed metadata is retained for future independent recovery verification.
    """
    cache = require_directory(Path(cache))
    directory = None; pinned = None; success = False
    try:
        with Path(download).open('rb') as stream, _bounded_zip(stream) as bundle:
            raw, signature = bundle.read('manifest.json'), bundle.read('manifest.sig')
            manifest = verify_manifest(raw, signature, **policy)
            if bundle.getinfo('installer.exe').file_size != manifest['installerBytes']:
                raise ValueError('The installer length differs from its signed metadata.')
            directory = require_directory(private_directory(cache/('release-'+secrets.token_hex(24))))
            digest = hashlib.sha256(); length = 0
            with os.fdopen(descriptor(directory/'installer.exe', writable=True, exclusive=True), 'wb') as target, bundle.open('installer.exe') as source:
                while data := source.read(1024 * 1024):
                    length += len(data)
                    if length > manifest['installerBytes']: raise ValueError('Installer exceeds its signed length.')
                    target.write(data); digest.update(data)
                target.flush(); os.fsync(target.fileno())
            if length != manifest['installerBytes'] or digest.hexdigest() != manifest['release']['sha256']:
                raise ValueError('The installer bytes differ from their signed release identity.')
            for name, content in (('manifest.json', raw), ('manifest.sig', signature)):
                with os.fdopen(descriptor(directory/name, writable=True, exclusive=True), 'wb') as target:
                    target.write(content); target.flush(); os.fsync(target.fileno())
            if sys.platform == 'win32':
                from platform_adapters.windows_identity import private_file_descriptor
                pinned = private_file_descriptor(directory/'installer.exe', share_write=False)
            else: pinned = descriptor(directory/'installer.exe')
            with os.fdopen(os.dup(pinned), 'rb') as source:
                if hashlib.file_digest(source, 'sha256').hexdigest() != manifest['release']['sha256']:
                    raise ValueError('The retained installer changed during verification.')
            result = VerifiedRelease(directory, manifest, pinned)
            success = True
            return result
    finally:
        if not success:
            if pinned is not None: os.close(pinned)
            if directory is not None:
                # Only these newly created files; no recursive cleanup of paths
                # or existing releases supplied by a download or another process.
                for name in NAMES: (directory/name).unlink(missing_ok=True)
                directory.rmdir()
