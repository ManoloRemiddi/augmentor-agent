<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Codex credentials and actual OS-store qualification

The shared host stores provider credentials through `OsCredentialStore` and
`services/codex/credentials.py`. Profiles contain opaque references; credentials
cross only the private helper pipe. The helper selects native macOS Keychain or
Linux Secret Service directly. User-configured keyring plugins, plaintext stores
and fallback chains are not loaded. An unavailable/locked store fails explicitly.
This does not implement or establish eligibility for subscription OAuth login.

## Release dependency correction — October 1

The credential helper's Python library was absent from both release declarations.
Synthetic-store unit tests did not catch that omission. Debian runtime now declares
`python3-keyring (>= 25.6)`, `python3-secretstorage` and `gnome-keyring`; dependency
installation is part of a future packaged release, not an update to the owner’s
current system. A compatible, unlocked session Secret Service is still required.

Mac’s hashed wheel lock and package inventory now include `keyring 25.6.0`,
`jaraco.classes 3.4.0`, `jaraco.context 6.0.1`, `jaraco.functools 4.1.0` and
`more-itertools 10.7.0`. All five universal Python wheels were retrieved and
verified against PyPI SHA-256 metadata; each contains upstream license notices.
Both Desktop and the standalone Browser companion include these credentials
libraries. The companion keeps its existing absence of Qt and GUI modules.
Their active dependency edges are complete and version-compatible for the pinned
CPython 3.12/Darwin target. Existing package pins remain unchanged. Mac's existing
wheel-notice inventory and package-environment checks include these additions; this does
not close unrelated native-binary source/license gates.

## Actual store proofs

```sh
# Linux: separate encrypted keyring and D-Bus session; owner stores are untouched.
python3 scripts/proof-codex-secretservice.py

# Mac: run with the intended build or bundled interpreter.
AUGMENTOR_PYTHON=/path/to/python node scripts/proof-codex-credentials.mjs
```

The shared proof uses the actual Node credential class and Python native backend.
It saves two fresh synthetic references, reads them through separate helper
processes, updates one, removes it twice and verifies the other is unaffected.
Cleanup attempts both owned references even if one operation fails, verifies their
removal, and fails the proof if cleanup is incomplete. It prints metadata only.
It neither lists nor reads existing credential references.

Linux's wrapper creates new HOME/data/runtime directories and a separate session
bus. It starts only its own Secret Service daemon and waits for that daemon to own
the bus name before reading the collection, avoiding competing auto-starts. The
actual proof passes in a disposable container using the same pinned Debian base
as CI, system keyring 25.6.0 and Node 24.19.0. No owner bus, wallet, credential,
installed app or model setting was accessed or changed.

Debian CI now requires that positive proof. Both Mac jobs require the native
Keychain proof with the build interpreter, packaged Desktop interpreter and
standalone Browser companion interpreter. Both packages also import the native
backend during staging and verify their inventory and signatures.
Mac results for this change remain pending; Linux's isolated proof does not
qualify the owner's desktop wallet or Mac Keychain. An interactive locked store
may require its owner to unlock it. No automatic plaintext fallback is permitted.

The two credential unit tests and two Mac package-inventory tests also pass.
See [full integration status](CODEX-INTEGRATION.md), [local Qwen activation
decision](CODEX-LOCAL-QWEN.md) and the [C0–C9 plan](CODEX-INTEGRATION-PLAN.md).
