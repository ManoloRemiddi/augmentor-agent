<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Wiki tools on Linux and macOS

As of October 20, 2026, native-workspace Harness conversations support the same
six Wiki tools and nine bundled skills on Linux and macOS. Both owner Macs now
select and run the qualified macOS artifact. This supersedes the earlier
Linux-only Wiki limitation in the dated installation and plugin records.

## Use

Open **Augmentor Harness** from Applications, then **Settings → Plugins → Wiki
tools & skills**. The overview exposes its enabled state; the detail form shows
the vault path, query limit, routing and operation review. Configuration changes
use the same revision checks and same-owner SDK resource reload on both systems.
An unconfirmed application must be refreshed before starting further work.

Each Mac has a new independent vault at `~/Augmentor Wiki`. A **Getting Started**
page and the original generic scaffold are present. Ask Harness to find that
page, save a useful answer, or maintain the wiki. Existing chats retain their
permission mode: changing actions still require approval in **Ask before
actions**, and **Read Only** blocks them. Obsidian can open the vault as ordinary
Markdown. Synchronising these new vaults or copying the MX knowledge base was
not part of this installation.

| Tool | Behavior retained from the existing binding |
| --- | --- |
| `wiki_query` | Quick index/hot-cache view or ranked full-text search |
| `wiki_write` | Type routing, frontmatter, links, indexes, log and source manifest |
| `wiki_rename` | Page rename and backlink updates |
| `wiki_scaffold` | Mode-specific folders, conventions and seed pages; existing files kept |
| `wiki_archive` | Raw-source archiving, manifest updates and collision preservation |
| `wiki_lint` | Vault health checks and generated reports |

The approved resource catalog contains `wiki`, `wiki-query`, `wiki-ingest`,
`wiki-lint`, `save`, `think`, `obsidian-markdown`, `obsidian-bases` and `defuddle`.
A bundled skill is guidance, not an installed external application. Optional
external Defuddle/Obsidian services and every skill workflow are not qualified by
this port. Browser-extension and delegated conversations retain their existing
native-resource exclusions; opening the web Harness does not turn a conversation
into a browser-extension session.

## Adapter and source contract

The copied MIT Wiki Tools **0.14.0** and Wiki Skills **0.2.1**, original operation
bodies, source manifests and notices are unchanged. Pi remains **1.1.0** and the
product remains **0.2.13**. There is no second agent loop or new package pin.

Linux retains its `/proc/self/fd` implementation. macOS uses a scoped Python
helper with descriptor-relative `dir_fd` operations and `O_NOFOLLOW` traversal.
The helper admits one configured root, pins directory handles, checks ownership,
regular-file type, link count and the 64 MiB file bound, and separates read-only
from mutation scopes. It does not execute a shell or inherit provider credentials.
The installer supplies its absolute bundled Python path through
`AUGMENTOR_PYTHON`; `wiki-native.py` is copied beside the compiled runtime.
See the [Python descriptor-relative API](https://docs.python.org/3/library/os.html#paths-relative-to-directory-descriptors).

Darwin lock identity combines UID/PID, microsecond process birth time from the
public `proc_pidinfo(PROC_PIDTBSDINFO)` ABI and the current boot-session UUID.
See Apple's [public process-info declaration](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/proc_info.h).
Receipts, native-call identity, serialisation, cancellation, explicit risk review
and the prohibition on replaying an uncertain mutation remain the shared
contract. An unresolved lock or started/unknown operation blocks further changes.
These are application IO boundaries, not an OS sandbox for every model tool.

## Qualification and installed acceptance

Runtime implementation `d9a546df` and fixture-only revision
`fda0cc3bc2be7b2bbf53893ae4e97c28a5125678` produce the installed artifact:

- SHA-256 `698b95813eaaba8136146faff4b5d2e8f52f7c3950a7d20baebe8d2850e3083b`.
- **47,129** inventoried regular files/symlinks, including bundled runtimes and
  dependencies; contents, file modes and link targets verify on both Macs.
- All **3,831 tracked regular source files** compare to revision `fda0cc3b`.
  Later documentation, CI and test-platform guards do not change runtime code.
- Strict source check/full build pass on macOS and Linux. Mac Mini passes **14
  Wiki + 30 regression + two actual browser cases**. The Air passes **14 Wiki +
  30 regression cases** on the identical transferred artifact. Linux passes the
  **14 Wiki cases**, then **32 browser/regression cases** with the final fixture
  revisions. No failures or skips occur in these passing runs.
- The Wiki suite drives all six original tools through an actual supported Pi
  owner using a synthetic model. It checks routing, rename/backlinks, raw archive
  bytes/manifest, approved skill delivery, read-only refusal, linked/hardlinked
  paths, oversized files, pinned-root replacement, unknown outcomes and killed
  lock-owner review. Model fixtures are distinct from the live checks below.
- Both running Mac installations pass fresh-profile Brave inspection of the
  original Plugins form: enabled Wiki, correct editable path, nine approved
  resources and zero console errors. Mac browser fixtures also check dark-text
  contrast, stale saves, failed application recovery and cold reopening.
- On **each Mac**, the real selected cloud model executes scaffold, write, query
  and lint. Independent reads verify the created page and completed receipts.
  After automatic process recovery, the real model queries the page again.
  Rename/archive are covered by the Pi fixture, not a destructive live-owner test.

Before each activation, the prepared idle owner was retired with its LaunchAgent
held. Configuration, state, shared data and workspace copies verify byte-for-byte;
readable shared SQLite databases also have validated backup images. The previous
release is retained. Existing histories (**four Mini / two Air** at activation),
models, browser login/address, grouping and writing components verify preserved.
The single new Wiki conversation on each machine is left available. Its temporary
installation permission was restored to its original value. The initial new
vault also has a verified private snapshot; no owner material enters public tests.

Both service owners subsequently exit through the guarded shutdown API and are
restarted by their existing KeepAlive LaunchAgent. Histories (**five Mini / three
Air**), Wiki settings, model and browser address survive. HTTP/operator access,
RunAtLoad/KeepAlive and the graphical-login opener verify. This is process recovery;
**neither Mac was physically rebooted in this qualification**. Applications
launchers and the Air's existing AC-only awake policy are preserved.

### Retained failures and scope

An initial Mini model call was refused before dispatch because its changing action
had no connected approval UI. Only the installation conversation received a
temporary permission change for the authorised checks; global defaults were not
changed, and that conversation's original mode was restored.

A proposed Documents vault timed out during admission in the background service
on both Macs, without a mutation-attempt notification or a created vault. Those
refused receipts are retained. Protected-folder access remains unqualified; no
Full Disk Access or privacy-setting change was made. The configured home-level
vault passes the actual service tests. Do not silently move it into Documents.

Fresh Comet profiles first selected onboarding rather than the fixture page,
then injected a font blocked by the existing CSP. The corrected tests own their
page and pass in clean Brave profiles; CSP was not weakened. The Air transfer's
file modes were corrected to the frozen manifest before activation; content
hashes already matched. Linux disposable-build cleanup initially retained a
workspace because of transient process references; after references cleared, the
completed scratch was inspected and removed. This task’s completed app mirrors were removed.

The existing broader native desktop/browser adapter failures recorded in
[installation defaults](HARNESS-INSTALLATION-DEFAULTS.md) are separate. Windows
Wiki remains unsupported; the new POSIX helper cases explicitly skip it. The
POSIX Wiki suite is now included in the existing Linux/macOS SDK workflow, but a
new hosted workflow pass is not inferred from local or installed results.

The Mini's native Codex CLI reports a ChatGPT login. Harness's Pi account store
is separate; this task does not import those credentials or claim an AH Codex
subscription connection. The current model and privately configured local
providers remain unchanged.

## Recovery and retention

Retain the selected Wiki release, the preceding plugin release, the cold
pre-upgrade backup, initial-vault snapshot and small manifests/receipts. Use one
MX disposable build workspace and remove it after verification. Do not retain
per-test application copies. Private installation records identify exact roots,
PIDs and backup hashes; the [portable receipt](../release/harness-wiki-macos-20261020.json)
contains only public source/artifact references and acceptance results.

For a rollback while the new owner is usable, first save Wiki **disabled** through
its revisioned API and confirm application, preserving the vault. The preceding
macOS runtime rejects enabled Wiki configuration. Finish active work and drafts,
prepare shutdown once, hold the LaunchAgent, atomically select the recorded
preceding release and bootstrap the same job. Restore its installation manifest,
not the entire old profile over newer work. If preparation or Wiki application is
unconfirmed, inspect it rather than forcing shutdown or replaying writes.
`host.shutdown` already performs preparation; do not call preparation and then
that composite method a second time. A candidate test alone never proves a
selected or running owner has changed.
