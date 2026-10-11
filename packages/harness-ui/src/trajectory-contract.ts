// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Minimal presentation contract for the adapted MIT DSH timeline; no DSH engine.
export type TrajectoryCellKind = 'system' | 'user' | 'context' | 'compacted' | 'message' | 'tool' | 'subtool';
export interface TrajectoryCellProps {
  index: number;
  kind: TrajectoryCellKind;
  text: string;
  startedAt?: number | null;
  timeSeconds?: number | null;
  requestOnly?: boolean;
  isError?: boolean;
}
export interface TrajectoryTurnModel {
  turn: number | null;
  groups: {cells: TrajectoryCellProps[]}[];
}
export type TrajectoryTranslate = (key: string, params: {value: string}) => string;
export function formatDurationMillis(milliseconds: number, translate: TrajectoryTranslate) {
  if (!Number.isFinite(milliseconds)) return '—';
  return translate('unit.milliseconds', {value: Math.round(milliseconds).toLocaleString('en-US')});
}
