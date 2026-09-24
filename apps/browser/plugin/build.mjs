// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension
// Copyright © 2026 Manolo Remiddi
// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.

import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';

await build({
  absWorkingDir: fileURLToPath(new URL('../../../', import.meta.url)),
  entryPoints: ['apps/browser/plugin/src/index.ts'],
  outfile: 'apps/browser/plugin/dist/index.js',
  bundle: true, platform: 'node', format: 'esm', target: 'node22',
  external: ['ws', '@deepseek-ai/dsh-tools', '@deepseek-ai/schemastery'],
  banner: {js: '// Augmentor — dsh-augmentor plugin, pipe, and Chromium extension\n'
    + '// Copyright © 2026 Manolo Remiddi\n'
    + '// SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0\n'
    + '// License: MIT with Augmentor Resale Restriction — see LICENSE at the repository root.'},
});
