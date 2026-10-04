#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Take a package lifetime lease, then replace this process with the component."""
import os
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/lifecycle'))
from lease import hold

def component_environment(root):
    env=dict(os.environ)
    marker=root/'linux-python-runtime.json'
    if (sys.platform == 'linux' and (root/'scripts/linux-python-runtime.py').is_file()) or marker.exists() or marker.is_symlink():
        spec=importlib.util.spec_from_file_location('component_linux_python',root/'scripts/linux-python-runtime.py')
        runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
        env=runtime.environment(root,env.get('AUGMENTOR_PYTHON'),env)
        python=env.get('AUGMENTOR_PYTHON')
        if python:env['PATH']=str(Path(python).parent)+os.pathsep+env.get('PATH','')
    return env


def main(args):
    if len(args)<2 or args[0] not in ('runtime','desktop'):
        raise ValueError('Usage: run-component.py runtime|desktop COMMAND [ARG...]')
    hold(args[0])
    env=component_environment(Path(__file__).resolve().parents[1])
    command=args[1:]
    if env.get('AUGMENTOR_OFFICIAL_PYTHON') == command[0]:
        command=[env['AUGMENTOR_PYTHON'],*command[1:]]
    os.execvpe(command[0],command,env)


if __name__=='__main__':
    try:main(sys.argv[1:])
    except (OSError,ValueError,RuntimeError) as error:raise SystemExit(str(error)) from None
