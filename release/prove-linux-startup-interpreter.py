#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Exercise canonical entrypoints using a real locked runtime and synthetic app.

Run as the dedicated ordinary user in a disposable container. This never
enables a user service or claims graphical/product/package qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    assert os.geteuid()!=0 and os.environ.get('USER')=='proof'
    assert Path('/.dockerenv').is_file()
    owner_home=Path.home()
    assert args.runtime.absolute().is_relative_to(owner_home) and args.out.absolute().is_relative_to(owner_home)
    policy_path=args.policy.resolve();assert policy_path.is_relative_to(ROOT/'release')
    runtime=load('startup_runtime',ROOT/'scripts/linux-python-runtime.py')
    value=runtime.policy(policy_path);receipt=runtime.verify(value,args.runtime)
    assert value['profile'] in ('leap16-cp313-x86_64-voice','arch20261001-cp314-x86_64-voice')
    selected=str(args.runtime.absolute()/'bin/python3')
    installer=load('startup_installer',ROOT/'scripts/install-desktop-startup.py')
    with tempfile.TemporaryDirectory(prefix='startup proof space ',dir=owner_home) as folder:
        home=Path(folder);app=home/'candidate';native=app/'apps/native/augmentor_linux';native.mkdir(parents=True)
        (native/'window.py').write_text('# synthetic --ensure-running fixture\n')
        (native/'__init__.py').write_text('')
        (native/'__main__.py').write_text('import json,sys\nprint(json.dumps({"python":sys.executable,"arguments":sys.argv[1:]}))\n')
        (app/'release').mkdir();(app/'release/product.json').write_text('{"version":"synthetic"}')
        (app/'scripts').mkdir();shutil.copy2(ROOT/'scripts/linux-python-runtime.py',app/'scripts/linux-python-runtime.py')
        shutil.copy2(policy_path,app/'linux-python-runtime.json')
        env={**os.environ,'HOME':str(home),'XDG_DATA_HOME':str(home/'data'),
             'XDG_CONFIG_HOME':str(home/'config'),'XDG_STATE_HOME':str(home/'state'),
             'XDG_RUNTIME_DIR':str(home/'ipc'),'PYTHONDONTWRITEBYTECODE':'1'}
        (home/'ipc').mkdir(mode=0o700)
        with patch.dict(os.environ,env),patch.object(Path,'home',return_value=home):
            manifest=installer.install(app,selected,Path(sys._base_executable),enable=False)
        assert manifest['python']==selected and manifest['bootstrapPython']==value['python']
        wrappers={name:(home/'.local/bin'/name).read_text() for name in ('augmentor-agent','augmentor-recover','augmentor-update')}
        for wrapper in wrappers.values():assert shlex.split(wrapper.splitlines()[1])[1]==value['python']
        service=(home/'config/systemd/user/augmentor-desktop.service').read_text()
        executable=next(line.split('=',1)[1] for line in service.splitlines() if line.startswith('ExecStart='))
        command=shlex.split(executable);assert command[0]==value['python']
        def run(command):return json.loads(subprocess.check_output(command,text=True,env=env,timeout=60))
        cold=run(command);assert cold=={'python':selected,'arguments':['--ensure-running']}
        secondary=run([str(home/'.local/bin/augmentor-agent'),'--instance','secondary'])
        assert secondary=={'python':selected,'arguments':['--instance','secondary']}
        status=run([str(home/'.local/bin/augmentor-update'),'status'])
        assert status['selected']['root']==str(app) and all(row is None for row in status['running'].values())
    runtime.verify(value,args.runtime)
    report={'format':'augmentor-linux-startup-interpreter-fixture/1','target':value['target'],
            'policySha256':hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            'runtimeArtifactSha256':receipt['artifactSha256'],'bootstrapPython':value['python'],
            'selectedPythonPreserved':True,'actualServiceExecStartTested':True,
            'actualSecondaryWrapperTested':True,'actualUpdateStatusWrapperTested':True,
            'systemPython3AliasPresent':Path('/usr/bin/python3').is_file(),
            'wrapperContents':wrappers,'proofSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'installerSha256':hashlib.sha256((ROOT/'scripts/install-desktop-startup.py').read_bytes()).hexdigest(),
            'syntheticApplication':True,'userServiceEnabled':False,'graphicalLoginTested':False,
            'recoveryConnectionTested':False,'installedProductTested':False,'ownerStateChanged':False}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('target','bootstrapPython','systemPython3AliasPresent','actualServiceExecStartTested')}))


if __name__=='__main__':main()
