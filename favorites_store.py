"""
お気に入り(保存済みケースレポート)をJSONファイルに保存・読み込みするモジュール。

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


def load_favorites() -> dict:
    """PMIDをキーにした、保存済みケースレポートのdictを返す。"""
    if not os.path.exists(FAVORITES_PATH):
        return {}
    try:
        with open(FAVORITES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_favorites(favorites: dict) -> None:
    with open(FAVORITES_PATH, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def add_favorite(report: CaseReport) -> None:
    favorites = load_favorites()
    favorites[report.pmid] = asdict(report)
    save_favorites(favorites)


def remove_favorite(pmid: str) -> None:
    favorites = load_favorites()
    if pmid in favorites:
        del favorites[pmid]
        save_favorites(favorites)


def is_favorite(pmid: str, favorites: Optional[dict] = None) -> bool:
    if favorites is None:
        favorites = load_favorites()
    return pmid in favorites
