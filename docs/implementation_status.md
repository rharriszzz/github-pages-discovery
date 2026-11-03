# Implementation status — 2026-11-02

This records execution, not completion of the entire merged research plan.

## Reconciliation and existing behavior

- Inspected both authoritative plans, the original research plan, all original
  source/tests/data, public generated artifacts, Actions, recent commits, local
  branches and worktrees. Initial branch: `main`, at `7ddc0ee`, clean and matching
  its recorded upstream. No other branches, stashes or uncommitted work existed.
- All six original tests passed before changes. The offline report reproduced
  the seven public sample records without changes. Their labels and interest
  keywords remain intact; no new survey or live HTTP verification is claimed.
- The original public JSON store is retained. A separate private SQLite v1 store
  supplies the common research model, avoiding a rewrite of working public tools.
- Official Google endpoint/OAuth/quota documentation and GitHub rate-limit
  documentation were checked. API constraints and setup links are in
  [YouTube setup](youtube_setup.md); storage/migration decisions are in
  [architecture](architecture.md).

## Implemented and validated offline

- Stable IDs, provenance, explicit completeness/confidence/visibility, historical
  titles, typed engagement, manual feedback and transactional checkpoints.
- Versioned v0-to-v1 initialization and refusal of unknown future/nonempty
  unversioned schemas. Private paths and outputs are constrained outside Git.
- Desktop OAuth with only youtube.readonly, PKCE and loopback callback; no pasted
  credentials, browser approval bypass or OAuth URL/token logging by the CLI.
- Owned-playlist metadata pagination, deduplication, resumable budgets and private
  HTML/JSON/CSV inventory. Annotation download/apply preserves explicit labels.
  This milestone has no playlistItems/videos API import path.
- Private Takeout source snapshots and conservative history JSON/HTML plus CSV
  collection imports. Collection semantics are explicit; reviewed playlist
  purposes are required before curated playlist contents can be imported.
- Versioned successful/error response caching and persistent atomic admission
  ledgers; bounded YouTube retries; saved 403/429/server-header cooldowns; cache
  reuse and explicit refresh; public robots/HTML response caching and pacing.
- Guarded public input/export contracts, artifact allowlist and CI/deployment
  checks. Public deployment does not run any personal importer.

## Validation and denominators

The original infrastructure checkpoint passed 43 standard-library tests on
Python 3.14.4, including the original six. The bookmark extension below raises
that checkpoint's total to 52 passing tests. The bookshelf extension below raises
the current total to 63 passing tests.
The CI workflow uses Python 3.11; that interpreter was unavailable locally.
OAuth SDK invocation is tested with a synthetic mock against its documented
signature; optional OAuth libraries were not installed in the base interpreter.
No live browser sign-in, token refresh or Windows-to-WSL callback is claimed.

- Synthetic inventory: two API page fixtures, three distinct playlists spanning
  private/unlisted/public, one repeated ID and a title change. Counts include a
  12,000-item collection without downloading any of those items.
- Synthetic history: six JSON rows, four retained events (including two identical
  video/time occurrences), two unavailable/unrecognized rows and one unknown local
  timestamp. HTML overlap reconciles an existing event; missing IDs stay excluded.
- Synthetic Likes: three CSV rows, two retained memberships and one excluded row.
  Synthetic Watch Later: two retained intent records, including one unknown date.
- Cache/offline resume, retry bounds, persisted shared budgets, Pacific daylight
  saving reset, quota stops, review preservation, repository/symlink isolation,
  publication blocks and original public clients are exercised.
- Offline public regeneration: seven sites; generated HTML/CSV/JSON remain
  byte-for-byte unchanged. Publication guard and whitespace checks pass.

At that original infrastructure checkpoint, actual YouTube API attempts: **0**.
Actual YouTube quota used: **0**.
Real private playlists/history rows imported: **0**. Live public research API or
site-fetch batches in this implementation run: **0**. Documentation browsing is
separate from research API usage. There are no actual missed-video suggestions
or user evaluations yet.

## Current gate and next user action

At the original infrastructure checkpoint, the Desktop client had not yet been
configured. Account-specific setup, inventory and annotation results are kept
locally; this public document does not track private account state. Follow the
[local setup](youtube_setup.md), put the downloaded Desktop client in the external
configuration folder, and approve the read-only browser flow. Do not paste secrets
into chat. Run the bounded inventory, then interpret playlist purposes/relevance
in its local viewer before choosing contents. This is the required gate before
bulk imports. A small real Takeout source is optional and needs explicit selection.

## Deferred and unsupported

- Gate 3: actual channel histories, publication-to-first-observation lag, upload
  catalogs for 3–5 selected channels, gap/drift/series analysis, private timeline
  charts and ten human-reviewed suggestions. Chronology-gap tests belong here.
- Gate 4: automated extraction/inference, calibrated ranking facets and
  keyword-comparator evaluation. The curated bookshelf map below is a bounded
  initial graph, not a completed multi-source preference model or evaluation.
- Gates 5–6: new 20/100-site pilots, wider crawling and justified scaling.
- Watch minutes, fractional completion, 50%/95% progress: `not_measurable`.
- API history/Watch Later unsupported. Likes API (deferred) capped at latest 1,000.
- Arbitrary localized HTML, ZIP extraction/streaming, conditional ETag requests,
  automatic cache eviction and multi-installation quota coordination are deferred.
- Rate budgets cover calls sharing this tool's ledger; external consumers may
  spend project/token quota. Provider responses always take precedence.

No automatic jobs, paid models, playlist writes or playback are configured.

## Additional source: selected local Chrome bookmarks

Implemented a private `import-bookmarks` command using the existing schema v1.
It requires explicit folder selection, preserves hierarchy and source dates,
deduplicates content while retaining memberships, and writes a filtered source
snapshot plus private JSON/HTML reports. It does not fetch linked pages or copy
unselected bookmarks, sync data, last-used values or arbitrary metadata. Source
files are opened read-only. Publication guards and public catalog inputs remain
unchanged. Real source details and results are recorded only in private reports.

Nine additional synthetic tests cover selection scope and missing/ambiguous/
overlapping folders, nested paths, URL deduplication, cross-source YouTube IDs,
date conversion, excluded schemes, metadata isolation, title escaping, CLI output,
unchanged source/public files, repeat imports, and durable manual feedback.
Total: **52 passing tests**. The synthetic Chrome fixture has eight bookmark
entries, four unique valid items, five saved memberships and two excluded entries.
No linked-page requests or new public discovery batches are part of this extension.

## Additional source: user-published bookshelf evidence

Safely fetched and fast-forwarded the clean working tree from `64a97d4` to the
user's `8f73624` bookshelf commit. Existing work was preserved. The Markdown
transcription is retained unchanged, with 13 identified volumes and its original
bibliographic uncertainty. A separate public-safe seed map describes 24 subject,
method and intellectual-history concepts and six cross-disciplinary hypotheses.
No personalized reading/priority feedback is committed with that map.

The private import uses the requested physical-visibility provenance and reuses
schema v1. Known source reports, inferred topic mappings and hypothetical research
connections have different relationship types/statuses. Books do not create
viewing/reading events or preference weights. Repeated introductory coverage is
one evidence family, not independent votes. Primary references were checked for
the proposed directions; only scoped citation metadata and summaries are cached.
The importer itself makes no requests and does not ingest book full texts/media.

The local viewer exposes books, themes, hypotheses, optional entry points, source
limitations and durable feedback. Aggregate reading annotations are private and
do not assign individual completion or proficiency. The independent public
keyword baseline and seven-site catalog remain unchanged. No larger discovery
pilot or historical-video analysis was run as part of this integration.

Eleven additional tests bring the total to **63 passing tests**, covering exact
provenance, typed links, unspecified priorities/progress, bounded hypotheses,
source validation, cache/idempotency, private aggregate feedback, skip overrides,
preserved manual reviews/engagement, public-data isolation and offline CLI use.
Explicit application-scope corrections support both required contexts and soft
preferences with exploratory additions. Private scoring separates primary and
exploratory contributions; context keywords still require semantic review, and
recommendation batch quotas/calibration remain unimplemented. Personal corrections
are stored outside Git and never rewrite the public keyword comparator.
