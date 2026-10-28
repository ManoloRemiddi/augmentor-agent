# dsh-plugin-wiki-skills

English | [中文](#中文)

The [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian)-derived knowledge-suite skills as a [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) plugin: `wiki`, `wiki-ingest`, `wiki-query`, `wiki-lint`, and `save`, mounted on the `ctx.skills` registry as a read-only bundled provider.

## Attribution

The five skills are adapted from [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) by AgriciDaniel (AI Marketing Hub), MIT licensed — see [ORIGINAL_LICENSE](ORIGINAL_LICENSE). The adaptation is based on the v1-era prompt-centric skills, substantially rewritten for ZCode and now for dsh. Changes made in this adaptation:

- Removed the upstream Community Footer (promotional block) and the routing rows for sub-skills not bundled here (`autoresearch`, `canvas`).
- Added a `dsh adaptation` note to each skill: upstream product scripts (transport detection, `wiki-mode.py`, `wiki-lock.sh`, DragonScale address allocation, `.vault-meta/`) are not bundled; the companion package **[dsh-plugin-wiki-tools](https://github.com/Lion-1209/dsh-plugin-wiki-tools)** provides native tools for the mechanical core.

The vault design itself follows the [LLM Wiki pattern](https://github.com/karpathy) described by Andrej Karpathy.

## Install

```sh
dsh plugin --profile web add dsh-plugin-wiki-skills
```

The package declares a `dsh.bundle` patch that inserts one `wiki-skills` row. Pair it with `dsh-plugin-wiki-tools` for the native `wiki_query` / `wiki_write` / `wiki_lint` tools.

## Skills

| Skill | Routes when |
| --- | --- |
| `wiki` | Vault setup, scaffolding, cross-project referencing, hot-cache management |
| `wiki-ingest` | Ingest sources into the vault: extract entities/concepts, cross-reference, log |
| `wiki-query` | Answer from the vault: hot cache → index → pages, with citations |
| `wiki-lint` | Health check: orphans, dead links, frontmatter gaps, stale index entries |
| `save` | File conversation insights back into the vault |
| `think` | The 10-principle reasoning loop (OBSERVE…GROW) every wiki skill maps onto |
| `obsidian-markdown` | Obsidian Flavored Markdown syntax reference (wikilinks, callouts, embeds) |
| `obsidian-bases` | Obsidian Bases reference for data views over note properties |
| `defuddle` | Cleaning fetched web pages before ingestion (ad-free readable text) |

The upstream `autoresearch`, `canvas`, `wiki-cli`, `wiki-fold`, `wiki-mode`, and `wiki-retrieve` skills are not bundled: their script-bound mechanics are covered natively by [dsh-plugin-wiki-tools](https://github.com/Lion-1209/dsh-plugin-wiki-tools) (query/write/rename/scaffold/archive/lint with BM25 retrieval); the research and canvas workflows remain upstream features.

## Behavior

- Registers one provider named `wiki-skills` with bundled-rank (600) candidates, so project, runtime, and user skills with the same name win over this suite.
- Each skill declares `resourceBase: directory`, letting bodies reference sibling files under `references/`.
- Malformed frontmatter fails loud at discovery instead of silently skipping a skill.

## Develop

```sh
npm install
node --test
```

## License

[MIT](LICENSE) for this packaging. The bundled skill content derives from claude-obsidian (MIT) — see [ORIGINAL_LICENSE](ORIGINAL_LICENSE).

---

# 中文

claude-obsidian 衍生知识库技能套件的 DeepSeek Harness 插件版：`wiki`、`wiki-ingest`、`wiki-query`、`wiki-lint`、`save` 五个技能，以只读 bundled provider 挂到 `ctx.skills`。

## 出处归属

五个技能改编自 AgriciDaniel 的 [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian)（MIT，见 [ORIGINAL_LICENSE](ORIGINAL_LICENSE)），基于其 v1 时代以提示词为中心的版本，经 ZCode 适配后再度适配到 dsh。本适配版做的改动：移除上游推广页脚与未打包子技能的路由行；为每个技能加了 dsh 适配说明（上游脚本基建未打包，机械核心由配套包 **dsh-plugin-wiki-tools** 的原生工具承担）。vault 设计遵循 Karpathy 描述的 LLM Wiki 模式。

## 安装

```sh
dsh plugin --profile web add dsh-plugin-wiki-skills
```
