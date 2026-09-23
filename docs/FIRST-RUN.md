<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Connect your model in the preview

Install the [Debian preview packages](LINUX-PACKAGES.md), then open **Augmentor
Agent** from the application menu. On a new Pi configuration with no available
model, the connection form opens automatically. You can reopen it from
**More options → Connect a model**.

1. Give the connection a name. Enter your OpenAI-compatible endpoint URL,
   exact model ID and API key. Use the model limits supplied by your provider.
   A local endpoint on this computer can omit the key. Remote endpoints require
   HTTPS. Other Pi provider formats remain available in **Models & providers**.
2. Choose an approval mode. **Ask before changes** is the default. Routine
   information checks run directly; actions that change files or applications
   require approval. **Read only** blocks changing tools. **Allow actions without
   asking** gives the tools your Linux user's access. These are tool policies,
   not operating-system sandboxes.
3. Enable **Image input** only for a model that supports images, then press
   **Check connection**. Augmentor sends one short request through Pi, with a
   generated test image if selected. The provider may charge for it. It sends no files, history
   or tools, performs no automatic retry, and saves no connection yet.
4. After the check succeeds, press **Save and use model**. Changing any connection
   field requires a new check. If another window changes the model configuration
   during setup, Augmentor refuses to overwrite it and requests another check.
5. Send a message, then try a bounded file task. Keep **Stop** available while
   the agent works. The model must support tool calls for file tasks; the initial
   connection check establishes response/input acceptance, not tool or visual
   reasoning quality.

Credentials are stored without encryption in the user's private Pi configuration
(`~/.config/augmentor-pi/agent/models.json` by default), with mode `0600` and a
private parent directory. Setup treats keys as literal text, including `$` and
`!`; they cannot introduce Pi configuration commands or environment expansion.
The normal conversation and provider settings remain independent of the setup
check, and reopening the app does not repeat it.

The browser companion offers the same checked Pi setup automatically on a fresh
profile. Reopen it with the **Connect model** icon. Its test, save and cancellation
use the same runtime boundary and private configuration as Linux. Browser-role
file and shell tools remain unavailable even with automatic approval.

To use DSH, follow [Connect DSH](DSH-SETUP.md) from either surface. It checks the
supported separately installed DSH version and installs Augmentor's owned roles;
DSH keeps its own model configuration. Optional [Hindsight memory](MEMORY.md) is
configured independently in Memory. Linux's [desktop control preview](DESKTOP-CONTROL.md)
uses OS sharing consent and requires image input. See the
[execution ledger](PRODUCTIZATION-STATUS.md) for the remaining product scope.

## Development evidence

`scripts/first-run-proof.py` opens the real Qt window against an isolated Pi
runtime and deterministic HTTP model. It clicks the form, checks that testing
has no tools or persistent configuration, edits a field and requires rechecking,
saves/selects the model, completes a real Pi file write and reopens without
replaying a request. It can run against `/usr/lib/augmentor` to exercise the
installed application. This is a repeatable UI/SDK test, not live-provider,
Wayland-computer-use or independent-user certification.
