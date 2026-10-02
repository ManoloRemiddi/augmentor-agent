// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export type ToolContent = {type: 'inputText'; text: string} | {type: 'inputImage'; imageUrl: string};
export interface ToolReply {success: boolean; contentItems: ToolContent[]}
export const toolFailure = (text: string): ToolReply => ({success: false, contentItems: [{type: 'inputText', text}]});
/** Validate the bounded transport envelope; image decoding remains the consumer's job. */
export function validImageUrl(value: unknown, limit = 700000): value is string {
  if (typeof value !== 'string' || value.length > limit || !/^data:image\/jpeg;base64,[A-Za-z0-9+/]+={0,2}$/.test(value)) return false;
  const data = value.slice('data:image/jpeg;base64,'.length); const bytes = Buffer.from(data, 'base64');
  return bytes.length >= 4 && bytes.toString('base64') === data && bytes[0] === 255 && bytes[1] === 216 && bytes.at(-2) === 255 && bytes.at(-1) === 217;
}
