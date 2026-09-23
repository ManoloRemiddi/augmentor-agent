// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
import {build} from 'esbuild';
await build({entryPoints:['adapters/dsh-prompt-library/src/client.js'],bundle:true,format:'iife',outfile:'adapters/dsh-prompt-library/lib/client.js',banner:{js:'// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0'}});
