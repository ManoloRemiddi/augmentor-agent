<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Selected Pi utilities

Source: [Pi 1.1.0 prompt-templates.ts](https://raw.githubusercontent.com/earendil-works/pi/abe508e1b89912adde45528136c3221eb69acdd7/packages/coding-agent/src/core/prompt-templates.ts), upstream commit `abe508e1b89912adde45528136c3221eb69acdd7`. Full upstream file SHA-256: `11db52a6bea6f3f094c6f533d4a3162462bdef4693f238ba1a8a1be6729d4545`.

`parseCommandArgs`, `substituteArgs` and `expandPromptTemplate` are selected verbatim; resource discovery, filesystem loaders and SDK-private imports are excluded. The local module adds only the original MIT copyright/SPDX notice and a public SDK type import. Its adjacent [original MIT license](LICENSE) is retained in compiled/staged distributions. The surrounding input/lifecycle adapter is Augmentor-authored and retains the repository license. No independent agent loop is copied.

## Configuration value resolver

`config-value.ts` retains the complete [Pi 1.1.0 resolve-config-value.ts](https://raw.githubusercontent.com/earendil-works/pi/abe508e1b89912adde45528136c3221eb69acdd7/packages/coding-agent/src/core/resolve-config-value.ts), upstream commit `abe508e1b89912adde45528136c3221eb69acdd7`, SHA-256 **`0f53dad47fe5d5d8837c022b7951ccd3bd5a9b577bd662f0986272110e83bcc7`**. Downloaded pinned source matches the locked npm source map byte for byte. The only source edit replaces its SDK-internal shell import with the supported public `getShellConfig` export; the module adds the original MIT copyright/SPDX notice above. The adjacent original license is unchanged.

The independently authored managed transport uses `resolveConfigValueUncached` to preserve SDK environment interpolation, literal escaping, trusted command values and platform shell behavior. It sanitizes resolution failures rather than echoing the private configured value. No SDK client/session/OAuth loop is copied. Configuration remains restricted to the explicitly managed profile and approved extension registrations.
