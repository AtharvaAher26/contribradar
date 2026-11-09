from datetime import datetime, timezone

from contribradar.config import DEFAULT_CONFIG
from contribradar.digest import render_digest
from contribradar.scoring import score_issue
from fixtures import maintainer_comment, make_issue, make_repo

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


def _find():
    issue = make_issue()
    score = score_issue(
        issue, make_repo(), config=DEFAULT_CONFIG, now=NOW,
        comments=[maintainer_comment()], external_merge_90d=True, linked_pr=False,
    )
    return {
        "url": issue["html_url"],
        "title": issue["title"],
        "repo": "octocat/llm-tools",
        "created_at": issue["created_at"],
        "score": score,
    }


def test_digest_renders_find_with_reasons():
    text = render_digest([_find()], [], generated_at=NOW, rejected_count=3)
    assert "Add RAG support to the CLI" in text
    assert "score 90/90" in text
    assert "external contributor's PR was merged" in text
    assert "3 candidates rejected" in text


def test_digest_renders_pipeline_sections():
    items = [
        {
            "url": "https://github.com/octocat/llm-tools/issues/42",
            "title": "Add RAG support to the CLI",
            "state": "claimed",
            "updated": "2026-11-08",
        },
        {
            "url": "https://github.com/octocat/llm-tools/issues/7",
            "title": "Fix the thing",
            "state": "merged",
            "updated": "2026-11-01",
        },
    ]
    text = render_digest([], items, generated_at=NOW)
    assert "**claimed**" in text
    assert "**merged**" in text
    assert "claimed: 1" in text and "merged: 1" in text


def test_digest_empty_states():
    text = render_digest([], [], generated_at=NOW)
    assert "No new finds" in text
    assert "pipeline is empty" in text
