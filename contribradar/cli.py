"""ContribRadar CLI.

    contribradar init                     write a default config.json
    contribradar scan                     search -> score -> digest.md (+ pipeline)
    contribradar digest                   re-render digest.md from the last scan
    contribradar track add <issue-url>    add an issue to the pipeline
    contribradar track move <url> <state> move a pipeline item
    contribradar track list [--state X]   show the pipeline

State lives in the state dir (default: current directory):
``pipeline.json``, ``seen.json``, ``last_scan.json``, ``digest.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import github_token, load_config, write_default_config
from .digest import render_digest
from .github_client import GitHubClient, GitHubError, build_issue_query, repo_full_name_from_issue
from .scoring import ScoreResult, score_issue
from .tracker import Pipeline, SeenSet, TransitionError


def _state_paths(state_dir: Path) -> dict[str, Path]:
    return {
        "pipeline": state_dir / "pipeline.json",
        "seen": state_dir / "seen.json",
        "last_scan": state_dir / "last_scan.json",
        "digest": state_dir / "digest.md",
    }


def _find_from_record(record: dict) -> dict:
    """Rebuild a digest find (with a ScoreResult) from last_scan.json."""
    score_data = record["score"]
    result = ScoreResult(
        total=score_data["total"],
        rejected=score_data.get("rejected", False),
        reject_reasons=score_data.get("reject_reasons", []),
        flags=score_data.get("flags", []),
    )
    from .scoring import Signal

    result.signals = [Signal(**s) for s in score_data.get("signals", [])]
    return {
        "url": record["url"],
        "title": record["title"],
        "repo": record["repo"],
        "created_at": record.get("created_at", ""),
        "score": result,
    }


def _score_to_record(find: dict) -> dict:
    score: ScoreResult = find["score"]
    return {
        "url": find["url"],
        "title": find["title"],
        "repo": find["repo"],
        "created_at": find.get("created_at", ""),
        "score": {
            "total": score.total,
            "rejected": score.rejected,
            "reject_reasons": score.reject_reasons,
            "flags": score.flags,
            "signals": [
                {"name": s.name, "points": s.points, "detail": s.detail} for s in score.signals
            ],
        },
    }


def run_scan(args: argparse.Namespace, client: GitHubClient | None = None) -> int:
    config = load_config(args.config)
    state_dir = Path(args.state_dir)
    paths = _state_paths(state_dir)
    client = client or GitHubClient(token=github_token())
    now = datetime.now(timezone.utc)

    seen = SeenSet.load(paths["seen"])
    pipeline = Pipeline.load(paths["pipeline"])

    # 1. Collect candidate issues, one query per beginner label.
    candidates: dict[str, dict] = {}
    for label in config["labels"]:
        query = build_issue_query([label], config["languages"])
        try:
            items = client.search_issues(query, per_page=int(config["per_query"]))
        except GitHubError as exc:
            print(f"warning: search for label '{label}' failed: {exc}", file=sys.stderr)
            continue
        for item in items:
            url = item.get("html_url")
            if url and url not in candidates:
                candidates[url] = item
    if not args.include_seen:
        candidates = {u: i for u, i in candidates.items() if u not in seen}

    # 2. Repo-level facts, computed once per repo.
    repos: dict[str, dict] = {}
    repo_external_merge: dict[str, bool | None] = {}
    repo_open_refs: dict[str, set[int] | None] = {}
    for item in candidates.values():
        full_name = repo_full_name_from_issue(item)
        if not full_name or full_name in repos:
            continue
        try:
            repos[full_name] = client.get_repo(full_name)
        except GitHubError as exc:
            print(f"warning: repo {full_name} fetch failed: {exc}", file=sys.stderr)
            repos[full_name] = {}
        try:
            repo_external_merge[full_name] = client.external_merge_in_last_days(full_name, now=now)
        except GitHubError:
            repo_external_merge[full_name] = None
        try:
            repo_open_refs[full_name] = client.open_pr_issue_refs(full_name)
        except GitHubError:
            repo_open_refs[full_name] = None

    # 3. Score every candidate; fetch comments only when they can matter.
    finds: list[dict] = []
    rejected_count = 0
    comment_fetches = 0
    max_fetches = int(config["max_comment_fetches"])
    for url, item in candidates.items():
        full_name = repo_full_name_from_issue(item) or ""
        comments = None
        if int(item.get("comments") or 0) > 0 and comment_fetches < max_fetches:
            try:
                comments = client.get_issue_comments(full_name, int(item["number"]))
                comment_fetches += 1
            except GitHubError:
                comments = None
        refs = repo_open_refs.get(full_name)
        linked_pr = None if refs is None else int(item["number"]) in refs
        result = score_issue(
            item,
            repos.get(full_name, {}),
            config=config,
            now=now,
            comments=comments,
            external_merge_90d=repo_external_merge.get(full_name),
            linked_pr=linked_pr,
        )
        seen.mark(url)
        if result.rejected:
            rejected_count += 1
            continue
        finds.append(
            {
                "url": url,
                "title": item.get("title") or url,
                "repo": full_name,
                "created_at": item.get("created_at", ""),
                "score": result,
            }
        )

    # 4. Rank, persist, digest.
    finds.sort(key=lambda f: f["created_at"], reverse=True)  # newest first
    finds.sort(key=lambda f: f["score"].total, reverse=True)  # stable: score, then recency
    finds = finds[: int(config["top_n"])]
    for find in finds:
        pipeline.add(
            find["url"],
            title=find["title"],
            repo=find["repo"],
            score=find["score"].total,
            state="found",
        )
    pipeline.save(paths["pipeline"])
    seen.save(paths["seen"])
    paths["last_scan"].parent.mkdir(parents=True, exist_ok=True)
    paths["last_scan"].write_text(
        json.dumps(
            {"finds": [_score_to_record(f) for f in finds], "rejected_count": rejected_count},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    digest_text = render_digest(
        finds, pipeline.list(), generated_at=now, rejected_count=rejected_count
    )
    paths["digest"].write_text(digest_text, encoding="utf-8")

    print(f"Scanned {len(candidates)} candidates · {rejected_count} rejected · "
          f"{len(finds)} finds -> {paths['digest']}")
    for find in finds:
        score = find["score"]
        print(f"\n{score.total}/90  {find['title']}\n  {find['url']}")
        for reason in score.reasons():
            print(f"    + {reason}")
        for flag in score.flags:
            print(f"    ! {flag}")
    return 0


def run_digest(args: argparse.Namespace) -> int:
    paths = _state_paths(Path(args.state_dir))
    if not paths["last_scan"].exists():
        print("No scan yet — run `contribradar scan` first.", file=sys.stderr)
        return 1
    data = json.loads(paths["last_scan"].read_text(encoding="utf-8"))
    finds = [_find_from_record(r) for r in data.get("finds", [])]
    pipeline = Pipeline.load(paths["pipeline"])
    text = render_digest(
        finds, pipeline.list(), rejected_count=int(data.get("rejected_count", 0))
    )
    paths["digest"].write_text(text, encoding="utf-8")
    print(f"Wrote {paths['digest']} ({len(finds)} finds)")
    return 0


def run_track(args: argparse.Namespace) -> int:
    paths = _state_paths(Path(args.state_dir))
    pipeline = Pipeline.load(paths["pipeline"])
    try:
        if args.action == "add":
            item = pipeline.add(
                args.url, title=args.title or "", repo=args.repo or "", state="found"
            )
            print(f"Added [{item['state']}] {item['url']}")
        elif args.action == "move":
            item = pipeline.move(args.url, args.state)
            print(f"Moved -> [{item['state']}] {item['url']}")
        elif args.action == "list":
            items = pipeline.list(state=args.state)
            if not items:
                print("Pipeline is empty." if not args.state else f"Nothing in '{args.state}'.")
            for item in items:
                score = f" score {item['score']}" if item.get("score") is not None else ""
                print(f"[{item['state']}] {item.get('title') or item['url']}{score}")
                print(f"    {item['url']} (updated {item['updated']})")
            return 0
    except TransitionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    pipeline.save(paths["pipeline"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contribradar", description=__doc__)
    parser.add_argument("--state-dir", default=os.environ.get("CONTRIBRADAR_STATE_DIR", "."))
    parser.add_argument("--config", default=None, help="path to config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="write a default config.json")
    scan_p = sub.add_parser("scan", help="search GitHub, score candidates, write the digest")
    scan_p.add_argument("--include-seen", action="store_true",
                        help="reconsider issues surfaced by earlier scans")
    sub.add_parser("digest", help="re-render digest.md from the last scan")

    track_p = sub.add_parser("track", help="manage the contribution pipeline")
    track_sub = track_p.add_subparsers(dest="action", required=True)
    add_p = track_sub.add_parser("add")
    add_p.add_argument("url")
    add_p.add_argument("--title", default="")
    add_p.add_argument("--repo", default="")
    move_p = track_sub.add_parser("move")
    move_p.add_argument("url")
    move_p.add_argument("state")
    list_p = track_sub.add_parser("list")
    list_p.add_argument("--state", default=None)

    args = parser.parse_args(argv)
    if args.command == "init":
        target = Path(args.config or "config.json")
        write_default_config(target)
        print(f"Wrote default config to {target}")
        return 0
    if args.command == "scan":
        return run_scan(args)
    if args.command == "digest":
        return run_digest(args)
    if args.command == "track":
        return run_track(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
