// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Augmentor-owned boundary; this is not a Resonant CORE protocol.
export const COMPUTER_USE_VERSION = 'augmentor-computer-use/1';
export interface DesktopBrief {
  task: string;
  successCriteria: string;
  constraints: string;
}
export type DesktopStatus = 'completed' | 'blocked' | 'unknown' | 'cancelled' | 'budget_exceeded' | 'failed';
export interface DesktopResult {
  version: typeof COMPUTER_USE_VERSION;
  runId: string;
  status: DesktopStatus;
  summary: string;
  verification: string;
  verificationSource: 'worker_observation' | 'runtime';
  observedAfterLastAction: boolean;
  actionAttempted: boolean;
  model: {provider: string; id: string};
  counts: {requests: number; tools: number; images: number};
}
export interface DesktopLimits {
  requests: number;
  tools: number;
  timeoutMs: number;
  contextTokens: number;
  outputTokens: number;
  recentImages: number;
  imageTokenReserve: number;
  evidenceBytes: number;
}
export const DEFAULT_DESKTOP_LIMITS: Readonly<DesktopLimits> = Object.freeze({
  requests: 24, tools: 40, timeoutMs: 180_000, contextTokens: 24_000,
  outputTokens: 1024, recentImages: 2, imageTokenReserve: 4096,
  evidenceBytes: 16 * 1024 * 1024,
});
export interface DesktopExecutor {
  id: string;
  domainInstructions: string;
  control(method: string, owner: string, params: unknown, signal?: AbortSignal): Promise<any>;
  observe(params: {appPid?: number}, signal?: AbortSignal): Promise<unknown>;
}
