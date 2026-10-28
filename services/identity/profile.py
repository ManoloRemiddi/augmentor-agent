# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Private, shared agent identity. Soul is an ordinary atomically replaced Markdown file."""
import base64
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 32768


def directory():
    return Path(os.environ.get('AUGMENTOR_IDENTITY_DIR', Path(os.environ.get('AUGMENTOR_PI_CONFIG', Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'augmentor-pi'))/'identity'))


def default_soul():
    return (ROOT/'config/agent-persona.md').read_text(encoding='utf-8')


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def bounded_read(path, limit):
    with path.open('rb') as file:
        raw = file.read(limit+1)
    if len(raw)>limit:
        raise ValueError('The saved agent file exceeds its size limit.')
    return raw.decode('utf-8')


def soul():
    path = directory()/'soul.md'
    value = bounded_read(path, LIMIT) if path.exists() else default_soul()
    if not value.strip():
        raise ValueError('Soul cannot be empty.')
    return {'text': value, 'revision': digest(value), 'default': default_soul()}


def profile():
    path = directory()/'profile.json'
    raw = bounded_read(path, 524288) if path.exists() else '{}'
    value = json.loads(raw)
    return {'name': value.get('name', 'Augmentor'), 'avatar': value.get('avatar', ''), 'revision': digest(raw)}


@contextmanager
def locked():
    folder = directory()
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (folder/'.lock').open('a') as file:
        os.chmod(file.name, 0o600)
        fcntl.flock(file, fcntl.LOCK_EX)
        yield


def replace(path, text):
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
            name = file.name
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
        name = None
        fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if name: Path(name).unlink(missing_ok=True)


def save_soul(text, expected_revision):
    if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8'))>LIMIT or '\0' in text:
        raise ValueError('Enter nonempty instructions of at most 32 KiB.')
    with locked():
        if soul()['revision'] != expected_revision:
            raise ValueError('Soul changed in another window. Your draft is kept; reopen Soul to load the latest version.')
        replace(directory()/'soul.md', text)
    return soul()


def save_profile(name, avatar, expected_revision):
    name = name.strip()
    if not name or len(name)>80 or any(ord(c)<32 for c in name):
        raise ValueError('Enter an agent name of 1–80 characters.')
    if not isinstance(avatar, str) or len(avatar)>400000:
        raise ValueError('Choose a smaller image.')
    if avatar:
        try: raw = base64.b64decode(avatar, validate=True)
        except ValueError as error: raise ValueError('Invalid agent image.') from error
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Agent images must be decoded and saved as PNG.')
    with locked():
        if profile()['revision'] != expected_revision:
            raise ValueError('Identity changed in another window. Reopen settings to load the latest version.')
        replace(directory()/'profile.json', json.dumps({'name': name, 'avatar': avatar}, ensure_ascii=False))
    return profile()
