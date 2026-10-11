<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Public DSH streaming text pages

`page.ts` selects the original `cutPage` implementation from
[workspace-files](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/workspace-files/src/index.ts)
at the pinned public MIT baseline. It retains the supplier's line, UTF-8 byte
budget and EOF semantics. The extraction exports the function, supplies its
local Page type and substitutes Augmentor's error class; these changes are
marked in the source. SOURCE.json records the selected and full upstream hashes.
LICENSE preserves the supplier MIT notice.

The separately authored PiFilePreview supplies cancellation, actual file reads,
version checks and operator authority. No DSH service owner is mounted. These
supplier bytes remain MIT; Augmentor's authored-code licence does not relabel them.
