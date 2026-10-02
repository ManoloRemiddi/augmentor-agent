// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {readFileSync} from 'node:fs';
import {soulText, sessionSoul} from '../../dist/identity/src/index.js';
export const name = 'augmentor-identity';
export const inject = ['systemPrompt'];
export function apply(ctx) {
  const recovery = readFileSync(new URL('../../config/browser-recovery.md', import.meta.url), 'utf8');
  const original = readFileSync(new URL('../../config/agent-persona.md', import.meta.url), 'utf8');
  const snapshot = agent => {
    // Existing chats without a snapshot retain their original packaged persona.
    const historical = agent.session.snapshotEvents().some(event => event.type==='user/message'||event.type==='assistant/message');
    const parent = agent.session.header?.parentSession;
    return sessionSoul(agent.id, parent ? sessionSoul(parent, original) : historical ? original : soulText());
  };
  ctx.on('agent/created', ({agent}) => snapshot(agent));
  ctx.effect(() => ctx.systemPrompt.section({name: 'deployment:persona-prefix', order: ctx.systemPrompt.getSectionOrder('DEPLOYMENT_PERSONA_PREFIX'), text: context => (context.agent ? snapshot(context.agent) : soulText())+'\n\n'+recovery, complete: true}), 'identity.section()');
  ctx.effect(() => ctx.systemPrompt.section({name: 'deployment:persona-suffix', order: ctx.systemPrompt.getSectionOrder('DEPLOYMENT_PERSONA_SUFFIX'), text: ''}), 'identity.suffix()');
  ctx.systemPrompt.suppressRuntimeContext();
}
