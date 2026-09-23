// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {test} from 'node:test'
import assert from 'node:assert/strict'
import {improvePrompt} from '../adapters/dsh-product/improve-prompt.mjs'
const input={text:'make this clear',instructions:'Edit [clipboard]',provider:'test',model:'test'}
function mock(text,kind='stop'){return {async prepareCall(){return {config:{},async *stream(options){assert.deepEqual(options.tools,[]);assert.equal(options.messages[0].content[0].text,input.text);yield {type:'text-delta',text};yield {type:'finish',reason:{kind}}}}}}}
test('rewrite is tool-free and returns editable text',async()=>assert.deepEqual(await improvePrompt(mock('{"kind":"rewrite","text":"Clarify this text."}'),input),{kind:'rewrite',text:'Clarify this text.'}))
test('clarification is distinct from replacement',async()=>assert.equal((await improvePrompt(mock('{"kind":"clarify","text":"Which text?"}'),input)).kind,'clarify'))
test('rejects truncated and invalid rewrites',async()=>{await assert.rejects(improvePrompt(mock('{}','max-tokens'),input));await assert.rejects(improvePrompt(mock('not JSON'),input))})
