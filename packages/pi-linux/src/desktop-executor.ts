// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {control} from '../../desktop/src/index.js';
import {runDesktop} from './index.js';
import type {DesktopExecutor} from '../../computer-use/src/contracts.js';
export function linuxDesktopExecutor(backend: string): DesktopExecutor {
  return {
    id: process.platform==='darwin'?'macos-screencapturekit':'kde-wayland-portal',
    domainInstructions: (process.platform==='darwin'?'macOS, one monitor.':'Linux KDE Plasma Wayland, one monitor.')+' Sharing requires the user’s OS consent. The executor checks active-window identity and target geometry. Text input is limited to 256 characters per action; Linux currently requires ASCII. Use platform accessibility for application structure. Stop on unsupported layouts or text; do not emulate unsupported characters with shell commands. Do not assume a distribution or an application is installed.',
    control,
    observe: (params, signal) => runDesktop(backend, {action: 'observe', ...params}, signal),
  };
}
