"""Authoritative score definitions, shared with the browser through test cases."""

import hashlib
import json
import math


def calculate_result(run, payload):
    if not isinstance(payload, dict):
        raise ValueError("结果必须是 JSON 对象。")
    attempts = payload.get("attempted_chars")
    correct = payload.get("correct_attempts")
    elapsed = payload.get("elapsed_ms")
    text = payload.get("final_input")
    if type(attempts) is not int or type(correct) is not int or attempts <= 0:
        raise ValueError("字符尝试数必须为正整数，正确尝试数必须为整数。")
    if not 0 <= correct <= attempts or attempts > 2**53 - 1:
        raise ValueError("正确尝试数不能大于总尝试数。")
    try:
        finite_elapsed = type(elapsed) in (int, float) and math.isfinite(elapsed)
    except OverflowError:
        finite_elapsed = False
    if not finite_elapsed or elapsed < 0:
        raise ValueError("练习用时必须是有效的非负数值。")
    if not isinstance(text, str):
        raise ValueError("缺少最终作答文字。")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) > attempts:
        raise ValueError("最终文字长度不能超过字符尝试数。")
    target = run["target_text"]
    if run["mode"] == "timed":
        expected_ms = run["duration_seconds"] * 1000
        if elapsed < expected_ms:
            raise ValueError("限时练习尚未达到结束时间。")
        elapsed = float(expected_ms)
        final_correct = sum(char == target[index % len(target)] for index, char in enumerate(text))
    else:
        if len(text) != len(target):
            raise ValueError("请完成全部目标后再保存成绩。")
        final_correct = sum(a == b for a, b in zip(text, target))
        elapsed = max(1.0, float(elapsed))
    accuracy = correct / attempts * 100
    speed_unit = "字符/分钟" if run["language"] == "zh" else "WPM"
    speed = final_correct * 60000 / elapsed / (1 if run["language"] == "zh" else 5)
    passed = int(correct * 100 >= attempts * 95) if run["mode"] == "lesson" else None
    canonical = {"final_input": text, "attempted_chars": attempts,
                 "correct_attempts": correct, "elapsed_ms": elapsed}
    fingerprint = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"attempted_chars": attempts, "correct_attempts": correct,
            "final_correct_chars": final_correct, "final_length": len(text), "elapsed_ms": elapsed,
            "accuracy": accuracy, "speed": speed, "speed_unit": speed_unit,
            "passed": passed, "fingerprint": fingerprint}
