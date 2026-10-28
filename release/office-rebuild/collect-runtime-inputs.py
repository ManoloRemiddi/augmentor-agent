#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Export the completed Office diagnostic's verified Emscripten source/notices.

Consumes an already fetched pinned public archive. No network, engine compile,
installed update or public redistribution approval is performed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('office_source_export',
    Path(__file__).with_name('collect-source-inputs.py'))
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)


def match_source(archive_path, installed, pin):
    if (archive_path.is_symlink() or not archive_path.is_file() or
            archive_path.stat().st_size != pin['sourceArchive']['bytes'] or
            inputs.digest(archive_path) != pin['sourceArchive']['sha256']):
        raise ValueError('Public Emscripten archive differs from the reviewed source.')
    wanted = {}
    for group in pin['installedSourceGroups']:
        for path in (installed / group).rglob('*'):
            if '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                raise ValueError('Linked installed runtime source is unsupported.')
            if path.is_file():
                name = path.relative_to(installed).as_posix()
                wanted[name] = {'bytes': path.stat().st_size, 'sha256': inputs.digest(path)}
    root_sources = {path.name for path in installed.iterdir() if path.is_file() and
                    path.name not in ('emscripten-version.txt', 'emscripten-revision.txt')}
    if root_sources != set(pin['installedRootSources']):
        raise ValueError('Installed runtime root source inventory changed.')
    for name in pin['installedRootSources']:
        path = inputs.regular(installed, name)
        wanted[name] = {'bytes': path.stat().st_size, 'sha256': inputs.digest(path)}
    if len(wanted) != pin['installedPreferredSourceFiles']:
        raise ValueError('Installed runtime preferred-source inventory changed.')
    seen = set()
    version_source_seen = False
    prefix = 'emscripten-' + pin['emscriptenRevision']
    with tarfile.open(archive_path, 'r|gz') as archive:
        for entry in archive:
            path = PurePosixPath(entry.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts or
                    path.parts[0] != prefix):
                raise ValueError('Unsafe public source archive path.')
            name = '/'.join(path.parts[1:])
            if name == 'emscripten-version.txt':
                if version_source_seen or not entry.isfile() or entry.size > 256:
                    raise ValueError('Ambiguous public version source.')
                raw = archive.extractfile(entry).read()
                if (raw.decode() != pin['publicVersionSource']['bytes'] or
                        hashlib.sha256(raw).hexdigest() != pin['publicVersionSource']['sha256']):
                    raise ValueError('Public version source changed.')
                version_source_seen = True
            if name not in wanted:
                continue
            if not entry.isfile() or name in seen or entry.size > 32 * 1024 * 1024:
                raise ValueError('Ambiguous or oversized public runtime source.')
            sha = hashlib.sha256()
            with archive.extractfile(entry) as stream:
                while block := stream.read(1024 * 1024):
                    sha.update(block)
            if wanted[name] != {'bytes': entry.size, 'sha256': sha.hexdigest()}:
                raise ValueError('Installed runtime differs from public source: ' + name)
            seen.add(name)
    if seen != set(wanted) or not version_source_seen:
        raise ValueError('Installed runtime source absent from the public archive.')
    return wanted


def link_inputs(cache, pin):
    matches = [path for path in (cache / 'thin-build-debug').glob('*.rsp.utf-8')
               if not path.is_symlink() and path.is_file() and path.stat().st_size < 1024 * 1024
               and inputs.digest(path) == pin['finalLinkResponseSha256']]
    if len(matches) != 1:
        raise ValueError('The exact final link response is unavailable or ambiguous.')
    response = matches[0]
    args = shlex.split(response.read_text())
    if (args.count('-o') != 1 or args[args.index('-o') + 1] != pin['finalOutput']):
        raise ValueError('The retained linker response targets another output.')
    directory = cache / 'emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/thinlto'
    libraries = {}
    for arg in args:
        if arg.startswith('-l') and len(arg) > 2:
            name = 'lib' + arg[2:] + '.a'
            if (directory / name).is_file():
                libraries[name] = inputs.digest(inputs.regular(directory, name))
    if libraries != pin['systemLibraries']:
        raise ValueError('The final link system-library inputs changed.')
    for name, sha in pin['explicitSystemObjects'].items():
        expected = '/office/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/thinlto/' + name
        if args.count(expected) != 1 or inputs.digest(inputs.regular(directory, name)) != sha:
            raise ValueError('The explicit runtime object changed.')
    return response, libraries


def submodule_scope(cache):
    config = {}
    for filename in ['config_host.mk', 'config_host_lang.mk']:
        for line in inputs.regular(cache, 'build-thin/' + filename).read_text().splitlines():
            if '=' in line:
                key, value = line.removeprefix('export ').split('=', 1)
                config[key] = value
    if (set(config['BUILD_TYPE'].split()) & {'DICTIONARIES', 'HELP'} or
            config['WITH_MYSPELL_DICTS'] or config['WITH_LANG'] or
            config['WITH_LANG_LIST'] != 'en-US'):
        raise ValueError('Core submodule use differs from the qualified build.')
    for name in ['dictionaries', 'helpcontent2', 'translations']:
        directory = cache / 'core' / name
        if directory.is_symlink() or not directory.is_dir() or any(directory.iterdir()):
            raise ValueError('A Core submodule now contains unqualified inputs.')
    return {'emptySubmodules': ['dictionaries', 'helpcontent2', 'translations'],
            'dictionaryAndHelpBuildTypesAbsent': True, 'bundledDictionaries': False,
            'translationLanguages': config['WITH_LANG_LIST'],
            'scope': 'These source directories are empty in the successful producer; no submodule sources were inputs.'}


def collect(cache, producer, source_archive, base, output):
    if not sys.platform.startswith('linux'):
        raise ValueError('This runtime-source companion currently requires Linux.')
    if (output.parent != (ROOT / 'outputs').resolve() or output.exists() or output.is_symlink()):
        raise ValueError('Choose a new direct child of repository outputs/.')
    qualification = json.loads((ROOT / 'release/office-rebuild/source-inputs-qualification-20261017.json').read_text())
    base_manifest = inputs.regular(base, 'SOURCE-INPUTS.json')
    if inputs.digest(base_manifest) != qualification['export']['sourceManifestSha256']:
        raise ValueError('The companion requires the independently verified Core source bundle.')
    pin = json.loads((ROOT / 'release/office-rebuild/emscripten-runtime-inputs.json').read_text())
    build = json.loads((ROOT / 'release/office-rebuild/thin-engine-qualification.json').read_text())['build']
    actor = json.loads(subprocess.check_output(['docker', 'inspect', producer]))[0]
    if (actor['State']['Status'] != 'exited' or actor['State']['ExitCode'] != 0 or
            actor['State']['OOMKilled'] or actor['Image'] != build['builderImageId'] or
            not any(row['Source'] == str(cache) and row['Destination'] == '/office' for row in actor['Mounts'])):
        raise ValueError('The completed runtime source producer differs.')
    if inputs.git(cache / 'emsdk', 'rev-parse', 'HEAD').decode().strip() != build['emsdkCommit']:
        raise ValueError('Emsdk checkout changed.')
    installed = cache / 'emsdk/upstream/emscripten'
    if (json.loads(inputs.regular(installed, 'emscripten-version.txt').read_text()) != pin['emscriptenVersion'] or
            inputs.regular(installed, 'emscripten-revision.txt').read_text().strip() != pin['emscriptenRevision'] or
            inputs.regular(cache, 'emsdk/upstream/.emsdk_version').read_text().strip() !=
            'releases-' + pin['sdkReleaseCommit'] + '-64bit'):
        raise ValueError('Installed runtime revision/version changed.')
    if inputs.digest(inputs.regular(cache, 'dist-thin/soffice.wasm')) != build['assets']['soffice.wasm']['sha256']:
        raise ValueError('Completed Office engine changed.')
    preferred = match_source(source_archive, installed, pin)
    response, libraries = link_inputs(cache, pin)
    modules = submodule_scope(cache)
    stage = Path(tempfile.mkdtemp(prefix='.office-runtime-inputs-', dir=output.parent))
    try:
        files = {}
        files['source/emscripten.tar.gz'] = inputs.copy_checked(source_archive,
            stage / 'source/emscripten.tar.gz', pin['sourceArchive']['sha256'])
        for name in pin['standaloneNotices']:
            source = inputs.regular(installed, name)
            files['notices/' + name] = inputs.copy_checked(source, stage / 'notices' / name,
                                                         preferred[name]['sha256'])
        for name, source in [('final-link.rsp', response),
                             ('config_host_lang.mk', inputs.regular(cache, 'build-thin/config_host_lang.mk'))]:
            files['build/' + name] = inputs.copy_checked(source, stage / 'build' / name, inputs.digest(source))
        for name in ['emscripten-version.txt', 'emscripten-revision.txt']:
            source = inputs.regular(installed, name)
            files['release-overlays/' + name] = inputs.copy_checked(source,
                stage / 'release-overlays' / name, inputs.digest(source))
        report = {'schema': 'augmentor-office-runtime-source-inputs/1', 'files': files,
                  'baseSourceManifestSha256': qualification['export']['sourceManifestSha256'],
                  'emscriptenRevision': pin['emscriptenRevision'], 'installedPreferredSources': preferred,
                  'systemLibraryInputHashes': libraries, 'explicitSystemObjects': pin['explicitSystemObjects'],
                  'systemInputScope': 'Inputs named in the final linker response; not per-symbol output provenance',
                  'coreSubmoduleScope': modules, 'sourceArchiveUrl': pin['sourceArchive']['url'],
                  'releaseVersionOverlay': pin['releaseVersionOverlay'],
                  'publicVersionSource': pin['publicVersionSource'],
                  'publicRedistributionQualified': False, 'engineBuildsStarted': 0, 'installedChanges': 0,
                  'remaining': ['Complete source delivery/rebuild and third-party coverage review.',
                                'Representative document/font/resource/security and installed promotion/rollback.']}
        # The public-source comparison also witnesses that preferred inputs stayed exact.
        if (any(inputs.digest(inputs.regular(installed, name)) != row['sha256']
                for name, row in preferred.items()) or link_inputs(cache, pin)[1] != libraries):
            raise ValueError('Runtime inputs changed during export.')
        (stage / 'RUNTIME-SOURCE-INPUTS.json').write_text(json.dumps(report, indent=2) + '\n')
        inputs.publish(stage, output)
        return report
    except BaseException:
        print('Failed private companion retained at ' + str(stage), file=sys.stderr)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['cache', 'source-archive', 'base-source-inputs', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--producer', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    report = collect(args.cache.absolute(), args.producer, args.source_archive.absolute(),
                     args.base_source_inputs.absolute(), args.output.absolute())
    print(json.dumps({'exportedFiles': len(report['files']),
                      'preferredSourcesMatched': len(report['installedPreferredSources']),
                      'linkSystemLibraries': len(report['systemLibraryInputHashes']),
                      'explicitSystemObjects': len(report['explicitSystemObjects']),
                      'emptyCoreSubmodules': len(report['coreSubmoduleScope']['emptySubmodules']),
                      'engineBuildsStarted': 0, 'installedChanges': 0, 'publicRedistributionQualified': False}))
