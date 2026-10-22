import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, jsonify, request

from .content import get_article, get_articles, normalize_text
from .courses import COURSE_VERSION, get_lesson, get_progress
from .db import get_db
from .scoring import calculate_result

bp = Blueprint("api", __name__, url_prefix="/api")


class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status


@bp.errorhandler(ApiError)
def api_error(error):
    return jsonify(error=error.message), error.status


@bp.errorhandler(ValueError)
def invalid_request(error):
    return jsonify(error=str(error)), 400


@bp.errorhandler(sqlite3.OperationalError)
def database_unavailable(_error):
    return jsonify(error="本地数据暂时无法保存或读取，请稍后重试。"), 503


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError("请求必须是 JSON 对象。")
    return body


@bp.get("/articles")
def articles():
    return jsonify(articles=get_articles(request.args.get("language", "zh")))


@bp.get("/lessons")
def lessons():
    return jsonify(get_progress())


@bp.post("/runs")
def create_run():
    body = json_body()
    mode = body.get("mode")
    language = body.get("language", "en" if mode == "lesson" else "zh")
    if mode not in ("full", "timed", "lesson") or language not in ("zh", "en"):
        raise ValueError("请选择有效的练习模式和语言。")
    duration = None
    version = None
    if mode == "lesson":
        lesson = get_lesson(body.get("lesson_id"))
        if lesson is None:
            raise ApiError("没有找到这个关卡。", 404)
        state = next(item for item in get_progress()["lessons"] if item["id"] == lesson["id"])
        if not state["unlocked"]:
            raise ApiError("请先完成前面的关卡，再来练习这一关。", 403)
        language, kind, source_id = "en", "lesson", lesson["id"]
        title, target, version = lesson["title"], lesson["text"], COURSE_VERSION
    else:
        if body.get("article_id") is not None and body.get("text") is not None:
            raise ValueError("请选择内置文章或自定义文本中的一种。")
        if body.get("article_id") is not None:
            article = get_article(body["article_id"])
            if article is None:
                raise ApiError("没有找到这篇文章。", 404)
            if article["language"] != language:
                raise ValueError("文章语言与所选练习语言不一致。")
            title, target, kind, source_id = article["title"], article["text"], "article", article["id"]
        else:
            target = normalize_text(body.get("text"))
            title, kind, source_id = "自定义练习", "custom", None
        if mode == "timed":
            duration = body.get("duration_seconds")
            if type(duration) is not int or duration not in (60, 180, 300):
                raise ValueError("限时时长请选择 1、3 或 5 分钟。")
    run = {"id": uuid4().hex, "mode": mode, "language": language, "source_kind": kind,
           "source_id": source_id, "title": title, "target_text": normalize_text(target),
           "course_version": version, "duration_seconds": duration,
           "created_at": datetime.now(timezone.utc).isoformat()}
    connection = get_db()
    with connection:
        connection.execute(
            "INSERT INTO practice_runs (id,mode,language,source_kind,source_id,title,target_text,"
            "course_version,duration_seconds,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", tuple(run.values()),
        )
    return jsonify(run=run), 201


def result_record(run_id):
    row = get_db().execute(
        "SELECT s.*,r.mode,r.language,r.title,r.source_id FROM practice_results s "
        "JOIN practice_runs r ON r.id=s.run_id WHERE s.run_id=?", (run_id,),
    ).fetchone()
    return serialize_result(row)


def serialize_result(row):
    result = dict(row)
    result.pop("fingerprint", None)
    result["error_attempts"] = result["attempted_chars"] - result["correct_attempts"]
    if result["passed"] is not None:
        result["passed"] = bool(result["passed"])
    return result


@bp.post("/runs/<run_id>/result")
def save_result(run_id):
    connection = get_db()
    run = connection.execute("SELECT * FROM practice_runs WHERE id=?", (run_id,)).fetchone()
    if run is None:
        raise ApiError("没有找到本次练习，请重新开始。", 404)
    score = calculate_result(run, json_body())
    values = {"run_id": run_id, **score, "finished_at": datetime.now(timezone.utc).isoformat()}
    # The column names below come only from our score definition, never from request keys.
    columns = list(values)
    with connection:
        cursor = connection.execute(
            f"INSERT OR IGNORE INTO practice_results ({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)})", tuple(values.values()),
        )
        created = cursor.rowcount == 1
        existing = connection.execute("SELECT fingerprint FROM practice_results WHERE run_id=?", (run_id,)).fetchone()
        if existing["fingerprint"] != score["fingerprint"]:
            raise ApiError("这次练习已有不同的结算结果，请重新开始练习。", 409)
    return jsonify(result=result_record(run_id), progress=get_progress()), 201 if created else 200


def get_summary():
    row = get_db().execute(
        "SELECT count(*) AS total, coalesce(sum(elapsed_ms),0) AS elapsed_ms, "
        "coalesce(avg(accuracy),0) AS average_accuracy FROM practice_results"
    ).fetchone()
    return dict(row)


def get_history(limit=20, offset=0):
    rows = get_db().execute(
        "SELECT s.*,r.mode,r.language,r.title,r.source_id FROM practice_results s "
        "JOIN practice_runs r ON r.id=s.run_id ORDER BY s.finished_at DESC,s.rowid DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [serialize_result(row) for row in rows]


@bp.get("/history")
def history():
    try:
        limit = int(request.args.get("limit", "20"))
        offset = int(request.args.get("offset", "0"))
    except (ValueError, TypeError):
        raise ValueError("分页参数必须是整数。")
    if not 1 <= limit <= 100 or not 0 <= offset <= 2**31 - 1:
        raise ValueError("分页范围无效，请重新选择。")
    summary = get_summary()
    return jsonify(results=get_history(limit, offset), total=summary["total"], summary=summary)
