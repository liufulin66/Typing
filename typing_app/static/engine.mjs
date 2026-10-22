export const characters = (text) => Array.from(text.replace(/\r\n?/g, "\n"));

/** All accounting is based on committed text, never physical IME keystrokes. */
export class PracticeBuffer {
  constructor({ target_text, mode = "full", language = "en" }) {
    this.target = characters(target_text);
    this.mode = mode;
    this.language = language;
    this.text = "";
    this.attempts = 0;
    this.correctAttempts = 0;
  }

  targetAt(index) {
    return this.mode === "timed" ? this.target[index % this.target.length] : this.target[index];
  }

  commit(value, edit = null) {
    const previous = characters(this.text);
    let next = characters(value);
    if (this.mode !== "timed") next = next.slice(0, this.target.length);
    let start = 0;
    let inserted = [];
    if (edit && edit.inputType?.startsWith("delete")) {
      // A deletion changes the buffer, but it cannot erase a past mistake.
    } else if (edit && edit.inputType?.startsWith("insert") && Number.isInteger(edit.start)) {
      start = Math.min(edit.start, next.length);
      const removed = Math.max(0, edit.end - edit.start);
      const count = Math.max(0, next.length - previous.length + removed);
      inserted = next.slice(start, start + count);
    } else {
      while (start < previous.length && start < next.length && previous[start] === next[start]) start++;
      let suffix = 0;
      while (suffix < previous.length - start && suffix < next.length - start &&
             previous[previous.length - 1 - suffix] === next[next.length - 1 - suffix]) suffix++;
      inserted = next.slice(start, next.length - suffix);
    }
    inserted.forEach((char, index) => {
      this.attempts++;
      if (char === this.targetAt(start + index)) this.correctAttempts++;
    });
    this.text = next.join("");
    return inserted.length;
  }

  metrics(elapsedMs) {
    const text = characters(this.text);
    const finalCorrect = text.reduce((count, char, index) => count + Number(char === this.targetAt(index)), 0);
    const elapsed = Math.max(1, elapsedMs);
    return {
      attempted_chars: this.attempts,
      correct_attempts: this.correctAttempts,
      error_attempts: this.attempts - this.correctAttempts,
      final_correct_chars: finalCorrect,
      accuracy: this.attempts ? this.correctAttempts / this.attempts * 100 : 0,
      speed: finalCorrect * 60000 / elapsed / (this.language === "zh" ? 1 : 5),
      speed_unit: this.language === "zh" ? "字符/分钟" : "WPM",
    };
  }
}

export class PracticeSession {
  constructor(run, { clock = () => performance.now(), onFinish = () => {} } = {}) {
    Object.assign(this, { clock, onFinish });
    this.reset(run);
  }

  reset(run = this.run) {
    this.run = run;
    this.buffer = new PracticeBuffer(run);
    this.state = "ready";
    this.startedAt = null;
    this.elapsedMs = 0;
    this.payload = null;
  }

  start() {
    if (this.state === "ready") {
      this.startedAt = this.clock();
      this.state = "running";
    }
  }

  elapsed() {
    if (this.state === "ready") return 0;
    if (this.state !== "running") return this.elapsedMs;
    const elapsed = Math.max(0, this.clock() - this.startedAt);
    return this.run.mode === "timed" ? Math.min(elapsed, this.run.duration_seconds * 1000) : elapsed;
  }

  accepting() {
    if (this.state === "running" && this.run.mode === "timed" &&
        this.clock() - this.startedAt >= this.run.duration_seconds * 1000) this.finish();
    return this.state === "ready" || this.state === "running";
  }

  afterCommit() {
    if (this.buffer.attempts) this.start();
    if (this.state === "running" && this.run.mode !== "timed" &&
        characters(this.buffer.text).length === this.buffer.target.length) this.finish();
  }

  tick() { this.accepting(); }

  finish() {
    if (this.state !== "running") return;
    this.elapsedMs = this.run.mode === "timed" ? this.run.duration_seconds * 1000 : Math.max(1, this.elapsed());
    this.state = "finished";
    this.payload = Object.freeze({ final_input: this.buffer.text,
      attempted_chars: this.buffer.attempts, correct_attempts: this.buffer.correctAttempts,
      elapsed_ms: this.elapsedMs });
    this.onFinish(this.payload);
  }
}
