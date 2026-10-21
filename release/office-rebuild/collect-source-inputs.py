#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Export verified inputs/notices from the completed ThinLTO diagnostic, privately.

This does not qualify corresponding-source completeness, replace the default
engine, fetch anything, restart the builder or approve public redistribution.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from dsh_project_bundle import publish


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(root, name):
    relative = PurePosixPath(name)
    if (relative.is_absolute() or '..' in relative.parts or '\\' in name or
            relative.as_posix() != name):
        raise ValueError('Unsafe source input path: ' + name)
    path = root / name
    if (path.is_symlink() or not path.is_file() or root.is_symlink() or
            any(parent.is_symlink() for parent in path.parents if parent != root.parent) or
            not path.resolve().is_relative_to(root.resolve())):
        raise ValueError('Missing, linked or non-regular input: ' + name)
    return path


def constants(text):
    """Read literal upstream assignments; never evaluate Make or shell code."""
    values = {}
    for line in text.splitlines():
        match = re.fullmatch(r'([A-Z][A-Z0-9_]*)\s*:?=\s*(.*?)\s*', line)
        if match:
            if match[1] in values:
                raise ValueError('Duplicate upstream constant: ' + match[1])
            values[match[1]] = match[2]
    return values


def expand(value, values):
    for _ in range(16):
        if '$' not in value:
            return value
        changed = re.sub(r'\$\(([A-Z][A-Z0-9_]*)\)',
                         lambda match: values[match[1]], value)
        if changed == value:
            break
        value = changed
    raise ValueError('Unsupported or cyclic upstream constant; never evaluated.')


def external_pins(text):
    values = constants(text)
    pins = {}
    for key, value in values.items():
        if not key.endswith(('_TARBALL', '_TTF')):
            continue
        name = expand(value, values)
        sha = expand(values[key.rsplit('_', 1)[0] + '_SHA256SUM'], values)
        if (not re.fullmatch(r'[a-zA-Z0-9_.+-]+', name) or name in ('.', '..') or
                not re.fullmatch(r'[a-f0-9]{64}', sha) or name in pins):
            raise ValueError('Invalid or ambiguous upstream external identity.')
        pins[name] = {'variable': key, 'sha256': sha}
    if not pins:
        raise ValueError('No external source pins found.')
    return pins


def copy_checked(source, target, expected):
    """Verify copied bytes, without replacing or linking an existing destination."""
    if source.is_symlink() or not source.is_file() or digest(source) != expected:
        raise ValueError('Source changed before copy: ' + source.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as incoming, target.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    if digest(target) != expected or digest(source) != expected:
        raise ValueError('Source changed during copy: ' + source.name)
    return {'bytes': target.stat().st_size, 'sha256': expected}


def git(directory, *args):
    return subprocess.check_output(['git', *args], cwd=directory)


def archive_commit(source, target):
    # Read Git blobs directly. `git archive` honours export-ignore and can omit
    # preferred source (Core's schema files), so it is insufficient here.
    rows = git(source, 'ls-tree', '-rz', 'HEAD').split(b'\0')
    with target.open('xb') as output:
        process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=source,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            with gzip.GzipFile(filename='', mode='wb', fileobj=output,
                               compresslevel=1, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode='w|') as archive:
                    for row in filter(None, rows):
                        metadata, name = row.split(b'\t', 1)
                        mode, kind, oid = metadata.split(b' ')
                        if kind == b'commit':
                            continue  # The manifest records excluded gitlinks.
                        if kind != b'blob' or mode not in (b'100644', b'100755', b'120000'):
                            raise ValueError('Unexpected committed source entry.')
                        process.stdin.write(oid + b'\n')
                        process.stdin.flush()
                        identity = process.stdout.readline().split()
                        if len(identity) != 3 or identity[:2] != [oid, b'blob']:
                            raise ValueError('Git source blob unavailable.')
                        size = int(identity[2])
                        item = tarfile.TarInfo(os.fsdecode(name))
                        item.mode = int(mode, 8) & 0o777
                        if mode == b'120000':
                            item.type = tarfile.SYMTYPE
                            item.linkname = os.fsdecode(process.stdout.read(size))
                            archive.addfile(item)
                        else:
                            item.size = size
                            archive.addfile(item, process.stdout)
                        if process.stdout.read(1) != b'\n':
                            raise ValueError('Incomplete Git source blob.')
            process.stdin.close()
            if process.wait(timeout=30) != 0:
                raise ValueError('Committed-source archive failed.')
        finally:
            if not process.stdin.closed:
                process.stdin.close()
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()
    return {'bytes': target.stat().st_size, 'sha256': digest(target)}


def regenerate_license(cache, configuration, image, stylesheet):
    command = ['docker', 'run', '--rm', '--network=none', '--read-only',
               '--memory=268435456', '--memory-swap=268435456', '--cpus=1',
               '--pids-limit=32', '--cap-drop=ALL', '--security-opt=no-new-privileges',
               '--user=' + str(os.getuid()) + ':' + str(os.getgid()),
               '--mount', 'type=bind,src=' + str(cache / 'core/readlicense_oo/license') +
               ',dst=/input,readonly', '--entrypoint', '/usr/bin/xsltproc', image,
               '--nonet', '--novalid', '--stringparam', 'build_type', configuration['BUILD_TYPE'],
               '--stringparam', 'os', configuration['OS'], '--stringparam', 'themes',
               configuration['WITH_THEMES']]
    if not configuration['MPL_SUBSET']:
        command += ['--stringparam', 'no_mpl_subset', 'no_mpl_subset']
    command += ['/input/' + stylesheet, '/input/license.xml']
    return subprocess.run(command, check=True, capture_output=True, timeout=30).stdout


def collect(cache, producer, output):
    if not sys.platform.startswith('linux'):
        raise ValueError('This diagnostic export currently requires Linux.')
    outputs = (ROOT / 'outputs').resolve()
    if (output.parent != outputs or output.parent.is_symlink() or
            output.exists() or output.is_symlink()):
        raise ValueError('Choose a new direct child of repository outputs/.')
    if cache.is_symlink() or not cache.is_dir():
        raise ValueError('Use the real completed build cache.')
    expected = json.loads((ROOT / 'release/office-rebuild/thin-engine-qualification.json').read_text())['build']
    environment = json.loads((ROOT / 'release/office-rebuild/environment.json').read_text())
    inspected = json.loads(subprocess.check_output(['docker', 'inspect', producer]))[0]
    state = inspected['State']
    if (state['Status'] != 'exited' or state['ExitCode'] != 0 or state['OOMKilled'] or
            inspected['Image'] != expected['builderImageId'] or
            not any(row['Source'] == str(cache) and row['Destination'] == '/office'
                    for row in inspected['Mounts'])):
        raise ValueError('The completed source producer identity differs.')
    for directory, commit in [('core', expected['coreCommit']), ('emsdk', expected['emsdkCommit'])]:
        if git(cache / directory, 'rev-parse', 'HEAD').decode().strip() != commit:
            raise ValueError('Source checkout revision changed: ' + directory)
    patch = git(cache / 'core', 'diff', '--binary', 'HEAD', '--')
    if hashlib.sha256(patch).hexdigest() != expected['rawSourceDiffSha256']:
        raise ValueError('Patched Core source differs from the built source.')
    for name, item in expected['assets'].items():
        if digest(regular(cache, 'dist-thin/' + name)) != item['sha256']:
            raise ValueError('Built engine asset changed: ' + name)
    for name, sha in [('run-thin-lto.sh', environment['thinLtoExperiment']['driverSha256']),
                      ('thin-linker-resources.patch', environment['thinLtoExperiment']['additionalPatchSha256']),
                      ('thin-resource-profile.json', expected['resourceProfileSha256'])]:
        if digest(regular(cache, name)) != sha:
            raise ValueError('Build resource input changed: ' + name)
    configuration = {}
    for line in regular(cache, 'build-thin/config_host.mk').read_text().splitlines():
        if '=' in line:
            key, value = line.removeprefix('export ').split('=', 1)
            configuration[key] = value
    notices = {}
    for name, stylesheet in [('LICENSE', 'license_plain_text.xsl'), ('LICENSE.html', 'license_html.xsl')]:
        actual = regular(cache, 'build-thin/instdir/' + name).read_bytes()
        regenerated = regenerate_license(cache, configuration, expected['builderImageId'], stylesheet)
        if actual != regenerated:
            raise ValueError('Generated licence text does not reproduce: ' + name)
        notices[name] = hashlib.sha256(actual).hexdigest()
    pins = external_pins(regular(cache, 'core/download.lst').read_text())
    archives = []
    for source in sorted((cache / 'tarballs').iterdir()):
        if source.is_symlink():
            raise ValueError('Linked external input: ' + source.name)
        if source.is_dir() or source.name == 'fetch.log':
            continue
        if (source.name not in pins or source.is_symlink() or not source.is_file() or
                source.stat().st_size > 256 * 1024 * 1024 or digest(source) != pins[source.name]['sha256']):
            raise ValueError('Unpinned, changed or linked external input: ' + source.name)
        archives.append({'name': source.name, 'bytes': source.stat().st_size, **pins[source.name]})
    if not 0 < len(archives) <= 128 or sum(row['bytes'] for row in archives) > 512 * 1024 * 1024:
        raise ValueError('External input inventory exceeds diagnostic bounds.')
    versions = {}
    for source in sorted((cache / 'build-thin/workdir/UnpackedTarball').glob('*.version')):
        value = regular(source.parent, source.name).read_text()
        name = value.removeprefix('/office/tarballs/')
        if value == name or name not in {row['name'] for row in archives}:
            raise ValueError('An unpacked source has no retained pinned input.')
        versions[source.stem] = name
    stage = Path(tempfile.mkdtemp(prefix='.office-source-inputs-', dir=outputs))
    try:
        files = {}
        for row in archives:
            target = 'external/' + row['name']
            files[target] = copy_checked(cache / 'tarballs' / row['name'], stage / target, row['sha256'])
        for name in ['LICENSE', 'LICENSE.html', 'NOTICE']:
            source = regular(cache, 'build-thin/instdir/' + name)
            files['notices/' + name] = copy_checked(source, stage / 'notices' / name, digest(source))
        for name in ['download.lst', 'readlicense_oo/license/license.xml',
                     'readlicense_oo/license/license_plain_text.xsl',
                     'readlicense_oo/license/license_html.xsl', 'readlicense_oo/CustomTarget_license.mk']:
            source = regular(cache, 'core/' + name)
            files['source-reference/' + name] = copy_checked(source, stage / 'source-reference' / name, digest(source))
        for name in ['autogen.input', 'config_host.mk', 'dsh-build-identity.json', 'dsh-wasm-build.json']:
            source = regular(cache, 'build-thin/' + name)
            files['build/' + name] = copy_checked(source, stage / 'build' / name, digest(source))
        recipe = (cache / 'recipe').resolve()
        recipe_pins = json.loads((ROOT / 'release/office-engine-linux-wasm.json').read_text())['files']
        for name, sha in recipe_pins.items():
            if name.startswith('sources/'):
                relative = name.removeprefix('sources/')
                source = regular(recipe, relative)
                files['recipe/' + relative] = copy_checked(source, stage / 'recipe' / relative, sha)
        for name in ['run-thin-lto.sh', 'thin-linker-resources.patch', 'thin-resource-profile.json']:
            source = regular(cache, name)
            files['build/' + name] = copy_checked(source, stage / 'build' / name, digest(source))
        name = 'engine/wasm-source/patches/0032-augmentor-linker-resources.patch'
        source = regular(recipe, name)
        files['recipe/' + name] = copy_checked(source, stage / 'recipe' / name, digest(source))
        (stage / 'source').mkdir()
        (stage / 'source/core-changes.patch').write_bytes(patch)
        files['source/core-changes.patch'] = {'bytes': len(patch), 'sha256': hashlib.sha256(patch).hexdigest()}
        for name in ['core', 'emsdk']:
            target = 'source/' + name + '.tar.gz'
            files[target] = archive_commit(cache / name, stage / target)
        gitlinks = [line for line in git(cache / 'core', 'ls-tree', 'HEAD').decode().splitlines()
                    if line.startswith('160000 ')]
        report = {'schema': 'augmentor-office-source-inputs/1',
                  'scope': 'Private source-input/notice export for the completed ThinLTO diagnostic; not a release',
                  'coreCommit': expected['coreCommit'], 'emsdkCommit': expected['emsdkCommit'],
                  'engineWasmSha256': expected['assets']['soffice.wasm']['sha256'],
                  'builderImageId': expected['builderImageId'], 'files': files,
                  'externals': archives, 'unpackedSourceReceipts': versions,
                  'noticeReproduction': notices, 'coreGitlinksNotArchived': gitlinks,
                  'sourceBundlesAreCommittedSnapshotsPlusSeparatePatch': True,
                  'publicRedistributionQualified': False, 'defaultEngineChanged': False,
                  'remaining': ['Emscripten/runtime/toolchain source and third-party notice coverage.',
                                'Submodule inclusion/exclusion and full source-closure/rebuild proof.',
                                'Representative document/font/resource/security and installed/rollback qualification.',
                                'Public source delivery and final packaging approval.']}
        (stage / 'SOURCE-INPUTS.json').write_text(json.dumps(report, indent=2) + '\n')
        # Revalidate mutable source receipts before publishing the new private directory.
        if (git(cache / 'core', 'diff', '--binary', 'HEAD', '--') != patch or
                any(digest(regular(cache, 'tarballs/' + row['name'])) != row['sha256'] for row in archives)):
            raise ValueError('Source inputs changed during export.')
        publish(stage, output)
        return report
    except BaseException:
        print('Failed private export retained at ' + str(stage), file=sys.stderr)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--producer', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    result = collect(args.cache.absolute(), args.producer, args.output.absolute())
    print(json.dumps({'externalInputs': len(result['externals']),
                      'unpackedSourceReceipts': len(result['unpackedSourceReceipts']),
                      'exportedFiles': len(result['files']), 'generatedNoticesReproduce': True,
                      'publicRedistributionQualified': False, 'defaultEngineChanged': False}))
