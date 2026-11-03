# Unified research architecture: interests, lost videos, and new discoveries

Status: design specification, **not a claim of implemented functionality**. Prepared 2026-11-02. This supersedes the earlier standalone expansion prompts; retain `RESEARCH_PLAN.md` as the baseline specification for the original GitHub Pages survey.

## 1. Purpose and intended outcomes

Build one locally controlled discovery system with three closely related jobs:

1. **Model my intellectual interests.** Study my public GitHub projects, selected public material, and my own explicitly authorized YouTube signals. Model *subjects*, *methods*, *questions*, *creators*, and *adjacent ideas*, rather than only word-frequency matches.
2. **Recover "lost" YouTube videos.** Find older public videos from creators I watched extensively or saved/loved, but whose videos no longer reliably appear in recommendations. Detect skipped uploads, changes in viewing frequency, partially explored series, and formerly favored channels I have drifted away from.
3. **Discover unfamiliar material.** Find interesting public GitHub Pages sites, projects, research, and potentially YouTube channels/videos. Include genuinely novel adjacent work, not just exact-topic matches. Preserve the original owner-type investigation (GitHub User vs Organization).

These are two distinct retrieval tasks (missing videos from *known* creators, and *new* material) powered by one shared evidence-backed interest graph. **Do not conflate absence from a data source with disinterest or never having watched something.**

Success is measured by *useful discoveries confirmed by human review*, data-quality coverage, and low false-positive rates—not record counts or an opaque combined score. Provide an interactive, fast, light-background interface suitable for rapid scanning.

## 2. Recover the earlier 2025 YouTube research requirements

The March 2025 design discussion included:

- Identify producers/channels once watched frequently but now watched rarely. Rank by both unique videos and watch events; chart monthly/yearly histories. Plot *actual minutes watched* **only if defensible duration data exists**.
- Enumerate producers' public upload catalogs, find historical gaps, especially unwatched-or-unrecorded *older* videos around positively engaged videos, and identify series gaps.
- Analyze time between **publication** and **first evidenced viewing** (median, distribution, and other meaningful summaries by channel). The earlier proposal also discussed videos watched for at least one minute but less than 95%, and time to 50% viewing completion. Standard YouTube watch-history exports typically **do not include progress or playback duration**. Implement those analyses *only if an independently verified, legitimate data source supplies per-view playback/progress measurements*. Never invent fractional completion, minutes, or 'watch-through'. Report an explicit `not_measurable` result otherwise.
- Provide efficient browser-based exploration, channel timelines and histograms, local caching, and reproducible testing with fixtures. The earlier discussion favored JavaScript/SVG for the UI, with local Python tooling where useful. Do not let the old UI choice dictate a fragile architecture, but preserve the goal of simple, locally operable interactive charts.

The central distinction: *not found in available history* is **not** *never watched*. History may be incomplete, disabled, deleted, or missing periods; channels can change names; videos can be deleted, made private or moved.

## 3. Shared data model and boundaries

Use stable IDs and provenance on every observation. Propose a small versioned local database (SQLite is reasonable for thousands/millions of rows) or equivalent tested persistent store. Reuse the existing `pagefinder` module and its public sample rather than replacing it wholesale.

### Objects and relationships

- **Evidence**: source type, source identifier/path, date retrieved, time observed where applicable, confidence, visibility (public/private), method/version, completeness notes.
- **Content item**: public GitHub page/project/repository, YouTube video/playlist/channel, public article, or user-curated note. Canonical URL, stable native ID, title, creator, publication date, availability and source references.
- **Creator/account**: YouTube channel ID and title history; GitHub owner ID/login/type, repositories and verified sites. Distinguish site from owner, and account type from team size.
- **Interest concepts**: subjects, methods, scientific/engineering questions, techniques and neighboring topics. Multiple labels per item; typed relationships with evidence (e.g., *uses method*, *addresses question*, *adjacent to*).
- **Engagement observations**: saved to playlist, liked, appeared in Takeout history, repeat play, manual keep/skip/later, or other verifiable signals. Record each event without assuming equal importance.
- **Discovery candidate**: why surfaced, which retrieval path, deduplication key, assessment facets, evidence links, uncertainties, review status.

Keep *public facts* (public videos, websites, repo metadata) separate from *private facts* (the user's viewing dates, Likes, private playlist names/membership, source exports and notes). The public GitHub Pages catalog must never bundle private records or a reconstructable private interest graph.

### Inputs and signal semantics

- **Public repositories**: Examine README, current design plans/results and useful non-default branches of `rharriszzz` repos. Recent sustained research is usually more informative than irrelevant old forks; do not infer strength from repository count alone.
- **User-curated YouTube playlists**: A saved video is a positive signal *when the playlist's purpose supports it*. First inventory playlist name/ID/privacy/count, then ask for an editable purpose/relevance annotation. A temporary inbox or queue is not the same as a carefully curated favorites list.
- **Liked videos**: Moderate positive signal by default; overlapping playlist membership may increase confidence but do not blindly double count.
- **Watch history**: Evidence of encounter/engagement, not automatic endorsement. Repeated videos and sustained channel engagement matter; a single play does not.
- **Watch Later**: Intent to watch, *not proof of watching*. Treat separately.
- **Manual feedback**: Keep/skip/later/unknown; explicit corrections should outweigh weak inferred preferences and remain durable across recomputation.

Interest graph edges must explain their source and direction. For speculative adjacent branches, label them as hypotheses rather than known user interests. Permit expansive recursive exploration but use bounded depth, quotas and measured yield; retain surprising results without turning every association into a permanent preference.

## 4. YouTube ingest: sources, API constraints, and privacy

### First: playlist inventory, without large content imports

Implement read-only OAuth 2.0 **Desktop** application for Windows Chrome + WSL2, using `https://www.googleapis.com/auth/youtube.readonly`. Prefer an existing local configuration folder outside the repository, e.g. `~/.config/github-pages-discovery/youtube/` for `client_secret.json` and tokens. Never log tokens or commit them. Use the browser OAuth flow; no pasted account password. The user's Google approval is mandatory.

- Retrieve user-created **private, unlisted and public** playlists with `playlists.list(mine=true, part=snippet,contentDetails,status)`, following `nextPageToken`; inventory counts/metadata only first.
- Store the inventory in a **private local output folder outside the repo**. Provide a simple editable annotation view for playlist purpose and relevance before downloading contents.
- After review, retrieve chosen playlist items via `playlistItems.list`, paging up to 50 and checkpointing. Normalize stable video ID/channel ID, unavailable/deleted items and playlist membership. Use public video metadata only where accessible.
- For Likes, `videos.list(myRating=like)` returns at most the **most recent 1,000** videos even when the reported count is higher. Do not silently describe this as complete; consider complementary Takeout exports.
- YouTube Data API **does not allow retrieving Watch History or Watch Later items**. Support Google Takeout imports where present, without bypassing access restrictions. Parse documented/observed formats defensively, with test fixtures and explicit source limitations.
- For uploads from a known creator use `channels.list(part=contentDetails)` to get the *uploads* playlist ID, then `playlistItems.list`. These are accessible **currently listed uploads**, not every video ever published; removals, private videos and metadata changes create gaps.
- Use pagination, caching, quotas, ETags where practical, retry with bounded backoff, and resume from checkpoints. Do not use broad expensive `search.list` calls as the default way to enumerate a known channel's full catalog.

Google's public references (verify during implementation):
- https://developers.google.com/youtube/data/reference/rest/v3/playlists/list
- https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list
- https://developers.google.com/youtube/data/reference/rest/v3/videos/list
- https://developers.google.com/youtube/data/reference/rest/v3/channels/list
- https://developers.google.com/youtube/data/guides/auth/installed-apps

### Privacy contract (non-negotiable)

- Private raw exports, playlist inventories, engagement events, credentials, OAuth tokens, caches, and per-user recommendations remain **outside the Git working tree** by default, not merely excluded by `.gitignore`.
- No API credential in URLs, logs, test fixtures, reports or screenshots. Never ask the user to paste secrets into chat.
- Public GitHub Pages workflow publishes ONLY deliberately reviewed public artifacts in `docs/`; no private data generation on GitHub Actions. Keep local analytics and private dashboards on loopback/localhost. Add safeguards/tests against accidental inclusion of private paths and tokens.
- Explicit user consent to examine private playlists is **not** consent to publish their names, membership or individual history on the internet.
- No requirement to make private playlists public, to bypass YouTube restrictions, or to scrape authenticated pages in violation of site rules.

## 5. Two retrieval/recommendation modes, one concept graph

### A. Lost-video recovery (catalog completion)

Input: known creator/channel from Takeout history, saved/liked videos, or manual selection. Build a local channel-affinity history:

- Counts of watch-history *events* and distinct watched IDs by month/year; saved/liked counts, first/last observed, and observed windows of inactivity.
- Pair each *publicly available* upload with all available positive/negative observations; record status: `history_seen`, `liked_or_saved_only`, `not_found_in_available_history`, `unknown_or_unavailable`, or `reviewed`. Do not equate saved with watched.
- Detect **internal gaps**: a video chronologically surrounded by multiple recorded watched videos; missed entries in a recognized series; older uploads of favored creators; a creator whose watch frequency declined sharply even though they continued publishing.
- Rank candidates using separate, explainable facets: past channel affinity, proximity to positively engaged neighboring videos, topic/method fit, age/recommendation neglect, series continuity, confidence of data coverage, and novelty. Display why a video was surfaced and which data may be missing.
- Include "rediscover dormant channel", "overlooked video within an active series", "old unencountered upload", and "recent upload from formerly favored channel" as different discovery labels.
- Feedback: `watch/keep`, `later`, `already watched`, `not interested`, `not enough evidence`. Do not pretend to modify YouTube's actual history unless user requests a separate authorized action.

Evaluate manually on a mixed sample of known and unfamiliar candidates. Distinguish relevance from certainty of "unwatched" status. Report exclusions and the denominator of searchable uploads.

### B. New-site/new-creator discovery (open-world)

- Retain the GitHub Pages research design: broad and targeted discovery cohorts, account User/Organization via GitHub API, site/repo mapping, deduplication, live verification, source bias, conservative crawling, evidence and confidence.
- Enrich the common interest graph from public repos + vetted private signals; discover useful adjacent disciplines, techniques and authors not found by literal keyword search.
- Score **direct topical fit**, **methodological affinity**, **adjacent curiosity**, **novelty**, **rigor/quality**, **activity** and **evidence confidence** separately. Never equate popularity or surface design with usefulness.
- For a public recommendation, cite actual public source pages or repositories. For local private recommendations, you may explain that the item matches a saved/liked channel without exposing that information publicly.
- Be explicit that GitHub Pages discovery is selective; do not imply an exhaustive sample of all `*.github.io` sites.

### Shared exploration and learning loop

For either retrieval mode, capture user reviews and the specific *reason* a suggestion was worthwhile. Calibrate rankings against these reviews, identify low-yield associations, expand useful graph neighborhoods, and preserve the distinction between *known preference*, *inferred interest* and *unexplored connection*. Cap recursive breadth/depth and external request budgets.

## 6. User experience: two surfaces

1. **Public Pages catalog** (existing `docs/`): public GitHub website/project survey only; filters for topic, owner account type, project/homepage, confidence and review status **provided those reviews are public-safe**. Continue generating public static exports and coverage reports from **public input only**.
2. **Private local research dashboard**: playlist inventory and annotation; producer charts/timelines; chronological upload gap maps; missed-video queue; cross-domain interest graph; review controls; provenance and evidence details. Host on loopback or an offline local interface only, not on public Pages. Support clickable YouTube links for user-directed viewing; never autoplay or claim videos were watched.

Use a local cache, incremental updates, and a simple JavaScript UI (SVG/Canvas where useful), with a Python CLI/service where helpful. Keep a fast path for bulk personal-data imports without expensive LLM calls for every item.

## 7. Sequenced implementation, acceptance gates

**Gate 0 — Inspect and reconcile.** Read all existing code, tests, branches, docs and state before modifying; preserve the seven researched samples and public-site outputs. Run the existing six tests. Document changed assumptions, schema versioning, and rollback/migration. Do not rewrite working modules merely to pursue a clean-slate architecture.

**Gate 1 — Privacy/data contract and local runtime.** Define versioned entities and evidence fields, separation of public/private, fixture-based tests, per-source completeness and an inspectable storage location outside the repo. Add safe import/export and private-data leakage tests. Produce architecture rationale and CLI help.

**Gate 2 — YouTube inventory + Takeout foundation.** Implement the desktop read-only OAuth flow, playlist **names/counts only** inventory (including private and unlisted), and a reviewable classification of playlist purposes. Add robust Google Takeout import for history, Likes and Watch Later where available. Test with **synthetic fixtures**, then a small user-authorized real dataset. Record missing/ambiguous sources. **Stop for the user's interpretation of playlist purposes before bulk import.**

**Gate 3 — Historical channel research.** Build channel histories with accurate monthly/yearly counts; publication-to-first-observation lag; upload inventory for ~3–5 user-selected channels; gap detection, drift and series continuity. Where watch progress isn't measured, show it as unavailable. Generate private local dashboards and evaluate ten actual suggestions with user feedback.

**Gate 4 — Integrate interest graph.** Study public repos and relevant branches; combine vetted playlist/like/history signals into concept/evidence graph. Build bounded neighbor expansion and separate facet scores; a fixed keyword baseline must remain for comparison. Document why an edge exists and what could falsify it.

**Gate 5 — Public discovery pilot.** Continue the original GitHub Pages crawl plan at 20, then roughly 100 diverse validated sites; maintain broad and targeted cohorts and independent site verification. Use the enriched *public-safe* interest model for ranking without publishing private signals. Evaluate top hits and false positives.

**Gate 6 — Scale if justified.** Only after confirmed high-quality findings: expand playlists/channels and site cohorts with quotas, checkpoints, progress snapshots and repeatable incremental refresh. No uncontrolled Actions crawlers or unrequested scheduling.

### Required reports

- `docs/architecture.md` or comparable public-safe architecture summary
- `reports/methodology.md`, `reports/coverage.md`, `reports/findings.md`, `reports/interesting-sites.md` for the public-site portion
- Private local `playlist_inventory`, `channel_drift`, `missed_videos`, `interest_graph`, `evidence_coverage` reports, **not committed**
- `docs/implementation_status.md` with explicit tests passed, sample sizes, API quota used, blockers, unsupported metrics and next actions

### Decision criteria

Continue a direction only if it yields *intellectually interesting, verifiable suggestions*. Favor a small demonstrably useful collection over thousands of shallow classifications. Avoid taking all recommendations from the same creator, repo, or high-volume topic; show unexpected but defensible connections. Respect the user's preference for reasoned evidence and intelligible visual diagnostics.

## 8. Important non-goals

No exhaustive inventory of GitHub Pages or YouTube; no claim to know the user's full preferences, watch completion, real-world identity of site owners, or unseen/deleted videos; no private-data publication; no platform recommendation manipulation; no uncontrolled long-running crawls; no reliance on an external paid model without authorization; and no background process that assumes a Google login or interactive authorization succeeds unattended.


## 9. Additional bounded strategy: creators publishing code and explanations

The cross-platform creator experiment is a new open-world retrieval strategy under
section 5B, not a replacement for interest modeling, lost-video recovery or the
GitHub Pages survey. It reuses the private graph, evidence, caches, candidates and
reviews. Identity/affiliation, operator versus guest-presenter role, subject/method/
approach connections and eight assessment facets remain separate. Official links
are necessary for verified affiliation; references and shared names are insufficient.

The first execution and limitations are documented in
[the aggregate pilot report](reports/creator-pilot.md) and implementation status.
Personalized twelve-card review and detailed research evidence remain local. Scale
only after user review, and test the intersection against matched code-only and
video-only evidence rather than treating targeted retrieval yield as quality uplift.
