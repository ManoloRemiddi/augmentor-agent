<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# DSH timeline source and attribution

The timeline projection in `src/dsh-timeline.ts` is copied from the public
[DSH Trajectory timeline](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/ui-trajectory/src/client/timeline.ts)
at commit `d743267388641bc76f17c45ce8b4c231aed1d32c`.
Copyright belongs to DeepSeek; [the original MIT license](LICENSE) is retained.

The changes are an attribution header and replacing DSH-specific imports with
Augmentor's minimal presentation contract. Projection, duration handling, lane
selection, idle compression and inclusive timeline focus retain the upstream
implementation. The adapted file remains MIT licensed; Augmentor's separately
authored adapters keep their declared license.

No DSH runtime, Cordis service, model loop, analytics or request transport is
included. The UI must supply recorded start times and durations; missing timing
is not fabricated. Record indexes belong to the view's stable event mapping.
