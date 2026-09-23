// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
// Android IMEs can emit beforeinput without a meaningful keydown. Forward only
// committed edits; disconnected/composing text must never become replayed input.
export function bindKeyboard(field, sendKey, isConnected) {
  const send = key => { if (isConnected()) sendKey(key); };
  const commit = event => {
    if (event.isComposing) return;
    const value = field.value;
    field.value = '';
    if (!isConnected()) return;
    for (const character of value) {
      const cp = character.codePointAt(0);
      sendKey(cp <= 255 ? cp : 0x01000000 | cp);
    }
  };
  field.addEventListener('input', commit);
  field.addEventListener('compositionend', commit);
  field.addEventListener('beforeinput', event => {
    if (event.isComposing) return;
    const key = {deleteContentBackward:0xff08, deleteContentForward:0xffff,
      insertLineBreak:0xff0d, insertParagraph:0xff0d}[event.inputType];
    if (key) { event.preventDefault(); send(key); }
  });
  field.addEventListener('keydown', event => {
    if (event.isComposing) return;
    const key = {Backspace:0xff08, Delete:0xffff, Enter:0xff0d,
      Tab:0xff09, Escape:0xff1b}[event.key];
    if (key) { event.preventDefault(); send(key); }
  });
}
