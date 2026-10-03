#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Actual CPU Identity computation in a disposable locked Linux interpreter.

Uses ONNX's published Apache-2.0 test model, not speech or owner model data.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
MODEL_SHA256='cee798fc84cc4a49233de96443dd0990881a9a5e0beb8d3a9c3257884c84ceed'
MODEL_URL='https://raw.githubusercontent.com/onnx/onnx/v1.19.0/onnx/backend/test/data/node/test_identity/model.onnx'
parser=argparse.ArgumentParser(description=__doc__)
for name in ('policy','runtime','model','out'):parser.add_argument('--'+name,type=Path,required=True)
args=parser.parse_args()
assert os.geteuid()!=0 and args.runtime.resolve().is_relative_to(Path.home())
assert args.out.resolve().is_relative_to(Path.home()) and Path(sys.prefix)==args.runtime.resolve()
assert args.policy.resolve().is_relative_to(ROOT/'release')
spec=importlib.util.spec_from_file_location('locked_linux_runtime',ROOT/'scripts/linux-python-runtime.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
value=tool.policy(args.policy);receipt=tool.verify(value,args.runtime)
assert any(row['name']=='onnxruntime' for row in value['wheels'])
assert args.model.is_file() and not args.model.is_symlink() and tool.digest(args.model)==MODEL_SHA256
import numpy as np
import onnxruntime as ort
session=ort.InferenceSession(str(args.model),providers=['CPUExecutionProvider'])
assert session.get_providers()==['CPUExecutionProvider']
assert [(row.name,row.type,row.shape) for row in session.get_inputs()]==[('x','tensor(float)',[1,1,2,2])]
original=np.array([[[[1,2],[3,4]]]],dtype=np.float32)
result=session.run(['y'],{'x':original})
assert len(result)==1 and np.array_equal(result[0],original)
tool.verify(value,args.runtime)
report={'format':'augmentor-linux-cpu-onnx-fixture/1','target':value['target'],
        'proofSha256':tool.digest(Path(__file__)),'runtimeToolSha256':tool.digest(ROOT/'scripts/linux-python-runtime.py'),
        'policySha256':tool.digest(args.policy),'runtimeArtifactSha256':receipt['artifactSha256'],
        'modelUrl':MODEL_URL,'modelSha256':MODEL_SHA256,'modelBytes':args.model.stat().st_size,
        'providers':session.get_providers(),'identityOutputMatches':True,'runtimeUnchanged':True,
        'speechModelTested':False,'physicalAudioTested':False,'installedProductTested':False}
args.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
