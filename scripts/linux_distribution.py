# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Pure distribution/package plans for complete Linux installation.

The host must match an explicit bundle target. ID_LIKE is diagnostic information,
not permission to install a package prepared for another distribution/version.
No command is executed and no state is written by this module.
"""
from pathlib import Path
import platform
import shlex
import re

NOBLE='ubuntu24.04-amd64'

TARGETS = {
    'debian13-amd64': ('debian', '13', 'apt', '.deb'),
    'ubuntu26.04-amd64': ('ubuntu', '26.04', 'apt', '.deb'),
    NOBLE: ('ubuntu', '24.04', 'apt', '.deb'),
    'fedora43-x86_64': ('fedora', '43', 'dnf', '.rpm'),
    'fedora44-x86_64': ('fedora', '44', 'dnf', '.rpm'),
}


def os_release(text):
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, raw = line.split('=', 1)
        if name not in ('ID', 'VERSION_ID', 'ID_LIKE', 'PRETTY_NAME'):
            continue
        parts = shlex.split(raw, comments=False)
        if len(parts) != 1:
            raise ValueError('Invalid os-release field: ' + name)
        values[name] = parts[0]
    return values


def host_target(info=None, machine=None):
    if info is None:
        info = os_release(Path('/etc/os-release').read_text())
    machine = platform.machine() if machine is None else machine
    if machine not in ('x86_64', 'amd64'):
        raise ValueError('This bundle requires x86-64; ' + machine + ' needs a separately qualified artifact.')
    for target, (name, version, _, _) in TARGETS.items():
        if (info.get('ID'), info.get('VERSION_ID')) == (name, version):
            return target
    label = info.get('PRETTY_NAME', info.get('ID', 'unknown Linux'))
    if (info.get('ID'), info.get('VERSION_ID')) == ('ubuntu', '24.04') or (info.get('ID') == 'linuxmint' and info.get('VERSION_ID', '').split('.')[0] == '22'):
        raise ValueError(label + ' needs the managed PySide6 runtime; this system-Qt bundle cannot install it.')
    raise ValueError('No qualified package adapter for ' + label + '. Supported candidates: ' + ', '.join(TARGETS))


def package_files(manifest, target):
    if target not in TARGETS:
        raise ValueError('Unknown complete bundle target: ' + str(target))
    suffix = TARGETS[target][3]
    files = manifest.get('packages')
    if files is None:
        files = [name for name in manifest['sha256'] if name.endswith(suffix)]
    expected = 2 if suffix == '.deb' else 1
    if not isinstance(files, list) or len(files) != expected or not all(isinstance(name,str) for name in files):
        raise ValueError('The bundle must contain the matching runtime/desktop packages for ' + target)
    if len(set(files)) != expected:
        raise ValueError('The bundle must contain the matching runtime/desktop packages for ' + target)
    for name in files:
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(suffix) or name not in manifest['sha256']:
            raise ValueError('Invalid or unchecked system package in complete bundle.')
    version = manifest['version']
    if suffix == '.deb':
        if set(files) != {f'augmentor-{kind}_{version}_amd64.deb' for kind in ('runtime', 'desktop')}:
            raise ValueError('The runtime and desktop package identities must match the bundle version.')
    elif not files[0].startswith('augmentor-agent-' + version + '-') or not files[0].endswith('.fc'+TARGETS[target][1]+'.x86_64.rpm'):
        raise ValueError('The Fedora package identity must match the bundle version and architecture.')
    return sorted(files)


def python_runtime_contract(manifest,target):
    value=manifest.get('pythonRuntime')
    if target!=NOBLE:
        if value is not None:raise ValueError('This bundle target cannot use a Noble Python runtime.')
        return None
    if (not isinstance(value,dict) or value.get('format')!='augmentor-linux-python-runtime-contract/1'
            or value.get('target')!=NOBLE or value.get('profile') not in ('noble-cp312-x86_64-voice','noble-cp312-x86_64-source-qt-voice')
            or value.get('pythonAbi')!=[3,12] or value.get('architecture')!='x86_64'
            or not all(isinstance(value.get(key),str) and re.fullmatch('[a-f0-9]{64}',value[key]) for key in ('policySha256','lockIdentity'))):
        raise ValueError('The Noble bundle requires its complete verified Python runtime contract.')
    if value['profile']=='noble-cp312-x86_64-source-qt-voice':
        import importlib.util
        spec=importlib.util.spec_from_file_location('distribution_source_qt',Path(__file__).with_name('linux-source-qt.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.contract(value)
        if value.get('licenseReviewComplete') is not False or value.get('embeddedSourceCoverageComplete') is not False:
            raise ValueError('The source Qt contract remains an unqualified candidate.')
    elif 'sourceQt' in value:
        raise ValueError('The vendor runtime cannot declare a source Qt payload.')
    return value


def dependency_packages(target, *, voice=False, gpu=False, memory=False, memory_engine_present=False):
    manager = TARGETS[target][2]
    if manager == 'apt':
        result = ['ca-certificates', 'python3-venv', 'npm', 'libportaudio2',
                  'libasound2-plugins', 'pulseaudio-utils']
        if voice:
            result += ['git', 'cmake', 'g++', 'pkg-config']
        if gpu:
            result += ['libvulkan-dev', 'glslc', 'spirv-headers']
        if memory and not memory_engine_present:
            result += ['docker.io']
    else:
        npm = 'nodejs-npm' if target == 'fedora43-x86_64' else 'nodejs24-npm'
        result = ['ca-certificates', 'python3-pip', npm, 'portaudio',
                  'alsa-plugins-pulseaudio', 'pulseaudio-utils']
        if voice:
            result += ['git', 'cmake', 'gcc-c++', 'pkgconf-pkg-config']
        if gpu:
            result += ['vulkan-loader-devel', 'glslc', 'spirv-headers-devel']
        if memory and not memory_engine_present:
            result += ['moby-engine']
    return result


def install_plan(manifest, bundle, *, info=None, machine=None, voice=False, gpu=False, memory=False, memory_engine_present=False):
    target = host_target(info, machine)
    declared = manifest.get('target')
    if declared != target:
        raise ValueError(f'This bundle targets {declared}; the detected system requires {target}. Download its matching bundle.')
    if gpu and not voice:
        raise ValueError('GPU speech requires voice provisioning.')
    files = package_files(manifest, target)
    runtime=python_runtime_contract(manifest,target)
    dependencies = dependency_packages(target, voice=voice, gpu=gpu, memory=memory,memory_engine_present=memory_engine_present)
    manager = TARGETS[target][2]
    command = ['sudo', manager, 'install', '-y']
    command += [str(Path(bundle).resolve() / name) for name in files] + dependencies
    return {'target': target, 'packageManager': manager, 'packages': files, 'pythonRuntime':runtime,
            'dependencies': dependencies, 'command': command,
            'memoryEngine': 'docker' if memory else 'deferred',
            'installMemoryEngine': bool(memory and not memory_engine_present),
            'qualification': 'Package adapter; real desktop/browser/voice acceptance is separate.'}
