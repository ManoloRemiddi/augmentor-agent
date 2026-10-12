<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Original Harness PDF previews

## Original viewer binding — October 12

Desktop file chips and chat/file-activity links now select the original DSH PDF
viewer for `.pdf`. The original document registry, PDF registration, lazy body,
page canvas, selectable text layer, fit-width/fixed zoom, failure/Retry controls,
per-tab viewing store, tab lifetime and CSS remain in use. This is a file
presentation adapter; it creates no AgentSession, tool call, attachment receipt
or model-facing text.

The existing authenticated complete-byte reader supplies actual current local
bytes, with its **20 MiB** cap, regular-file/version checks, read namespace,
maintenance lease and cancellation. Browser-only conversations and read-only
inspectors retain no local-file authority. Original metadata refresh/reload,
docking, splitting, narrow fullscreen and tab-close behavior stay in use.
Closing a tab, changing session/role/Host epoch or disposing the adapter retires
resources and viewing faces; parser workers remain owned by the original mounted
body rather than a shared background service.

The source selection adds **13 public files**, bringing MIT DSH to **496 files**
at **d743267388641bc76f17c45ce8b4c231aed1d32c**. The pinned public archive matches
all 483 preceding reviewed upstream hashes. Twelve new supplier bodies are
verbatim. The PDF runtime has one marked adaptation: its original worker
creation uses a fixed, reviewed same-origin module URL in place of a blob URL.
Every selected CSS body remains verbatim. Existing source modifications and
licences are preserved; dsh-context remains **108 files (92 verbatim/16 marked),
Apache-2.0**, at its preceding pinned ref.

## Local worker, assets and security policy

The source page's existing `script-src 'self'` policy rejects the original blob
worker. The adapter preserves that page policy and serves
`dsh-pdf-worker-6.3.289.mjs` through the build-owned asset allowlist. The library
worker body remains byte-exact with PDF.js; the original DSH readiness message is
appended. Source and generated-worker hashes are recorded in the browser source
manifest. Original Worker readiness, error propagation, no main-thread parsing
fallback, loading-task disposal, termination and page-render cancellation remain
in use.

Only that trusted worker response gets a separate policy permitting its local
Wasm decoders: `default-src 'none'; script-src 'self' 'wasm-unsafe-eval';
connect-src 'none'; worker-src 'none'`. The application page gains no eval,
blob-script, outbound network or file authority. The parser receives document
bytes by postMessage and bundled binary-data replies. It requires no remote
viewer, CDN/font service, account, registry check or supplier Host/Cordis runtime.

PDF.js **6.3.289** matches the public DSH lock and is pinned as a browser/build
dependency. The original asset recipe includes **189** local CMap/font/decoder
files and **ten** licence documents. The library, worker and data are deferred
until a PDF body mounts. A first object-valued esbuild define hoisted the resource
map into the initial graph; a build-local constant in the original asset module
preserves its semantics while keeping library/data outside the initial static
closure. The generated asset allowlist serves only reviewed outputs. Successful
graph/notice verification precedes replacing workspace-generated browser assets,
so obsolete chunks do not accumulate in ordinary artifacts. Selected installed
releases are never rebuilt or patched.

## Licensing and release scope

The copied viewer remains **MIT**. [PDF.js](https://github.com/mozilla/pdf.js/blob/v6.3.289/LICENSE)
is **Apache-2.0**. Its bundled OpenJPEG, JBIG2 and qcms data retain their upstream
BSD/MIT and PDF.js notices. Foxit and Liberation font notices are preserved
verbatim. **Liberation font data carries GPL-2.0 terms with a font exception**;
it is not relabelled MIT. Its required source/rebuild/public-distribution review
joins the existing public Debian Sharp/libvips gate. Source publication and a
private MX artifact do not establish public binary-distribution compliance.

The build manifest records the exact worker and every asset's size/hash alongside
licence paths. Browser notice records add PDF.js and all bundled data notices;
production dependency, native-binary and ordinary-license claims must be verified
against the separate artifact. No Node canvas runtime is required by this
browser viewer; PDF.js optional Node canvas packages are development-only.

## Evidence and current qualification

The independent public fixture authors a two-page PDF with ASCII text and a
red vector rectangle. Actual Chromium/public SDK/HTTP checks verify real canvas
pixels, a real browser double-click selection from the original text layer,
page visibility, original zoom, one native module Worker, version reload,
malformed-file reporting and worker retirement, narrow fullscreen and tab close.
A separate authored JPEG2000 image PDF exercises the real local JPX/Wasm decoder.
No owner document or upstream test archive is copied.

The fixture observes the real native Worker constructor/termination without
replacing parsing or relaxing CSP. Generic DevTools target enumeration omitted
dedicated workers even while pixels/text had rendered; constructor observation
uses the actual native superclass. An incorrect guessed zoom selector is
corrected to the original labelled button. The deliberate malformed PDF's exact
indexing warning is classified separately from unexpected errors. Raster
readbacks use a separate scratch canvas, avoiding a test-induced rendering
performance warning in the production canvas. No deadline or two-worker schedule
is relaxed.

The earlier blob-worker failure remains recorded; subsequent original text/
Markdown/image checks pass alongside PDF checks. The fixture performs one
deterministic provider seed to obtain a real SDK native history, then preserves
that history and request log during preview actions. This differs from live
owner inference or installed/physical platform acceptance.

Source check/build, supplier hashes, graph/asset/worker verification and the
focused **2/2 across two files** pass with Node 24.19.0, prepared QtTest, two
workers and unchanged deadlines. The wider source cohort passes **295/295 across
55 files**, zero failures/skips/cancellations. Fresh ordinary and installed MX
qualifications follow separately. The
currently selected/running preview remains the [qualified prompt-wrapping
release](CONTEXT-PROMPT-WRAPPING.md#installed-mx-qualification--october-12);
building the PDF candidate does not activate it.

The wider recipe is the [54-file prompt-wrapping
cohort](CONTEXT-PROMPT-WRAPPING.md#installed-mx-qualification--october-12) plus
`tests/harness-pdf-chromium.test.mjs`. Focused reproduction after a normal build:

```sh
AUGMENTOR_PYTHON=/path/to/prepared/python node --test --test-concurrency=2 tests/harness-pdf-chromium.test.mjs tests/harness-file-preview-chromium.test.mjs
```

Office conversion, spreadsheets, rendered HTML, native open/download, sidebar
keyboard commands and complete Harness/P0/P1 migration remain open. Password
handling retains the original viewer's explicit unsupported status. Full parser
format coverage is not inferred from the authored samples. Physical/live/
platform, privacy and public package/source/rebuild gates remain open. DSH stays
available; Windows, macOS and other Linux implementation remain deferred for
owner MX feedback. This shared Host/browser change adds no OS adapter.

