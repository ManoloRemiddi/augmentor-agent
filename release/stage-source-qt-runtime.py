# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage a separate Qt 6.8.2 runtime candidate with an explicit plugin/QML scope.

Records static ELF closure, not complete dynamic or licensing qualification.
Never copies the build SDK or mutates the producer prefix.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

MODULES=('Core','Gui','Widgets','Network','DBus','Svg','OpenGL','Qml','Quick','QuickWidgets','Test')
PLUGIN_DIRS=('wayland-graphics-integration-client','iconengines','platforminputcontexts',
    'xcbglintegrations','wayland-decoration-client','tls','networkinformation','imageformats',
    'wayland-shell-integration','platformthemes')
PLATFORMS=('libqxcb.so','libqwayland-egl.so','libqwayland-generic.so','libqoffscreen.so','libqminimal.so')
QML_DIRS=('QML','QtQuick','QtQml','QtQml/Models','QtQml/WorkerScript')


def dynamic(path):
    result=subprocess.run(['readelf','-d',str(path)],text=True,capture_output=True,check=True,timeout=10).stdout
    return {'needed':re.findall(r'\(NEEDED\).*?\[([^\]]+)\]',result),
        'soname':re.findall(r'\(SONAME\).*?\[([^\]]+)\]',result),
        'paths':re.findall(r'\((?:RUNPATH|RPATH)\).*?\[([^\]]+)\]',result)}


def stage(prefix,destination):
    prefix=prefix.resolve(strict=True)
    if destination.exists():raise RuntimeError('Use a new separate runtime output path.')
    if destination.resolve().is_relative_to(prefix):raise RuntimeError('Runtime must be separate from the producer prefix.')
    libraries={};metadata={}
    for path in (prefix/'lib').glob('libQt6*.so.6.8.2'):
        if not path.resolve(strict=True).is_relative_to(prefix):raise RuntimeError('Producer library escapes the prefix.')
        values=dynamic(path)
        if len(values['soname'])!=1:raise RuntimeError('Qt library SONAME is missing or ambiguous.')
        soname=values['soname'][0]
        if soname in libraries:raise RuntimeError('Qt library SONAME is duplicated.')
        libraries[soname]=path;metadata[soname]=values
    selected=set();queue=['libQt6'+name+'.so.6' for name in MODULES];resources=[]
    for directory in PLUGIN_DIRS:
        folder=prefix/'plugins'/directory
        files=sorted(path for path in folder.iterdir() if path.is_file())
        if not files:raise RuntimeError('Required plugin directory is empty: '+directory)
        resources.extend(files)
    for name in PLATFORMS:resources.append(prefix/'plugins/platforms'/name)
    # These are immediate module members, never recursive copies of QtQuick
    # controls/test/tooling or other unrequested modules.
    for directory in QML_DIRS:
        folder=prefix/'qml'/directory
        if not (folder/'qmldir').is_file():raise RuntimeError('Required QML module is missing: '+directory)
        resources.extend(sorted(path for path in folder.iterdir() if path.is_file()))
    for path in resources:
        if not path.resolve(strict=True).is_relative_to(prefix):raise RuntimeError('Producer resource escapes the prefix.')
        with path.open('rb') as handle:is_elf=handle.read(4)==b'\x7fELF'
        if is_elf:queue.extend(name for name in dynamic(path)['needed'] if name.startswith('libQt6'))
    while queue:
        name=queue.pop()
        if name in selected:continue
        if name not in libraries:raise RuntimeError('Required Qt library is absent: '+name)
        if name in ('libQt6QmlCompiler.so.6','libQt6QuickControlsTestUtils.so.6','libQt6QuickTestUtils.so.6'):
            raise RuntimeError('Runtime closure reaches a prohibited build/test component: '+name)
        selected.add(name);queue.extend(item for item in metadata[name]['needed'] if item.startswith('libQt6'))
    paths=sorted(set(resources+[libraries[name] for name in selected]))
    # Complete validation before creating the output. Keep any later partial
    # output for diagnosis and require a new path on retry.
    destination.mkdir(mode=0o700,parents=False);inventory=[];external=set()
    for source in paths:
        relative=source.relative_to(prefix);target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        data=target.read_bytes();entry={'path':str(relative),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        if data[:4]==b'\x7fELF':
            entry['dynamic']=dynamic(target);external.update(name for name in entry['dynamic']['needed'] if not name.startswith('libQt6'))
        inventory.append(entry)
    links=[]
    for name in sorted(selected):
        target=destination/'lib'/name;target.symlink_to(libraries[name].name)
        links.append({'path':str(target.relative_to(destination)),'target':libraries[name].name})
    report={'format':'augmentor-source-qt-runtime-stage/1','qtVersion':'6.8.2',
        'toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'qtSonames':sorted(selected),'externalSonames':sorted(external),'files':inventory,'symlinks':links,
        'qmlModuleScope':list(QML_DIRS),'producerBytesChanged':False,
        'dynamicClosureQualified':False,'licenseReviewComplete':False,'publicReleaseQualified':False}
    (destination/'stage-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();report=stage(args.prefix,args.destination)
    print(json.dumps({key:report[key] for key in ('qtSonames','externalSonames','dynamicClosureQualified','licenseReviewComplete')},indent=2))


if __name__=='__main__':main()
