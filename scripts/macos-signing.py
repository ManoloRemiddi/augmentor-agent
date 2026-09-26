#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Prepare a separately signed/notarized candidate; never install or publish it.

Use --plan for a read-only code inventory. Signing requires a Developer ID
Application identity and an expected Team ID. Notarization credentials must
already be in a Keychain profile, never command-line passwords or repository files.
Product/first-run/license acceptance is separate from Apple's acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile


MACH_MAGICS = {b'\xce\xfa\xed\xfe': '<', b'\xcf\xfa\xed\xfe': '<',
               b'\xfe\xed\xfa\xce': '>', b'\xfe\xed\xfa\xcf': '>'}
FAT_MAGICS = {b'\xca\xfe\xba\xbe': ('>', False), b'\xbe\xba\xfe\xca': ('<', False),
              b'\xca\xfe\xba\xbf': ('>', True), b'\xbf\xba\xfe\xca': ('<', True)}


def binary_type(path):
    """Read actual Mach-O file types, including fat binaries; don't trust suffixes."""
    with path.open('rb') as stream:
        magic = stream.read(4)
        if magic in MACH_MAGICS:
            stream.seek(12)
            return struct.unpack(MACH_MAGICS[magic]+'I', stream.read(4))[0]
        if magic not in FAT_MAGICS:
            return None
        endian, wide = FAT_MAGICS[magic]
        count = struct.unpack(endian+'I', stream.read(4))[0]
        if not 1 <= count <= 16:
            raise ValueError('Invalid universal binary: '+str(path))
        types = set()
        for index in range(count):
            stream.seek(8 + index*(32 if wide else 20) + 8)
            offset = struct.unpack(endian+('Q' if wide else 'I'), stream.read(8 if wide else 4))[0]
            stream.seek(offset)
            slice_magic = stream.read(4)
            if slice_magic not in MACH_MAGICS:
                raise ValueError('Invalid universal Mach-O slice: '+str(path))
            stream.seek(offset+12)
            types.add(struct.unpack(MACH_MAGICS[slice_magic]+'I', stream.read(4))[0])
        if len(types) != 1:
            raise ValueError('Inconsistent universal Mach-O types: '+str(path))
        return types.pop()


def framework_version(path):
    versions = path/'Versions'
    actual = [p for p in versions.iterdir() if p.is_dir() and not p.is_symlink()]
    if len(actual) != 1:
        raise ValueError('Expected a single framework version: '+str(path))
    current = versions/'Current'
    if (current.exists() or current.is_symlink()) and current.resolve() != actual[0].resolve():
        raise ValueError('Unexpected current framework version: '+str(path))
    return actual[0]


def normalize_frameworks(app):
    """Restore symlinks omitted by wheel ZIPs, in the disposable signing copy only."""
    for path in sorted(app.rglob('*.framework')):
        if path.is_symlink():
            continue
        version = framework_version(path)
        metadata = plistlib.loads((version/'Resources/Info.plist').read_bytes())
        if Path(metadata['CFBundleExecutable']).name != metadata['CFBundleExecutable']:
            raise ValueError('Invalid framework executable name.')
        for name in ('Resources', metadata['CFBundleExecutable']):
            target, original = path/name, version/name
            if target.is_symlink():
                if target.resolve() != original.resolve():
                    raise ValueError('Unexpected framework link: '+str(target))
                continue
            if target.exists():
                if not target.is_dir() or name != 'Resources':
                    raise ValueError('Unexpected duplicate framework executable: '+str(target))
                # Wheel resources may be duplicated; discard only an exact copy.
                def contents(directory):
                    result = {}
                    for item in directory.rglob('*'):
                        if item.is_symlink():
                            raise ValueError('Unexpected link in duplicate framework resources.')
                        if item.is_file():
                            result[item.relative_to(directory).as_posix()] = item.read_bytes()
                    return result
                if contents(target) != contents(original):
                    raise ValueError('Framework resources differ: '+str(target))
                shutil.rmtree(target)
            target.symlink_to('Versions/Current/'+name)
        current = path/'Versions/Current'
        if not current.is_symlink():
            current.symlink_to(version.name, target_is_directory=True)


def signing_plan(app):
    app = app.resolve(strict=True)
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') not in ('com.augmentor.Agent', 'com.augmentor.Agent.Companion'):
        raise ValueError('Expected an Augmentor application bundle.')
    if not re.fullmatch(r'\d+\.\d+\.\d+', info.get('CFBundleShortVersionString', '')):
        raise ValueError('Expected a numeric three-part application version.')
    paths = sorted(app.rglob('*'))
    binaries = {}
    bundles = {app: app/'Contents/MacOS'/info['CFBundleExecutable']}
    for path in paths:
        if path.is_symlink():
            if not path.resolve(strict=True).is_relative_to(app):
                raise ValueError('Bundle link escapes the app: '+str(path.relative_to(app)))
            continue
        if path.is_file():
            kind = binary_type(path)
            if kind is not None:
                if kind not in (2, 6, 8):  # MH_EXECUTE, MH_DYLIB, MH_BUNDLE
                    raise ValueError('Unsupported Mach-O file type: '+str(path.relative_to(app)))
                binaries[path] = kind
        if path.is_dir() and path.suffix == '.framework':
            version = framework_version(path)
            framework_info = plistlib.loads((version/'Resources/Info.plist').read_bytes())
            bundles[path] = version/framework_info['CFBundleExecutable']
        elif path.is_dir() and path.suffix in ('.app', '.xpc', '.bundle'):
            nested_info = path/'Contents/Info.plist'
            if nested_info.is_file():
                metadata = plistlib.loads(nested_info.read_bytes())
                executable = metadata.get('CFBundleExecutable')
                if executable:
                    bundles[path] = path/'Contents/MacOS'/executable
    for bundle, executable in bundles.items():
        if executable.resolve() not in binaries:
            raise ValueError('Bundle executable is missing or not Mach-O: '+str(bundle))
    bundle_executables = {executable.resolve() for executable in bundles.values()}
    targets = {path: {'kind': 'binary', 'executable': kind == 2}
               for path, kind in binaries.items() if path not in bundle_executables}
    targets.update({path: {'kind': 'bundle', 'executable': binaries[executable.resolve()] == 2}
                    for path, executable in bundles.items()})
    steps = []
    for path in sorted(targets, key=lambda p: (-len(p.parts), str(p))):
        relative = path.relative_to(app).as_posix()
        steps.append({'path': relative, **targets[path],
                      # The bundled Node runtime needs V8 executable memory.
                      # No blanket get-task-allow or library-validation exception.
                      'entitlements': {'com.apple.security.cs.allow-jit': True}
                      if relative == 'Contents/Resources/app/node/bin/node' else {}})
    return {'schema': 'augmentor-macos-signing-plan/1', 'bundleId': info['CFBundleIdentifier'],
            'version': info['CFBundleShortVersionString'], 'steps': steps,
            'machOFiles': [p.relative_to(app).as_posix() for p in sorted(binaries)],
            'publicReleaseReady': False}


def run(*args, **kwargs):
    kwargs.setdefault('check', True)
    return subprocess.run([str(arg) for arg in args], **kwargs)


def capture(*args):
    return run(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def validate_identity(identity, team):
    if not re.fullmatch(r'[A-Fa-f0-9]{40}', identity) or not re.fullmatch(r'[A-Z0-9]{10}', team):
        raise ValueError('Use the certificate SHA-1 identity and ten-character Apple Team ID.')
    identities = capture('security', 'find-identity', '-v', '-p', 'codesigning').stdout
    matching = [line for line in identities.splitlines() if identity.upper() in line.upper()]
    if len(matching) != 1 or '"Developer ID Application:' not in matching[0] or f'({team})"' not in matching[0]:
        raise ValueError('The expected valid Developer ID Application identity is not available in Keychain.')


def sign_code(app, plan, identity, team, evidence):
    for number, step in enumerate(plan['steps']):
        path = app/step['path']
        command = ['codesign', '--force', '--sign', identity, '--timestamp', '--options', 'runtime',
                   '--generate-entitlement-der']
        with tempfile.TemporaryDirectory(prefix='entitlements-', dir=evidence) as folder:
            if step['entitlements']:
                entitlements = Path(folder)/'entitlements.plist'
                entitlements.write_bytes(plistlib.dumps(step['entitlements']))
                command += ['--entitlements', str(entitlements)]
            run(*command, path, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f'Signed code item {number+1}/{len(plan["steps"])}', flush=True)
    # Verify every binary too: resources-positioned code is not necessarily
    # visited by codesign's --deep bundle traversal.
    evidence_rows = []
    for relative in [*plan['machOFiles'], '.']:
        path = app/relative
        run('codesign', '--verify', '--strict', path, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        details = capture('codesign', '--display', '--verbose=4', path).stderr
        if f'TeamIdentifier={team}\n' not in details or 'Authority=Developer ID Application:' not in details:
            raise ValueError('A code item has an unexpected signing authority: '+relative)
        if 'Timestamp=' not in details or '(runtime)' not in details:
            raise ValueError('A code item lacks secure timestamp or hardened runtime: '+relative)
        evidence_rows.append({'path': relative, 'teamId': team, 'timestamped': True, 'hardenedRuntime': True})
    run('codesign', '--verify', '--deep', '--strict', app)
    write_json(evidence/'signature-verification.json', evidence_rows)


def notarize(path, profile, evidence, label):
    """Persist the submission ID before waiting, so an interrupted run is traceable."""
    result = capture('xcrun', 'notarytool', 'submit', path, '--keychain-profile', profile, '--output-format', 'json')
    submission = json.loads(result.stdout)
    write_json(evidence/(label+'-submission.json'), submission)
    identifier = submission['id']
    if not re.fullmatch(r'[a-fA-F0-9-]{36}', identifier):
        raise ValueError('Apple returned an invalid notarization submission ID.')
    waiting = run('xcrun', 'notarytool', 'wait', identifier, '--keychain-profile', profile,
                  '--output-format', 'json', '--timeout', '30m',
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    # Always retain Apple's log, including rejected submissions. A timeout must
    # not be retried as an unrelated new submission without checking this ID.
    run('xcrun', 'notarytool', 'log', identifier, '--keychain-profile', profile,
        evidence/(label+'-notary-log.json'))
    status = json.loads(waiting.stdout)
    write_json(evidence/(label+'-result.json'), status)
    log = json.loads((evidence/(label+'-notary-log.json')).read_text())
    if waiting.returncode != 0 or status.get('status') != 'Accepted' or log.get('status') != 'Accepted':
        raise ValueError('Apple has not accepted this submission; inspect the saved notarization evidence.')
    if log.get('issues'):
        raise ValueError('Apple returned notarization issues; review the saved log before distribution.')
    return identifier


def prepare(source, out, identity, team, profile):
    if sys.platform != 'darwin':
        raise ValueError('Signing and notarization require macOS.')
    if out.exists():
        raise ValueError('Choose a new output directory; previous evidence must not be overwritten.')
    source = source.resolve(strict=True)
    if out.resolve().is_relative_to(source):
        raise ValueError('Output cannot be inside the source application.')
    plan = signing_plan(source)
    validate_identity(identity, team)
    run('codesign', '--verify', '--deep', '--strict', source)
    out.mkdir(parents=True, mode=0o700)
    stage = out/'candidate.noindex'; stage.mkdir(mode=0o700)
    app = stage/source.name
    run('ditto', source, app)
    normalize_frameworks(app)
    plan = signing_plan(app)
    write_json(out/'signing-plan.json', plan)
    sign_code(app, plan, identity, team, out)
    # Signing is a candidate qualification stage, never a publication signal.
    report = {'schema': 'augmentor-macos-signed-candidate/1', 'version': plan['version'],
              'bundleId': plan['bundleId'], 'teamId': team, 'signedForDistribution': True,
              'notarized': False, 'publicReleaseReady': False,
              'remainingAcceptance': 'Product setup, licensing, signed runtime and installed release acceptance.'}
    inventory = source/'Contents/Resources/app/application-inventory.json'
    if inventory.is_file():
        report['sourceApplicationInventorySha256'] = hashlib.sha256(inventory.read_bytes()).hexdigest()
    write_json(out/'candidate.json', report)
    if not profile:
        return report
    archive = out/'notarization-upload.zip'
    run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', app, archive)
    report['appSubmission'] = notarize(archive, profile, out, 'app')
    run('xcrun', 'stapler', 'staple', app)
    run('xcrun', 'stapler', 'validate', app)
    run('codesign', '--verify', '--deep', '--strict', app)
    run('spctl', '--assess', '--type', 'execute', '--verbose=2', app)
    archive.unlink()
    # Staple the app before creating the final image, then notarize/staple the
    # image too. Users copying the app off an image retain its own offline ticket.
    (stage/'Applications').symlink_to('/Applications', target_is_directory=True)
    component = 'companion' if plan['bundleId'].endswith('.Companion') else 'desktop'
    dmg = out/f'augmentor-{component}-{plan["version"]}-macos-arm64-candidate.dmg'
    run('hdiutil', 'create', '-quiet', '-volname', 'Augmentor Agent', '-srcfolder', stage,
        '-format', 'UDZO', dmg)
    run('codesign', '--sign', identity, '--timestamp', dmg)
    report['dmgSubmission'] = notarize(dmg, profile, out, 'dmg')
    run('xcrun', 'stapler', 'staple', dmg)
    run('xcrun', 'stapler', 'validate', dmg)
    run('hdiutil', 'verify', '-quiet', dmg)
    run('spctl', '--assess', '--type', 'open', '--context', 'context:primary-signature', '--verbose=2', dmg)
    with dmg.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    report.update(notarized=True, artifact=dmg.name, sha256=checksum, bytes=dmg.stat().st_size)
    write_json(out/'candidate.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    parser.add_argument('--plan', action='store_true', help='Read-only inventory, no credentials required')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--identity', help='Developer ID Application certificate SHA-1')
    parser.add_argument('--team-id')
    parser.add_argument('--notary-profile', help='Existing Keychain credential profile (no secrets in arguments)')
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(signing_plan(args.app), indent=2)); return
    if not all((args.out, args.identity, args.team_id)):
        parser.error('Signing requires --out, --identity and --team-id.')
    os.umask(0o077)
    print(json.dumps(prepare(args.app, args.out, args.identity, args.team_id, args.notary_profile)))


if __name__ == '__main__':
    main()
