from contribradar.github_client import build_issue_query, repo_full_name_from_issue
from fixtures import make_issue


def test_build_issue_query():
    q = build_issue_query(["good first issue"], ["python"])
    assert 'label:"good first issue"' in q
    assert "language:python" in q
    assert "is:issue" in q and "is:open" in q


def test_repo_full_name_from_repository_url():
    assert repo_full_name_from_issue(make_issue()) == "octocat/llm-tools"


def test_repo_full_name_missing():
    issue = make_issue(repository_url="", html_url="")
    assert repo_full_name_from_issue(issue) is None
