#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Remove explicitly reviewed, unloadable optional plugins from a staged wheel."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil

WIDGET_MODULES = {'QtCore', 'QtGui', 'QtWidgets', 'QtNetwork', 'QtDBus', 'QtSvg', 'QtTest'}
WIDGET_PLUGINS = {'platforms', 'styles', 'imageformats', 'iconengines', 'tls', 'networkinformation'}
QUICK_MODULES = {'QtQml', 'QtQuick', 'QtQuickWidgets', 'QtOpenGL'}
QUICK_FRAMEWORKS = QUICK_MODULES | {'QtQmlMeta', 'QtQmlModels', 'QtQmlWorkerScript'}
QUICK_IMPORTS = {'QML', 'QtQml', 'QtQml/Models', 'QtQml/WorkerScript', 'QtQuick', 'QtQuick/Window'}


def widgets_only(root, quick_plasma=False):
    """Retain Widgets and, when requested, the small LGPL Quick effect closure.

    No Designer, Quick 3D, Shader Tools compiler or optional QML controls ship.
    The shader compiler runs only at development time; the output is our shader.
    """
    modules = WIDGET_MODULES | (QUICK_MODULES if quick_plasma else set())
    frameworks = WIDGET_MODULES | (QUICK_FRAMEWORKS if quick_plasma else set())
    required = [root/(name+'.abi3.so') for name in modules]
    required += [root/'Qt/lib'/(name+'.framework') for name in frameworks]
    if any(not path.exists() for path in required):
        raise ValueError('Pinned Widgets module is missing; no modules removed')
    remove = [p for p in (root/'Qt/lib').glob('*.framework') if p.stem not in frameworks]
    remove += [p for p in root.glob('Qt*') if p.is_file() and p.name.split('.')[0] not in modules]
    plugins = WIDGET_PLUGINS | ({'scenegraph'} if quick_plasma else set())
    remove += [p for p in (root/'Qt/plugins').iterdir() if p.name not in plugins]
    optional = ['Qt/libexec','Qt/bin','Assistant.app','Designer.app','Linguist.app',
                'lrelease','lupdate','qmlformat','qmllint','qmlls','svgtoqml','qsb']
    if quick_plasma:
        qml = root/'Qt/qml'
        for path in sorted(qml.rglob('*'), key=lambda p: len(p.parts)):
            if not path.is_dir(): continue
            relative = path.relative_to(qml).as_posix()
            if relative not in QUICK_IMPORTS and not any(parent in remove for parent in path.parents):
                remove.append(path)
    else:
        optional += ['Qt/qml', 'libpyside6qml.abi3.6.8.dylib']
    remove += [root/p for p in optional if (root/p).exists()]
    for path in remove:
        if path.is_symlink():raise ValueError('Unexpected link in Qt staging')
    for path in remove:
        if path.is_dir():shutil.rmtree(path)
        else:path.unlink()
    # Fail the build if a retained component links a removed framework.
    binaries = [*root.glob('*.so'), *root.rglob('*.dylib')]
    binaries += [root/'Qt/lib'/(name+'.framework')/'Versions/A'/name for name in frameworks]
    missing = {str(p.relative_to(root)): missing_frameworks(root,p) for p in binaries}
    if any(missing.values()):raise ValueError('Widgets dependency closure is incomplete: '+str(missing))
    return {'frameworks':sorted(frameworks), 'quickPlasma':quick_plasma,
            'removed':[str(p.relative_to(root)) for p in remove]}

def missing_frameworks(root,file):
    result=set()
    for line in subprocess.check_output(['otool','-L',str(file)],text=True).splitlines()[1:]:
        value=line.strip().split(' (',1)[0]
        if value.startswith('@rpath/Qt') and '.framework/' in value:
            if not (root/'Qt/lib'/value.removeprefix('@rpath/')).exists():result.add(value)
    return sorted(result)

def stage(root,policy):
    planned={row['path']:row for row in policy['plugins']};observed={}
    for file in sorted(root.rglob('*.dylib')):
        missing=missing_frameworks(root,file)
        if missing:observed[str(file.relative_to(root))]=missing
    expected={path:row['missingQtFrameworks'] for path,row in planned.items()}
    if observed!=expected:raise ValueError('Qt plugin dependencies differ from the reviewed policy; no files removed')
    removed=[]
    for path in planned:
        file=root/path
        if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):raise ValueError('Unexpected plugin path')
        removed.append({'path':path,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'missingQtFrameworks':observed[path]})
    for row in removed:(root/row['path']).unlink()
    report = {'reason':policy['reason'],'removed':removed,'remainingMissingQtFrameworks':[]}
    if policy.get('widgetsOnly'):report['widgetsOnly'] = widgets_only(root, policy.get('quickPlasma', False))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pyside',type=Path);parser.add_argument('--policy',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();report=stage(args.pyside.resolve(),json.loads(args.policy.read_text()))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
