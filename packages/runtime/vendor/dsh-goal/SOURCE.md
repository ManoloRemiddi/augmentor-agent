<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# DSH strict goal fold attribution

`fold.ts` reuses the public [DSH goal fold](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/goal/goal/src/fold.ts)
from `d743267388641bc76f17c45ce8b4c231aed1d32c`.
The original UTF-8 source SHA-256 is
`8dc7086395f436c6af4a816e668ddfd89ba527f801a877bf74d131f08870ab6e`.
Its MIT [license](LICENSE) and DeepSeek copyright are retained. The only source
changes are the attribution header and imports redirected to `contracts.ts`.
The fold body, strict decoder, revision/phase checks, ID reuse checks and admitted
round validation remain unchanged. `contracts.ts` is the minimal independently
authored type/event adapter; no DSH package is a runtime dependency.

Augmentor's owning `src/goals.ts` maps native custom entries and actual SDK input
admissions into these events. Its process-local activation, queue integration,
bounded native replay and operator controls are separately authored. DSH's service,
continuation driver, agent loop, transport, telemetry and GUI are not transplanted.
This selected MIT source is outside the root authored-source license restriction.
