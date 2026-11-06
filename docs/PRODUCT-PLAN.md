# ContribRadar — How It Works, Improvements & Product Plan

## How it works (the full loop)
1. **Collect** — GitHub Search API finds candidate issues: labels (`good first issue`, `help wanted`, `first-timers-only`) × user's languages/topics.
2. **Verify the repo** — for each candidate's repo: pushed within 30 days? Not archived? Has CONTRIBUTING/README? Has a test suite (safer first PRs)?
3. **Verify the merge reality** — the differentiator: did this repo merge PRs from *external, first-time* contributors in the last 90 days? What's its **first-PR success rate** (first-timer PRs merged ÷ opened, last 6 months)? How fast do maintainers respond (median first-reply time on issues/PRs)?
4. **Verify the issue** — unassigned, no linked PR, and a **collision check**: nobody has commented "I'm taking this" without being assigned. Description scored for clarity (does it say what done looks like?).
5. **Rank & explain** — transparent score; every recommendation carries its reasons ("active repo, 7 first-timer PRs merged this quarter, maintainer replies in ~1 day").
6. **Deliver** — weekly digest (Telegram/email), top 5–8 only.
7. **Track** — pipeline states per user: saved → claimed → PR opened → changes requested → merged. Merged PRs export to ProofPost (LinkedIn proof posts) and the resume.

## Improvements that make it genuinely better (build order)
1. **First-PR success rate + maintainer response index** — the two numbers beginners actually need; no major tool shows them.
2. **Difficulty estimation beyond labels** — files/areas touched + thread analysis: a "good first issue" that's secretly a refactor scores down.
3. **Collision detection** — scan comments for unassigned claims; saves the classic beginner heartbreak of duplicating someone's work.
4. **Personal fit learning** — the tool learns from the user's own history (which repo types merged them) and re-weights future picks.
5. **Claim-draft helper** — drafts the "Hi, I'd like to work on this" comment and a setup checklist from the repo's CONTRIBUTING; the user posts it themselves.
6. **Setup-difficulty rating** — does the repo's dev setup actually work (docs present, Docker/devcontainer, CI config)? Rates the hidden cost of a "first" contribution.
7. **Cohort mode** — a club/class leaderboard and shared shortlist (built for ACES Club first): friendly competition drives completions better than solo tools.

## The honest competition check
- **CodeTriage** exists (emails you issues from repos you pick) — but no health scoring, no merge-reality check, no tracker, no fit learning.
- **goodfirstissue.dev / First Timers Only** — static lists, no personalization, no repo verification.
- **GitHub search itself** — raw, unranked, no quality signals.
Wedge: **verified mergeability + explanation + pipeline tracking + the ProofPost loop**, aimed at students/clubs rather than the whole internet.

## Product path (deployment)
- **v1 (Dec 2026):** personal CLI + Telegram digest for Atharva.
- **v1.5 (2027):** Telegram bot with per-user config (stack, level) — clubs onboard by sharing one link.
- **v2:** web dashboard + GitHub OAuth ("import your starred repos"), cohort leaderboards for clubs/colleges.
- **Launch window:** Hacktoberfest (October) — the one month the whole world searches for exactly this. A 2027 Hacktoberfest launch with a college-club cohort already using it is the distribution play.
- **Engineering reality for multi-user:** GitHub search API is rate-limited (30 req/min; 5,000 core req/hr per token) — needs caching, a shared scan pool across users, and queued scoring. Solvable, but it's the main scaling cost; running cost stays near ₹0 at club scale on free tiers.
- **Monetization (if ever):** free for students/clubs; paid tier for bootcamps/communities that want cohort analytics. Never charge beginners for issue lists.

## Validation gates
- **Gate 1:** Atharva's own first merged PR comes through the tool (Dec–Jan). If the tool can't merge *him*, it helps nobody.
- **Gate 2:** ACES Club pilot (20–30 students, one month): green = ≥10 members land a merged PR.
- **Gate 3:** only then, public beta + Hacktoberfest launch planning.
