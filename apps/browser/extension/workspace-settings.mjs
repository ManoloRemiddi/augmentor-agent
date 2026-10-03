// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Shared installation administration is owned by standalone Augmentor. */
export function settingsSections(definitions, workspace) {
  if (!workspace?.sdkProtocol) return definitions
  return definitions.filter(([id]) => !['dictation', 'harnesses', 'home', 'support'].includes(id))
}
