async function sendResult(runId, payload) {
  const response = await fetch(`/api/runs/${encodeURIComponent(runId)}/result`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "暂时无法保存，请稍后重试。");
  return data;
}

export class ResultSaver {
  constructor(runId, { send = sendResult, storage = typeof sessionStorage === "undefined" ? null : sessionStorage,
                       onState = () => {} } = {}) {
    Object.assign(this, { runId, send, storage, onState });
    this.key = `keyjourney:finished:${runId}`;
    this.state = "idle";
    this.payload = null;
    this.promise = null;
    this.saved = null;
  }

  prepare(payload) {
    if (!payload.attempted_chars) throw new Error("没有有效输入，不生成成绩。");
    this.payload = Object.freeze({ ...payload });
    try { this.storage?.setItem(this.key, JSON.stringify(this.payload)); } catch { /* In-memory retry still works. */ }
  }

  restore() {
    try {
      const data = JSON.parse(this.storage?.getItem(this.key) || "null");
      if (data && typeof data.final_input === "string" && data.attempted_chars > 0) {
        this.payload = Object.freeze(data);
        return this.payload;
      }
    } catch { /* A corrupt or unavailable browser cache cannot change stored grades. */ }
    return null;
  }

  save() {
    if (this.promise) return this.promise;
    if (this.state === "saved") return Promise.resolve(this.saved);
    if (!this.payload) return Promise.resolve(null);
    this.state = "saving"; this.onState(this.state);
    this.promise = (async () => {
      try {
        const data = await this.send(this.runId, this.payload);
        this.saved = data; this.state = "saved";
        try { this.storage?.removeItem(this.key); } catch { /* The unique run id also prevents duplicates. */ }
        this.onState(this.state, data);
        return data;
      } catch (error) {
        this.state = "save-failed";
        this.onState(this.state, error);
        return null;
      } finally { this.promise = null; }
    })();
    return this.promise;
  }
}
