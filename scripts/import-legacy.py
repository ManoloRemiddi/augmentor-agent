#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/native'))
from augmentor_linux.migration import migrate
parser=argparse.ArgumentParser(description='Copy selected preferences and reusable prompt text. Original stores are preserved; credentials and conversations are not imported.')
parser.add_argument('--appearance',type=Path)
parser.add_argument('--settings',type=Path,help='Legacy settings YAML: reads only model pins and prompt-library content')
parser.add_argument('--prompts',type=Path,help='Prompt-library JSON export')
args=parser.parse_args()
config=Path(os.environ.get('AUGMENTOR_PI_CONFIG',Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'augmentor-pi'))
print(json.dumps(migrate(config,args.appearance,args.settings,args.prompts),indent=2))
