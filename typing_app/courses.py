import json
from functools import lru_cache

from .content import DATA_DIR
from .db import get_db

COURSE_VERSION = 1
FINGER_GROUPS = {
    "左手小指": "qaz", "左手无名指": "wsx", "左手中指": "edc",
    "左手食指": "rfvtgb", "右手食指": "yhnujm", "右手中指": "ik",
    "右手无名指": "ol", "右手小指": "p", "拇指": " ",
}
FINGER_MAP = {key: name for name, keys in FINGER_GROUPS.items() for key in keys}


@lru_cache
def _catalog():
    items = json.loads((DATA_DIR / "lessons.json").read_text(encoding="utf-8"))
    learned = set()
    for number, item in enumerate(items, 1):
        learned.update(item["new_keys"])
        item.update(number=number, allowed_keys="".join(sorted(learned)), course_version=COURSE_VERSION)
    return items


def get_lessons():
    return [dict(item) for item in _catalog()]


def get_lesson(lesson_id):
    return next((dict(item) for item in _catalog() if item["id"] == lesson_id), None)


def get_progress():
    rows = get_db().execute(
        "SELECT DISTINCT r.source_id FROM practice_runs r JOIN practice_results s ON s.run_id=r.id "
        "WHERE r.mode='lesson' AND r.course_version=? AND s.passed=1", (COURSE_VERSION,),
    ).fetchall()
    passed_ids = {row["source_id"] for row in rows}
    lessons = get_lessons()
    previous_passed = True
    for lesson in lessons:
        lesson["passed"] = lesson["id"] in passed_ids
        lesson["unlocked"] = previous_passed
        lesson["status"] = "passed" if lesson["passed"] else "available" if previous_passed else "locked"
        previous_passed = previous_passed and lesson["passed"]
    next_lesson = next((item for item in lessons if item["unlocked"] and not item["passed"]), None)
    return {"lessons": lessons, "next_lesson": next_lesson,
            "completed": sum(item["passed"] for item in lessons), "total": len(lessons),
            "all_done": all(item["passed"] for item in lessons), "finger_map": FINGER_MAP}
