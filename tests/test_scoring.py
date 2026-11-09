from datetime import datetime, timezone

import pytest

from contribradar.config import DEFAULT_CONFIG
from contribradar.scoring import (
    detect_claims,
    is_external_pr,
    score_issue,
)
from fixtures import (
    claim_comment,
    external_pr,
    maintainer_comment,
    make_issue,
    make_repo,
)

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


def signal(result, name):
    return next(s for s in result.signals if s.name == name)


def perfect_score(**kwargs):
    kwargs.setdefault("comments", [maintainer_comment()])
    kwargs.setdefault("external_merge_90d", True)
    kwargs.setdefault("linked_pr", False)
    return score_issue(make_issue(), make_repo(), config=DEFAULT_CONFIG, now=NOW, **kwargs)


def test_full_score_is_90_and_decomposed():
    result = perfect_score()
    assert not result.rejected
    assert result.total == 90
    assert {s.name for s in result.signals} == {
        "beginner_label",
        "repo_active_30d",
        "external_merge_90d",
        "unclaimed",
        "maintainer_replied",
        "stack_match",
    }
    # Every point is explained by a named signal.
    assert sum(s.points for s in result.signals) == result.total
    assert len(result.reasons()) == 6


def test_beginner_label_variants():
    issue = make_issue(labels=[{"name": "help wanted"}])
    result = score_issue(issue, make_repo(), config=DEFAULT_CONFIG, now=NOW)
    assert signal(result, "beginner_label").points == 20
    issue = make_issue(labels=[{"name": "enhancement"}])
    result = score_issue(issue, make_repo(), config=DEFAULT_CONFIG, now=NOW)
    assert signal(result, "beginner_label").points == 0


def test_stale_repo_loses_activity_points():
    repo = make_repo(pushed_at="2026-06-01T00:00:00Z")
    result = score_issue(make_issue(), repo, config=DEFAULT_CONFIG, now=NOW)
    assert signal(result, "repo_active_30d").points == 0


def test_no_external_merge_loses_points():
    result = perfect_score(external_merge_90d=False)
    assert signal(result, "external_merge_90d").points == 0
    assert result.total == 70


def test_assigned_issue_loses_unclaimed_points():
    issue = make_issue(assignees=[{"login": "someone"}])
    result = score_issue(
        issue, make_repo(), config=DEFAULT_CONFIG, now=NOW,
        external_merge_90d=True, linked_pr=False,
    )
    assert signal(result, "unclaimed").points == 0


def test_linked_pr_loses_unclaimed_points():
    result = perfect_score(linked_pr=True)
    assert signal(result, "unclaimed").points == 0
    assert "already references" in signal(result, "unclaimed").detail


def test_maintainer_reply_points_and_absence():
    result = perfect_score(comments=[maintainer_comment()])
    assert signal(result, "maintainer_replied").points == 10
    result = perfect_score(comments=[claim_comment()])
    assert signal(result, "maintainer_replied").points == 0


def test_unchecked_signals_score_zero_and_say_so():
    result = score_issue(make_issue(), make_repo(), config=DEFAULT_CONFIG, now=NOW)
    assert signal(result, "maintainer_replied").detail == "comments not checked"
    assert signal(result, "external_merge_90d").points == 0
    assert "not checked" in signal(result, "external_merge_90d").detail


def test_stack_match_uses_word_boundaries():
    # "said" must not trigger the keyword matcher via a substring.
    issue = make_issue(title="Fix what the docs said", body="The manual said to restart.")
    result = score_issue(issue, make_repo(topics=[], description=""), config=DEFAULT_CONFIG, now=NOW)
    assert signal(result, "stack_match").points == 0
    issue = make_issue(title="Add an agent mode", body="x" * 60)
    result = score_issue(issue, make_repo(topics=[], description=""), config=DEFAULT_CONFIG, now=NOW)
    assert signal(result, "stack_match").points == 10


def test_reject_archived_repo():
    result = score_issue(make_issue(), make_repo(archived=True), config=DEFAULT_CONFIG, now=NOW)
    assert result.rejected
    assert any("archived" in r for r in result.reject_reasons)


def test_reject_old_issue():
    issue = make_issue(created_at="2026-01-01T00:00:00Z")  # >180 days before NOW
    result = score_issue(issue, make_repo(), config=DEFAULT_CONFIG, now=NOW)
    assert result.rejected
    assert any("older" in r for r in result.reject_reasons)


def test_reject_comment_swamp():
    issue = make_issue(comments=57)
    result = score_issue(issue, make_repo(), config=DEFAULT_CONFIG, now=NOW)
    assert result.rejected
    assert any("comments deep" in r for r in result.reject_reasons)


def test_collision_flag_from_claim_comment():
    result = perfect_score(comments=[claim_comment(), maintainer_comment()])
    assert any("collision" in f and "eager-newcomer" in f for f in result.flags)


def test_thin_description_flag():
    issue = make_issue(body="broken")
    result = score_issue(issue, make_repo(), config=DEFAULT_CONFIG, now=NOW)
    assert any("thin issue description" in f for f in result.flags)


def test_detect_claims_ignores_maintainers():
    comments = [maintainer_comment(body="I'm working on the roadmap")]
    assert detect_claims(comments) == []
    assert detect_claims([claim_comment()]) == ["eager-newcomer"]


@pytest.mark.parametrize(
    "assoc,author,expected",
    [
        ("FIRST_TIME_CONTRIBUTOR", "newbie", True),
        ("NONE", "outsider", True),
        ("CONTRIBUTOR", "regular", True),
        ("MEMBER", "insider", False),
        ("OWNER", "octocat", False),
        ("COLLABORATOR", "helper", False),
    ],
)
def test_is_external_pr_by_association(assoc, author, expected):
    pr = external_pr(author_association=assoc, user={"login": author})
    assert is_external_pr(pr, "octocat/llm-tools") is expected


def test_is_external_pr_falls_back_to_owner_login():
    pr = external_pr(author_association="", user={"login": "octocat"})
    assert is_external_pr(pr, "octocat/llm-tools") is False
    pr = external_pr(author_association="", user={"login": "someone-else"})
    assert is_external_pr(pr, "octocat/llm-tools") is True
