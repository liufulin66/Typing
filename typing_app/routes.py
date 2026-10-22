from flask import Blueprint, render_template, request

from .api import get_history, get_summary, result_record
from .content import get_articles
from .courses import FINGER_MAP, get_progress
from .db import get_db

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    return render_template("index.html", progress=get_progress(), summary=get_summary(),
                           articles=get_articles("zh"))


@bp.get("/practice")
def practice():
    progress = get_progress()
    lesson_id = request.args.get("lesson")
    lesson = next((item for item in progress["lessons"] if item["id"] == lesson_id), None)
    if lesson_id and (lesson is None or not lesson["unlocked"]):
        return render_template("error.html", message="请先完成前面的关卡，再来练习这一关。" if lesson else "没有找到这个关卡。"), 403 if lesson else 404
    run, saved = None, None
    if request.args.get("run"):
        row = get_db().execute("SELECT * FROM practice_runs WHERE id=?", (request.args["run"],)).fetchone()
        if row is None:
            return render_template("error.html", message="这次练习已不存在，请重新选择素材。"), 404
        run = dict(row)
        if run["mode"] == "lesson":
            lesson = next((item for item in progress["lessons"] if item["id"] == run["source_id"]), None)
            if lesson is None or not lesson["unlocked"]:
                return render_template("error.html", message="请先完成前面的关卡。"), 403
        if get_db().execute("SELECT 1 FROM practice_results WHERE run_id=?", (run["id"],)).fetchone():
            saved = result_record(run["id"])
    mode = request.args.get("mode", "full")
    language = request.args.get("language", "zh")
    if mode not in ("full", "timed"):
        mode = "full"
    if language not in ("zh", "en"):
        language = "zh"
    boot = {"articles": {"zh":get_articles("zh"), "en":get_articles("en")},
            "initial_mode":mode, "initial_language":language,
            "article_id":request.args.get("article_id"), "lesson":lesson,
            "run":run, "saved_result":saved, "finger_map":FINGER_MAP}
    return render_template("practice.html", boot=boot, lesson=lesson)


@bp.get("/lessons")
def lessons():
    return render_template("lessons.html", progress=get_progress())


@bp.get("/history")
def history():
    summary = get_summary()
    pages = max(1, (summary["total"] + 19) // 20)
    page = min(pages, max(1, request.args.get("page", 1, type=int)))
    return render_template("history.html", records=get_history(20, (page - 1) * 20),
                           summary=summary, page=page, pages=pages)
