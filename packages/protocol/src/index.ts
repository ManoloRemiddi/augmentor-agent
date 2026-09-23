// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
export const PROTOCOL = 'augmentor-pi/1';
export const MAX_FRAME = 1024 * 1024;
export type Data = Record<string, any>;
export interface Request { id: string; method: string; params?: Data }
export interface DisplayEvent {seq: number; type: string; data: Data; turnId?: string}
export function request(value: any): asserts value is Request {
  if (!value || typeof value.id !== 'string' || value.id.length > 128 || !/^[\w.-]+$/.test(value.id) ||
      typeof value.method !== 'string' || !/^[a-zA-Z]+\.[a-zA-Z]+$/.test(value.method) ||
      (value.params !== undefined && (!value.params || Array.isArray(value.params) || typeof value.params !== 'object'))) {
    throw new Error('Invalid request');
  }
}
export function identifier(value: unknown): string {
  if (typeof value !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(value)) throw new Error('Invalid identifier');
  return value;
}
export function text(value: unknown, limit = 65536): string {
  if (typeof value !== 'string' || !value.trim() || value.length > limit) throw new Error('Invalid or oversized text');
  return value;
}
