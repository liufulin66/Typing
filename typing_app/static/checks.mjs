import { PracticeBuffer, PracticeSession } from "./engine.mjs";
import { InputController } from "./input.mjs";
import { ResultSaver } from "./save.mjs";

export function runBufferChecks(cases) {
  return cases.map((test) => {
    const buffer = new PracticeBuffer(test.run);
    test.steps.forEach((step) => buffer.commit(step.value, step.edit));
    const metrics = buffer.metrics(test.elapsed_ms);
    const failures = Object.entries(test.expected).filter(([key, value]) => Math.abs(metrics[key] - value) > 0.000001);
    return { name: test.name, passed: !failures.length, detail: JSON.stringify(failures) };
  });
}

class FakeInput extends EventTarget {
  constructor() { super(); this.value = ""; this.selectionStart = 0; this.selectionEnd = 0; }
}

function fire(element, name, properties = {}) {
  const event = new Event(name, { cancelable: true });
  Object.entries(properties).forEach(([key, value]) => Object.defineProperty(event, key, { value }));
  element.dispatchEvent(event);
  return event;
}

export async function runInputChecks() {
  const results = [];
  async function check(name, action) {
    try { await action(); results.push({ name, passed: true }); }
    catch (error) { results.push({ name, passed: false, detail: error.message }); }
  }
  function assert(condition, message) { if (!condition) throw new Error(message); }
  function setup() {
    const element = typeof document === "undefined" ? new FakeInput() : document.createElement("textarea");
    const buffer = new PracticeBuffer({ target_text: "你好世界", language: "zh" });
    const controller = new InputController(element, { buffer });
    return { element, buffer, controller };
  }
  await check("中文组字仅在确认后计分并去重", async () => {
    const { element, buffer } = setup();
    fire(element, "compositionstart");
    element.value = "ni";
    fire(element, "input", { isComposing: true, inputType: "insertCompositionText" });
    assert(buffer.attempts === 0, "拼音被计分");
    element.value = "你好";
    fire(element, "compositionend", { data: "你好" });
    fire(element, "input", { inputType: "insertFromComposition" });
    await Promise.resolve();
    fire(element, "input", { inputType: "insertText" });
    assert(buffer.attempts === 2 && buffer.correctAttempts === 2, "重复计分或上屏丢失");
  });
  await check("输入先于组字结束也只统计一次", async () => {
    const { element, buffer } = setup();
    fire(element, "compositionstart");
    element.value = "你";
    fire(element, "input", { isComposing: false, inputType: "insertText" });
    fire(element, "compositionend", { data: "你" });
    await Promise.resolve();
    assert(buffer.attempts === 1 && buffer.text === "你", "事件顺序不兼容");
  });
  await check("取消组字不增加尝试", async () => {
    const { element, buffer } = setup();
    fire(element, "compositionstart"); element.value = "ni";
    fire(element, "compositionend", { data: "" });
    await Promise.resolve();
    assert(buffer.attempts === 0 && element.value === "", "取消仍然计分");
  });
  await check("作答区拒绝粘贴拖入，素材区不受影响", async () => {
    const { element, buffer } = setup();
    assert(fire(element, "paste").defaultPrevented, "未阻止粘贴");
    assert(fire(element, "drop").defaultPrevented, "未阻止拖入");
    assert(buffer.attempts === 0, "粘贴改变计数");
    const source = typeof document === "undefined" ? new FakeInput() : document.createElement("textarea");
    assert(!fire(source, "paste").defaultPrevented, "素材区被误拦截");
  });
  return results;
}

export async function runTimeChecks() {
  const results = [];
  async function check(name, action) {
    try { await action(); results.push({ name, passed: true }); }
    catch (error) { results.push({ name, passed: false, detail: error.message }); }
  }
  function assert(condition, message) { if (!condition) throw new Error(message); }
  for (const seconds of [60, 180, 300]) {
    await check(`${seconds} 秒截止且结算仅一次`, () => {
      let now = 0, finished = 0;
      const session = new PracticeSession({ target_text: "ab", mode: "timed", language: "en", duration_seconds: seconds },
        { clock: () => now, onFinish: () => finished++ });
      now = 5000; session.tick();
      assert(session.state === "ready", "等待也在计时");
      session.start(); session.buffer.commit("ababab"); session.afterCommit();
      assert(session.state === "running", "短素材提前结束");
      now += seconds * 1000 - 1; session.tick();
      assert(session.state === "running", "提前截止");
      now += 10000; session.tick(); session.tick();
      assert(finished === 1 && session.payload.elapsed_ms === seconds * 1000, "截止漂移或重复结算");
      assert(!session.accepting(), "结束仍可计分");
    });
  }
  await check("全文带错结算，重试完全清零", () => {
    let now = 0;
    const session = new PracticeSession({ target_text: "ab", mode: "full", language: "en" }, { clock: () => now });
    session.start(); now = 1000; session.buffer.commit("ax"); session.afterCommit();
    assert(session.state === "finished" && session.buffer.metrics(1000).accuracy === 50, "全文未结算");
    session.reset();
    assert(session.state === "ready" && session.buffer.attempts === 0 && session.buffer.text === "" && session.elapsed() === 0, "重试未清零");
  });
  await check("限时在组字中结束只保留上屏快照", async () => {
    let now = 0;
    const session = new PracticeSession({ target_text: "你好", mode: "timed", language: "zh", duration_seconds: 60 }, { clock: () => now });
    const element = typeof document === "undefined" ? new FakeInput() : document.createElement("textarea");
    new InputController(element, { buffer: session.buffer, allowed: () => session.accepting(),
      onStart: () => session.start(), onCommit: () => session.afterCommit() });
    element.value = "你"; fire(element, "input", { inputType: "insertText" });
    element.selectionStart = element.selectionEnd = 1;
    fire(element, "compositionstart"); element.value = "你hao";
    fire(element, "input", { isComposing: true });
    now = 60001; session.tick();
    element.value = "你好"; fire(element, "compositionend", { data: "好" });
    await Promise.resolve();
    assert(session.payload.final_input === "你" && session.payload.attempted_chars === 1, "组字混入结算");
  });
  return results;
}

export async function runSaveChecks() {
  const results = [];
  const memory = new Map();
  const storage = { getItem: (key) => memory.get(key), setItem: (key, value) => memory.set(key, value), removeItem: (key) => memory.delete(key) };
  const payload = { final_input: "fj", attempted_chars: 2, correct_attempts: 2, elapsed_ms: 1000 };
  async function check(name, action) {
    try { await action(); results.push({ name, passed: true }); }
    catch (error) { results.push({ name, passed: false, detail: error.message }); }
  }
  function assert(condition, message) { if (!condition) throw new Error(message); }
  await check("保存失败保留同一成绩，成功后才确认进度", async () => {
    let calls = 0, unlocked = false;
    const saver = new ResultSaver("one", { storage,
      send: async (id, value) => { calls++; assert(id === "one" && JSON.stringify(value) === JSON.stringify(payload), "重试改变了成绩");
        if (calls === 1) throw new Error("模拟保存失败"); return { progress: { unlocked: true } }; },
      onState: (state, data) => { if (state === "saved") unlocked = data.progress.unlocked; } });
    saver.prepare(payload); await saver.save();
    assert(saver.state === "save-failed" && !unlocked && saver.restore(), "失败未保留或提前解锁");
    await saver.save();
    assert(saver.state === "saved" && unlocked && calls === 2 && !saver.restore(), "成功后状态错误");
  });
  await check("连续点击只发送一次保存请求", async () => {
    let calls = 0, release;
    const saver = new ResultSaver("two", { storage, send: () => { calls++; return new Promise((resolve) => { release = resolve; }); } });
    saver.prepare(payload);
    const first = saver.save(), second = saver.save();
    assert(calls === 1, "重复发送");
    release({ result: {} }); await Promise.all([first, second]); await saver.save();
    assert(calls === 1, "已保存仍发送");
  });
  await check("刷新可恢复完成成绩，不恢复半途输入", async () => {
    const first = new ResultSaver("three", { storage }); first.prepare(payload);
    const reloaded = new ResultSaver("three", { storage });
    assert(JSON.stringify(reloaded.restore()) === JSON.stringify(payload), "冻结结果丢失");
    assert(new ResultSaver("different", { storage }).restore() === null, "恢复了其他练习");
  });
  return results;
}

if (typeof document !== "undefined") {
  const cases = await fetch("/static/score-cases.json").then((response) => response.json());
  const results = [...runBufferChecks(cases), ...await runInputChecks(), ...await runTimeChecks(), ...await runSaveChecks()];
  const list = document.getElementById("checks");
  for (const test of results) {
    const item = document.createElement("li");
    item.textContent = `${test.passed ? "通过" : "失败"} · ${test.name}${test.passed ? "" : test.detail}`;
    list.append(item);
  }
  document.getElementById("check-status").textContent = `${results.filter((test) => test.passed).length}/${results.length} 验收样例通过`;
}
