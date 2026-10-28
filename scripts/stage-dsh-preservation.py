#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Stage/verify a private DSH preservation plan; never install, stop or start DSH."""
import argparse
import json
from pathlib import Path
import sys
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services'))
from dsh.preserve import stage,verify

parser=argparse.ArgumentParser(description=__doc__)
commands=parser.add_subparsers(dest='command',required=True)
prepare=commands.add_parser('stage')
for name in ('home','incoming','output','cli'):prepare.add_argument('--'+name,type=Path,required=True)
check=commands.add_parser('verify');check.add_argument('--output',type=Path,required=True);check.add_argument('--sha256',required=True)
if __name__=='__main__':
    args=parser.parse_args()
    try:
        result=stage(args.home,args.incoming,args.output,args.cli) if args.command=='stage' else verify(args.output,args.sha256)
        print(json.dumps(result))
    except (OSError,ValueError,TypeError,KeyError,RecursionError,yaml.YAMLError):
        print('DSH preservation staging refused; inspect input provenance, edited files, profile structure and stage hashes. No owner file was changed.',file=sys.stderr)
        raise SystemExit(1)
