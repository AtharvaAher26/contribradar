"""Minimal GitHub REST/Search API client (requests + stdlib only).

Works unauthenticated for small runs (search: 10 req/min, core: 60 req/hr)
and uses ``GITHUB_TOKEN`` when present (search: 30 req/min, core: 5,000/hr).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import requests

from .scoring import is_external_pr

API_BASE = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


def build_issue_query(labels: list[str], languages: list[str]) -> str:
    """One search query per label, OR-ing the configured languages."""
    parts = ["is:issue", "is:open"]
    if labels:
        parts.append(" ".join(f'label:"{lab}"' for lab in labels))
    for lang in languages:
        parts.append(f"language:{lang}")
    return " ".join(parts)


def repo_full_name_from_issue(issue: dict) -> str | None:
    """Search results carry ``repository_url`` (…/repos/owner/name)."""
    url = issue.get("repository_url") or ""
    marker = "/repos/"
    if marker in url:
        return url.split(marker, 1)[1]
    html = issue.get("html_url") or ""
    parts = [p for p in html.split("/") if p]
    if len(parts) >= 2:
        return f"{parts[-3]}/{parts[-2]}" if len(parts) >= 3 else None
    return None


class GitHubClient:
    def __init__(self, token: str | None = None, session: requests.Session | None = None):
        self.session = session or requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "contribradar/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.session.headers.update(headers)

    # -- low level ------------------------------------------------------
    def _get(self, path: str, params: dict | None = None) -> object:
        resp = self.session.get(f"{API_BASE}{path}", params=params, timeout=30)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise GitHubError(
                "GitHub rate limit hit. Set GITHUB_TOKEN or wait a minute and retry."
            )
        if resp.status_code >= 400:
            raise GitHubError(f"GET {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    # -- endpoints ------------------------------------------------------
    def search_issues(self, query: str, per_page: int = 20) -> list[dict]:
        data = self._get(
            "/search/issues",
            {"q": query, "per_page": per_page, "sort": "created", "order": "desc"},
        )
        return list(data.get("items", []))  # type: ignore[union-attr]

    def get_repo(self, full_name: str) -> dict:
        return dict(self._get(f"/repos/{full_name}"))  # type: ignore[arg-type]

    def get_issue_comments(self, full_name: str, number: int) -> list[dict]:
        data = self._get(f"/repos/{full_name}/issues/{number}/comments", {"per_page": 100})
        return list(data)  # type: ignore[arg-type]

    def external_merge_in_last_days(
        self, full_name: str, days: int = 90, now: datetime | None = None
    ) -> bool:
        """True if the repo merged an external contributor's PR recently."""
        now = now or datetime.now(timezone.utc)
        since = (now - timedelta(days=days)).date().isoformat()
        query = f"repo:{full_name} is:pr is:merged merged:>={since}"
        items = self.search_issues(query, per_page=50)
        return any(is_external_pr(item, full_name) for item in items)

    def open_pr_issue_refs(self, full_name: str) -> set[int]:
        """Issue numbers referenced (#123) by any open PR's title or body."""
        refs: set[int] = set()
        data = self._get(f"/repos/{full_name}/pulls", {"state": "open", "per_page": 100})
        for pr in data:  # type: ignore[union-attr]
            text = f"{pr.get('title') or ''}\n{pr.get('body') or ''}"
            refs.update(int(n) for n in re.findall(r"#(\d+)", text))
        return refs
