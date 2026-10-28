# DSH Metafolder Plugin

Visual **meta-folders** for the DeepSeek Harness sidebar.

Nest real workspace folders and individual sessions under named, collapsible groups — for example every
Resonant OS project under one "Resonant OS" meta folder. The safe organization layer changes how
sessions and workspace folders are visualised and persists in this browser’s localStorage. An optional Host integration exists,
but durable Host storage and cross-device sync are not implemented:

- workspace paths, permissions, and session working directories are untouched;
- workspace and session grouping is metadata-only;
- physical workspace moves remain guarded until DSH exposes a supported path-migration API;
- ungrouping returns a folder to the main list unchanged;
- the AI's permissions stay attached to the real folder, because the real folder
  is what the plugin renders.

## Features

- **Meta-folders** over the real workspace rows, with per-folder session counts.
- **Drag and drop**: drag a workspace or session row onto a meta folder to file it;
  drop it on the list background to take it out again.
- **Local assignments**: groups and assignments survive page reloads in the same
  browser. Clearing browser storage removes them. The optional Host service uses
  memory only; it is not durable storage or cross-device sync.
- **Physical move boundary**: actual workspace/project moves are intentionally guarded until
  DSH provides a workspace/session migration API or a dedicated atomic Host capability.
- **Row menu**: `→ <meta folder>` to file, `Remove from meta folder` to unfile,
  plus rename / move up / move down, and delete workspace.
- **Per-folder colour**: pick it when you create the folder — an eight-swatch
  palette, the theme colour, or a custom colour — and change it any time from
  *Rename meta folder*. The colour tints the folder glyph, its label, and the
  drop-target outline.
- **View options** (the shipped menu, preserved): group by **Workspace** /
  **Flat**, order by **Manual** / **Updated**. Manual order honours the order
  already stored by the shipped browser (`dsh.workspace.view.v5`).
- **Add workspace** still works, from both the wide sidebar and the collapsed
  rail, via the composed directory-flow picker with a Host-picker fallback.
- Session search (local + Host index), rename / fork / archive per session,
  per-workspace new session.

Everything the shipped browser offered is still here — the meta-folder layer is
an addition to the toolbar, not a replacement.

## Requirements

- DeepSeek Harness `>= 0.1.5-rc.1` on the `web` profile.
- The shipped `@deepseek-ai/dsh-client-ui-sidebar` and
  `@deepseek-ai/dsh-client-ui-workspace` client packages (the seat it shadows).
- Node `^22.19.0 || >=24.0.0` to build the browser half.

## Install

One package, two halves:

| file | role |
| --- | --- |
| `lib/index.js` | host half — optional in-memory service; mounting it enables the client-module scan |
| `lib/client.js` | browser half — shadows the `sidebar.workspaces` seat and renders the meta-folder browser |
| `client.js` | **source of truth** (dynamic-Cordis form, also usable with the `cordis_define` runtime tool) |

`lib/client.js` is generated from `client.js`; regenerate and check it after
editing:

```sh
npm run check     # build + syntax + export smoke test
```

### Download and install

[Download version 1.2.1](https://github.com/ManoloRemiddi/DSH-Metafolder-Plugin/releases/tag/v1.2.1).
The `.tgz` asset is ready to install; no build or manual symlink is needed:

```sh
dsh plugin --profile web add https://github.com/ManoloRemiddi/DSH-Metafolder-Plugin/releases/download/v1.2.1/dsh-metafolder-plugin-1.2.1.tgz
```

Finish any running tasks, restart your existing DSH process, and reload its web
page. Use your actual profile if it is not `web`. The shipped sidebar and workspace
packages must be present. This release was checked with DSH 0.1.5-rc.1; newer
releases may change the UI interfaces it uses.

For an existing manual symlink installation, update that checkout to `v1.2.1`
and keep its existing registration. Do not add a second copy or duplicate patch row.

For development, clone the repository and run `npm run check` and `npm test`.
The built browser file is included in both the repository and the release.

> **Registration note:** a `single` slot takes one registration per priority and
> the lowest renders, so the seat is registered with `priority: -1` to shadow
> the shipped browser at `0`. Registering at the default `0` is rejected with
> *"already has a registration at priority 0 … register at a different priority
> to shadow it"*.

### Remove

For a CLI installation:

```sh
dsh plugin --profile web remove dsh-metafolder-plugin
```

For the older manual installation, remove only its `metafolder-plugin` insert
row and its package symlink. Restart DSH and reload the page. Groups stay under
`dsh.wsmeta.v1` in localStorage; uninstalling does not move workspace files.

## Support and related plugins

[Report a problem](https://github.com/ManoloRemiddi/DSH-Metafolder-Plugin/issues)
with your DSH version, browser version, install method and reproduction steps.
Do not attach credentials or private session logs.

Browse the [DeepSeek Harness Plugins collection](https://github.com/ManoloRemiddi/deepseek-harness-plugins).

## Verified against

- `@deepseek-ai/dsh-client-ui-workspace` — `sidebar.workspaces` registration,
  the `sidebar.workspaces.directoryFlow` hole, `WorkspaceBrowserProps`.
- `@deepseek-ai/dsh-client-ui-sidebar` — owner share `{ wide, expandSidebar }`.
- `@deepseek-ai/dsh-api-workspace-controller` / `dsh-api-session-controller` —
  workspace and session service methods and snapshot shapes.
- DSH physical move boundary: the remaining work for true physical moves requires an
  upstream DSH workspace/session migration API or a dedicated Host capability that atomically
  updates the filesystem, workspace registry, and session metadata.

MIT © 2026 Manolo Remiddi
