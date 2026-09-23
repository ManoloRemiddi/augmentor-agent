// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"use strict";
(() => {
  // adapters/dsh-prompt-library/src/improve-composer.js
  function registerImproveComposer(ctx, React) {
    const h = React.createElement;
    function Improve({ useInput, inputActions, directory }) {
      const input = useInput((s) => s), latest = React.useRef(input);
      latest.current = input;
      const [busy, setBusy] = React.useState(false), [preview, setPreview] = React.useState(""), [settling, setSettling] = React.useState(false), [note, setNote] = React.useState(""), [undo, setUndo] = React.useState(null);
      const button = React.useRef(null), active = React.useRef(null), [geometry, setGeometry] = React.useState(null);
      const cancel = () => {
        active.current?.abort();
        active.current = null;
        setBusy(false);
        setSettling(false);
        setPreview("");
      };
      React.useEffect(() => () => {
        active.current?.abort();
        active.current = null;
      }, []);
      React.useEffect(() => {
        if (active.current && !active.current.committing && input?.draftRev !== active.current.revision) cancel();
      }, [input?.draftRev]);
      React.useEffect(() => {
        if (!busy) return;
        const card = button.current?.closest("[data-composer-card]"), editor = card?.querySelector("[contenteditable]");
        if (!card || !editor) return;
        const position = () => {
          const c = card.getBoundingClientRect(), r = editor.getBoundingClientRect(), style = getComputedStyle(editor);
          setGeometry({ left: r.left - c.left, top: r.top - c.top, width: r.width, height: r.height, font: style.font, lineHeight: style.lineHeight, padding: style.padding, color: getComputedStyle(card).color });
        };
        position();
        const observer = new ResizeObserver(position);
        observer.observe(editor);
        const key = (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            e.stopPropagation();
          } else if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            cancel();
          }
        };
        card.addEventListener("keydown", key, true);
        return () => {
          observer.disconnect();
          card.removeEventListener("keydown", key, true);
        };
      }, [busy]);
      const improve = async () => {
        if (active.current) {
          cancel();
          return;
        }
        const original = latest.current;
        if (!original?.draft.trim() || original.phase !== "plain" || original.occurrences?.length) return;
        const request = new AbortController();
        request.revision = original.draftRev;
        const timeout = setTimeout(() => {
          if (active.current === request) {
            cancel();
            setNote("Prompt improvement timed out. Try again.");
          }
        }, 75e3);
        active.current = request;
        setBusy(true);
        setPreview(original.draft);
        setSettling(false);
        setNote("");
        setUndo(null);
        try {
          const model = await directory.load();
          if (!model.current) throw Error("Select a model first.");
          const response = await fetch("/api/augmentor-prompts", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action: "improve", text: original.draft, provider: model.current.provider, model: model.current.model }), signal: request.signal });
          const result = await response.json();
          if (!response.ok || !result.ok) throw Error(result.error || "Could not improve the prompt.");
          if (active.current !== request) return;
          if (latest.current.draftRev !== original.draftRev) {
            cancel();
            return;
          }
          if (result.kind !== "rewrite") {
            setNote(result.text);
            cancel();
            return;
          }
          setPreview(result.text);
          setSettling(true);
          await new Promise((resolve) => setTimeout(resolve, 700));
          if (active.current !== request) return;
          if (latest.current.draftRev !== original.draftRev) {
            cancel();
            return;
          }
          request.committing = true;
          inputActions.setDraft(result.text);
          setUndo({ original: original.draft, replacement: result.text, revision: original.draftRev });
          active.current = null;
          setBusy(false);
          setSettling(false);
          setPreview("");
          setNote("");
          button.current?.closest("[data-composer-card]")?.querySelector("[contenteditable]")?.focus();
        } catch (error) {
          if (active.current === request) {
            cancel();
            if (error.name !== "AbortError") setNote(error.message);
          }
        } finally {
          clearTimeout(timeout);
        }
      };
      const canUndo = Boolean(undo && input?.draft === undo.replacement);
      React.useEffect(() => {
        if (undo && input?.draftRev > undo.revision && input?.draft !== undo.replacement) setUndo(null);
      }, [input?.draft, input?.draftRev, undo]);
      const undoImprovement = () => {
        inputActions.setDraft(undo.original);
        setUndo(null);
        setNote("");
        button.current?.closest("[data-composer-card]")?.querySelector("[contenteditable]")?.focus();
      };
      const disabled = !inputActions || !input?.draft.trim() || input.phase !== "plain" || Boolean(input.occurrences?.length);
      return h(
        React.Fragment,
        null,
        h("style", null, `.augmentor-improve{position:absolute;right:8px;top:8px;z-index:12;pointer-events:auto;width:24px;height:24px;border:0;border-radius:5px;background:transparent;color:inherit;font-size:16px;cursor:pointer}.augmentor-improve:hover{background:rgba(127,150,150,.18)}.augmentor-improve:disabled{opacity:.35;cursor:default}[data-composer-card]:has(.augmentor-improve) [contenteditable]{padding-right:42px!important}[data-composer-card]:has(.augmentor-improve-busy) [contenteditable]{color:transparent!important;caret-color:transparent!important}.augmentor-letter-preview{position:absolute;z-index:10;pointer-events:none;white-space:pre-wrap;overflow-wrap:anywhere;overflow:hidden;box-sizing:border-box}.augmentor-letter-cell{display:inline-block;position:relative;height:1.3em;vertical-align:bottom;overflow:hidden}.augmentor-letter-width{visibility:hidden}.augmentor-letter-wheel{position:absolute;inset:0;animation:augmentor-letter-roll var(--speed) linear infinite;animation-delay:var(--delay)}.augmentor-letter-wheel span{display:block;height:1.3em}.augmentor-letter-preview.settle .augmentor-letter-wheel{animation:none;transform:translateY(0);transition:transform .3s}.augmentor-improve-status{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}@keyframes augmentor-letter-roll{from{transform:translateY(0)}to{transform:translateY(-2.6em)}}@media(prefers-reduced-motion:reduce){.augmentor-letter-wheel{animation:none}}`),
        h("button", { ref: button, type: "button", className: "augmentor-improve" + (busy ? " augmentor-improve-busy" : ""), "aria-label": busy ? "Cancel prompt improvement" : canUndo ? "Undo prompt improvement" : "Improve prompt", disabled: !busy && !canUndo && disabled, onClick: canUndo && !busy ? undoImprovement : improve }, busy ? "\xD7" : canUndo ? "\u21B6" : note ? "!" : "\u2726"),
        busy && geometry && h("div", { className: "augmentor-letter-preview" + (settling ? " settle" : ""), style: geometry, "aria-hidden": true }, Array.from(preview).map((char, i) => /\s/.test(char) ? char : h("span", { key: i, className: "augmentor-letter-cell", style: { "--speed": `${0.28 + i % 7 * 0.05}s`, "--delay": `${-i * 0.071}s` } }, h("span", { className: "augmentor-letter-width" }, char), h("span", { className: "augmentor-letter-wheel" }, [char, String.fromCharCode(97 + i * 13 % 26), char].map((c, j) => h("span", { key: j }, c)))))),
        note && h("span", { className: "augmentor-improve-status", role: "status" }, note)
      );
    }
    ctx.inject(["modelDirectories"], (scope) => scope.slots.inject("conversation.input.overlay", () => scope.slots.register({ name: "conversation.input.overlay", id: "augmentor-improve-prompt", order: 90, inject: (sessionId) => ({ directory: scope.modelDirectories.directoryFor(sessionId) }) }, Improve)));
  }

  // adapters/dsh-prompt-library/src/client.js
  window.__ModuleLoader__.load({
    id: "dsh-prompt-library",
    factory(require2) {
      const React = require2("react"), h = React.createElement;
      const NS = "prompt-library";
      function apply(ctx) {
        registerImproveComposer(ctx, React);
        const service = async (action, params = {}) => {
          const response = await fetch("/api/augmentor-prompts", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action, ...params }) });
          const result = await response.json();
          if (!result.ok) throw new Error(result.error);
          return result.library;
        };
        const unwrap = (response) => {
          if (!response?.result?.ok) throw new Error(response?.result?.error?.message || "DSH could not load the prompt library.");
          return response.result.value;
        };
        function ImprovementPage() {
          const [current, setCurrent] = React.useState(null), [text, setText] = React.useState(""), [note, setNote] = React.useState("Loading instructions\u2026"), [busy, setBusy] = React.useState(false);
          const alive = React.useRef(true);
          const load = async () => {
            setBusy(true);
            try {
              const value = (await service("list")).improvement;
              if (!value) throw Error("Restart the prompt service to load these settings.");
              if (alive.current) {
                setCurrent(value);
                setText(value.content);
                setNote("Changes take effect after saving.");
              }
            } catch (e) {
              if (alive.current) setNote(e.message);
            } finally {
              if (alive.current) setBusy(false);
            }
          };
          React.useEffect(() => {
            alive.current = true;
            load();
            return () => {
              alive.current = false;
            };
          }, []);
          const save = async () => {
            if (!current || busy) return;
            setBusy(true);
            try {
              const result = await service("improvement.save", { content: text, expectedRevision: current.revision });
              if (alive.current) {
                setCurrent(result.improvement);
                setNote("Instructions saved.");
              }
            } catch (e) {
              if (alive.current) setNote(e.message);
            } finally {
              if (alive.current) setBusy(false);
            }
          };
          return h(
            "div",
            null,
            h("p", null, "Instructions for \u2726 Improve prompt in the input box. These are separate from saved /prompts."),
            h("textarea", { "aria-label": "Prompt improvement instructions", rows: 14, maxLength: 8e3, disabled: busy || !current, value: text, onChange: (e) => setText(e.target.value) }),
            h(
              "div",
              { className: "pl-bar" },
              h("button", { type: "button", disabled: busy || !current, onClick: save }, "Save instructions"),
              h("button", { type: "button", disabled: busy, onClick: load }, "Reload"),
              h("button", { type: "button", disabled: busy || !current, onClick: () => {
                setText(current.defaultContent);
                setNote("Default loaded. Save to apply it.");
              } }, "Use default")
            ),
            h("p", { role: "status" }, note)
          );
        }
        function LibraryPage() {
          const [section, setSection] = React.useState("saved");
          const [library, setLibrary] = React.useState(null);
          const [form, setForm] = React.useState({ id: null, name: "", content: "" });
          const [editing, setEditing] = React.useState(false);
          const [dirty, setDirty] = React.useState(false);
          const textRef = React.useRef(null);
          const [query, setQuery] = React.useState("");
          const [status, setStatus] = React.useState("Loading prompts\u2026");
          const [busy, setBusy] = React.useState(false);
          const alive = React.useRef(true), busyRef = React.useRef(false), formRef = React.useRef(form), editingRef = React.useRef(false);
          formRef.current = form;
          editingRef.current = editing;
          const load = async (syncForm = true) => {
            const result = await service("list");
            const next = { revision: result.revision, value: result };
            if (!next) throw new Error("The Prompt library plugin is not running.");
            if (alive.current) {
              setLibrary(next);
              if (syncForm && !editingRef.current && formRef.current.id) setForm(next.value.prompts.find((p) => p.id === formRef.current.id) || { id: null, name: "", content: "" });
            }
            return next;
          };
          React.useEffect(() => {
            alive.current = true;
            load().then(() => {
              if (alive.current) setStatus("");
            }, (error) => {
              if (alive.current) setStatus(error.message);
            });
            const timer = setInterval(() => {
              if (!busyRef.current) load(!editingRef.current).catch((error) => {
                if (alive.current) setStatus(error.message);
              });
            }, 1500);
            return () => {
              alive.current = false;
              clearInterval(timer);
            };
          }, []);
          const select = (item) => {
            if (dirty && !window.confirm("Discard your unsaved prompt changes?")) return;
            setForm(item || { id: null, name: "", content: "" });
            setEditing(!item);
            setDirty(false);
            setStatus("");
          };
          const cancelEdit = () => {
            setForm(library?.value.prompts.find((p) => p.id === form.id) || { id: null, name: "", content: "" });
            setEditing(false);
            setDirty(false);
            setStatus("");
          };
          const edit = (key, value) => {
            setForm((prev) => ({ ...prev, [key]: value }));
            setDirty(true);
          };
          const save = async (remove) => {
            if (!library || busyRef.current) return;
            if (remove && !window.confirm("Delete /" + form.name + "?")) return;
            busyRef.current = true;
            setBusy(true);
            try {
              const item = { id: form.id, name: form.name.trim().replace(/^\//, ""), content: form.content, expectedRevision: form.revision };
              const result = await service(remove ? "delete" : "save", item);
              const committed = result.prompts.find((p) => p.id === form.id || p.name === item.name);
              await load();
              if (!alive.current) return;
              setForm(remove ? { id: null, name: "", content: "" } : committed);
              setEditing(false);
              setDirty(false);
              setStatus(remove ? "Prompt deleted." : "Saved. Type /" + item.name + " in either Augmentor app.");
            } catch (error) {
              if (alive.current) setStatus(error.message);
            } finally {
              busyRef.current = false;
              if (alive.current) setBusy(false);
            }
          };
          const prompts = library?.value.prompts || [];
          const matches = prompts.filter((p) => p.name.includes(query.toLowerCase().replace(/^\//, ""))).sort((a, b) => a.name.localeCompare(b.name));
          return h(
            "section",
            { className: "dsh-prompt-library", "aria-label": "Prompt library" },
            h("style", null, `.dsh-prompt-library{max-width:760px;padding:8px 4px 24px;font:14px/1.5 inherit}.dsh-prompt-library h2{margin:0 0 8px;font-size:21px}.dsh-prompt-library p{opacity:.8}.dsh-prompt-library input,.dsh-prompt-library textarea{display:block;width:100%;box-sizing:border-box;color:inherit;background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.35);border-radius:10px;padding:10px 12px;font:inherit}.dsh-prompt-library textarea{resize:vertical;min-height:170px}.dsh-prompt-library label{display:block;margin:16px 0 0}.dsh-prompt-library button{font:inherit;color:inherit;background:rgba(128,128,128,.1);border:1px solid rgba(128,128,128,.3);border-radius:9px;padding:7px 12px;cursor:pointer}.dsh-prompt-library button:hover{background:rgba(128,128,128,.23)}.dsh-prompt-library button:disabled{opacity:.4;cursor:default}.dsh-prompt-library .pl-bar{display:flex;gap:8px;margin:14px 0;flex-wrap:wrap}.dsh-prompt-library .pl-list{display:flex;flex-direction:column;gap:5px;max-height:185px;overflow:auto;margin:12px 0}.dsh-prompt-library .pl-list button{text-align:left}.dsh-prompt-library button[aria-pressed=true]{border-color:#62b4a0;background:rgba(98,180,160,.14)}.dsh-prompt-library .pl-status{min-height:24px;overflow-wrap:anywhere}`),
            h("style", null, `.dsh-prompt-library .pl-preview{white-space:pre-wrap;overflow-wrap:anywhere;max-height:300px;overflow:auto;padding:16px;border-radius:12px;background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.25);line-height:1.6}.dsh-prompt-library h3{font-size:16px;margin:20px 0 10px}.dsh-prompt-library .pl-list button small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:.65;font-size:12px;margin-top:2px}`),
            h("h2", null, "Prompt library"),
            h("div", { className: "pl-bar" }, h("button", { type: "button", "aria-pressed": section === "saved", onClick: () => setSection("saved") }, "Saved prompts"), h("button", { type: "button", "aria-pressed": section === "improve", onClick: () => setSection("improve") }, "Improve prompt")),
            h("div", { hidden: section !== "improve" }, h(ImprovementPage)),
            h(
              "div",
              { hidden: section !== "saved" },
              h("p", null, "Shared across Augmentor interfaces and harnesses. Click a prompt to preview it, or type / in chat to insert it into your draft."),
              h("input", { "aria-label": "Search saved prompts", placeholder: "Search prompts\u2026", value: query, onChange: (e) => setQuery(e.target.value) }),
              h(
                "div",
                { className: "pl-bar" },
                h("button", { type: "button", disabled: busy, onClick: () => select(null) }, "New prompt"),
                h("button", { type: "button", disabled: busy, onClick: () => load(false).then(() => setStatus(editing ? "Library refreshed. Your draft is kept." : "Library refreshed."), (e) => setStatus(e.message)) }, "Refresh")
              ),
              h("div", { className: "pl-list" }, matches.map((p) => h("button", { key: p.id, type: "button", disabled: busy, "aria-label": "/" + p.name, "aria-pressed": p.id === form.id, onClick: () => select(p) }, "/" + p.name, h("small", { "aria-hidden": true }, p.content.replace(/\s+/g, " ").slice(0, 100))))),
              library && !prompts.length && !editing && h("p", null, "Your library is empty. Choose New prompt to get started."),
              prompts.length > 0 && !matches.length && h("p", null, "No matching prompts."),
              !editing && !form.id && prompts.length > 0 && h("p", null, "Select a prompt above to preview it."),
              !editing && form.id && h(
                React.Fragment,
                null,
                h("h3", null, "/" + form.name),
                h("div", { className: "pl-preview", role: "region", "aria-label": "Prompt preview" }, form.content),
                h(
                  "div",
                  { className: "pl-bar" },
                  h("button", { type: "button", disabled: !library || busy, onClick: () => {
                    setEditing(true);
                    setStatus("");
                  } }, "Edit"),
                  h("button", { type: "button", disabled: !library || busy, onClick: () => save(true) }, "Delete prompt")
                )
              ),
              editing && h(
                React.Fragment,
                null,
                h("h3", null, form.id ? "Edit prompt" : "New prompt"),
                h("label", null, "Shortcut name", h("input", { "aria-label": "Prompt shortcut name", placeholder: "For example: summarise", maxLength: 128, disabled: busy, value: form.name, onChange: (e) => edit("name", e.target.value) })),
                h("label", null, "Prompt text", h("textarea", { ref: textRef, "aria-label": "Saved prompt text", rows: 7, maxLength: 32e3, disabled: busy, value: form.content, onChange: (e) => edit("content", e.target.value) })),
                h(
                  "div",
                  { className: "pl-bar" },
                  h("button", { type: "button", disabled: busy, onClick: () => {
                    const t = textRef.current;
                    const start = t.selectionStart, end = t.selectionEnd;
                    edit("content", form.content.slice(0, start) + "[clipboard]" + form.content.slice(end));
                    requestAnimationFrame(() => {
                      t.focus();
                      t.setSelectionRange(start + 11, start + 11);
                    });
                  } }, "Insert clipboard"),
                  h("button", { type: "button", disabled: !library || busy || !form.name.trim() || !form.content.trim(), onClick: () => save(false) }, busy ? "Saving\u2026" : "Save prompt"),
                  h("button", { type: "button", disabled: busy, onClick: cancelEdit }, "Cancel")
                )
              ),
              h("p", { role: "status", className: "pl-status" }, status),
              h("p", null, "Stored in the shared Augmentor library. This library does not send prompts to a model.")
            )
          );
        }
        ctx.slots.inject("settings.section", () => ctx.slots.register({ name: "settings.section", id: NS, order: 95, label: () => "Prompt library" }, LibraryPage));
      }
      return { name: "dsh-prompt-library", inject: ["slots", "connection", "remote"], apply };
    }
  });
})();
