// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {SettingsManager} from '@earendil-works/pi-coding-agent';

/** Managed SDK sessions do not inherit CLI install-reporting opt-ins. */
export function managedPiSettings(compaction=true){
  // Pi's public environment override takes precedence over SettingsManager,
  // including its provider-attribution headers. Apply the product opt-out before
  // each SDK owner is created; keep explicit model/provider headers unchanged.
  process.env.PI_TELEMETRY='0';
  return SettingsManager.inMemory({enableInstallTelemetry:false,enableAnalytics:false,
    cacheWarming:'off',retry:{enabled:false,provider:{maxRetries:0}},
    compaction:{enabled:compaction},packages:[],defaultProjectTrust:'never'});
}
