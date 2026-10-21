<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Browser current-chat permissions

In Augmentor Browser, **More → Approval mode** displays the current AH/Pi chat's
mode. Open it and use **This chat** to choose Read only, Ask before actions or
Full access. A separate **Future chats** tab changes the Harness default;
changing either scope leaves the other alone. No existing chat or default is
raised automatically. DSH retains its default-only control.

Read only permits page inspection but blocks navigation, typing and clicking.
Ask before actions requests approval for those actions. Full access removes
per-action prompts after an explicit confirmation; browser target scopes and
limits still apply. Changing permissions does not cancel work already running
or resolve an approval already waiting. Stop or finish the action first; this
Browser control disables selection during a turn.

The old menu wrote only `permission.defaultPreset`, even when the user intended
to change the open conversation. An AH read-only chat could inspect pages but
could not act, whereas a DSH conversation using full access could act. This
was a permission mismatch, not an absent Browser connection. The new control
reads `session.permission` and writes `session.selectPermission` with the exact
chat ID and permission revision. Reading a fresh chat may create its metadata;
it never calls the model. Unsupported, disconnected and historical contexts do
not offer a writable current-chat control. Changed sessions/connections invalidate
pending UI reads; rejected or stale writes refresh the authoritative snapshot.

AH/Pi approvals also use the existing single-document claim registry. With two
Browser panels open, one document owns each approval. A non-owner cannot answer
it, and a disconnected document releases its claim. A native-port failure clears
old claims and interactions. This fixes duplicate prompts and actions waiting on
a second panel. DSH's existing approval transport is preserved.

## Qualification and MX installation — October 21, 2026

The common Browser source passes **31 regression checks**, including five DOM
permission-control cases, approval ownership, AH routing and owner isolation,
real Pi/Chromium actions, and runtime current/default permission behavior.
`tests/browser-session-permissions-chromium.test.mjs` additionally loads the real
extension and native host against a real AH/Pi runtime with an independently
authored synthetic provider and page. Physical browser input opens More and the
permission control, changes modes and handles actual approval dialogs. It checks:

- read-only blocks navigation, typing and clicking;
- Ask before actions allows approved navigation/typing and blocks a denied click;
- cancelling Full access changes nothing; confirming it enables actual actions;
- reload retains the current mode without changing future defaults;
- future defaults are separately editable and do not change the current mode;
- stale revisions, invalid modes and unrelated chat IDs cannot raise permissions;
- two loaded panels produce exactly one approval per action.

The compatible MX 0.2.11 client receives only six Browser UI/bridge files, plus
an overlay provenance receipt. Desktop code, dependency versions, DSH integration,
speech and the AH runtime remain intact. Ordinary candidate checks and the exact
sealed candidate pass; the selected native host and actual unpacked extension
folder also pass the action test against the installed AH runtime on isolated
data. The live unpacked extension predates the packaged client: its separate
narrow backport keeps its existing custom modules and adds the approval registry
and service-worker hookup without importing newer queue or Codex modules. No owner model call, shopping replay or chat-policy change is used for
qualification. See the [installed evidence](../release/browser-chat-permissions-mx-20261021.json).

The immutable client was staged and selected through the standard deployment
helper. Unchanged immutable files share storage using hard links; changed files
are independently replaced, and the previous seal is verified unchanged. Managed
scratch is removed. The previous application and a small backup of replaced
extension files remain available for rollback; Browser profile/storage is not
moved or rewritten.

**An already loaded owner extension still needs one reload** from Chromium's
Extensions page, followed by reopening Augmentor Browser. Its in-memory code is
not evidence of the new disk contents. No forced browser restart or owner-draft
loss is part of this update. The automated fresh Chromium run verifies the new
installed code, not a reload of the owner's existing Browser window. Existing
Desktop windows likewise retain their prior build until reopened; their UI did
not change in this update.

The common source is shared with macOS and its DOM tests are platform-neutral.
This installed qualification and rollout cover MX Linux only. No signed Mac
Desktop replacement or Comet extension update is claimed here. Windows remains
outside this MX-first deployment.
