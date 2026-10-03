// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0

// DSH 0.1 stores tool output in a block wrapper; 0.2 stores it on the message.
// Keep the original shape when replacing context so either format can replay.
export const toolContent = message => message?.content?.[0]?.type === 'tool-result'
  ? message.content[0].content : message?.content ?? [];
export const toolFailed = message => message?.isError === true ||
  message?.content?.some(block => block.type === 'tool-result' && block.isError) === true;
export const withToolContent = (message, content) => ({...message, content:
  message.content?.[0]?.type === 'tool-result' ? [{...message.content[0], content}] : content});
// Match attribution migrated from old logs as well as newly authored context.
export const fromProducer = (source, name) => source?.kind === `plugin:${name}` ||
  source?.kind === 'plugin' && source.plugin === name;
