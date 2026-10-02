#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build exact Qt/PySide sources in the marked isolated Noble builder.

No recipient runtime is staged or selected. A completed build is not a license,
closure, rebuild, replacement or product qualification result. Failed and partial
build directories are retained and never silently resumed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=Path('/inputs'))
    parser.add_argument('--root',type=Path,default=Path('/work/runtime-build'))
    args=parser.parse_args()
    assert os.geteuid()==1001 and os.environ.get('USER')=='augmentor-proof'
    assert Path('/.dockerenv').is_file()
    assert Path('/etc/augmentor-source-build-container').read_text()=='Owned Augmentor Noble Qt source builder; no application installation\n'
    release=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    assert release['ID'].strip('"')=='ubuntu' and release['VERSION_ID'].strip('"')=='24.04'
    assert sys.version_info[:2]==(3,12) and not Path('/usr/lib/augmentor').exists()
    inputs=args.inputs.resolve();assert inputs==Path('/inputs')
    root=args.root.absolute();assert root.parent==Path('/work') and not root.exists() and not root.is_symlink()
    policy=inputs/'linux-lgpl-runtime-sources.json';value=json.loads(policy.read_text())
    assert value['format']=='augmentor-linux-source-runtime-acquisition/1'
    order=['qtbase','qtshadertools','qtsvg','qtimageformats','qtdeclarative','qtwayland','pyside-setup']
    assert value['buildOrder']==order and len(value['sources'])==7
    for row in value['sources']:
        path=inputs/row['file'];assert path.parent==inputs and path.is_file() and not path.is_symlink()
        assert sha(path)==row['sha256']
    root.mkdir();sources=root/'sources';sources.mkdir();builds=root/'builds';builds.mkdir()
    prefix=root/'qt-prefix';logs=root/'logs';logs.mkdir()
    report={'format':'augmentor-linux-source-runtime-build/1','policySha256':sha(policy),
        'toolSha256':sha(Path(__file__)),'dependencyInventorySha256':sha(inputs/'build-package-versions.txt'),
        'sources':{},'commands':[],'runtimeBuilt':False,'runtimeClosureTested':False,
        'licenseReviewComplete':False,'correspondingSourceRebuildTested':False,
        'recipientReplacementTested':False,'publicReleaseQualified':False,'ownerStateChanged':False}
    def save():
        tmp=root/'build.json.tmp';tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(root/'build.json')
    save()
    for row in value['sources']:
        with tarfile.open(inputs/row['file']) as archive:
            names={member.name.split('/')[0] for member in archive.getmembers()}
            assert len(names)==1 and next(iter(names)).startswith(row['name']+'-everywhere-src-')
            archive.extractall(sources,filter='data')
        source=sources/next(iter(names));assert source.is_dir()
        report['sources'][row['name']]={'sourceDirectory':str(source),'archiveSha256':row['sha256'],
            'reviewedGitCommit':row['reviewedGitCommit'],'archiveToGitTreeEqualityVerified':False}
        save()
    env={**os.environ,'CMAKE_BUILD_PARALLEL_LEVEL':'2','LLVM_INSTALL_DIR':'/usr/lib/llvm-18'}
    def run(module,phase,command,cwd):
        logfile=logs/(module+'-'+phase+'.log')
        record={'module':module,'phase':phase,'argv':list(map(str,command)),'cwd':str(cwd),'completed':False}
        report['commands'].append(record);save();print(module,phase,flush=True)
        with logfile.open('xb') as stream:
            result=subprocess.run(record['argv'],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        record.update(exit=result.returncode,logSha256=sha(logfile));save()
        if result.returncode:raise RuntimeError(module+' '+phase+' failed; retain exact partial tree and log.')
        record['completed']=True;save()
    try:
        for module in order[:-1]:
            source=Path(report['sources'][module]['sourceDirectory']);build=builds/module;build.mkdir()
            if module=='qtbase':
                command=[source/'configure','-prefix',prefix,'-shared','-release','-nomake','tests','-nomake','examples',
                    '-feature-testlib','-feature-dbus','-feature-wayland','-feature-accessibility',
                    '-feature-accessibility-atspi-bridge','-icu','-xcb','-opengl','desktop','-egl',
                    '-openssl-linked','-fontconfig',
                    '-system-zlib','-system-pcre','-system-doubleconversion','-system-freetype',
                    '-system-harfbuzz','-system-libpng','-system-libjpeg','--','-GNinja']
            else:
                command=[prefix/'bin/qt-configure-module',source]
                if module=='qtimageformats':command+=['-system-tiff','-system-webp']
                if module=='qtwayland':command+=['-feature-wayland-client','-no-feature-wayland-server']
                command+=['--','-GNinja','-DCMAKE_BUILD_TYPE=Release','-DQT_BUILD_TESTS=OFF','-DQT_BUILD_EXAMPLES=OFF']
            run(module,'configure',command,build)
            if module=='qtbase':
                cache=dict(line.split('=',1) for line in (build/'CMakeCache.txt').read_text().splitlines()
                    if '=' in line and not line.startswith(('#','//')))
                required=['testlib','dbus','wayland','accessibility','accessibility_atspi_bridge',
                    'icu','xcb','xcb_glx','egl','openssl','openssl_linked','fontconfig',
                    'system_zlib','system_pcre2','system_doubleconversion',
                    'system_freetype','system_harfbuzz','system_png','system_jpeg']
                report['qtbaseRequiredFeatures']={name:cache.get('QT_FEATURE_'+name+':INTERNAL') for name in required}
                save()
                assert all(v=='ON' for v in report['qtbaseRequiredFeatures'].values()), 'A required Qt feature or system-library choice is disabled/missing.'
            run(module,'compile',['cmake','--build','.', '--parallel','2'],build)
            run(module,'install',['cmake','--install','.'],build)
        source=Path(report['sources']['pyside-setup']['sourceDirectory'])
        run('pyside-setup','wheel',[sys.executable,'setup.py','bdist_wheel','--qtpaths='+str(prefix/'bin/qtpaths'),
            '--module-subset=Core,Gui,Widgets,Network,DBus,Svg,Qml,Quick,QuickWidgets,OpenGL,Test',
            '--no-qt-tools','--limited-api=yes','--parallel=2'],source)
        report['runtimeBuilt']=True;save();print('Build completed; all downstream qualification gates remain open.',flush=True)
    except Exception as error:
        report['failure']=str(error);save();raise


if __name__=='__main__':main()
