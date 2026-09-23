# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Build an internal APK with pinned SDK tools; never use this development key for release."""
import argparse
from pathlib import Path
import shutil
import subprocess
import zipfile
import hashlib

HERE = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,default=Path.home()/'.local/share/augmentor-android/sdk')
    args=parser.parse_args()
    tools=args.sdk/'build-tools/36.0.0';platform=args.sdk/'platforms/android-36/android.jar'
    if not platform.exists() or not (tools/'apksigner').exists():
        parser.error('Install platforms;android-36 and build-tools;36.0.0 first.')
    build=HERE/'build';build.mkdir(exist_ok=True)
    for name in ('classes','dex','res/drawable'): (build/name).mkdir(parents=True,exist_ok=True)
    def run(*command):subprocess.run([str(x) for x in command],check=True)
    shutil.copyfile(HERE.parent/'web/icon-192.png',build/'res/drawable/icon.png')
    run(tools/'aapt2','compile','--dir',build/'res','-o',build/'resources.zip')
    run(tools/'aapt2','link','-o',build/'unsigned.apk','-I',platform,'--manifest',HERE/'AndroidManifest.xml',build/'resources.zip')
    compiler=['javac'] if shutil.which('javac') else ['java','-m','jdk.compiler/com.sun.tools.javac.Main']
    run(*compiler,'-source','8','-target','8','-classpath',platform,'-d',build/'classes',HERE/'MainActivity.java')
    run(tools/'d8','--lib',platform,'--min-api','26','--output',build/'dex',*sorted((build/'classes').rglob('*.class')))
    with zipfile.ZipFile(build/'unsigned.apk','a') as apk:
        for dex in (build/'dex').glob('*.dex'):apk.write(dex,dex.name)
    run(tools/'zipalign','-f','4',build/'unsigned.apk',build/'aligned.apk')
    private=Path.home()/'.local/state/augmentor-mobile';private.mkdir(parents=True,exist_ok=True,mode=0o700)
    key=private/'android-internal.p12'
    if not key.exists():
        run('keytool','-genkeypair','-keystore',key,'-storetype','PKCS12','-storepass','android','-keypass','android',
            '-alias','internal','-keyalg','RSA','-keysize','2048','-validity','3650','-dname','CN=Augmentor Internal Development')
        key.chmod(0o600)
    output=build/'augmentor-remote-internal.apk'
    run(tools/'apksigner','sign','--ks',key,'--ks-key-alias','internal','--ks-pass','pass:android','--out',output,build/'aligned.apk')
    run(tools/'apksigner','verify','--verbose',output)
    run(tools/'zipalign','-c','4',output)
    print(str(output))
    print('SHA-256 '+hashlib.sha256(output.read_bytes()).hexdigest())


if __name__=='__main__':main()
