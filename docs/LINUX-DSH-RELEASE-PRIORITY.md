<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Linux DSH first release priority

User direction on 2026-09-15 supersedes the earlier simultaneous Linux/macOS
and DSH/Pi release sequence. Remaining account usage is approximately 20%, as
reported by the user; minimize repeated testing and unrelated development.

1. Finish and qualify Augmentor Agent Desktop for Linux using DSH only.
2. Match the enabled plugins and functionality of the user's working installation.
   Installed dependencies alone do not establish this baseline; resolve enabled
   plugins, presets and integrations before declaring parity. Preserve existing
   configuration, credentials, sessions and disabled-plugin choices.
3. Freeze and publish the Linux release once its acceptance and distribution
   requirements pass. Do not carry macOS-only signing/source gates into Linux
   unless that Linux artifact actually distributes the affected dependencies.
4. Reassess remaining budget, then complete macOS with DSH only.
5. Pause Pi development and release qualification. Preserve its code and user data;
   do not spend the remaining budget removing an existing implementation solely
   because its release support is deferred. Windows remains deferred.

## Immediate critical path

- Record effective DSH plugin/preset baseline and compare application exposure.
- Address Linux capture reliability and package the latest invalid-frame guard.
- Run targeted regression checks for actual changes; retain valid candidate 8
  DSH and package lifecycle evidence rather than blindly rerunning every suite.
- Qualify the final Linux artifact and supported distro/session labels, preserve
  installation/recovery data, and complete applicable licensing/download guidance.
- Record source/artifact identity and remaining blockers honestly before publishing.

Current Debian candidate 12 includes the invalid-frame guard and accessibility
focus traversal fix. Its installed DSH Stop test passes without diagnostic
instrumentation. Candidate 11 passes installed DSH/Model Picker checks; candidate
8 retains package lifecycle evidence. The current source passes 232 native tests
and TypeScript checking. Intermittent Wayland capture and full enabled-plugin
workflow qualification remain open; none of these candidates is public-ready.

The dependency snapshot in
`outputs/cross-platform/linux-dsh-reference-dependencies.json` is inspection
input only. It is not an enabled-plugin inventory or compatibility claim.
