// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync,realpathSync} from 'node:fs';
import {dirname,isAbsolute,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {CODEX_VERSION} from '../../../dist/codex-runtime/src/runtime.js';

/** Test-only selection of the real, separately installed supplier CLI. */
export function codexTestNpmEntry(){
 const entry=process.env.AUGMENTOR_TEST_CODEX_NPM_ENTRY??fileURLToPath(new URL('../../../node_modules/@openai/codex/bin/codex.js',import.meta.url));
 if(!isAbsolute(entry))throw Error('Codex qualification needs an absolute external npm entry.');
 const actual=realpathSync(entry),meta=JSON.parse(readFileSync(join(dirname(actual),'../package.json'),'utf8'));
 if(meta.name!=='@openai/codex'||meta.version!==CODEX_VERSION||meta.bin?.codex!=='bin/codex.js')throw Error('Codex qualification prerequisite differs from the product contract.');
 return actual;
}

export function useCodexTestNpmEntry(t){
 const entry=codexTestNpmEntry(),previous=process.env.AUGMENTOR_CODEX_CLI;
 process.env.AUGMENTOR_CODEX_CLI=entry;
 t.after(()=>{if(previous===undefined)delete process.env.AUGMENTOR_CODEX_CLI;else process.env.AUGMENTOR_CODEX_CLI=previous;});
 return entry;
}
