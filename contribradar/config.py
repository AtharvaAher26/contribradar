"""Configuration for ContribRadar.

Defaults live here; a user ``config.json`` (see ``contribradar init``) is
merged over them. Nothing here is secret — the GitHub token comes only from
the ``GITHUB_TOKEN`` environment variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_CONFIG: dict = {
    # Labels that mark an issue as beginner-welcoming on GitHub.
    "labels": ["good first issue", "help wanted", "first-timers-only"],
    # Languages to restrict the search to.
    "languages": ["python"],
    # Stack keywords: a hit in the issue title/body or repo topics earns the
    # stack-match points. Matched on word boundaries.
    "stack_keywords": [
        "llm",
        "rag",
        "agent",
        "agents",
        "machine learning",
        "deep learning",
        "nlp",
        "automation",
        "transformer",
        "chatbot",
        "langchain",
        "gpt",
    ],
    # How many search results to pull per label query (keep small: the
    # unauthenticated search rate limit is 10 requests/minute).
    "per_query": 20,
    # How many ranked finds make the digest shortlist.
    "top_n": 8,
    # Issues older than this are rejected outright (plan rule).
    "max_issue_age_days": 180,
    # Issues with at least this many comments are rejected (plan rule:
    # "not 40 comments deep").
    "max_comments": 40,
    # Fetch issue comments (needed for the maintainer-reply and collision
    # signals) for at most this many candidates per scan.
    "max_comment_fetches": 40,
}


def load_config(path: str | Path | None = None) -> dict:
    """Return DEFAULT_CONFIG merged with an optional JSON config file."""
    config = dict(DEFAULT_CONFIG)
    if path is not None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Config file {path} must contain a JSON object")
        config.update(data)
    return config


def write_default_config(path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    return path


def github_token() -> str | None:
    """The GitHub token, if the user provided one via the environment."""
    return os.environ.get("GITHUB_TOKEN") or None
