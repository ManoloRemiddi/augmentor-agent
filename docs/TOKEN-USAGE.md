<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Recorded token activity

The Desktop Agent page shows the past 365 days as a compact activity calendar.
The larger animated profile, understated stacked Identity/Memory actions and
single access row leave a distinct space for activity at the bottom of the fixed
settings frame. The default profile fits without scrolling at the standard
700 × 760 design size. A custom photo uses the same space, with Reset image next
to the profile caption. Narrow screens place the avatar above the name and may
scroll vertically; the calendar and settings do not scroll horizontally.

The visual reference is [GitHub's contribution calendar](https://docs.github.com/en/account-and-profile/concepts/contributions-on-your-profile).
[GitHub's accessibility discussion](https://github.com/orgs/community/discussions/49015)
also informs day tooltips, arrow-key selection and a visible text summary. Each
square represents one local calendar day. Intensity compares that day's reported
total with the maximum recorded daily total in the displayed period; it is not a
quota, cost or billing estimate. Click or use arrows to select a day. Home/End
select the first/latest day. The readable summary reports total, input and output;
blank days say **No recorded tokens**, rather than claiming no model activity.
The calendar uses the current theme and accent colour.

## Data and coverage

`services/usage/history.mjs` independently reads existing local native journals;
`apps/native/augmentor_linux/token_usage.py` loads its aggregate asynchronously.
The helper returns dates and counts, never conversation text. Opening the page
or pressing Refresh reads history; there is no background polling, new database,
provider request or model inference. Nothing in source history is modified.

- DSH: the registered shared harness home, personal Augmentor Linux/Browser
  preset aliases, v3 assistant usage in plain or concatenated Zstandard journals.
  Compressed history is preferred when both representations exist. Seeded forks
  skip inherited events through the end-seed marker.
- Pi: registered session metadata pointing to its in-state native SDK journals.
  Copied inherited native entries are counted once. Display journals lack usage
  and are not used. Outside-state and symlink journal paths are rejected.
- Codex: ready registered Augmentor-owned threads and their native rollouts.
  Cumulative token-count notifications become validated positive deltas;
  repeated notifications and verbatim inherited events are counted once.
  A delta requires matching last-turn usage, rather than invented input/output.
  Unrelated Codex app chats are outside this scope.

Totals honor each provider's recorded total. Cached tokens may already be part
of input or total and are not added a second time. This scope includes recorded
Desktop and Browser personal-agent usage across supported registered harnesses,
not all account/provider activity, memory processing, other presets or arbitrary
historical formats. Deleted histories cannot be reconstructed. A local day uses
the machine timezone; DST boundaries follow its local calendar.

Missing/invalid usage, unreadable journals, torn tails and bounded scan limits
produce **Partial history; some counts unavailable**. Valid committed prefixes
survive incomplete final writes. Individual files, decompression, file count,
read bytes and time are bounded (64 MiB file, 128 MiB decompressed DSH journal,
4,000 journals, 512 MiB read, 12-second scan). Counters and accumulated totals
must be nonnegative safe integers. Unavailable helpers show **Usage unavailable**
and allow refresh; an empty usable history shows an empty calendar explicitly.
A partial total is an observed amount, not an exhaustive billing statement.

## Qualification — 2 October 2026

Shared native source: 637 cases, 635 pass and two Mac-only skips. New Qt cases
exercise readable keyboard announcements, click selection, 365 cells fitting
narrow widths, serialized refresh and distinct empty/partial/error states.
The actual Window checks standard frame fit with a custom image and loaded
usage, bottom alignment in dark/light themes and no narrow horizontal overflow.
The full root Node suite passes 491 cases (489 pass, two opt-in memory proof
skips). Seven independently authored Node fixture cases check DSH compressed/seeded
history, Pi registration, Codex deltas/forks, unavailable counts, torn writes,
scan limits and atomic overflow rejection. Rendering fixtures are synthetic.

A read-only local scan also finds real provider counters in DSH/Pi history and
finishes in about one second, with incomplete coverage labelled. No conversation
text, machine-specific summary or live usage image is published. This is stored
usage evidence, not a new live model or billing reconciliation proof. Linux and
Mac share the implementation; installed Mac GUI acceptance remains unverified.
Installed candidate identity and Node suite evidence follow in
[Desktop agent settings](AGENT-SETTINGS.md#agent-profile-and-token-activity--2-october-2026).
