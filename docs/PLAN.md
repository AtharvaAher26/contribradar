# ContribRadar — Plan

**One line:** A personal radar that finds open-source issues matched to your stack and level — in repos that are actively maintained and actually merge outside contributions — and tracks your pipeline from issue claimed to PR merged.

## Why (the problem with existing "good first issue" sites)
Generic aggregators dump thousands of stale, abandoned, or already-contested issues. A beginner wastes weeks on repos where maintainers never reply. ContribRadar's value is the *filtering intelligence*, not the listing:
- **Stack match:** Python + LLM/RAG/agents topics first (configurable).
- **Repo health:** commits in the last 30 days, not archived, real README/CONTRIBUTING.
- **Merge reality check:** the repo has merged PRs from external contributors recently — proof beginners get through.
- **Issue quality:** labelled `good first issue` / `help wanted`, has a description with actual content, not assigned, no PR already open against it, not 40 comments deep.

## How it works
```
GitHub Search API ──► candidate issues (labels + language + topics)
   ──► HEALTH SCORER (repo activity, external-merge history, issue quality)
   ──► ranked shortlist (top 5–8, with "why this fits you" per issue)
   ──► weekly Telegram digest (JobFinder bot pattern)
   ──► PIPELINE TRACKER: claimed → PR opened → changes requested → merged
   ──► merged PRs feed ProofPost (proof posts) and the resume
```

## Scoring model (transparent, tunable)
| Signal | Points |
|---|---|
| Issue labelled good-first-issue / help-wanted | +20 |
| Repo pushed within 30 days | +15 |
| External PR merged in last 90 days | +20 |
| Issue unassigned, no linked PR | +15 |
| Maintainer replied on the issue | +10 |
| Stack/topic match (LLM, RAG, agents) | +10 |
| Issue older than 6 months / repo archived | reject |

## Build plan (December 2026, ~1 day — reuses JobFinder architecture)
- Block 1: GitHub search queries + health scorer; verify on live data.
- Block 2: Telegram digest + seen-dedup (never repeat an issue).
- Block 3: pipeline tracker (simple CLI/CSV like tracker.py).
- Stack: Python, GitHub REST API, SQLite/JSON state. Running cost ₹0.

## Success definition
First merged external PR within 4 weeks of weekly use; 3–5 merged contributions by mid-2027 (the roadmap's OSS track target). Merged PRs are the currency: they feed the resume, LinkedIn (via ProofPost), and internship applications.
