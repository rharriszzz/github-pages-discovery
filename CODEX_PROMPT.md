# Prompt for Codex: GitHub Pages Interest Finder — expand and verify the pilot

You are working in my **new** repository, `rharriszzz/github-pages-discovery`. It contains a working Python standard-library-only starter implementation. My main goal is to discover interesting `x.github.io` websites, find out whether each is owned by a GitHub **User** or **Organization** account, and learn whether the site's and owner's interests overlap my own. I am more interested in **discovering genuinely worthwhile research and engineering projects** than in a superficial numerical popularity leaderboard.

**Read** `README.md`, `RESEARCH_PLAN.md`, `data/interests.json`, the sample `data/sites.json`, all of `pagefinder/`, and the tests first. Review existing code for bugs; do not assume the starter implementation is production-ready. Do not throw away its auditable output, manually curated sample, or human-review fields.

## Phase 1: validate and harden the included implementation

1. Run the unit tests and offline report. Examine the sample output in `docs/index.html`. Verify the seven sample site URLs and associated GitHub accounts, including `owner.type`; flag any mismatches. Improve tests for URL/redirect safety, escaped HTML, `robots.txt`, pagination, API errors, and cached/offline behavior.
2. Confirm the GitHub API search syntax, existence checks and actual site-source repository mapping. A project with `has_pages=true` may deploy to a custom domain; never silently treat a guessed `owner.github.io/repository/` as confirmed. Treat redirect/soft-404/stale-content cases explicitly. Maintain provenance for manual and automated classifications and never overwrite human review labels.
3. Do a **small** authenticated and rate-budgeted test run (prefer existing `gh auth` context; never ask me to paste credentials or save a token), first around 20, then a bounded 100 sites. Check actual GitHub rate-limit headers and search endpoint policies. Stop on 403/429 and respect `Retry-After` and reset times; no evasion or excessive concurrency. Do not claim a URL is a live site without successful independent verification.
4. Audit the HTML parser, content limits and polite crawling. Never execute external scripts. Respect `robots.txt`; never crawl off-domain or scrape emails/phone numbers, private data, or security-sensitive content. Keep requests modest and cache/checkpoint each batch.

## Phase 2: design a defensible discovery strategy

5. The internet contains many `*.github.io` sites, and GitHub's search API is **not an exhaustive directory**. Research better ways to discover candidate hosts: GitHub repo search, published Common Crawl indices/datasets, public link discovery, etc. Compare yield, bias, source legitimacy, compute/network cost and rate limiting. Avoid claiming an exhaustive census or an unbiased estimate without an actual sampling design.
6. Build two explicitly separate cohorts: (A) a broad and partially topic-agnostic sample for understanding who publishes sites and (B) an interest-targeted cohort for finding the best matches. Record denominator, date, query, page/search truncation, deduplicated hosts and whether a site was actually reachable. Include organizations and individuals without optimizing exclusively for one category.
7. Group related project pages under owner accounts to avoid letting prolific owners dominate. A GitHub `User` account does not prove a lone maintainer; an `Organization` may comprise one person. Distinguish **account type**, **actual site project**, **apparent maintainer/team (if explicitly documented)** and **owner portfolio interest**.

## Phase 3: make matching intellectually useful

8. Begin with the editable interest profile: Navier–Stokes and physically interesting CFD; numerical verification and Reynolds number questions; mathematics/VOAs/Monster and formal methods; AI scientific discoveries; Reversi search and learned evaluation; image reconstruction and bead crochet; music transcription and physical music boxes; space-based datacenters and thermal engineering; systems programming; recipes and other creative work.
9. Do not reward mere keyword repetition. Distinguish **direct topical overlap**, **shared tools/methods**, **potentially useful adjacent discoveries**, and **novel material I might enjoy**. For each high-ranked finding, give two or three concrete reasons with links to pages, README files or actual examples, plus a clear caution if evidence is weak. A website title alone is not adequate evidence.
10. Add human review statuses (`keep`, `skip`, `later`, `uncertain`), notes and suppression of low-quality duplicates/abandoned clones. Calibrate top-result precision with a manually labeled mixed sample. Report false positives and areas with poor coverage, not just success cases.
11. Compare project quality where relevant: scientific rigor and numerical validation, reproducibility, educational clarity, novelty, code accessibility, and maintained status. Keep these separate from topic similarity. Do not equate popularity, stars or slick design with scientific value.

## Phase 4: outputs and GitHub Pages

12. Improve the light-background static catalog in `docs/` with filters for topic, owner type, project vs homepage, review status and discovery source. Each result must link to both its live website and its source repository when verifiable. Preserve CSV/JSON for analysis. This website itself can be published on GitHub Pages once I choose that setting.
13. Produce `reports/methodology.md`, `reports/coverage.md`, `reports/findings.md`, and `reports/interesting-sites.md`, documenting date, exact query frames, rate limits, sample bias, account-type distribution **within each specific sample**, and the strongest matches worth reading. Clearly label what is verified and what is inferred.
14. Keep a checkpoint/resume workflow. Do not schedule uncontrolled GitHub Actions crawls, create recurring automations, or push secrets. The site deployment must only publish the checked-in static `docs` artifact.
15. Run tests, inspect the generated site, resolve obvious failures and commit/push the work to `main` only when the report and tests are consistent. Record what actually ran and what was deferred. If an API, service, or rate limit blocks progress, checkpoint everything and continue with useful offline work, then report the blocker plainly.

**Important judgment:** Favor a reliable, transparent survey of perhaps a few hundred or thousand websites over grand claims to have enumerated the whole domain. If a particular approach isn't yielding genuinely new and interesting sites, diagnose the failure and change the discovery strategy. Include unexpected but interesting neighboring research areas, not just exact matches for the words in my profile.
