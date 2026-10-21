/* Copyright (c) 2026 DeepSeek · SPDX-License-Identifier: MIT
 * Selected verbatim helper from ui-conversation/src/client/service.ts. */
export function isImageMediaType(value: string): boolean {
  return value === 'image/png' || value === 'image/jpeg' || value === 'image/webp' || value === 'image/gif'
}
