# ContribRadar

![license](https://img.shields.io/badge/license-MIT-green)
![status](https://img.shields.io/badge/status-planned%20·%20building%20Dec%202026-orange)
![cost](https://img.shields.io/badge/running%20cost-₹0-blue)

**Find open-source issues that fit you — in repos that actually merge beginners' PRs.**

Generic "good first issue" sites dump thousands of stale issues from abandoned repos. ContribRadar scores every candidate by *repo health* and *merge reality*: is the project active, do maintainers reply, have they merged external contributors recently, is the issue genuinely unclaimed? You get a short weekly list worth your time — not a haystack.

## How it works

```
GitHub Search API ──► candidate issues (good first issue / help wanted)
   ──► HEALTH SCORER ──► ranked top 5–8 with "why this fits you"
   ──► weekly Telegram digest
   ──► PIPELINE TRACKER: claimed → PR opened → merged
```

**Scoring signals:** good-first-issue/help-wanted label · repo active in last 30 days · external PR merged in last 90 days · issue unassigned with no linked PR · maintainer has replied · stack match (Python, LLM, RAG, agents — configurable). Stale or archived → rejected outright.

Full plan: [docs/PLAN.md](docs/PLAN.md)

## Why it pairs with ProofPost

ContribRadar finds the work; merged PRs become proof. Those merges feed **[ProofPost](https://github.com/AtharvaAher26/proofpost)** (LinkedIn drafts from real work) and the resume. Find → contribute → merge → post: one loop.

## Status

Design complete. Build scheduled **December 2026** (~1 day, reusing the JobFinder bot's scan → digest architecture). Stack: Python · GitHub REST API · Telegram. Target: first merged external PR within 4 weeks of weekly use.

## License

MIT — see [LICENSE](LICENSE).
