"""Render the weekly digest as markdown: top new finds + pipeline status."""

from __future__ import annotations

from datetime import datetime, timezone

from .tracker import STATES


def render_digest(
    finds: list[dict],
    pipeline_items: list[dict],
    *,
    generated_at: datetime | None = None,
    rejected_count: int = 0,
) -> str:
    """``finds`` items: {url, title, repo, score (ScoreResult), created_at}.

    ``pipeline_items`` are tracker item dicts (see tracker.Pipeline).
    """
    generated_at = generated_at or datetime.now(timezone.utc)
    lines: list[str] = [
        "# ContribRadar — weekly digest",
        "",
        f"_Generated {generated_at.date().isoformat()} · "
        f"{len(finds)} new finds · {rejected_count} candidates rejected by the health filter_",
        "",
        "## Top new finds",
        "",
    ]
    if not finds:
        lines.append("No new finds this scan. Widen the labels or stack keywords in config.json.")
    for idx, find in enumerate(finds, start=1):
        score = find["score"]
        lines.append(
            f"### {idx}. [{find['title']}]({find['url']}) — score {score.total}/90"
        )
        lines.append(f"- Repo: `{find['repo']}` · opened {str(find.get('created_at', ''))[:10]}")
        for reason in score.reasons():
            lines.append(f"- ✅ {reason}")
        for flag in score.flags:
            lines.append(f"- ⚠️ {flag}")
        lines.append("")

    lines += ["## Pipeline", ""]
    by_state: dict[str, list[dict]] = {state: [] for state in STATES}
    for item in pipeline_items:
        by_state.setdefault(item["state"], []).append(item)
    summary = " · ".join(
        f"{state}: {len(by_state[state])}" for state in STATES if by_state[state]
    )
    lines.append(f"_{summary or 'pipeline is empty'}_")
    lines.append("")
    for state in STATES:
        items = by_state[state]
        if not items:
            continue
        lines.append(f"**{state}**")
        for item in items:
            title = item.get("title") or item["url"]
            lines.append(f"- [{title}]({item['url']}) — since {item['updated']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
