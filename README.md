# ContribRadar

![license](https://img.shields.io/badge/license-MIT-green)
![status](https://img.shields.io/badge/status-v1%20implemented-green)
![cost](https://img.shields.io/badge/running%20cost-₹0-blue)

**Find open-source issues that fit you — in repos that actually merge beginners' PRs.**

Generic "good first issue" sites dump thousands of stale issues from abandoned repos. ContribRadar scores every candidate by *repo health* and *merge reality*: is the project active, do maintainers reply, have they merged external contributors recently, is the issue genuinely unclaimed? You get a short weekly list worth your time — not a haystack.

## How it works

```
GitHub Search API ──► candidate issues (good first issue / help wanted)
   ──► HEALTH SCORER ──► ranked top 5–8 with "why this fits you"
   ──► weekly digest (digest.md)
   ──► PIPELINE TRACKER: found → saved → claimed → PR opened → changes requested → merged
```

**Scoring signals:** good-first-issue/help-wanted label · repo active in last 30 days · external PR merged in last 90 days · issue unassigned with no linked PR · maintainer has replied · stack match (Python, LLM, RAG, agents — configurable). Stale or archived → rejected outright.

Full plan: [docs/PLAN.md](docs/PLAN.md)

## Why it pairs with ProofPost

ContribRadar finds the work; merged PRs become proof. Those merges feed **[ProofPost](https://github.com/AtharvaAher26/proofpost)** (LinkedIn drafts from real work) and the resume. Find → contribute → merge → post: one loop.

## Run it

Requires Python 3.11+.

```bash
pip install -r requirements.txt

python -m contribradar init     # optional: write a config.json you can edit
python -m contribradar scan     # search -> score -> digest.md (+ pipeline)
python -m contribradar digest   # re-render digest.md from the last scan
```

**GitHub token (optional):** scans work unauthenticated for small runs; a token raises the rate limits (search 10 → 30 req/min). Create a fine-grained token with no special permissions and set it in the environment — never commit it:

```bash
export GITHUB_TOKEN=ghp_...        # optional
export CONTRIBRADAR_STATE_DIR=.    # where pipeline.json / seen.json / digest.md live (default: .)
```

**Pipeline tracker** (states: `found → saved → claimed → pr_opened → changes_requested → merged`, plus `dropped`):

```bash
python -m contribradar track add https://github.com/owner/repo/issues/123 --title "Fix the thing"
python -m contribradar track move https://github.com/owner/repo/issues/123 claimed
python -m contribradar track list            # everything, grouped by state
python -m contribradar track list --state pr_opened
```

Every scan's score is fully decomposed: the digest prints each named signal and its points (label +20 · repo active +15 · external PR merged in 90 days +20 · unassigned & unlinked +15 · maintainer replied +10 · stack match +10 = 90 max), plus flags like possible comment-claim collisions and thin descriptions. Issues older than 6 months, issues 40+ comments deep, and archived repos are rejected, and seen issues are never suggested twice.

**Tuning:** edit `config.json` (labels, languages, stack keywords, `top_n`, limits) — see `contribradar/config.py` for the defaults. Run tests with `pip install -r requirements-dev.txt && python -m pytest` (39 tests, fully offline).

## Status

**v1 implemented** (November 2026, ahead of the December plan). Personal CLI: GitHub Search API scan → transparent health scoring → markdown digest → JSON pipeline tracker. Stack: Python · GitHub REST API · `requests` only. Target: first merged external PR within 4 weeks of weekly use.

Deliberately deferred from the plans: Telegram digest delivery (v1 digest is the `digest.md` file; the scan → digest architecture leaves a clean seam for it), first-PR success-rate and median maintainer response-time metrics, difficulty estimation, claim-draft helper, and cohort mode — see [docs/PRODUCT-PLAN.md](docs/PRODUCT-PLAN.md) for the build order.

## License

MIT — see [LICENSE](LICENSE).
