#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build pinned native portal bindings outside the product's runtime environment.

Requires declared native GLib/GI/Cairo build libraries. No user packages, broker,
portal session, model or deployment selection are changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def run(arguments,*,environment=None):
    subprocess.run([str(value) for value in arguments],env=environment,check=True,timeout=900)


def download(source,destination):
    digest=hashlib.sha256();size=0
    if not source['url'].startswith('https://files.pythonhosted.org/') or not 0<source['bytes']<=16*1024**2:
        raise ValueError('Use a bounded pinned official portal source archive.')
    with urllib.request.urlopen(source['url'],timeout=60) as response,destination.open('xb') as output:
        while chunk:=response.read(1024**2):
            size+=len(chunk)
            if size>source['bytes']:raise ValueError('The portal source grew beyond its pin.')
            digest.update(chunk);output.write(chunk)
    if size!=source['bytes'] or digest.hexdigest()!=source['sha256']:
        raise ValueError('The portal source differs from its reviewed archive.')


def stage(project,inputs):
    if sys.platform!='linux' or platform.machine() not in ('x86_64','aarch64'):
        raise ValueError('Build portal bindings on their native supported Linux CPU.')
    config=json.loads((ROOT/'release/linux-managed.json').read_text())['portal']
    if config['automaticInstallQualified'] is not False:raise ValueError('This producer does not grant automatic eligibility.')
    if inputs.exists():raise ValueError('Use a fresh private portal build directory.')
    inputs.mkdir(mode=0o700,parents=True)
    python=project/'python/bin/python3';build=inputs/'build-env'
    actual=json.loads(subprocess.check_output([str(python),'-I','-B','-c',
        'import json,platform;print(json.dumps([platform.python_version(),platform.machine()]))'],timeout=30))
    if actual!=['3.12.13',platform.machine()]:raise ValueError('Use the exact pinned native product interpreter.')
    run([python,'-I','-B','-m','venv','--without-pip',build])
    build_python=build/'bin/python3'
    run([sys.executable,'-m','pip','--python',build_python,'install','--require-hashes',
        '--only-binary=:all:','--no-deps','--no-compile','-r',ROOT/config['buildRequirements']])
    environment={**os.environ,'PATH':str(build/'bin')+os.pathsep+os.environ.get('PATH',''),
        'PYTHONDONTWRITEBYTECODE':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    wheels=[];provenance=[]
    for source in config['sources']:
        archive=inputs/source['file'];download(source,archive)
        directory=inputs/source['package'];directory.mkdir(mode=0o700)
        run([build_python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation',
            '--wheel-dir',directory,archive],environment=environment)
        produced=list(directory.glob('*.whl'))
        if len(produced)!=1 or not produced[0].is_file() or produced[0].is_symlink():
            raise ValueError('The native portal build did not produce one ordinary wheel.')
        wheel=produced[0];digest=sha(wheel);wheels.append(wheel)
        # PyGObject needs the newly built Pycairo headers in the build env.
        if source['package']=='pycairo':
            run([build_python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',wheel],environment=environment)
        if sha(wheel)!=digest:raise ValueError('A built portal wheel changed during preparation.')
        provenance.append({'package':source['package'],'version':source['version'],
            'sourceURL':source['url'],'sourceSHA256':source['sha256'],'wheel':wheel.name,
            'wheelSHA256':digest,'bytes':wheel.stat().st_size})
    run([python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',*wheels],environment=environment)
    for wheel,record in zip(wheels,provenance):
        if sha(wheel)!=record['wheelSHA256']:raise ValueError('A portal wheel changed during runtime installation.')
    code=('import gi,cairo,json;gi.require_version("Gio","2.0");from gi.repository import Gio,GLib;'
        'assert (GLib.MAJOR_VERSION,GLib.MINOR_VERSION)>=(2,80);'
        'assert Gio.DBusConnection is not None;assert cairo.cairo_version()>=11510;'
        'print(json.dumps({"pygobject":gi.__version__,"glib":[GLib.MAJOR_VERSION,GLib.MINOR_VERSION,GLib.MICRO_VERSION]}))')
    imports=json.loads(subprocess.check_output([str(python),'-I','-B','-c',code],timeout=30))
    if imports['pygobject']!=config['runtimePackages']['PyGObject']:raise ValueError('The installed portal version differs from its pin.')
    tools=json.loads(subprocess.check_output([str(build_python),'-I','-B','-c',
        'import json;from importlib.metadata import version;print(json.dumps({name:version(name) for name in '
        '("pip","meson","meson-python","ninja","packaging","pyproject-metadata")}))'],timeout=30))
    libraries={name:subprocess.check_output(['pkg-config','--modversion',name],text=True,timeout=10).strip()
        for name in ('glib-2.0','girepository-2.0','cairo')}
    report={'schema':'augmentor-linux-portal-build-proof/1','targetCPU':platform.machine(),
        'python':'3.12.13','packages':provenance,'imports':imports,'systemMinimum':config['systemMinimum'],
        'buildLockSHA256':sha(ROOT/config['buildRequirements']),'buildTools':tools,'nativeLibraries':libraries,
        'automaticInstallQualified':False,'sourceLicenseReviewComplete':False}
    notices=project/'licenses';notices.mkdir(exist_ok=True)
    (notices/'linux-portal-build.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--inputs',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(stage(args.project.resolve(),args.inputs.resolve())))
