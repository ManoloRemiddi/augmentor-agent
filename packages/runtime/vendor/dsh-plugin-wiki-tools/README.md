# dsh-plugin-wiki-tools

English | [中文](#中文)

Native [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) tools for an Obsidian wiki vault: `wiki_query`, `wiki_write`, and `wiki_lint` implement the mechanical core of the wiki skill suite — path routing, frontmatter completion, index/log bookkeeping, source delta tracking, and health checks — so the model spends its turns on synthesis instead of filesystem chores.

Pair with **[dsh-plugin-wiki-skills](https://github.com/Lion-1209/dsh-plugin-wiki-skills)** for the prompt-level skills (`wiki`, `wiki-ingest`, `wiki-query`, `wiki-lint`, `save`).

## Attribution

The vault layout and operation contracts follow the LLM Wiki pattern (Andrej Karpathy) as embodied by [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) (MIT, © 2026 AgriciDaniel). This package is an independent plain-ESM implementation of the mechanical core; it contains no code or skill text from claude-obsidian.

## Tools

| Tool | What it does |
| --- | --- |
| `wiki_query` | Quick mode returns `hot.md` + `index.md` verbatim (the skill's read order); standard mode is full-text search over content pages with snippets and the inbound/outbound link graph |
| `wiki_write` | Writes one page with complete bookkeeping: type→folder routing, frontmatter completion (keeps `created` and unknown fields on update), filename-uniqueness guard, master-index entry, log entry; with `source_path`, records the source hash and skips unchanged sources unless `force` |
| `wiki_lint` | Health check: duplicate filenames, dead wikilinks, orphan pages, frontmatter gaps, empty sections, stale index entries, stale hot cache — report only, with suggestions, written to `wiki/meta/lint-report-<date>.md` |

## Install and configure

```sh
dsh plugin --profile web add dsh-plugin-wiki-tools
```

`vaultPath` is **required**. The boot fails loud until you set it from your profile's `cordis.patch.yml`:

```yaml
- id: wiki-tools
  config:
    vaultPath: /absolute/path/to/vault
    # optional: reroute page types to your vault's folders; index section
    # headings follow the mapped folder name (e.g. "## Areas")
    typeFolders:
      domain: wiki/areas
```

The vault is the directory holding `wiki/` and `.raw/` — scaffold it first with the `wiki` skill's SCAFFOLD operation. `maxQueryResults` (default 10) is optional. `wiki_write` refreshes existing index entries in the section's own style (`: ` or ` — `), so em-dash vaults stay consistent.

## Design notes

- The vault is host-local user data outside any session workspace (cross-project referencing is the point), so the tools read and write through `node:fs` against the explicitly configured absolute root — not a dsh filesystem seam.
- Writes serialize per target file in-process; filenames are guarded unique vault-wide because wikilinks resolve by bare name.
- Registers on `ctx.tools` via `defineTool`; schemas stay stable regardless of vault contents.

## Develop

```sh
npm install
node --test
```

## License

[MIT](LICENSE)

---

# 中文

Obsidian wiki vault 的 DeepSeek Harness 原生工具：`wiki_query`、`wiki_write`、`wiki_lint` 实现知识库技能套件的机械核心（路径路由、frontmatter 补全、索引/日志簿记、来源增量追踪、健康检查），让模型把轮次花在综合而非文件操作上。与 [dsh-plugin-wiki-skills](https://github.com/Lion-1209/dsh-plugin-wiki-skills) 配套使用。

## 出处

vault 布局与操作契约遵循 LLM Wiki 模式（Karpathy），形态来自 claude-obsidian（AgriciDaniel，MIT）。本包为独立的纯 ESM 实现，不含 claude-obsidian 的代码或技能文本。

## 安装与配置

```sh
dsh plugin --profile web add dsh-plugin-wiki-tools
```

`vaultPath` 为必填项：在你的 profile `cordis.patch.yml` 里覆盖 `wiki-tools` 行的 config 指向 vault 根目录（含 `wiki/` 与 `.raw/`，先用 wiki 技能的 SCAFFOLD 操作搭建），否则启动时会明确报错并给出示例。
