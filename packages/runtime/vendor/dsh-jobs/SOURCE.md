# Selected DeepSeek Harness output ring

Upstream: [jobs-local/ring.ts](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/jobs/jobs-local/src/ring.ts), public MIT source at `d743267388641bc76f17c45ce8b4c231aed1d32c`.

The original bounded UTF-8 output-ring methods are retained. Local changes replace the type-only import with equivalent product contracts and add `restore` for validated private durable snapshots. Cordis, DSH session/controller and process-local registry code are not included. The separately attributed upstream LICENSE is retained. Product persistence, ownership, execution and policy are authored in `src/jobs.ts`.

Original file SHA-256: `ce5c351de29390a08cd459bf9b71194a1da6bcfceb6bbdf06ae4b8367528efc9`.

License SHA-256: `ebb4f09972aee8608be255debaf78451a68e95c290f55c240dec2ecfa16ea6be`.
