<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Restart reliability incident — 20 September 2026

## Failure chain

The installed desktop failed to reconnect after the computer restarted. This was
reproduced against the saved conversation, rather than inferred from the server
process being present.

1. **Two launch paths selected different builds.** The application menu and
   shortcut selected the user-local Resonant Voice preview. A separate login
   script hard-coded `/usr/bin/augmentor-agent`, selecting the older system UI
   without the audio button. Both happened to carry the 0.2.8 product version;
   that label did not distinguish their native features. The development source
   is 0.2.9; changing its version label would not repair either installed issue.
2. **The adaptive-reasoning plugin poisoned cold history reads.** Version 0.2.1
   appended `adaptive-reasoning/decision` and `/measurement` to DSH's replay log.
   DSH 0.1.5-rc.1 accepted these events in memory but rejected them after restart
   because they were unknown required event types. Its public `Session.append()`
   also drops an `ignorable` option, so adding an option at the call site is not
   a fix. Six current history artifacts contained 216 such diagnostic records.
3. **A chat failure disabled the whole interface.** Desktop startup reopened the
   last session before setting itself online. Reopening failed, so repeated
   connection attempts never reached Ready even though authenticated host,
   history listing and model-catalog requests succeeded.
4. **Recovery missed this failure mode.** It checked the runtime, history index
   and catalog, then the controller reopened the same rejected conversation.
   Its previous regression tests did not cover a full stored-chat cold read.
5. **Runtime startup was incomplete.** DSH automatic reconnect did not start a
   stopped host. The manual helper launched a detached process, which could race
   a managed service and lose its provider environment. Native/mobile cold
   starts now share a startup lock and the registered service owner.

The DSH process, local authentication and product identity were working in the
incident. Restarting DSH alone could not fix the stored-event problem. No GPU,
model, context, concurrency or precision change was made.

## Corrections

[Adaptive Reasoning 0.2.2](https://github.com/ManoloRemiddi/dsh-adaptive-reasoning)
keeps private routing/timing diagnostics in a bounded sidecar outside conversation
storage. Standard request headers retain the actual selected effort. Storage
errors in optional telemetry cannot fail a turn. The plugin's regression proof
now persists compressed histories and reopens them in another process without the
plugin loaded.

Augmentor recovery can repair only the two known informational legacy event
types. It takes the actual DSH kernel session lease, validates the complete
compressed artifact and contiguous sequences, verifies a private backup, writes
its hash manifest, and atomically replaces the file. It adds `ignorable: true`;
it does not remove events or change message, model, tool or sequence data.
Busy, corrupt, ambiguous and symlinked histories stop with a specific error.
Unknown future required events remain refused by DSH.

DSH stores concatenated Zstandard frames. Node's decoder processes one frame per
invocation; the old recovery helper therefore did not validate the whole artifact.
Recovery now scans every frame, validates decompression/checksums, rejects torn
input and bounds compressed/decompressed size to 512 MiB. The scanner is imported
from the pinned MIT-licensed DSH package with attribution. Repaired files retain
frame boundaries, including the separate header frame.

A permanently unreadable saved chat no longer makes a reachable runtime offline.
The UI retains the original saved pointer/history, exposes the cause, permits a
new conversation, and offers recovery of the blocked chat. Network timeouts do
not detach conversations. No prompt or unknown-outcome tool action is replayed.

## One desktop deployment and runtime owner

`scripts/install-desktop-startup.py` installs a per-user deployment descriptor,
one launcher, login entry, menu/shortcut aliases, recovery command and systemd
user service. It preserves shortcut bindings, takes backups and does not restart
an existing window as part of installation. Supply the build root and its Python
and Node interpreters explicitly; preserve the venv interpreter path.

All entrypoints read `~/.local/share/augmentor/desktop.json`, including the older
cached voice/login aliases. `augmentor-desktop.service` starts with the graphical
session and restarts after process failure. Its start operation does not toggle
an existing window. If KDE restores an obsolete executable first, the supervisor
uses its guarded close protocol only when it is idle; busy work is preserved.
A matching window started outside the service is watched until it exits, then
the service owns its replacement.

The descriptor registers the DSH service with its exact saved endpoint/home.
Native and mobile surfaces use that service, with its existing environment, and
serialize startup across processes. Unmanaged installations retain the CLI
fallback. An occupied unrelated port is never killed. Authentication and
integration errors retain their original cause instead of being called a stopped
server.

Installed commands:

```sh
augmentor-recover
systemctl --user status augmentor-desktop.service dsh-web.service
journalctl --user -u augmentor-desktop.service
```

The application menu also contains **Augmentor Agent — Recover connection**;
**Settings → Recover connection** uses the same worker. The standalone command
works without an AI response and verifies the final desktop connection, selected
build and saved-chat outcome. Maintenance status now exposes connection state,
recovery state, build root and audio-control availability.

For intentional backend maintenance, stop the desktop/mobile surfaces first;
otherwise their connection monitor will correctly bring DSH back online. Never
interrupt active work or an open voice session to run a deployment proof.

## Qualification and deployment scope

The installed change is the existing user-local voice preview plus the focused
native/recovery patches and startup deployment. The system package and DSH core
were not replaced. Plugin 0.2.2 was installed through DSH's package manager, then
loaded with idle services. Six affected histories were backed up and repaired;
independent before/after comparisons verified all original records and content.
Private backup manifests and diagnostic records stay outside GitHub.

Evidence on the installed MX/KDE host:

- Full native suite: **372 tests passed** using the repository's pinned `.venv`.
  This includes launcher session-restore coverage. The system
  Python/voice environment lacks QtTest; it is not the full UI test environment.
- Focused recovery tests cover stopped/managed runtimes, occupied ports, original
  error preservation, blocked-chat fallback, no prompt replay, legacy multi-frame
  repair, backup equality, idempotence, corrupt input and live leases.
- `scripts/proof-recovery.py`: real isolated Pi and DSH processes start and recover
  after stopping. It also reproduces and repairs a legacy history through an
  actual DSH server, without inference.
- `scripts/startup-recovery-proof.py --live`: installed desktop alone starts the
  stopped managed DSH; DSH loss reconnects; SIGKILL of the idle desktop triggers
  service recovery; repeated autostart keeps the same process; manual recovery
  succeeds; the saved conversation/model pointer is byte-identical.
- A deliberately restored old system executable was safely replaced by the
  configured voice preview through its idle-only close protocol.
- Recorded cold startup: **5.26 s**; runtime readiness after its restart was
  observed: **4.51 s**; idle desktop crash recovery: **22.30 s**. These are local
  observations, not upper-bound promises; startup and interaction leases can vary.
- Real selected local model: a separate synthetic conversation returned
  `AUGMENTOR_READY` in **10.29 s**, without tools or custom replay-log events.
  The user's existing conversation was not used for the prompt. After a further
  DSH restart, this synthetic conversation reopened with the answer intact.
- The restored current conversation obtained a valid `resonant-voice/1` ticket;
  the speech companion responded and the desktop audio control was present.

After these checks, the user performed a physical computer reboot and reported
that everything was working. This is user-reported reboot acceptance, in addition
to the process-level evidence above. Future release selection is governed by
[desktop deployments](DESKTOP-DEPLOYMENTS.md). Human
microphone/speaker acceptance remains separate from voice ticket/transport checks.


## Exact implementation references

- Augmentor startup/recovery implementation and local qualification:
  [`2dca65f1041de9a5cabe866fb34610944c6bef77`](https://github.com/ManoloRemiddi/augmentor-agent/commit/2dca65f1041de9a5cabe866fb34610944c6bef77).
- Adaptive Reasoning code, tests and maintained documentation:
  [`15d998168825cea9f5ff477758317f163a6c75f0`](https://github.com/ManoloRemiddi/dsh-adaptive-reasoning/commit/15d998168825cea9f5ff477758317f163a6c75f0).
- Installed 0.2.2 tarball SHA-256:
  `395033d80dc493cc3348022f9c1f803405232430e34d892d6c95251c6b678cae`.
  Its runtime files match the source reference above; the final additional test
  and documentation evidence do not change those runtime files.
- The installed native/recovery file hashes are in the private
  `~/.local/share/augmentor/desktop.json` deployment descriptor. They were checked
  against the files selected by the running desktop after the final cold start.

The Augmentor implementation is on the existing development branch/draft PR #3,
not merged into `main`. These are local source and installed-host qualifications;
the older September 19 CI run does not qualify this new patch.
