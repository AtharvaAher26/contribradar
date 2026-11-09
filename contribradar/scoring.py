"""Transparent health scoring for candidate issues.

Every point in the total comes from a named signal with a human-readable
detail string, following the scoring table in docs/PLAN.md:

    beginner label (good first issue / help wanted)   +20
    repo pushed within 30 days                        +15
    external PR merged in last 90 days                +20
    issue unassigned and no linked PR                 +15
    maintainer replied on the issue                   +10
    stack/topic match                                 +10
    issue older than 6 months, or repo archived       reject

Signals that could not be checked (e.g. comments not fetched) score 0 and
say "not checked" in their detail — never a silent black-box number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

BEGINNER_LABELS = {"good first issue", "help wanted", "first timers only"}
MAINTAINER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
EXTERNAL_ASSOCIATIONS = {"NONE", "CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER"}

# Phrases that usually mean an unassigned issue is already taken.
CLAIM_PHRASES = [
    "i'm working on",
    "i am working on",
    "i'll take",
    "i will take",
    "can i work on",
    "i'd like to work on",
    "i would like to work on",
    "working on this",
    "taking this up",
    "please assign",
    "assign me",
]

POINTS = {
    "beginner_label": 20,
    "repo_active_30d": 15,
    "external_merge_90d": 20,
    "unclaimed": 15,
    "maintainer_replied": 10,
    "stack_match": 10,
}


@dataclass
class Signal:
    name: str
    points: int
    detail: str


@dataclass
class ScoreResult:
    total: int = 0
    signals: list[Signal] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    rejected: bool = False
    reject_reasons: list[str] = field(default_factory=list)

    def reasons(self) -> list[str]:
        """One human-readable line per scored signal, for the digest."""
        return [f"{s.detail} (+{s.points})" for s in self.signals if s.points > 0]


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _norm_label(name: str) -> str:
    return re.sub(r"[-_]+", " ", name.strip().lower())


def issue_labels(issue: dict) -> list[str]:
    labels = []
    for lab in issue.get("labels") or []:
        if isinstance(lab, dict):
            labels.append(lab.get("name", ""))
        else:
            labels.append(str(lab))
    return labels


def is_external_pr(pr_item: dict, repo_full_name: str) -> bool:
    """A merged PR counts as external if its author is not a maintainer.

    Uses the search API's ``author_association``; falls back to comparing
    the author login against the repo owner login.
    """
    assoc = (pr_item.get("author_association") or "").upper()
    if assoc in MAINTAINER_ASSOCIATIONS:
        return False
    if assoc in EXTERNAL_ASSOCIATIONS:
        return True
    owner = repo_full_name.split("/")[0].lower()
    author = ((pr_item.get("user") or {}).get("login") or "").lower()
    return bool(author) and author != owner


def detect_claims(comments: list[dict]) -> list[str]:
    """Usernames of non-maintainers who commented that they're taking the issue."""
    claimers: list[str] = []
    for comment in comments or []:
        assoc = (comment.get("author_association") or "").upper()
        if assoc in MAINTAINER_ASSOCIATIONS:
            continue
        body = (comment.get("body") or "").lower()
        if any(phrase in body for phrase in CLAIM_PHRASES):
            login = (comment.get("user") or {}).get("login")
            if login and login not in claimers:
                claimers.append(login)
    return claimers


def _keyword_hit(text: str, keywords: list[str]) -> str | None:
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw.lower())}\b", text):
            return kw
    return None


def score_issue(
    issue: dict,
    repo: dict,
    *,
    config: dict,
    now: datetime | None = None,
    comments: list[dict] | None = None,
    external_merge_90d: bool | None = None,
    linked_pr: bool | None = None,
) -> ScoreResult:
    """Score one candidate issue.

    ``comments=None`` means comments were not fetched (maintainer-reply and
    collision signals are then reported as not checked). ``external_merge_90d``
    and ``linked_pr`` are repo-level facts computed once per repo by the
    caller; ``None`` likewise means "not checked".
    """
    now = now or datetime.now(timezone.utc)
    result = ScoreResult()

    # ---- hard rejects -------------------------------------------------
    if repo.get("archived"):
        result.rejected = True
        result.reject_reasons.append("repo is archived")
    created = parse_dt(issue.get("created_at"))
    max_age = int(config.get("max_issue_age_days", 180))
    if created is not None and now - created > timedelta(days=max_age):
        result.rejected = True
        result.reject_reasons.append(
            f"issue is older than {max_age} days (created {created.date()})"
        )
    comment_count = int(issue.get("comments") or 0)
    max_comments = int(config.get("max_comments", 40))
    if comment_count >= max_comments:
        result.rejected = True
        result.reject_reasons.append(
            f"issue is {comment_count} comments deep (limit {max_comments})"
        )

    def add(name: str, earned: bool, detail: str) -> None:
        points = POINTS[name] if earned else 0
        result.signals.append(Signal(name, points, detail))
        result.total += points

    # ---- beginner label (+20) ----------------------------------------
    labels = issue_labels(issue)
    normed = {_norm_label(lab) for lab in labels}
    hit_labels = sorted(normed & BEGINNER_LABELS)
    add(
        "beginner_label",
        bool(hit_labels),
        f"labelled '{hit_labels[0]}'" if hit_labels else "no beginner label",
    )

    # ---- repo active in last 30 days (+15) ----------------------------
    pushed = parse_dt(repo.get("pushed_at"))
    active = pushed is not None and now - pushed <= timedelta(days=30)
    add(
        "repo_active_30d",
        active,
        f"repo pushed {pushed.date() if pushed else 'unknown'} (within 30 days)"
        if active
        else f"repo last pushed {pushed.date() if pushed else 'unknown'}",
    )

    # ---- external PR merged in last 90 days (+20) ---------------------
    if external_merge_90d is None:
        result.signals.append(
            Signal("external_merge_90d", 0, "external-merge history not checked")
        )
    else:
        add(
            "external_merge_90d",
            external_merge_90d,
            "an external contributor's PR was merged in the last 90 days"
            if external_merge_90d
            else "no external PR merged in the last 90 days",
        )

    # ---- unassigned and no linked PR (+15) ----------------------------
    assignees = issue.get("assignees") or ([] if not issue.get("assignee") else [issue["assignee"]])
    unassigned = len(assignees) == 0
    if linked_pr is None:
        add("unclaimed", False, "unassigned" if unassigned else "issue is assigned")
        if unassigned:
            result.flags.append("linked-PR status not checked")
    else:
        earned = unassigned and not linked_pr
        if not unassigned:
            detail = "issue is assigned"
        elif linked_pr:
            detail = "an open PR already references this issue"
        else:
            detail = "unassigned and no open PR references it"
        add("unclaimed", earned, detail)

    # ---- maintainer replied (+10) -------------------------------------
    if comments is None:
        result.signals.append(Signal("maintainer_replied", 0, "comments not checked"))
    else:
        replied = any(
            (c.get("author_association") or "").upper() in MAINTAINER_ASSOCIATIONS
            for c in comments
        )
        add(
            "maintainer_replied",
            replied,
            "a maintainer has replied on the issue"
            if replied
            else "no maintainer reply yet",
        )
        claimers = detect_claims(comments)
        if claimers:
            result.flags.append(
                "possible collision: " + ", ".join(claimers) + " commented about taking this"
            )

    # ---- stack match (+10) --------------------------------------------
    keywords = [k.lower() for k in config.get("stack_keywords", [])]
    text = " ".join(
        [
            (issue.get("title") or ""),
            (issue.get("body") or ""),
            " ".join(repo.get("topics") or []),
            (repo.get("description") or ""),
            (repo.get("language") or ""),
        ]
    ).lower()
    kw_hit = _keyword_hit(text, keywords) if keywords else None
    add(
        "stack_match",
        kw_hit is not None,
        f"stack match on '{kw_hit}'" if kw_hit else "no stack keyword match",
    )

    # ---- soft flags ----------------------------------------------------
    body = (issue.get("body") or "").strip()
    if len(body) < 50:
        result.flags.append("thin issue description — what 'done' looks like may be unclear")

    return result
