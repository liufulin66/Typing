import { characters } from "./engine.mjs";

/** A small adapter between browser editing events and the committed-text buffer. */
export class InputController {
  constructor(element, { buffer, onStart = () => {}, onCommit = () => {},
                         allowed = () => true, notice = () => {} }) {
    Object.assign(this, { element, buffer, onStart, onCommit, allowed, notice });
    this.composing = false;
    this.pendingEdit = null;
    this.pendingComposition = null;
    this.handlers = {
      beforeinput: (event) => this.beforeInput(event),
      input: (event) => this.input(event),
      compositionstart: () => this.compositionStart(),
      compositionend: (event) => this.compositionEnd(event),
      paste: (event) => this.blockBulk(event),
      drop: (event) => this.blockBulk(event),
    };
    Object.entries(this.handlers).forEach(([name, handler]) => element.addEventListener(name, handler));
  }

  selection(inputType) {
    const value = this.element.value;
    return { start: characters(value.slice(0, this.element.selectionStart)).length,
             end: characters(value.slice(0, this.element.selectionEnd)).length, inputType };
  }

  blockBulk(event) {
    event.preventDefault();
    this.notice("练习区请手动输入；可以在素材设置中粘贴自定义文本。");
  }

  beforeInput(event) {
    if (!this.allowed()) { event.preventDefault(); return; }
    if (/insertFrom(Paste|Drop|Yank)/.test(event.inputType || "")) {
      this.blockBulk(event);
      return;
    }
    if (this.composing || event.isComposing || this.pendingComposition) return;
    this.pendingEdit = this.selection(event.inputType);
  }

  compositionStart() {
    if (!this.allowed()) return;
    this.composing = true;
    this.pendingComposition = null;
    this.compositionEdit = this.selection("insertCompositionText");
    this.pendingEdit = null;
    this.onStart();
  }

  compositionEnd(event) {
    this.composing = false;
    if (!this.allowed()) { this.restore(); return; }
    if (!event.data) { this.pendingComposition = null; this.restore(); return; }
    const pending = { edit: this.compositionEdit };
    this.pendingComposition = pending;
    // Some browsers emit the final input before compositionend, others after it.
    queueMicrotask(() => {
      if (this.pendingComposition === pending) this.commitComposition();
    });
  }

  commitComposition() {
    const pending = this.pendingComposition;
    this.pendingComposition = null;
    if (!this.allowed()) { this.restore(); return; }
    this.commit(pending?.edit);
  }

  input(event) {
    if (!this.allowed()) { this.restore(); return; }
    if (this.composing || event.isComposing) return;
    if (/insertFrom(Paste|Drop|Yank)/.test(event.inputType || "")) { this.restore(); return; }
    if (this.pendingComposition) { this.commitComposition(); return; }
    const edit = this.pendingEdit;
    this.pendingEdit = null;
    // A follow-up input reporting an already committed composition is a duplicate.
    if (!edit && this.element.value === this.buffer.text) return;
    this.commit(edit);
  }

  commit(edit) {
    if (!this.allowed()) { this.restore(); return; }
    const added = this.buffer.commit(this.element.value, edit);
    if (added) this.onStart();
    if (this.element.value !== this.buffer.text) this.element.value = this.buffer.text;
    this.pendingEdit = null;
    this.onCommit();
  }

  restore() {
    this.element.value = this.buffer.text;
    this.pendingEdit = null;
  }

  destroy() {
    this.pendingComposition = null;
    Object.entries(this.handlers).forEach(([name, handler]) => this.element.removeEventListener(name, handler));
  }
}
