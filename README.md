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

**Current implementation status:** The original public pilot still has seven researched seed records. The shared private SQLite schema, Desktop read-only OAuth integration, metadata-only playlist inventory/review, Takeout JSON/HTML/CSV foundation, selected Chrome bookmark imports, curated bookshelf concept mapping, persistent response caches and request budgets are implemented and tested offline. Account authorization, inventories, interest graphs and personal reports are handled locally; this repository publishes no private account records. Historical analysis, automated graph inference, calibrated ranking and lost-video recommendations remain later gates. See [implementation status](docs/implementation_status.md).

**Data-boundary rule:** All private playlist inventories, Likes, viewing-history exports, user-specific evidence, credentials and OAuth tokens must be stored outside the Git repository. The published `docs/` site contains only reviewed public-safe data. Personal YouTube analysis belongs in a private local application, not on GitHub Pages. 

## Private local research

```bash
python3 -m pagefinder.local --help
python3 -m pagefinder.local init
# After Desktop client setup and optional dependency installation:
python3 -m pagefinder.local auth
python3 -m pagefinder.local inventory
python3 -m pagefinder.local inventory --offline
```

Follow [YouTube setup and playlist review](docs/youtube_setup.md). Default personal
storage is `~/.local/share/github-pages-discovery/`, with credentials under
`~/.config/github-pages-discovery/youtube/`. `--data-dir` and `--config-dir` must
point outside Git working trees. The first inventory downloads names, descriptions,
privacy and counts only. Open its local HTML report, annotate purposes/relevance,
download the annotations outside Git, and apply them with the `annotate` command.
Playlist content imports require that review. No massive content import runs automatically.

API responses and Takeout source snapshots are cached; offline reruns do not need
credentials. Incomplete inventory runs checkpoint/resume; `--refresh` explicitly
starts a new snapshot and preserves old results and annotations. Persistent rate
budgets are shared by processes using the same ledger, include failed attempts,
honor server cooldowns and stop at batch/daily ceilings. The public GitHub/site
clients use the same admission/cache infrastructure with separate public storage.
Details and limitations are in [architecture](docs/architecture.md).

Chrome bookmarks are another private source. Import only explicitly selected folders
from a local Chrome profile's `Bookmarks` JSON file (not a whole-profile copy):

```bash
python3 -m pagefinder.local import-bookmarks /path/outside/git/Bookmarks --folder Study --folder Tools
```

Repeat `--folder` for each chosen folder. Names match without regard to case;
ambiguous names require a full path such as `bookmark_bar/Study`. The importer
preserves nested folders, titles, URLs and bookmark dates in a filtered private
snapshot and a searchable `bookmark_inventory.html`. It deduplicates content while
retaining separate folder memberships, reuses existing YouTube video IDs, and
records saved interest without inferring visits, enrollment or completion.
It makes no network requests and does not copy unrelated bookmarks, sync metadata
or last-used data. Reruns preserve prior evidence and manual reviews. Personal
folder names, URLs, counts and reports belong outside public Git data.

The user-published [bookshelf transcription](BOOKSHELF_INTEREST_EVIDENCE.md) also
supplies a reviewed-source starting point for subjects, methods and mathematical
connections. Its public title-level mapping is in `data/bookshelf_seeds.json`;
personal feedback and the instantiated interest graph remain outside Git:

```bash
python3 -m pagefinder.local import-bookshelf
python3 -m pagefinder.local interest-graph
```

The importer records physical visibility separately from inferred topic mappings
and adjacent research hypotheses. It neither creates reading events nor assigns
preference weights from book counts. It preserves bibliographic uncertainty,
provides primary-reference links and optional entry points, and keeps the existing
keyword profile/catalog unchanged as a comparator. An optional aggregate reading
annotation never assigns per-book progress. Use the existing private `review`
command on book/question IDs in `interest_graph.json`; corrections survive imports
and explicit question skips disable exploration eligibility. Source snapshots,
graph JSON and the searchable `interest_graph.html` viewer remain private.
Explicit application preferences can be saved with `set-interest-scope`: require
a context, or prefer it while retaining a small exploratory supplement. These
private corrections override weak source-derived assumptions without editing the
public comparator. `interest_profile.json` exposes the effective private profile;
private keyword scoring separates primary and exploratory contributions. It is
still an uncalibrated triage aid, not a calibrated recommendation engine.

Private `import-interest-notes SOURCE` records explicit interests, self-reported
background and appreciated resources separately from proposed connections. Its
search vocabulary is a curated interpretation, not a claim that every subfield
is preferred. Background and reading completion are separate dimensions. These
notes enrich the private graph/profile without changing the public comparator.

A first bounded public-project probe now has a private review queue. It includes
cached repository metadata/README excerpts, independent HTML checks for two
selected Pages sites, separate assessment facets and a keyword-baseline comparison.
Usefulness and novelty remain unmeasured until human review. No project code was
installed or executed. The existing public seven-site sample remains unchanged.

```bash
python3 -m pagefinder.local review-queue
```

The local `discovery_queue.html` and JSON source details stay outside Git. Saved
`review` decisions refresh both private viewers. See the current checkpoint and
remaining work at the top of [implementation status](docs/implementation_status.md).

```bash
python3 -m unittest discover -s tests -v
python3 -m pagefinder report
python3 -m pagefinder.publication
```

Both CI and the Pages deployment enforce the public-artifact guard. Only reviewed
public inputs feed the catalog. Private metrics report watch minutes and viewing
completion as `not_measurable` when the selected sources lack playback data.


## Cross-platform creator experiment

The private creator collection now contains the original twelve pilot cards and
40 additional recommendations from 150 new YouTube-first and 51 new GitHub-first
screens. Earlier cards, source snapshots and saved reviews are retained. Verified,
probable, guest-presenter, teaching-materials and single-platform cases remain
explicit. New research does not imply prior unfamiliarity or improved relevance.

```bash
# Existing private data directory and authorization are reused.
python3 -m pagefinder.local creator-review
python3 -m pagefinder.local serve-creators --port 8766
# Open http://127.0.0.1:8766/ ; Ctrl+C stops the service.
```

If startup reports `EROFS`, the private data directory is read-only to the process.
Run the command in your normal terminal or allow the sandbox to write to the
existing private data directory. `EACCES` or `EPERM` indicates a permissions or
sandbox restriction on private files or local sockets. `EADDRINUSE` means the port
is occupied; use `--port 8767` and open `http://127.0.0.1:8767/` instead.

The dashboard separates familiar interests and unexpected connections, with new
cards first. Combine subject, method, direction, affiliation, round, review-status
and platform filters with search. Expand representative works and explanations
on demand. Save Already familiar / Very interesting / Somewhat interesting /
Not interesting / Investigate later, with notes, directly to
the shared private SQLite review table. Offline HTML previews can download feedback
for explicit import instead:

```bash
python3 -m pagefinder.local creator-feedback /path/outside/git/creator-feedback.json
```

`creator_review.html`, `creator_review.json`, `creator_research_report.md`, source
snapshots and feedback stay in the private data directory. The local service exposes
only the dashboard, its research report and the review endpoint. It binds to
127.0.0.1, loads no external assets and never serves a repository/data directory.
The public Pages deployment does not import these records.

For a future bounded round, `creator-sources --likes --max-pages 2` or
`creator-sources --playlist-id ID --max-pages 1` imports only the selected collection.
Playlist access requires existing reviewed-positive annotations. `creator-seeds`
writes the sampling frame; `creator-metadata SOURCE` accepts a private bounded JSON
selection of channel/video IDs, handles, or cached channels' upload playlists.
Known-channel inspection uses uploads rather than expensive search. `--offline`
reuses caches without credentials/network; page checkpoints resume bounded imports.
These are explicit metadata reads, never watching events. `import-creators SOURCE`
validates a manually assessed private manifest (1–75 investigations per batch),
retains content-addressed evidence and merges it into the cumulative collection.
Stable IDs keep reviews attached; a later assessed revision can update a card
without deleting its earlier snapshot. Feedback imports accept up to 1,000 rows,
validate before writing and commit atomically. Unchanged and untouched reviews
retain their original state and timestamps. Identity is never inferred from a
URL or username automatically.

See the preserved [pilot](reports/creator-pilot.md) and the
[expanded methodology and aggregate findings](reports/creator-expanded.md). The
personalized full report is available through **Research report** in the local
viewer. User-rated improvement over either platform alone remains unmeasured.
