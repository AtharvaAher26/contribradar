"""Pipeline tracker: issue URL -> contribution state, stored as JSON.

States (docs/PRODUCT-PLAN.md): found -> saved -> claimed -> pr_opened ->
changes_requested -> merged, with ``dropped`` reachable from anywhere and
``changes_requested`` looping back to ``pr_opened``. The tracker also owns
the seen-set used to dedup scan results (an issue is never re-suggested).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATES = [
    "found",
    "saved",
    "claimed",
    "pr_opened",
    "changes_requested",
    "merged",
    "dropped",
]

TRANSITIONS: dict[str, set[str]] = {
    "found": {"saved", "claimed", "pr_opened", "dropped"},
    "saved": {"claimed", "pr_opened", "dropped"},
    "claimed": {"pr_opened", "saved", "dropped"},
    "pr_opened": {"changes_requested", "merged", "dropped"},
    "changes_requested": {"pr_opened", "merged", "dropped"},
    "merged": set(),
    "dropped": {"found"},
}


class TransitionError(ValueError):
    pass


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class Pipeline:
    def __init__(self, items: list[dict] | None = None):
        self.items: dict[str, dict] = {item["url"]: item for item in (items or [])}

    # -- persistence ----------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "Pipeline":
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data.get("items", []))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "items": sorted(self.items.values(), key=lambda i: i["added"])}
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # -- operations -----------------------------------------------------
    def add(
        self,
        url: str,
        *,
        title: str = "",
        repo: str = "",
        score: int | None = None,
        state: str = "found",
        date: str | None = None,
    ) -> dict:
        if state not in STATES:
            raise TransitionError(f"unknown state '{state}' (choose from {', '.join(STATES)})")
        if url in self.items:
            return self.items[url]
        date = date or _today()
        item = {
            "url": url,
            "title": title,
            "repo": repo,
            "score": score,
            "state": state,
            "added": date,
            "updated": date,
            "history": [{"state": state, "date": date}],
        }
        self.items[url] = item
        return item

    def move(self, url: str, new_state: str, date: str | None = None) -> dict:
        if url not in self.items:
            raise TransitionError(f"'{url}' is not in the pipeline — add it first")
        if new_state not in STATES:
            raise TransitionError(
                f"unknown state '{new_state}' (choose from {', '.join(STATES)})"
            )
        item = self.items[url]
        current = item["state"]
        if new_state == current:
            return item
        if new_state not in TRANSITIONS[current]:
            allowed = ", ".join(sorted(TRANSITIONS[current])) or "nothing (terminal state)"
            raise TransitionError(f"cannot move {current} -> {new_state}; allowed: {allowed}")
        date = date or _today()
        item["state"] = new_state
        item["updated"] = date
        item["history"].append({"state": new_state, "date": date})
        return item

    def list(self, state: str | None = None) -> list[dict]:
        items = sorted(self.items.values(), key=lambda i: i["added"])
        if state:
            items = [i for i in items if i["state"] == state]
        return items

    def counts(self) -> dict[str, int]:
        counts = {state: 0 for state in STATES}
        for item in self.items.values():
            counts[item["state"]] += 1
        return counts


class SeenSet:
    """URLs of issues already surfaced by a scan (never suggest twice)."""

    def __init__(self, urls: dict[str, str] | None = None):
        self.urls: dict[str, str] = dict(urls or {})

    @classmethod
    def load(cls, path: str | Path) -> "SeenSet":
        path = Path(path)
        if not path.exists():
            return cls()
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.urls, indent=2) + "\n", encoding="utf-8")

    def __contains__(self, url: str) -> bool:
        return url in self.urls

    def mark(self, url: str, date: str | None = None) -> None:
        self.urls.setdefault(url, date or _today())
