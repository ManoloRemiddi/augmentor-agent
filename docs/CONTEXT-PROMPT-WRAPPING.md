<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Context prompt wrapping on Pi

## Request-time binding — October 12

The original Settings → Plugins → System Prompt **Prefix** and **Suffix** fields
now connect to the private revisioned `dsh-context` namespace. The original
card, textarea draft/blur behavior, layout and CSS remain unchanged. Its nine
display defaults and these two text fields make **eleven connected controls**.
Both text fields default to empty and accept at most **64 KiB UTF-8 each**.
Values remain exact strings, including whitespace, line endings, Unicode and
`{{variables}}`; they are never interpolated. The supplier's original callback
disables a section only when its text is empty or whitespace-only.

The verbatim public
[`promptInjection.ts`](https://github.com/bowenliang123/dsh-context/blob/2c8095c34da3fcef729a01437d2df65c83e08499/src/host/promptInjection.ts)
registers its original prefix/suffix sections against a small authored registry
seat. A separately audited Node transpilation contains this single source and
zero runtime imports: the Cordis/config imports are type-only. Its Apache-2.0
licence and exact original source hash accompany the generated module. Current
selection is **108 dsh-context files: 92 verbatim / 16 marked adaptations**, at
0.68.1 / 2c8095c34da3fcef729a01437d2df65c83e08499. The **483-file MIT DSH
selection**, original GUI/CSS/icons/licence bodies and locked npm dependencies
remain preserved. No supplier agent Host or Cordis runtime is mounted.

## Composition and authority

Pi's supported `context_with_system` hook runs before every conversational model
call, after its ordinary context handlers and restored system/tool state. The
adapter reads one current private preference revision synchronously, then
executes the original section providers against that snapshot. Changes apply
from the **next model request**, including a subsequent step in an already
running turn. Saving text starts no model call, changes no submitted user message,
reloads no owner and resumes/replays no work.

The prefix is prepended to the leading system message's content. Structured text
blocks, existing sections, tool additions/removals, timestamps and other fields
remain intact. The suffix is added as the last named section on the final system
message, preserving Pi's ordered system updates. A pre-existing owner of the
canonical suffix name keeps its section; an unused numbered name is chosen for
the new section. These are ephemeral request copies; native source entries and
Pi's stored session context are never rewritten. No leading system message
means explicitly unavailable wrapping rather than inventing a prompt/tool state.
Both inactive sections leave the messages unchanged.

The same adapter runs for managed Native and Browser conversations, distinct
bounded agent workers, and the existing desktop specialist's own owner. It adds
no tools, grants or approvals. The desktop owner receives its own context
provenance binding; its task/evidence/consent/limits remain unchanged. Standalone
prompt-improvement and summary requests have separate instructions and do not
use this conversational hook. Later approved provider hooks and provider-specific
system conversion can still transform the request; the final captured provider
body remains the authority for what was sent at that observed boundary.

Preference writes remain operator-only, one field at a time, revision-checked
and atomically persisted before acknowledgment. Read-only parent/child inspectors
read no global profile and cannot change text. Stale, refused, lost or malformed
acknowledgments freeze the card until explicit Refresh; no automatic write retry
is introduced. Invalid persisted text types or over-limit strings normalize to
the empty default. The UI and Host both enforce the UTF-8 bound.

## Transparency and evidence

The existing bounded `context/provenance` record gains a request-local
`promptWrapping` snapshot with the applied revision, literal registered sections,
disabled/applied/unavailable state and actual suffix name. The original Context
system browser displays the effective captured prompt, and **Raw Pi context and
saved entries** exposes this provenance alongside before/after transforms and
provider bodies. Earlier snapshots retain their own text/revision after an edit.
Capture-disabled policy and the existing aggregate 8 MiB snapshot budget apply;
private text does not enter metadata-only evidence. Managed-hook application is
not a claim that an opaque later hook or remote service preserved it.

The public SDK fixture holds an actual tool step, changes both fields through the
Host, and proves that the first provider body keeps revision 2 while the next
request in the same turn receives revision 4. Tool schemas stay equal; cold reads
preserve exact saved requests/native originals and start no inference. Additional
actual SDK/Host fixtures cover Browser, distinct agent workers and the desktop
specialist, preserving scoped grants and the synthetic consent/evidence owner.
A structured multi-system case protects content blocks, named-section updates,
tool declarations and a colliding section name. Capture-disabled provenance
stays private even after later capture changes.

The actual Chromium fixture edits the original textareas using input and blur,
checks literal multiline/Unicode values after reload and cold Host restart,
keeps existing display-default/conflict checks, and proves inspectors remain
disabled. That fixture sends no model request; effective application is qualified
by the separate real SDK/provider tests. Initial focused runs failed on stale
disabled-textarea expectations, an incorrect payload page limit, and guessed
job/desktop-peer property names. The fixtures now use the served contracts and
bounded hash-verified paging. No product deadlines or two-worker schedule are
relaxed. Source, ordinary and installed qualification are separate checkpoints.

## Qualification and remaining work

Focused source evidence passes **20/20 across four files**, Node 24.19.0, prepared
QtTest, two workers and unchanged deadlines. Source check/build, selection hashes
and both separate browser/Node supplier graphs pass. The final wider source
cohort passes **294/294 across 54 files**, zero failures/skips/cancellations.
Fresh ordinary and installed MX qualification follow separately. The currently selected/running
MX preview remains the [qualified original Fleet runtime](CONTEXT-FLEET.md#installed-mx-qualification--october-12);
building this candidate does not patch or activate that release.

Reproduce after the normal build:

```sh
AUGMENTOR_PYTHON=/path/to/prepared/python node --test --test-concurrency=2 tests/pi-prompt-wrapping.test.mjs tests/pi-context-provenance.test.mjs tests/harness-context-preferences.test.mjs tests/harness-context-preferences-chromium.test.mjs
```

The wider cohort is the [52-file Fleet recipe](CONTEXT-FLEET.md#installed-mx-qualification--october-12)
plus `tests/pi-context-provenance.test.mjs` and
`tests/pi-prompt-wrapping.test.mjs`. Ordinary runs use their bundled Node and
`AUGMENTOR_PI_TEST_ROOT`. These independent synthetic fixtures contain no owner
source, private conversations or live service credentials.

This request-time composition qualifies the original two controls, not full
Harness migration. Coordinated Teams/mailbox, complete viewer/reference/command/
skill/admin/question/plan/provenance/effect-success and memory/voice/Home/browser/
desktop acceptance remain open. Public Debian Sharp/libvips source/collector/
rebuild, privacy/public packaging and physical/live/platform gates remain open.
DSH remains available. Windows, macOS and other Linux implementation remain
deferred for owner MX feedback; the shared Host/browser code and synthetic peer
checks do not prove physical OS parity.

