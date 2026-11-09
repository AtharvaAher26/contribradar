"""Offline fixture builders shaped like real GitHub API payloads."""

from __future__ import annotations

NOW_ISO = "2026-11-09T12:00:00Z"


def make_issue(**overrides) -> dict:
    issue = {
        "number": 42,
        "title": "Add RAG support to the CLI",
        "body": "It would be great if the CLI could index documents and answer "
        "questions over them using retrieval augmented generation.",
        "html_url": "https://github.com/octocat/llm-tools/issues/42",
        "repository_url": "https://api.github.com/repos/octocat/llm-tools",
        "created_at": "2026-10-20T09:30:00Z",
        "comments": 3,
        "labels": [{"name": "good first issue"}],
        "assignee": None,
        "assignees": [],
        "state": "open",
    }
    issue.update(overrides)
    return issue


def make_repo(**overrides) -> dict:
    repo = {
        "full_name": "octocat/llm-tools",
        "archived": False,
        "pushed_at": "2026-11-05T08:00:00Z",
        "topics": ["llm", "cli"],
        "description": "LLM command line tools",
        "language": "Python",
    }
    repo.update(overrides)
    return repo


def maintainer_comment(**overrides) -> dict:
    comment = {
        "body": "Thanks for filing — a fix here would touch parser.py only.",
        "author_association": "MEMBER",
        "user": {"login": "maintainer-jane"},
    }
    comment.update(overrides)
    return comment


def claim_comment(**overrides) -> dict:
    comment = {
        "body": "Hi! I'm working on this one, PR soon.",
        "author_association": "NONE",
        "user": {"login": "eager-newcomer"},
    }
    comment.update(overrides)
    return comment


def external_pr(**overrides) -> dict:
    pr = {
        "title": "Fix typo in docs",
        "author_association": "FIRST_TIME_CONTRIBUTOR",
        "user": {"login": "first-timer-fred"},
    }
    pr.update(overrides)
    return pr
