<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# DSH Steering

Make Steer respond during unfinished model output instead of waiting for the complete answer. Ordinary queued prompts still wait their turn. Running tools finish before steering is applied, so they are neither interrupted nor repeated.

Tested with DSH **0.1.5-rc.1**, Node **24.19.0**, and a local Qwen model. The manifest pins the tested DSH version. This package uses host-provided lifecycle hooks and has no bundled DSH runtime or third-party dependencies.

## Install

Download `dsh-steering-0.1.0.tgz`, then run:

```sh
dsh plugin --profile web add /absolute/path/to/dsh-steering-0.1.0.tgz
```

Finish active conversations and restart DSH. The bundle mounts `dsh-steering` in the web profile. Use the existing DSH queue's Steer action. No API keys or additional model calls are required by this plugin.

For an individual agent preset, add an entry pointing to the installed package instead of enabling it globally. Augmentor already includes this behavior in its Linux preset; an extra global installation is only needed to enable other DSH agents.

## Behavior and limits

The same queued message ID is preserved. During model generation, the obsolete request is canceled while retaining pending work; the correction wakes the driver ahead of ordinary follow-ups. This creates an aborted-turn boundary internally, not a new conversation. If a tool is executing, the correction waits for its safe step boundary. Already executed actions are not undone. Backend/provider cancellation latency can vary.

The package supplies the behavior, not a queue UI. Its bundle applies to agents in the selected DSH profile. To disable it, disable the `dsh-steering` profile entry and restart DSH when idle. Other DSH versions have not been verified.

## Build locally

```sh
npm pack ./adapters/dsh-steering
```

Repository regression tests: `node --test tests/responsive-steering.test.mjs`.
