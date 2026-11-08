# Implementation status — 2026-11-03

## Practical private Learning Queue

- Added a question-first Learning Queue on loopback port 8767. Optional goal,
  time and format controls produce up to five specific source-linked works;
  saved, useful, completed and dismissed views preserve independent feedback.
- A read-only arXiv Shelf adapter mirrors live schema-1 catalog event ordering,
  aliases, metadata and star-rating semantics. It agrees with the existing
  `Catalog.read_state()` on the local collection. PDF availability is verified
  separately; neither source membership nor a rating implies reading.
- The work index combines the existing creator collection, retained video
  descriptions, cited concepts, earlier project README excerpts and selected
  bookmarks. Refresh is local/offline, idempotent and retains cached partitions
  when a source is missing or malformed. Existing creator reviews remain intact.
- Independently revisited 18 works: five videos, six code resources, three
  technical articles and four collected papers. Actual sources, ranked example
  results, evidence and limitations are private. Five representative questions
  return mixed-source shortlists without requiring a paper for every question.
- Specific query anchors and documented method bridges avoid an observed generic
  keyword failure. Separate fit/evidence/effort facets remain inspectable; these
  checks do not establish improved human usefulness or unfamiliarity.
- Research usage: one YouTube metadata request, eleven logical GitHub connector
  calls (one unsuccessful branch guess), and four web-tool calls containing
  eighteen opens/clicks. One failed full-text route was resolved through an
  official page. No candidate code ran and no full video was watched.
- **112 tests pass**, including adapter semantics, refresh/fallback, retrieval,
  independent feedback, private-data boundaries, socket protections and useful
  startup/storage errors. Chromium desktop/narrow-width checks cover real queries
  and synthetic save/reload; Windows-to-WSL localhost access returns HTTP 200.
  Shelf files and existing reviews are unchanged; the public catalog is preserved.

Launch: `python3 -m pagefinder.local serve-learning --port 8767`, then open
`http://127.0.0.1:8767/` in Windows Chrome. No separate import/rebuild is required
on normal startup. See the [Learning Queue guide](../guides/learning-queue.md).

## Expanded creator discovery checkpoint

- Screened 150 new YouTube-first channels and 51 new GitHub-first canonical
  account/collective leads in checkpointed batches. Produced 40 new multi-work
  cards alongside the original twelve; the private dashboard now has 52 cards.
- Thirty new cross-platform affiliations are verified and one remains probable.
  Nine additional cards are labeled single-platform comparisons. Twenty-seven
  meet the stricter verified operator/software intersection definition; guest
  presenters and teaching slides remain distinct.
- Source-linked concepts, role-specific neighborhood trails and explicit
  limitations accompany the recommendations. Existing private reviews and the
  original experiment survive intact. New research does not establish novelty,
  and expanded relevance has not yet received human evaluation.
- The dashboard supports cumulative batches, round/review/platform filters,
  separate connection sections, expandable works/evidence and atomic durable
  feedback. Startup preflight and WSL2 recovery diagnostics are implemented.
- Research accounting: 116 YouTube attempt reservations (six transport failures),
  192 logical GitHub connector calls and 26 web-search queries. Remote/internal
  request counts are not exposed. Exact-ID metadata replaced throttled embeds.
- **89 tests pass**; Chromium desktop/mobile review and feedback workflow pass.
  Windows PowerShell reaches the WSL2 server with HTTP 200. Original public
  catalog regeneration, publication guards and whitespace checks pass.

See [expanded methodology and aggregate results](../reports/creator-expanded.md).
All creator identities, personalized source trails, reviews, account data,
screenshots and raw research remain outside Git. The earlier checkpoints below
retain their original scope and evaluation status.

# Earlier implementation status — 2026-11-02

This records execution, not completion of the entire merged research plan.

## Cross-platform creator checkpoint

An additional creator strategy is implemented on the existing private architecture.
It preserves the broader merged plan, existing feedback, interest graph, caches,
YouTube setup and original seven-site public catalog.

- Screened 50 YouTube-first channels and eight GitHub-first seeds; deeper work
  produced twelve private review cards with two or three projects/videos each.
  Eleven are operator/project intersections; one is a labeled guest presenter.
- Thirteen verified affiliation records include a sister-channel duplicate and
  that presenter; three probable, five uncertain and 37 unmatched records remain
  explicit. Recent software and recent video activity are assessed independently.
- Acquisition examined 61 channel IDs and 21 GitHub accounts, including alternatives
  and rejected matches. These exceed the seed frame and recommendation denominators.
- Shared observations, candidates, evidence, graph links, private profile and durable
  reviews are reused. A loopback page supports filters, decision notes, database saves
  and an offline feedback-download/import path. Private research reports include the
  full methodology, source trails, identity failures and next experiment.
- 28 YouTube API attempts/units, 53 logical GitHub connector calls (six unsuccessful),
  and 64 web-search queries. Remote connector/browser internal HTTP counts are not
  exposed. No remote project code ran; full videos/transcripts were not assessed.
- **78 tests pass**. Chromium desktop/mobile inspection passes with no external page
  requests, JavaScript errors or overflow. Synthetic-data save/reload and downloads
  pass. Public export regeneration and publication guards pass; original public
  catalog outputs and inputs remain unchanged.

GitHub-first retrieval was more productive in this adaptively selected pilot,
but neither general superiority nor improved user usefulness is established.
Next: collect twelve reviews, inspect selected technical examples/transcripts,
resolve probable affiliations, then run a matched single-platform/combined-evidence
comparison. Preserve excellent code-only and explanation-only candidates too.
See [public-safe methodology and aggregate findings](../reports/creator-pilot.md).
Personalized details and account-derived source records remain outside Git.

## Earlier private-project checkpoint

The source-ingest foundation now produces a first private, evidence-backed review
queue. This is a useful discovery checkpoint, not completion of the research plan.

Implemented:

- Private source ingestion for reviewed playlist metadata/annotations, selected
  Chrome bookmark folders, bookshelf transcription and explicit interest notes.
- A curated graph with provenance, known/inferred/hypothetical link types, durable
  feedback, application preferences, and separate user-reported background.
- A bounded five-public-repository probe with cached metadata and README excerpts.
  Two selected GitHub Pages sites also passed independent robots-respecting HTML
  checks. All five repository owners in this targeted probe are Organization
  accounts; the sample supports no population-wide ownership conclusions.
- A private review queue with separate fit/method/novelty/quality/activity/evidence
  facets, source limitations and a fixed-keyword-baseline comparison. Familiarity,
  novelty and human usefulness are still unmeasured. No remote project code ran.
- Cache reuse, persistent request budgets/cooldowns, private report isolation and
  a guarded public export. The original seven-site public sample is preserved.

Validation and request accounting for this checkpoint:

- **69 tests passed** locally. Public export regeneration and publication guard
  pass; original public HTML/CSV/JSON and public keyword inputs remain unchanged.
- **13 logical GitHub connector calls**, including one README 404. A directory
  listing resolved the correct filename. Connector-internal HTTP counts and rate
  headers are not exposed; each logical call passed local conservative admission.
- **6 site-request reservations**: two initial sandbox transport failures, then
  two successful robots fetches and two successful page fetches. Initial failures
  and successful checks are retained in the cached evidence.
- No YouTube API batch, bulk playlist import or missed-video evaluation ran in
  this increment. Public documentation lookups are separate from probe accounting.
- Detailed personal notes, recommendations, raw probe responses and review state
  are local/private, not published in these docs.

Next work, in order of practical usefulness:

1. Review the five candidates for keep/later/skip and reasons. This establishes
   usefulness and false positives; record counts alone do not establish success.
2. Corroborate the profile with a bounded examination of selected bookmarked
   public pages and the user's public project READMEs/plans/relevant branches.
3. Run the planned 20-site pilot with diverse cohorts and independent verification;
   expand toward 100 only after review. The present five-repository probe is not
   that 20-site experiment and includes sites outside the github.io-only frame.
4. For lost-video recovery, import a selected real Takeout history source, choose
   3–5 creator channels, implement upload chronology/gap/drift analysis and evaluate
   ten suggestions. Playlist purpose annotation is not selection of every playlist.
5. Calibrate preference/ranking facets and implement actual exploration quotas and
   queue selection using feedback. Automatic source-to-concept extraction and
   broad recursive exploration remain incomplete. The current graph is curated.

Private inputs do not establish viewing duration, course completion, proficiency
or an unseen video's unwatched status. Playback-completion metrics remain
`not_measurable`. No uncontrolled crawls, scheduled jobs or paid model calls run.

The sections below preserve earlier implementation checkpoints and denominators.

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
that checkpoint's total to 63 passing tests. The current checkpoint above has
69 passing tests.
At that historical checkpoint, CI used Python 3.11; that interpreter was unavailable locally.
The current CI configuration tests Python 3.14 and 3.15, while Pages validation
uses Python 3.15. This updates the recommended environment, not the historical result.
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
