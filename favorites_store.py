"""
お気に入り(保存済みケースレポート)を、ログインユーザーごとにJSONファイルへ保存・読み込みするモジュール。

データ構造:
{
  "user@example.com": {
    "12345678": { ...CaseReportの内容... },
    ...
  },
  ...
}

注意:
Streamlit Community Cloud(無料ホスティング)ではファイルシステムが一時的なため、
長時間アクセスがなくアプリが再起動した際にデータが消える可能性があります。
ローカルPCで実行している場合は、通常は消えずに残ります。
"""

import json
import os
from dataclasses import asdict
from typing import Optional

from pubmed_client import CaseReport

FAVORITES_PATH = os.path.join(os.path.dirname(__file__), "favorites.json")


def _load_all() -> dict:
    if not os.path.exists(FAVORITES_PATH):
        return {}
    try:
        with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(all_favorites: dict) -> None:
    with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
        json.dump(all_favorites, f, ensure_ascii=False, indent=2)


def load_favorites(user_email: str) -> dict:
    """指定ユーザーの、PMIDをキーにした保存済みケースレポートのdictを返す。"""
    return _load_all().get(user_email, {})


def add_favorite(user_email: str, report: CaseReport) -> None:
    all_favorites = _load_all()
    user_favorites = all_favorites.setdefault(user_email, {})
    user_favorites[report.pmid] = asdict(report)
    _save_all(all_favorites)


def remove_favorite(user_email: str, pmid: str) -> None:
    all_favorites = _load_all()
    user_favorites = all_favorites.get(user_email, {})
    if pmid in user_favorites:
        del user_favorites[pmid]
        _save_all(all_favorites)


def is_favorite(user_email: str, pmid: str, favorites: Optional[dict] = None) -> bool:
    if favorites is None:
        favorites = load_favorites(user_email)
    return pmid in favorites
