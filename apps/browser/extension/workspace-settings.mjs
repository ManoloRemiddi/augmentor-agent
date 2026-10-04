// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
/** Shared installation administration is owned by standalone Augmentor. */
export function settingsSections(definitions, workspace) {
  if (!workspace?.sdkProtocol) return definitions
  return definitions.filter(([id]) => !['dictation', 'harnesses', 'home', 'support', 'updates'].includes(id))
}

export const appearancePreferenceKeys=['augmentor-theme','augmentor-neut-hue','augmentor-neut-bright','augmentor-accent-hue','augmentor-accent-bright','augmentor-format-colours','augmentor-expand-thinking']
export function appearanceStorageKey(key,workspace) {
  return workspace?.sdkProtocol?'augmentor-workspace:'+workspace.id+':'+key:key
}

export function restoreWorkspaceAppearance(storage,workspace,preferences) {
  if(!workspace?.sdkProtocol)return
  for(const key of appearancePreferenceKeys){
    const scoped=appearanceStorageKey(key,workspace)
    if(preferences[key]===undefined)storage.removeItem(scoped)
    else storage.setItem(scoped,String(preferences[key]))
  }
}
