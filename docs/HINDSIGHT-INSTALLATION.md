<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Controlled Hindsight installation and source backport

[`setup-hindsight.py`](../scripts/setup-hindsight.py) installs the pinned 0.10.0
engine without authorizing memory inference. Pi remains the conversational owner;
the existing companion supplies bounded active-window inference. This path uses
Linux Docker host networking; other OS installation/release artifacts require
separate qualification. Existing MX reviews and selected installations are not
updated by a source change.

The explicit `--refresh-budget-backport` option selects the
[reviewed MIT refresh-default fix](SOURCES.md). `--no-refresh-budget-backport`
deliberately selects the pinned base source. Omission preserves a saved choice;
fresh profiles use the base. Thinking mode remains a separate memory-only
`--llama-cpp-thinking default|off` choice, also preserved by omission. These options
do not tune the model server, conversation/voice provider or processing limits.

Source extraction uses a uniquely labelled, never-started container from the exact
pinned image. Only the reviewed public engine file is read. Its original digest,
zero-fuzz patch result and MIT notice are verified in a new artifact directory.
That directory contains only the expected extension/source/notice/ownership files;
existing or linked/tampered artifacts are refused, not repaired. Temporary source
containers must have confirmed cleanup before an artifact can be used. The
engine source is mounted read-only, separately from its data volume.

## Separate installations

Choose a unique private shared-data directory, container name, named volume and
distinct API/gateway/PostgreSQL ports for an isolated installation. A fresh
installation defaults to API 8889/gateway 8890 and the engine's implicit embedded
database setting; explicit `--postgres-port` enables side-by-side testing.
`--restart no` avoids daemon autostart for a review or proof. These values are
recorded and preserved on subsequent calls when their options are omitted.

An optional `--public-model-cache` mounts only the two declared public model-cache
roots read-only and enables offline loading. Extra roots, credential files and
escaping links are rejected. A changed saved inventory requires an explicit
choice. Without a cache the pinned image may download its public models during
first setup. Image downloads occur only if the exact digest is not already local.
Telemetry opt-outs are recorded in the expected environment and checked on reuse.

```sh
AUGMENTOR_SHARED_DATA=/absolute/private-memory-directory \
  python3 scripts/setup-hindsight.py \
  --model-url http://127.0.0.1:8080/v1 --model EXPLICIT_LOCAL_MODEL_ID \
  --name UNIQUE_ENGINE --volume UNIQUE_DATA_VOLUME \
  --port 18440 --gateway-port 18441 --postgres-port 18442 \
  --refresh-budget-backport --llama-cpp-thinking off --restart no \
  --public-model-cache /absolute/verified-public-model-cache
```

Configuration is written atomically, mode 0600, only after exact-instance health,
version and controlled policy checks. A matching running instance is inspected
without another Start. A matching deliberately stopped instance starts by its
exact Docker ID. Docker inspection failure is distinct from confirmed absence.
The saved identity/ownership, named volume, read-only mounts, source and expected
environment must match; no name-based foreign replacement can grant authority.

## Stopped replacement and recovery

Changed source/mode/environment is refused while the engine runs, including when
`--replace-stopped` is present. Deliberately stop the correct engine before using
that option. Replacement supports only the exact pinned image and matching named
data volume. It first copies the stopped database into a private archive, checks
the archive and durable write, and records its SHA-256 and source ID in a separate
backup manifest, together with the previous private configuration for rollback.
Failure leaves the original instance/name/configuration intact.
Only then is the exact stopped ID made non-restarting and renamed; its volume,
container and backup remain retained. The replacement uses that same data volume.
No archive queue is drained and no historical processing is authorized by setup.

`hindsight.json`, `hindsight-installation.json` and the backup manifests are
**private credential-bearing files**. The installation receipt records the desired configuration before Docker
creation. After a lost acknowledgement, ordinary invocation refuses an automatic
repeat. `--recover-pending` verifies the recorded matching instance and completes
readiness/configuration without another creation or replacement. A missing or
different instance is refused for inspection. Preserve incomplete receipts and
backups; they are not portable public logs or proof of a completed installation.

The full memory proof can use a typed installer ownership receipt for cleanup;
both its exact container ID and private ready receipt must agree. Existing proof
labels remain supported. Cleanup stops the exact ID and verifies that same
instance is terminal; the original engine and public model-cache inventory remain
outside its mutation scope.

## Qualification status

Authored transport/source fixtures exercise real file hashes, patch application,
atomic configuration, read-only mounts, source-container cleanup, stopped-instance
restart, preserved choices, stopped replacement/backup and failed acknowledgements.
They are distinct from actual Docker/Qwen acceptance. Production adoption of the
owner's current engine and existing personal banks remains gated on live lifecycle
evidence and the owner's installed-update workflow. The running MX review remains
the separately qualified [guarded-memory review](HARNESS-MEMORY-SETTINGS.md).

## Actual installation and rollback qualification — October 16

Functional installer **60fa55f4e6089ddd017ede74ae89898a1571f3f6** passes source and
fresh ordinary **61 Python cases**, plus **31 fresh ordinary memory Node cases**.
The source Node/runtime inputs retain the preceding qualification; no app or GUI
code changes. Twenty-five source/licence cases pass. Frozen **3,415 tracked /
1,063 compiled / one Node / 20,702 dependency inputs** verify unchanged after use.
Existing bounds/workers/skips remain unchanged. No dependency or image is updated.

Actual Docker setup uses the exact already-cached image, three distinct ports,
fresh named volume/private profile, **43 verified public cache inputs**, explicit
memory-only **off**, the reviewed source backport and restart policy **no**.
The installer extracts the exact public base from its never-started source
container, applies/verifies the selected MIT patch, joins source-container removal
and starts the actual engine. Its full actual Pi/Hindsight/Qwen scenario passes:
18 memory requests all explicitly carry false and finish, ten conversation
requests/two authored tools, both six-stage jobs completed at attempt zero/no
failures. Remaining balances are **102.50 seconds / 37,527 tokens** and
**96.80 seconds / 26,853 tokens**. Seed/correction, scoped recall, isolation,
historical branch, cold companion restart, pause and outage recovery pass without
replay. The proof uses unchanged runtime **b7e0afaa**, budgets and source/date/scope
contracts; all proof actors/its initial engine join cleanup.

A subsequent native catalogue baseline is taken after the first installer start.
The deliberately tested same-instance stop/start, stopped replacement with base
source, and stopped replacement restoring the reviewed backport preserve the
**complete native responses** exactly: two banks, six documents and every document
detail, fifteen facts, page tree and two full pages. No fields/entries are filtered.
The source journal is byte-identical, both replacement archives validate/hash,
and old instances remain stopped/non-restarting on their original named volume.

One real archive is then restored into a separately confirmed empty named volume
through a uniquely owned never-started transfer container. The original database
volume is never mounted during restoration. A fresh actual installer instance on
that restored volume returns the exact same complete native catalogue, canonical
SHA-256 `a4158de57d27eb114237737e3bcd7e14af4c175058b326e9fe610e0273d3f525`.
The transfer container is removed and restored engine stopped.

Followup **d6361bd1bd3a36e9dd787c08ccb7569dcb0b18e8** adds only the previous private
configuration to the backup manifest. Its source/fresh ordinary each pass the
same **61 Python cases**. The exact rollback assertion fails against 60fa because
that field is absent. An independent actual stopped replacement verifies the
complete previous configuration, including credentials/source choice, in a
**0600** manifest; the archive hash and entire native state remain exact. That
engine is stopped. The full inference/initial lifecycle result belongs to 60fa;
the focused followup proves the one-field addition without relabelling its tested
revision or rerunning unchanged inference. Both frozen trees/compiled inputs verify.

All **five created engine instances** are terminal; both temporary public-source
containers and the archive-transfer container are removed. Cache inventories and
source overlays verify. Twelve sealed inventories/thirteen review owners plus
recognition, selected installation, 38 canonical/four original private changes
and six model/service configuration hashes remain preserved. The original memory
engine remains **default**; the existing MX review remains available and unchanged.
Qwen is online; Breeze remains below its unchanged GPU prerequisite, without
retry, tuning or eviction. No new artifact is staged/activated or binary published.

Retained preparation failures include older fixture identity/mount omissions, an
expanded fixture import path, its Docker peer intercepting the real patch tool,
and an observer initially selecting obsolete `ready=1` rather than all actual
banks. The failed observer captures no native baseline; the qualified lifecycle
uses all banks and complete native responses. The rollback missing-field negative
control is also retained. These failures are not counted as passes.

This qualifies the **offline-cache Linux synthetic-bank path**, not automatic
owner adoption or every interruption scenario. Larger/older banks, uncached
downloads, other providers, remaining interruption/rename/configuration rollback
boundaries, owner physical feedback/installed workflow, full voice and later OS
release gates remain. Original default-mode timing failures stay retained.
[Portable installation, lifecycle and restoration evidence](../release/harness-hindsight-installation-20261016.json).
