# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Start an isolated Pixel-sized Android 16 test device; software fallback is explicit."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--software',action='store_true',help='Slow software emulation when KVM is unavailable')
    parser.add_argument('--window',action='store_true')
    args=parser.parse_args()
    root=Path.home()/'.local/share/augmentor-android';sdk=root/'sdk'
    image=sdk/'system-images/android-36/google_apis/x86_64/source.properties'
    if not image.exists():parser.error('Install system-images;android-36;google_apis;x86_64 first.')
    if not args.software and not os.access('/dev/kvm',os.R_OK|os.W_OK):
        parser.error('KVM is unavailable. Enable it with administrator help, or explicitly use --software.')
    avd=root/'avd';avd.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'ANDROID_HOME':str(sdk),'ANDROID_AVD_HOME':str(avd)}
    name='augmentor_pixel_api36'
    if not (avd/(name+'.ini')).exists():
        subprocess.run([str(sdk/'cmdline-tools/22.0/bin/avdmanager'),'create','avd','-n',name,
                        '-k','system-images;android-36;google_apis;x86_64','-d','pixel_7'],
                       input='no\n',text=True,env=env,check=True)
    command=[str(sdk/'emulator/emulator'),'-avd',name,'-port','5580','-no-snapshot','-no-boot-anim',
             '-no-audio','-gpu','swiftshader','-memory','3072','-cores','2','-dns-server','100.100.100.100']
    if not args.window:command.append('-no-window')
    if args.software:command+=['-accel','off']
    print('Device: emulator-5580; private HTTPS resolves through the host tailnet DNS.',flush=True)
    os.execvpe(command[0],command,env)


if __name__=='__main__':main()
