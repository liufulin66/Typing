import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def normalize_text(value):
    if not isinstance(value, str):
        raise ValueError("请输入需要练习的文字。")
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ValueError("请先输入或粘贴有效的练习内容。")
    return text


@lru_cache
def _articles():
    return json.loads((DATA_DIR / "articles.json").read_text(encoding="utf-8"))


def get_articles(language):
    if language not in ("zh", "en"):
        raise ValueError("请选择中文或英文。")
    return [dict(item) for item in _articles() if item["language"] == language]


def get_article(article_id):
    return next((dict(item) for item in _articles() if item["id"] == article_id), None)
