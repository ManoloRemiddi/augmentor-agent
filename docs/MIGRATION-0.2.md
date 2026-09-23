<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->
# Installing and rolling back the shared implementation

## Layout

Development remains in this monorepo. Browser source was imported with history under `apps/browser`; the Qt surface is under `apps/native`. Engine-native sessions and credentials remain in their existing DSH/Pi locations.

Shared prompts live in `$XDG_DATA_HOME/augmentor/prompts.sqlite3` (default `~/.local/share/augmentor/prompts.sqlite3`). The private local socket lives in `$XDG_STATE_HOME/augmentor/prompts.sock`. `AUGMENTOR_SHARED_DATA` and `AUGMENTOR_SHARED_STATE` provide isolated test locations. The service starts on demand and does not require either harness to be running. This is sharing on one computer; cross-computer synchronization is not enabled.

## Build and deploy

```sh
npm ci --ignore-scripts
npm run build
npm test
npm run test:native
node --test apps/browser/test/prompts.test.mjs
python3 scripts/migrate-prompts.py --inspect
python3 scripts/migrate-prompts.py --apply
python3 scripts/install.py
python3 ~/.local/share/augmentor-pi/app/scripts/install-browser-host.py
```

For an existing unpacked extension, the browser-host installer accepts `--deploy-extension /path/to/existing/extension`. It verifies the extension key, stages the new files and retains a timestamped backup. Reload that extension in `chrome://extensions`. Alternatively load `~/.local/share/augmentor-pi/app/apps/browser/extension` as unpacked. The stable extension ID preserves Chrome storage. Do not run legacy browser auto-updaters over the unified installation; the new host rejects that replacement path.

To forward DSH's existing settings editor to the shared service:

```sh
dsh plugin --profile web add 'link:/home/example/.local/share/augmentor-pi/app/adapters/dsh-prompt-library' --ignore-scripts
```

Use the installed application path for your account. Back up the profile manifest/lockfile first, check that no DSH sessions are running, then restart the DSH web service if its plugin loader has not reloaded. Verify `/api/augmentor-prompts` and confirm the old independently writable `prompt-library` settings namespace is absent. The migration script imports old settings only before this writer cutover; subsequent exports/backups must use the shared service.

Existing Linux entry points can call `scripts/augmentor-linux --harness dsh` or `--harness pi`. They activate the one installed UI. Invoking the main launcher without a harness preserves the last selection and toggles visibility. Legacy desktop IDs and key bindings can be retained.

## This machine's migration

- All three source prompt bodies preserved. Pi's `/correct` stays `/correct`; the differing DSH version is `/correct-imported-2`. Nothing overwrote the source Markdown/YAML stores.
- Prompt backups: `~/.local/share/augmentor/backups/prompt-migration-20260906-111851` and `prompt-migration-20260906-114302`.
- Profile/launcher backups: `~/.local/share/augmentor/backups/unified-cutover-20260906-114302`.
- Previous application: `~/.local/share/augmentor-pi/app.previous`.
- Previous browser extension: `/home/example/Desktop/Deepseek harnes test/augmentor/extension.before-augmentor-20260906-115638`.
- Chromium still needs its Augmentor extension reloaded to activate the deployed 0.2.0 code. No browser restart is required.
- The existing unpacked extension directory is now a deployment copy. Development belongs in the monorepo; do not apply legacy repository updates over it.
- Existing Linux DSH/Pi launchers point to the shared app; old source repositories remain intact. The idle legacy Linux process was closed with an empty draft. Native Pi session/draft/visibility and the Ctrl+Hangul shortcut were checked across replacement.

## Rollback

Stop active turns first. Preserve the shared SQLite database and take an SQLite online backup before changing writers. Restore `app.previous` to the application path, restore the backed-up launchers and DSH profile manifest/lockfile, reinstall that profile's dependencies using its supported CLI, and restart DSH while idle. Restore the browser extension code backup and reload the extension. Retain the shared database: reverting old clients does not merge edits back into their original private stores.

A rollback of the UI alone must not silently reactivate multiple writable prompt stores. Export newer shared edits and reconcile them explicitly before resuming legacy writers. Do not sync an open SQLite database through a folder-sync service.

## Memory follow-up

The user selected Hindsight as the first provider on 2026-09-06. No provider is attached yet. The next memory slice must connect the chosen deployment, map the optional interface to Hindsight's actual storage/retrieval semantics, and test context insertion through each harness, cross-surface recall, provider failure and removal. Both surfaces and both harnesses share the same Augmentor memory service, with user/project scope and provenance preserved. Ordinary chat must continue to work when memory is unavailable.
