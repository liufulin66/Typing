import { PracticeSession, characters } from "./engine.mjs";
import { InputController } from "./input.mjs";
import { ResultSaver } from "./save.mjs";
import { KeyboardGuide } from "./keyboard.mjs";

const boot = JSON.parse(document.getElementById("practice-boot").textContent);
const $ = (id) => document.getElementById(id);
const form = $("setup-form");
const answer = $("answer");
let session = null, controller = null, timer = null, currentRun = null, startBody = null, saver = null;
let keyboardGuide = null;
let savedStats = null;

const formatTime = (ms) => {
  const seconds = Math.max(0, Math.ceil(ms / 1000));
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
};

function populateArticles() {
  const items = boot.articles[$("language").value];
  $("article").replaceChildren(...items.map((item) => new Option(`${item.title} · ${characters(item.text).length} 字符`, item.id)));
  if (items.some((item) => item.id === boot.article_id)) $("article").value = boot.article_id;
  previewArticle();
}

function previewArticle() {
  const item = boot.articles[$("language").value].find((item) => item.id === $("article").value);
  $("article-preview").textContent = item?.text || "";
}

function updateSetup() {
  $("duration-field").hidden = new FormData(form).get("mode") !== "timed";
  $("article-field").hidden = $("source").value !== "article";
  $("custom-field").hidden = $("source").value !== "custom";
}

function bodyFromRun(run) {
  if (run.mode === "lesson") return { mode: "lesson", lesson_id: run.source_id };
  return { mode: run.mode, language: run.language,
    ...(run.source_kind === "article" ? { article_id: run.source_id } : { text: run.target_text }),
    ...(run.mode === "timed" ? { duration_seconds: run.duration_seconds } : {}) };
}

function renderTarget() {
  if (!session) return;
  const typed = characters(session.buffer.text);
  const caret = controller?.composing ? typed.length : Math.min(typed.length, characters(answer.value.slice(0, answer.selectionStart)).length);
  const start = Math.max(0, caret - 90);
  const end = currentRun.mode === "timed" ? caret + 170 : Math.min(session.buffer.target.length, start + 320);
  const fragment = document.createDocumentFragment();
  if (start) fragment.append(document.createTextNode("… "));
  for (let index = start; index < end; index++) {
    const span = document.createElement("span");
    const expected = session.buffer.targetAt(index);
    span.textContent = expected === "\n" ? "↵\n" : expected;
    const status = index < typed.length ? typed[index] === expected ? "correct" : "incorrect" : "pending";
    span.className = `char ${status}${index === caret && session.accepting() ? " current" : ""}`;
    if (status === "incorrect") span.setAttribute("aria-label", `错误，目标为${expected === " " ? "空格" : expected}`);
    fragment.append(span);
  }
  if (currentRun.mode !== "timed" && end < session.buffer.target.length) fragment.append(document.createTextNode(" …"));
  $("target-text").replaceChildren(fragment);
  if (keyboardGuide) keyboardGuide.setTarget(session.state === "finished" ? null : session.buffer.targetAt(caret));
}

function renderMetrics(result = null) {
  if (!session) return;
  const elapsed = session.elapsed();
  const frozen = result || savedStats;
  const stats = frozen || session.buffer.metrics(elapsed);
  $("speed").textContent = stats.attempted_chars ? stats.speed.toFixed(1) : "—";
  $("speed-unit").textContent = stats.speed_unit;
  $("accuracy").textContent = stats.attempted_chars ? stats.accuracy.toFixed(1) : "—";
  $("timer").textContent = formatTime(currentRun.mode === "timed" && session.state !== "finished" ? currentRun.duration_seconds * 1000 - elapsed : elapsed);
  $("count").textContent = frozen ? frozen.final_length : characters(session.buffer.text).length;
  $("count-total").textContent = currentRun.mode === "timed" ? "字符" : `/ ${session.buffer.target.length}`;
  $("session-status").textContent = session.state === "ready" ? "● 准备就绪" : session.state === "running" ? "● 专注练习中" : "✓ 练习已结束";
}

function showResult(result) {
  $("result").hidden = false;
  const stats = result || session.buffer.metrics(session.elapsed());
  $("result-title").textContent = currentRun.mode === "lesson" ? "本关练习已结束。" : "又积累了一点熟悉感。";
  $("result-description").textContent = `本次准确率 ${stats.accuracy.toFixed(1)}%，${stats.final_correct_chars} 个位置正确的字符，${stats.error_attempts} 次错误尝试。保持练习，熟悉感会慢慢发生。`;
  $("save-status").textContent = result ? "✓ 本次成绩已保存在这台电脑上。" : "";
}

function finish() {
  clearInterval(timer);
  answer.readOnly = true;
  answer.value = session.buffer.text;
  renderMetrics(); renderTarget(); showResult();
  if (session.payload.attempted_chars) {
    saver.prepare(session.payload);
    saver.save();
  } else $("save-status").textContent = "本次没有确认输入的文字，因此不保存成绩。准备好后再试一次。";
}

function applySaved(data) {
  savedStats = data.result;
  renderMetrics(data.result); showResult(data.result);
  $("save-status").textContent = "✓ 本次成绩已保存在这台电脑上。";
  $("retry-save").hidden = true;
  if (currentRun.mode === "lesson") {
    const passed = data.result.passed;
    $("result-badge").textContent = passed ? "✓ 已通关" : "继续练习";
    $("result-title").textContent = passed ? data.progress?.all_done ? "十六关，一步一步走到了这里。" : "这一关，稳稳拿下。" : "再熟悉一点，就能过关。";
    if (!passed) $("result-description").textContent += " 准确率达到 95% 就能解锁下一关，先求准确，不必追赶速度。";
    const next = data.progress?.next_lesson;
    if (passed && (next || data.progress?.all_done)) {
      $("next-lesson").href = next ? `/practice?lesson=${encodeURIComponent(next.id)}` : "/practice";
      $("next-lesson").textContent = next ? "继续下一关 →" : "开始文章练习 →";
      $("next-lesson").hidden = false;
    }
  }
}

function initialize(run, savedResult = null) {
  controller?.destroy(); clearInterval(timer);
  currentRun = run; startBody = bodyFromRun(run);
  savedStats = savedResult;
  session = new PracticeSession(run, { onFinish: finish });
  saver = new ResultSaver(run.id, { onState: (state, data) => {
    if (currentRun.id !== run.id) return;
    $("retry").disabled = state === "saving";
    $("retry-save").disabled = state === "saving";
    if (state === "saving") { $("save-status").textContent = "正在把这次进步保存到本地…"; $("retry-save").hidden = true; }
    if (state === "save-failed") { $("save-status").textContent = `保存暂未成功：${data.message} 本次结果仍然保留，请重试。`; $("retry-save").hidden = false; }
    if (state === "saved") applySaved(data);
  } });
  $("setup").hidden = true; $("workspace").hidden = false; $("result").hidden = true;
  $("practice-title").textContent = run.title;
  $("source-title").textContent = `${run.language === "zh" ? "中文" : "English"} · ${characters(run.target_text).length} 字符`;
  $("mode-label").textContent = { full: "全文练习", timed: "限时挑战", lesson: "指法闯关" }[run.mode];
  $("time-label").textContent = run.mode === "timed" ? "剩余时间 TIME LEFT" : "练习用时 TIME";
  $("keyboard-panel").hidden = run.mode !== "lesson";
  $("keyboard").replaceChildren();
  keyboardGuide = run.mode === "lesson" ? new KeyboardGuide($("keyboard"), $("finger-hint"), boot.finger_map) : null;
  $("practice-notice").textContent = "";
  $("next-lesson").hidden = true; $("retry-save").hidden = true;
  $("result-badge").textContent = "练习完成";
  answer.value = ""; answer.readOnly = false;
  controller = new InputController(answer, { buffer: session.buffer,
    allowed: () => session.accepting(), onStart: () => session.start(),
    onCommit: () => { session.afterCommit(); renderMetrics(); renderTarget(); },
    notice: (message) => { $("practice-notice").textContent = message; } });
  timer = setInterval(() => { session.tick(); if (session.state !== "finished") renderMetrics(); }, 100);
  renderMetrics(); renderTarget();
  if (savedResult) {
    clearInterval(timer); session.state = "finished"; session.elapsedMs = savedResult.elapsed_ms;
    answer.readOnly = true; answer.placeholder = "本次成绩已保存，点击“再练一次”重新开始。";
    renderMetrics(savedResult); renderTarget(); showResult(savedResult);
    fetch("/api/lessons").then((response) => response.json()).then((progress) => applySaved({ result: savedResult, progress })).catch(() => {});
  } else {
    const pending = saver.restore();
    if (pending) {
      clearInterval(timer); session.state = "finished"; session.elapsedMs = pending.elapsed_ms; session.payload = pending;
      session.buffer.text = pending.final_input; session.buffer.attempts = pending.attempted_chars;
      session.buffer.correctAttempts = pending.correct_attempts;
      answer.value = pending.final_input; answer.readOnly = true;
      renderMetrics(); renderTarget(); showResult(); saver.save();
    } else answer.focus();
  }
}

async function start(body) {
  $("start").disabled = true; $("retry").disabled = true; $("setup-error").hidden = true;
  try {
    const response = await fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "暂时无法开始练习，请重试。");
    history.replaceState(null, "", `/practice?run=${data.run.id}`);
    initialize(data.run);
  } catch (error) {
    $("setup-error").textContent = error.message; $("setup-error").hidden = false; $("setup").hidden = false;
  } finally { $("start").disabled = false; $("retry").disabled = false; }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (boot.lesson) { start({ mode: "lesson", lesson_id: boot.lesson.id }); return; }
  const mode = new FormData(form).get("mode");
  const body = { mode, language: $("language").value };
  if ($("source").value === "custom") body.text = $("custom-text").value;
  else body.article_id = $("article").value;
  if (mode === "timed") body.duration_seconds = Number(new FormData(form).get("duration"));
  start(body);
});
$("language").addEventListener("change", populateArticles);
$("article").addEventListener("change", previewArticle);
form.addEventListener("change", updateSetup);
$("focus-answer").addEventListener("click", () => answer.focus());
$("target-text").addEventListener("click", () => answer.focus());
answer.addEventListener("click", renderTarget);
answer.addEventListener("keyup", renderTarget);
answer.addEventListener("keydown", (event) => {
  if (keyboardGuide && session?.accepting()) {
    const caret = characters(answer.value.slice(0, answer.selectionStart)).length;
    keyboardGuide.press(event.key, session.buffer.targetAt(caret));
  }
  if (currentRun?.language === "en" && event.getModifierState("CapsLock")) $("practice-notice").textContent = "当前大写锁定已开启，请留意目标字母的大小写。";
});
$("change-material").addEventListener("click", () => {
  controller?.destroy(); clearInterval(timer); session = null;
  $("workspace").hidden = true; $("setup").hidden = false;
});
$("retry").addEventListener("click", () => start(startBody));
$("retry-save").addEventListener("click", () => saver?.save());
document.addEventListener("visibilitychange", () => { session?.tick(); renderMetrics(); });
document.querySelector(`input[name="mode"][value="${boot.initial_mode}"]`).checked = true;
$("language").value = boot.initial_language;
populateArticles(); updateSetup();
if (boot.run) initialize(boot.run, boot.saved_result);
