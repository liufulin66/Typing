const rows = [
  ["Tab", ..."qwertyuiop", "[", "]"],
  ["Caps", ..."asdfghjkl", ";", "'", "Enter"],
  ["Shift", ..."zxcvbnm", ",", ".", "/", "Shift"],
  ["Ctrl", "Alt", " ", "Alt", "Ctrl"],
];

export class KeyboardGuide {
  constructor(container, hint, fingerMap) {
    Object.assign(this, { container, hint, fingerMap });
    this.keys = new Map(); this.expected = null; this.last = null; this.lastWrong = false;
    for (const row of rows) {
      const line = document.createElement("div"); line.className = "keyboard-row";
      for (const key of row) {
        const item = document.createElement("kbd");
        item.textContent = key === " " ? "space" : key.length === 1 ? key.toUpperCase() : key;
        item.className = `keyboard-key${key.length > 1 ? " modifier" : ""}${key === " " ? " space-key" : ""}${"fj".includes(key) ? " home-key" : ""}`;
        item.dataset.key = key;
        if (key.length === 1) {
          this.keys.set(key, item);
          item.setAttribute("aria-label", `${key === " " ? "空格" : key.toUpperCase()}${fingerMap[key] ? `，${fingerMap[key]}` : ""}`);
        }
        line.append(item);
      }
      container.append(line);
    }
  }

  setTarget(expected) { this.expected = expected; this.render(); }

  press(actual, expected) {
    if (actual.length !== 1) return;
    this.last = actual.toLowerCase();
    this.lastWrong = actual !== expected;
    this.render();
  }

  render() {
    for (const [key, element] of this.keys) {
      element.classList.toggle("target-key", key === this.expected);
      element.classList.toggle("last-key", key === this.last);
      element.classList.toggle("wrong-key", key === this.last && this.lastWrong);
    }
    if (!this.expected) { this.hint.textContent = "本次练习已结束，手指可以放松一下。"; return; }
    const label = this.expected === " " ? "空格" : this.expected.toUpperCase();
    const actual = this.last ? ` · 上次 ${this.last === " " ? "空格" : this.last.toUpperCase()}${this.lastWrong ? "（有误）" : ""}` : "";
    this.hint.textContent = `目标 ${label} · ${this.fingerMap[this.expected] || "请使用对应手指"}${actual}`;
  }
}
