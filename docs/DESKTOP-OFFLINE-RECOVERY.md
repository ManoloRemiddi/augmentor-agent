<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Desktop offline recovery

## Current restart/recovery implementation

See [the 20 September restart incident](RESTART-RELIABILITY-2026-09-20.md) for
the split-launcher and adaptive-event failures, managed startup, saved-chat
recovery, the standalone `augmentor-recover` command and current verification.
The September 16 evidence below is historical and did not cover those failures.

## Incident: 16 September 2026 (historical)

The native desktop was configured for DSH at `http://127.0.0.1:3080`.
DSH health, the Augmentor integration identity check, and the model catalog
worked. `session.list` failed because its session directory mixed compressed
`.jsonl.zstd` artifacts with uncompressed `.jsonl` artifacts. The error was:

> session persistence listing failed: session artifact uses .jsonl, but this backend is configured for compression "zstd"; use a separate root or select the matching compression mode

The desktop recovery routine loads the saved chat before marking the app online.
Its monitor catches any recovery error, marks the connection unavailable, and
shows “Reconnecting…” without surfacing the underlying exception. This made a
chat-storage problem look like a server/network outage. Restarting the app or
DSH alone would not remove the storage conflict.

419 uncompressed files were found. Decompressing their matching compressed
files showed 418 byte-identical copies and one where the compressed file
contained the entire plain file plus newer data. Only the redundant plain files
were moved outside the active session tree. The compressed histories were left
in place. Every moved file has a SHA-256 entry in the backup manifest:

`~/.local/state/augmentor-repair-backups/20260916-091305-compression/manifest.json`

The first rejected plain file had a filesystem change timestamp of 08:38 on
16 September, while its matching compressed file dated from 11 September.
This is consistent with later extraction or restoration of plain copies, but
the responsible command/process has not been identified. Do not attribute the
incident to an upgrade or crash without further evidence.

After repair, the same DSH adapter successfully loaded 525 sessions and seven
model-provider groups. The existing desktop process recovered automatically;
its accessibility tree reported “Ready”. No restart or model turn was needed.
This verifies connection/history/catalog recovery, not model inference.

## One-click recovery

Open **Settings → Recover connection**. Recovery starts immediately and reports
progress in the dialog. The worker checks the selected harness, history and
model catalog, then restores the current conversation and its event stream.
Messages are never replayed. A second recovery cannot run concurrently.

- A stopped Pi runtime is started through its existing lifecycle helper.
- A stopped DSH web profile is started using the saved local endpoint and data
  folder, with the supported installed CLI. Startup output stays in a private
  recovery log. An occupied port is never treated as permission to kill a server.
- The known zstd/plain-history conflict triggers a reversible repair: acquire
  DSH's session lease, verify the complete compressed file, confirm the plain
  file is an identical copy or prefix, verify a backup and write its hash
  manifest, then remove only the redundant plain file from active storage.
- Divergent/missing/corrupt counterparts, active session locks and changed files
  stop repair with an explanation. Symlinks are not followed. Decoding is bounded
  to 30 seconds and 512 MiB per file using the bundled Node runtime.
- Backups and startup logs are under `~/.local/state/augmentor-recovery/` (or the
  corresponding `XDG_STATE_HOME`). Keep backups until the recovered history has
  been checked. Partial repairs remain backed up if a later file needs attention.
- A working runtime is reconnected without restarting it. An unidentified or
  unresponsive occupied port is reported rather than forcibly killing a server
  that might own work in another interface. Missing installations, authentication
  problems, disk failures and divergent histories can still require attention.

For prevention, decompress chat exports into a separate folder, never alongside
live session files. Keep backup/restore tools from mixing physical compression
formats in the active DSH session directory.

Connection errors now retain their actual cause and point to Settings → Recover
connection. The dialog displays the full last error and the recovery outcome.

## Verification

The native suite passes 251 tests, including recovery worker/dialog tests,
verified-prefix backups, divergent/corrupt/missing counterpart preservation,
active leases, symlinks, startup routing and occupied-port protection.
`scripts/proof-recovery.py` starts a real Pi runtime in isolated state, and starts,
stops and recovers a real DSH fixture profile without sending model requests.
The DSH fixture deliberately omits the product integration; the live installation
was separately verified through its existing product adapter in the incident.
