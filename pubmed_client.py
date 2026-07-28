"""
PubMed (NCBI E-utilities) から最新のケースレポートを取得するクライアント。

NCBI E-utilities は無料・登録不要で利用可能(ただしAPIキーがあるとレート制限が緩和される)。
公式ドキュメント: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class CaseReport:
    pmid: str
    title: str
    journal: str
    pub_date: str
    abstract: str
    authors: str
    url: str


def _request_with_retry(url: str, params: dict, retries: int = 3, backoff: float = 1.5) -> requests.Response:
    """NCBI側の一時エラーに備えて簡単なリトライを行う。"""
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_err = e
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"PubMedへのリクエストに失敗しました: {last_err}")


def search_case_report_pmids(
    days: int = 1,
    retmax: int = 20,
    api_key: Optional[str] = None,
    extra_term: Optional[str] = None,
) -> list[str]:
    """
    直近 `days` 日以内に発行された、Publication Type = "Case Reports" の
    論文のPMID一覧を新しい順に取得する。

    extra_term: 診療科などで絞り込みたい場合に追加するPubMed検索語
                (例: "cardiology[MeSH Terms]")。医学全般の場合はNoneでよい。
    """
    term = 'Case Reports[Publication Type] AND English[Language]'
    if extra_term:
        term += f" AND {extra_term}"

    params = {
        "db": "pubmed",
        "term": term,
        "sort": "pub+date",
        "retmax": str(retmax),
        "retmode": "json",
        "reldate": str(days),   # 直近days日以内
        "datetype": "pdat",     # 出版日を基準にする
    }
    if api_key:
        params["api_key"] = api_key

    resp = _request_with_retry(f"{EUTILS_BASE}/esearch.fcgi", params)
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_case_reports(pmids: list[str], api_key: Optional[str] = None) -> list[CaseReport]:
    """PMIDのリストから、タイトル・抄録・雑誌名などをまとめて取得する。"""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key

    resp = _request_with_retry(f"{EUTILS_BASE}/efetch.fcgi", params)
    root = ET.fromstring(resp.content)

    reports = []
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else ""

        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else "(タイトル不明)"

        journal_el = article.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else "(雑誌名不明)"

        # 抄録は複数セクション(Background/Case Presentation等)に分かれることがあるため結合
        abstract_parts = []
        for ab_text in article.findall(".//Abstract/AbstractText"):
            label = ab_text.get("Label")
            text = "".join(ab_text.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = "\n".join(abstract_parts).strip() or "(抄録なし)"

        # 出版日
        pub_date_el = article.find(".//Article/ArticleDate") or article.find(".//JournalIssue/PubDate")
        if pub_date_el is not None:
            year = pub_date_el.findtext("Year", default="")
            month = pub_date_el.findtext("Month", default="")
            day = pub_date_el.findtext("Day", default="")
            pub_date = "-".join(p for p in [year, month, day] if p)
        else:
            pub_date = "(日付不明)"

        # 著者
        authors = []
        for author in article.findall(".//AuthorList/Author"):
            last = author.findtext("LastName")
            fore = author.findtext("ForeName")
            if last and fore:
                authors.append(f"{fore} {last}")
            elif last:
                authors.append(last)
        authors_str = ", ".join(authors[:3]) + (" ほか" if len(authors) > 3 else "")

        reports.append(
            CaseReport(
                pmid=pmid,
                title=title,
                journal=journal,
                pub_date=pub_date,
                abstract=abstract,
                authors=authors_str or "(著者不明)",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            )
        )
    return reports


def get_latest_case_reports(
    days: int = 1,
    retmax: int = 20,
    api_key: Optional[str] = None,
    extra_term: Optional[str] = None,
) -> list[CaseReport]:
    """検索から詳細取得までをまとめて実行するショートカット関数。"""
    pmids = search_case_report_pmids(days=days, retmax=retmax, api_key=api_key, extra_term=extra_term)
    return fetch_case_reports(pmids, api_key=api_key)
