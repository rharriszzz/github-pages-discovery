# GitHub Pages Interest Finder

A conservative research tool for discovering public `*.github.io` websites, identifying whether the **GitHub account** is a `User` or an `Organization`, and estimating overlap with a user-editable set of technical and creative interests.

**Status:** Working starter implementation and **seven manually researched sample records**, not a comprehensive survey. The sample account types were verified against GitHub repository metadata on 2026-11-02. The local HTTP crawler has not yet been run against the entire sample; those records are marked `research_preview` rather than pretending to be fresh automatic HTTP checks.

## What the tool does

- Discover candidate sites through **bounded GitHub repository searches**. Results may include personal/organization sites (`owner.github.io`) or project sites (`owner.github.io/repository/`). Each candidate is *only a candidate* until the page is checked.
- Read GitHub account classification from the GitHub API's `type` field, never from the visual style of the site. `User` means an individual-account *type*, **not proof of the number or identity of maintainers**. `Organization` does not imply a company, and can be a one-person project.
- Fetch a small HTML excerpt from permitted public pages, obey `robots.txt`, restrict requests to `https://*.github.io`, cap bytes, cache responses, and keep request rates low. Never follow redirects to unrelated hosts without explicit review.
- Rank sites using explainable keyword matching against `data/interests.json`. This is a **first-pass triage heuristic**, not a model-based project review or a calibrated percentage of similarity.
- Export a static, searchable report in `docs/index.html`, plus `reports/results.csv` and `reports/results.json`.
- Stop cleanly when API rate limits are encountered; save checkpoints instead of increasing request rates or rotating credentials/IP addresses.

## Quick start (Python 3.11+, standard library only)

```bash
python -m unittest discover -s tests -v
python -m pagefinder stats
python -m pagefinder report
# Open docs/index.html in a browser.
```

These commands do not require network access.

## Optional discovery / enrichment

Use a local GitHub CLI login (`gh auth login`) or an environment `GH_TOKEN` / `GITHUB_TOKEN` for authenticated GitHub API queries. **Do not commit a token.** An unauthenticated run is also possible but severely rate limited. The script reads `gh auth token` when available. It never logs or saves secrets.

```bash
# 1. Discover candidate site URLs. Results are checkpointed to data/sites.json.
python -m pagefinder discover --queries-file data/search_queries.txt --per-page 30 --pages 1

# 2. Validate a small, bounded batch. May make HTTPS requests.
python -m pagefinder enrich --max-sites 20

# 3. Rank and export.
python -m pagefinder report
```

The order of records affects enrichment. Review the first batch before increasing `--max-sites`; a very large broad search is not yet recommended. Search API queries are intentionally capped, and truncation is reported; **no completeness claim is justified**.

For a completely offline cached run, pass `--offline` to `discover` or `enrich` (the `report` command is always offline). Enrichment of an existing successful (`ok`) site is skipped. Adjust the raw sample in `data/sites.json` only if you understand the schema.

## Outputs

- `docs/index.html` — accessible light-background catalog with search and account-type filter; deployable through GitHub Pages.
- `reports/results.csv` — sortable / spreadsheet-compatible result export.
- `reports/results.json` — machine-readable records with per-interest matched terms and source fields.
- `data/sites.json` — incremental working set; preserves prior manual fields and checkpoints.
- `data/interests.json` — adjustable topics, terms, and integer weights (current profile is intentionally technical).
- `data/search_queries.txt` — bounded discovery queries; contains highly *biased* selection criteria. A sampling track is a follow-on requirement.

## GitHub Pages deployment

Create an empty repository, suggested name `github-pages-discovery`, and push this project's files to `main`. In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**. `.github/workflows/pages.yml` deploys the checked-in `docs/` folder on future pushes. No crawler is run by the Pages workflow. The expected URL is `https://rharriszzz.github.io/github-pages-discovery/` after GitHub reports a successful deployment.

The Pages site is public: avoid committing anything you consider private. The shipped interest profile describes research topics and is editable; it contains no API tokens, private messages or personal contact details.

## Scientific / research cautions

1. **Discovery bias** is the central problem. GitHub repository search does not directly search GitHub Pages HTML and limits results per query. A site that is not returned is not necessarily uninteresting.
2. **Owner identity** is different from GitHub account type. Do not infer a real person's identity, organization size, affiliation or contact information from the `type` field.
3. **Project versus account interests:** One page is evidence of a project theme, not necessarily the account owner's broader interests. In future, aggregate several public repositories with links and distinguish owner-level interest from individual-site interest.
4. **Freshness:** Cached pages and hand-researched records are labeled. An HTTP 200 does not by itself establish current substantive content; detect Pages soft-404s and parked sites in a follow-up.
5. **Scoring:** Keyword matches can be accidental. Reasons are exposed so the user can reject false positives. Independent manual evaluation on a stratified sample should precede automated high-confidence classification.
6. **Fair use of infrastructure:** Respect robots, avoid aggressive crawling, and do not evade rate limits or scrape personal contact details.

## Research / documentation

- [Github Pages site types](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [GitHub REST API rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [GitHub repository search](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories)
- [GitHub REST search endpoint limitations](https://docs.github.com/en/rest/search/search)
- [Common Crawl statistics](https://commoncrawl.github.io/cc-crawl-statistics/plots/domains)

See `RESEARCH_PLAN.md` for survey methodology and `CODEX_PROMPT.md` for the next development task.

## Unified research direction (2026-11-02)

This repository now has a **combined research plan** for (a) learning interests from public repositories and authorized YouTube data, (b) rediscovering older videos missing from available watch history, and (c) finding new relevant GitHub Pages sites and other research. Read [`MERGED_PROJECT_PLAN.md`](MERGED_PROJECT_PLAN.md) for the integrated architecture and [`CODEX_PROMPT.md`](CODEX_PROMPT.md) for the staged implementation instructions. The older [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md) remains the detailed baseline for the public GitHub Pages sampling method.

**Current implementation status:** The shipped code still implements only the original **public GitHub Pages pilot** (seven researched seed records). The merged YouTube importer, private history analysis, interest graph and lost-video recommendations are **planned, not yet implemented**. This note documents scope; it does not claim that private playlists are connected or that any Google account has been authorized.

**Data-boundary rule:** All private playlist inventories, Likes, viewing-history exports, user-specific evidence, credentials and OAuth tokens must be stored outside the Git repository. The published `docs/` site contains only reviewed public-safe data. Personal YouTube analysis belongs in a private local application, not on GitHub Pages. 
