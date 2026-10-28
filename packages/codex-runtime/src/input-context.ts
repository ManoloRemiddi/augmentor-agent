// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Versioned request-scoped style; native history retains older context entries. */
import {inputModeInstructions} from '../../prompt-library/src/input-mode.js';
export function inputContext(requestId: string): Record<string, {kind: 'application'; value: string}> {
  const spoken = /^resonant-voice:[a-f0-9-]{36}$/.test(requestId);
  return {augmentor_input_mode: {kind: 'application', value: inputModeInstructions(requestId, spoken ? 'voice' : 'text')}};
}
