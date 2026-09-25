// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync} from 'node:fs';
try {
  const token=readFileSync(process.env.HOME_AGENT_TOKEN_FILE,'utf8').trim();
  const res=await fetch('http://127.0.0.1:'+(process.env.PORT??8181)+'/ready',{
    headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(4000)});
  await res.body?.cancel();if(!res.ok)process.exitCode=1;
} catch {process.exitCode=1;}
