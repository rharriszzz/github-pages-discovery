# Codex task: unified interest discovery and lost-YouTube-video recovery

**Authoritative design:** Read [`MERGED_PROJECT_PLAN.md`](MERGED_PROJECT_PLAN.md) completely before coding. This replaces the earlier separate prompts for interest modeling, YouTube importing, and forgotten-video recovery. Do **not** concatenate or separately implement those prompts. The original [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md) remains the reference for the GitHub Pages sampling experiment.

## Mission

Improve `rharriszzz/github-pages-discovery` into a single evidence-driven research tool that (1) learns my sustained intellectual interests from my public GitHub repositories and, with my authorization, YouTube playlists/Likes/history, (2) finds older public YouTube uploads I plausibly missed from channels I used to value, and (3) finds new relevant websites, projects, creators and adjacent subject areas.

**Common core:** stable IDs, provenance, engagement observations, interest/concept graph, review feedback, storage/checkpointing, privacy separation, and transparent ranking facets. **Separate retrieval strategies:** catalog gaps among *known creators* versus open-ended discovery of *new material*. They must share the core, not duplicate implementations.

The 2025 YouTube discussion is important: forgotten channels, monthly/yearly watching histograms, publication-to-discovery lag, series gaps, and exploring partial watches if playback-completion data legitimately exists. Do **not** fabricate viewing minutes or 50%/95% completion from Takeout history timestamps. A video not found in an incomplete export is not necessarily unwatched.

## Before editing

1. Inspect working tree, branch, recent commits, `README.md`, `RESEARCH_PLAN.md`, `MERGED_PROJECT_PLAN.md`, `data/interests.json`, current source, tests, `docs/`, and GitHub Pages Actions. Retain existing sample data, human labels and generated public catalog.
2. Run baseline tests and offline report. Confirm API features/limits against up-to-date official documentation, especially YouTube private playlist OAuth, `videos.list(myRating=like)` 1,000-result bound, unsupported Watch Later/History access, and channel uploads playlist.
3. Identify any Codex work on other branches or uncommitted local files; integrate rather than overwrite. If current local state differs from what the plan assumes, record the differences.

## Stage 1 — build the shared foundations now

- Write a small, testable, versioned schema for public entities, private observations, evidence/provenance, concepts/relationships and recommendations. Store private user records under a configurable folder **outside** the Git working tree. Keep the public pagefinder implementation working.
- Add explicit completeness states, confidence/uncertainty, historical title/ID handling, persisted manual reviews, checkpoints, bounded retries, and test fixtures.
- Test for accidental inclusion of OAuth secrets or private data in exported `docs/` content; don't merely rely on `.gitignore`.
- Provide an implementation-status report distinguishing implemented functions from designs and unsupported metrics.
- Keep the public Pages site public-safe and the personal YouTube dashboard local to WSL2/localhost.

## Stage 2 — the first user-visible milestone: playlist names

Implement a Python CLI to authenticate with the YouTube Data API using a read-only Desktop OAuth client that the user will obtain in Google Cloud Console. Assume WSL2 Linux user `rharris`, Windows Chrome available, and credentials in:

`~/.config/github-pages-discovery/youtube/client_secret.json`

Use `https://www.googleapis.com/auth/youtube.readonly`. Handle WSL2 loopback-browser authorization carefully. Never request or store a password; no tokens or private data in Git. Respect quota and pagination.

**First retrieve only every accessible user-created playlist's title, ID, privacy, description and count**, including private playlists. Also clearly report which system collections (Likes, Watch Later, History) do not support the same enumeration path. Save a **local-only** editable playlist-inventory report, with purpose/relevance labels the user can correct. Do not import thousands of videos yet.

If no credentials are present, provide clear setup instructions and stop at an offline-tested importer. Do not block unrelated code/tests while awaiting sign-in. Do **not** ask for screenshots of very large playlists.

## Stage 3 — import history and prove lost-video discovery

- Support Google Takeout formats for Watch History and, where present, Likes, playlists and Watch Later. Parse cautiously, with versioned/synthetic fixtures and an import completeness report. API Likes are limited to the most recent 1,000 returned items.
- After I review the playlist inventory, import chosen playlist contents, normalize videos/channels and create engagement observations. A saved item is not proof of a play; Watch Later means intent, not completion.
- For a pilot of **3–5 high-affinity YouTube channels**, retrieve currently accessible uploads with the channel's uploads playlist; compare publication chronology to the locally available history and saved/liked videos. Demonstrate missed-item gaps surrounded by watched items and formerly frequent channels now encountered less often.
- Make a **private local** browser viewer for producer timelines, monthly/yearly watch-event and distinct-video counts, first-view versus publication lag, candidate queues and evidence/confidence. Only show estimated watch minutes when evidence really supports them. Keep meaningful user-review feedback.
- Evaluate at least ten candidates with explicit false-positive and missing-data accounting before crawling large numbers of channels.

## Stage 4 — use that profile to improve public discovery

Study my public repositories, including relevant non-default branches, to populate subject/method/question relationships. Integrate only vetted and private-safe summaries of YouTube-derived interest signals. Maintain a keyword-only comparator and test whether graph expansion actually improves discovery.

Then harden the original GitHub Pages discovery, validate ~20 sites and a bounded ~100-site diverse sample, and produce the original owner-type, coverage, bias, and interesting-site reports. Keep public/site rankings separate from private missed-video rankings, each with explanations, multiple scoring facets, and evidence.

## Execution rules

- Work in coherent increments, with local tests and checkpoints before each external/API batch; no uncontrolled crawls or rate-limit evasion.
- Aim for a useful, reviewable milestone rather than a large count. Record exactly what has run, including request totals or quotas, dataset coverage, and unavailable sources.
- Keep raw user data, credentials, OAuth tokens and private reports outside the repository and all Pages artifacts. Do not expose playlist membership indirectly via public scores/examples or filenames.
- Honor robots.txt and GitHub API limits for external sites; use public API endpoints for YouTube where allowed. No automatic playback, no YouTube history writes, no unrequested scheduling.
- Tests should cover data isolation, schema migration, pagination, duplicate IDs, unavailable videos, time-zone handling, chronology gaps, missing history, cached/offline reruns, and static output safety.
- Preserve working `pagefinder` features, their test coverage and the existing seven examples.
- Commit/push verified public code and documentation only; leave raw YouTube data on the user's PC. Explain any outstanding user action required for Google authorization.

## First deliverable / stop point

Before a large crawl, produce a **privacy-safe local YouTube playlist inventory**, a reusable public/private data architecture, an offline-tested history importer, and an updated implementation-status report. Request the user's playlist-purpose annotations and/or Google credentials when truly necessary. The broader historical analysis and public discovery phases follow those gates; don't start by importing every video or creating a massive taxonomy.

The operating question is not "How many results did we classify?" but: **"Did we find worthwhile old videos I would have missed, and genuinely interesting new ideas I didn't already know about?"**
