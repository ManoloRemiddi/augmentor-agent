<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Saved prompts and DSH commands

Type `/news` or `/crit` and press **Enter** to insert the highlighted saved
prompt into the composer without sending it. Review/edit it, then press **Enter
again** to send. Tab and clicking a completion also insert the prompt. Arrow keys
select a different match. Both Desktop and Browser implement this behavior;
sharing the prompt service does not automatically share their keyboard handlers.

If a prompt and DSH command share a name, Enter chooses the visible prompt.
Dismiss the picker with Escape, then Enter to submit the literal command; the
Send button also submits the current draft. Commands without a matching prompt,
such as `/goal pause`, retain their existing command routing. Enter waits while
the initial prompt catalog loads. Clipboard expansion inserts one snapshot and
never sends automatically; Browser blocks another Enter during its asynchronous
clipboard read. Holding Enter does not send the newly expanded draft.

## September 26 correction

This restores the owner's requested two-step Enter interaction. The September 16
Enter-bypasses-picker behavior below is historical and superseded. Source is on
`fix/slash-prompt-enter`, based on main `43acb1d`; both renderers and their tests
change together. Regression coverage includes news/crit, highlighted choice,
same-named commands through Escape, no match, delayed loading, clipboard expansion
and the full Browser sidebar's first-Enter/no-send and second-Enter/send sequence.


Source qualification: build, 46 Browser tests, 17 native prompt/improvement tests,
7 native command transport tests and 1 Node command-routing test passed. These
use deterministic Qt/DOM/transport fixtures; no prompt was sent to a live model.


Command results appear as DSH messages in the transcript, including when reopening history. Unknown commands and command errors keep the draft and never fall through to a model prompt. Network failures are not replayed. Ordinary text and absolute paths such as `/home/example/file.txt` retain normal prompt routing. Completed commands do not remain in the desktop prompt queue or latch the browser turn indicator.

DSH 0.1.5-rc.1 disables the host `command-goal` row because its shipped session presets register that command. Older custom presets can omit it. Augmentor setup now registers `command-goal` in both product presets, and the browser preset gets `tool-goal` so the model can manage goal completion; the desktop already includes that tool.

## Historical September 16 command qualification

On this machine, `~/.dsh/cordis.patch.yml` now overrides `command-goal` with `disabled: false`, providing a host fallback for existing custom presets. The pre-change file is preserved as `cordis.patch.yml.before-goal-20260916`. The installed harness reloaded this change without restarting: the PID stayed unchanged and the active task remained running. Live command catalogs for standard-codex, augmentor-linux-product, and augmentor-browser-product now include goal. Fresh test sessions in all three presets successfully executed `/goal`, returning its usage. Desktop/browser proof histories contained `command/run` and `command/done`, with no model turn. The browser preset also received tool-goal while preserving its customized text; its existing ownership manifest was already out of sync, so it was not rewritten to claim ownership of those customizations.

Validation on 2026-09-16: 17 Node tests (browser picker, renderer, command transport), 12 Qt prompt/history tests, 7 Python transport tests, 6 queue tests, and 4 setup tests passed. Live verification exercised goal inspection, not autonomous model-driven goal completion.

The installed application hotfix is staged under `outputs/goal-hotfix-20260916`. Its installer verifies the original hashes of all ten files, preserves a rollback copy at `/usr/lib/augmentor.before-goal-20260916`, and applies only this fix. It does not deploy unrelated working-tree UI changes. The loaded Chromium extension uses the legacy checkout under `~/Desktop/Deepseek harnes test/augmentor/extension`; its three affected files were patched in place with a backup at `extension.before-goal-20260916`, preserving other local changes. Reload that extension after installing the host update, and reopen Augmentor Desktop to load updated Python modules.
