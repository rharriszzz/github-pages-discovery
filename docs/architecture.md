# Shared discovery architecture, schema v1

Implemented 2026-11-02. Scope: local evidence/storage, playlist metadata inventory,
annotations, Takeout foundation, caching and request admission. Historical ranking
and interest inference remain later gates in `MERGED_PROJECT_PLAN.md`.
Selected local Chrome bookmark folders and a user-published bookshelf transcription
are supported as additional inputs. The bookshelf has curated concept links;
automated extraction, calibrated preference inference and ranking remain future work.

## Two data boundaries

The existing `pagefinder` public survey continues to use the reviewed public
`data/sites.json` and `data/interests.json`. Its seven seed sites, manual labels,
keyword comparator and generated catalog are preserved. Personal research runs
through `python -m pagefinder.local`; the public report never opens that database.

Private defaults:

- `~/.local/share/github-pages-discovery/`: SQLite, API response history, source
  snapshots, inventory HTML/JSON/CSV, annotation snapshots and import reports.
- `~/.config/github-pages-discovery/youtube/`: Desktop client and OAuth tokens.

`--data-dir`, `PAGEFINDER_PRIVATE_DIR` and `--config-dir` allow dedicated alternatives.
Resolved paths inside this or another Git working tree, symlinks into repositories,
and ancestors of this repository are rejected. Private folders use mode 0700;
atomic private report/token writes use 0600. These are filesystem protections,
not encryption. Keep one account per private research directory. Inventory checks
owner channel IDs to prevent accidentally mixing different owners.

`python -m pagefinder.publication` validates public input field allowlists, rejects
private record/credential patterns and personal absolute paths, and checks a small
allowlist of deployable files. The exporter validates before writing. Both CI and
Pages deployment run the guard; Pages uploads only `docs/` and never runs private
imports or a crawler. These checks supplement deliberate public-source review;
no scanner can detect every private fact disguised as ordinary prose.

## Versioned local model

`research.sqlite3` uses SQLite `PRAGMA user_version=1`, foreign keys and transactions.
Native IDs are namespaced, such as `youtube:video:<id>`; snapshot/event keys use
SHA-256. The schema supports both retrieval paths without duplicating engagement.

| Table | Meaning |
| --- | --- |
| evidence | Source reference, retrieval/observation dates, method/version, confidence, visibility, completeness and limitations |
| entities / titles | Content and creators/accounts, stable native IDs, URLs, availability, publication dates and historical titles |
| observations / observation_sources | History events, Likes, saved membership and Watch Later intent, linked to each supporting export |
| concepts / relationships | Subjects/methods/questions and directed evidence-backed links; known, inferred or hypothesis with falsification notes |
| candidates | Separate catalog-gap/open-world retrieval paths, deduplication key, facets, explanations and uncertainty |
| reviews | Durable explicit keep/skip/later/already-watched/unknown feedback and reasons |
| playlist_annotations | Explicit purpose, relevance, notes and review status; never regenerated from playlist title guesses |
| checkpoints | Atomic page progress, metadata and source import summaries |

Completeness states are `unknown`, `partial`, `complete_for_request`,
`bounded_export` and `unsupported`. A complete owned-playlist metadata request
is not a complete account history. All data derived from an authorized account,
including publicly visible playlists in its inventory, remains private locally.
Concepts/relationships now contain a bounded curated bookshelf map. Candidate
ranking still has schema support only; no calibrated interest strength or
recommendation score is inferred. Bookshelf mappings do not automatically change
public keyword scores.

## Cache and request admission

Private API responses are versioned in private `http.sqlite3`. Public GitHub and
site responses use `.cache/http.sqlite3`, containing public responses only. Existing
public JSON caches remain compatible. Response records include retrieval time,
status, content hash, bounded body and safe headers (ETag, content type and rate
headers). Authorization, cookies, credentials and OAuth endpoint exchanges are
never cached. Takeout inputs are copied to content-addressed private snapshots.

The cache is checked before admission. Completed private inventories are reused
until `--refresh`; unfinished runs resume at the next page. Refresh retains older
responses, metadata title evidence and user annotations. Public caches keep their
existing 7-day API/2-day site freshness windows. Offline commands do not request
credentials or access the network. Reports retain exclusions and partial coverage.

Admission uses SQLite `BEGIN IMMEDIATE` so separate processes sharing a ledger
cannot simultaneously spend the same remaining budget. Reservations precede
requests; failed attempts consume budget conservatively. Cooldowns and counters
survive restarts. No daemon or scheduling is installed.

| Service | Conservative local policy |
| --- | --- |
| YouTube | 1 second spacing, 60 attempts/minute, default 9,000 units/Pacific calendar day; batch default 100 attempts and 100 pages |
| GitHub core | At least 1 second spacing, 60 attempts/hour without auth or 5,000 with auth |
| GitHub search | Additional 6.1 second spacing and 10 attempts/minute, sharing core accounting |
| Public sites | At least 1 second globally, 2 seconds/host; 500 attempts/hour globally, 100/host |

YouTube metadata calls cost one unit each. At most three attempts use bounded
1/2-second backoff for transport/5xx failures; every attempt is admitted and
counted. HTTP 403/429 stops the batch without immediate retry. Retry-After and
GitHub remaining/reset headers persist cooldowns. YouTube quota exhaustion blocks
until Pacific midnight, including daylight saving changes. Public crawling stops
on exhausted budgets instead of swallowing the rate-limit error. Site redirects
also pass admission, remain on allowed GitHub Pages hosts and have bounded depth.
ETags are retained for inspection; conditional revalidation is not yet implemented.

The ledger covers this installation's calls sharing that database. Other tools,
other data directories and other users of the Google project/token can consume
remote quota too; provider responses remain authoritative. Choose a lower
`--daily-units` when sharing a project. Retained response/source history grows with
use; there is no automatic eviction because results were requested to be cached.

## Imports and signal semantics

Watch-history JSON, observed English UTC/GMT history HTML, and CSV video tables
are supported using synthetic versioned fixtures. CSV supports a preceding playlist
metadata table. A collection kind must be selected explicitly; filenames do not
determine engagement semantics. Curated playlist content import requires a prior
reviewed annotation. APIs for video import/catalog expansion are intentionally
not exposed yet.

Time-zone-aware timestamps normalize to UTC. Ambiguous/local dates remain unknown;
missing/deleted IDs remain in the source snapshot and exclusion counts. Same
video/time occurrences reconcile across overlapping history exports; repeated
identical rows within a history export remain distinct. Events with unknown time
cannot be reconciled across different exports reliably. Likes and saved membership
deduplicate by video/collection and never create history events. A per-view title
or channel name is evidence, not proof of current availability or endorsement.

Playback minutes, fractional completion and time to 50% are `not_measurable`.
Missing history means unrecorded in the available export, not never watched.
Archives are not extracted automatically; each selected file is limited to 100 MB.
Unrecognized formats are rejected or reported without guessing; localized HTML
and archive streaming remain future work.

### Selected Chrome bookmarks

`import-bookmarks SOURCE --folder NAME` accepts a local Chrome version 1 Bookmarks
JSON file and requires explicit folder selectors. Names match case-insensitively;
full root/folder paths disambiguate repeated names. Missing, ambiguous and
overlapping selections are rejected before persistence. Nested folders are retained.
Chrome's source file is opened read-only and is bounded to 100 MB. No page is fetched.

The persisted source is a **filtered subset**, containing only selected trees and
whitelisted node fields: type, name, native ID/GUID, URL, date added and date
modified. Unrelated folders, sync metadata, arbitrary node metadata and last-used
values are excluded. Content-addressed snapshots and import summaries remain in
the private store, with local JSON and a searchable, light-background HTML viewer.

Folder identities use Chrome GUIDs where available, with source-local fallbacks.
Web content deduplicates by a conservative normalized URL; query strings and
fragments remain intact. YouTube video URLs share the existing stable video ID.
Each content/folder pair is one `saved` observation, so overlapping collections
retain their memberships without multiplying identical entries in one folder.
Repeated imports add evidence without duplicating those memberships or replacing
manual reviews. Historic memberships remain after moves/deletions; the latest
inventory report describes current membership in the selected snapshot.

Dates convert Chrome's microseconds since 1601-01-01 UTC to UTC timestamps;
invalid/zero dates remain unknown. They are bookmark dates, not publication or
viewing dates. Unsupported URL schemes and URLs containing credentials are
excluded from normalized observations/viewer links and counted in the private
report. Saved interest does not imply visits, course enrollment/completion or
current endorsement. Concept inference and public-page enrichment remain later
work. These additions reuse schema v1 without a migration.

Format/date references: Chromium's [bookmark codec](https://github.com/chromium/chromium/blob/main/components/bookmarks/browser/bookmark_codec.cc)
and [time definitions](https://github.com/chromium/chromium/blob/main/base/time/time.h).

### Bookshelf evidence and bounded hypotheses

`import-bookshelf` reads the user-published Markdown transcription and a versioned
title-level mapping in `data/bookshelf_seeds.json`. It validates all identified
volumes before writing; changed identifications require an explicit map correction.
Exact textual inputs and the existing keyword baseline are cached privately.
The original photograph and book full texts are not inputs to this importer.

The exact provenance is `source=bookshelf_photo_2026_11_02` and
`evidence_type=physical_book_visible`. A `known` relationship means a book was
reported visible in that source, not that its contents were read. Book-to-subject,
method and intellectual-history links are `inferred` title-level interpretations.
Six adjacent research questions use `hypothesis` links, scoped primary references,
entry-point proposals and falsification/correction conditions. Keyword-baseline
links are explicitly distinguished from documented active-project evidence.
The curated expansion is one step deep and capped at ten questions. The importer
performs no network calls; checked reference metadata/summaries are cached, not
the linked articles' full text.

Book counts and repeated foundational subjects create no preference weights.
All per-book reading states and discovery priorities start unspecified. Optional
user-reported aggregate reading feedback is stored separately as private manual
evidence, never assigned to individual books or interpreted as proficiency.
Suggested small examples and prerequisites coexist with advanced material.

The graph uses schema v1 concepts/relationships and ordinary durable manual reviews.
Concepts are also represented as entities so feedback can target books or questions.
Evidence-specific relationships retain source distinctions; unchanged inputs reuse
their model snapshot without duplicating graph evidence. Reviews remain separate
from recomputation. Explicitly skipped questions are ineligible for exploration;
if all supporting books are skipped, that question is ineligible too. This supports
human review, not automatic broad recursive retrieval or calibrated scoring.
Private `interest_graph.json` and `interest_graph.html` expose provenance, source
limitations, proposed connections and feedback. Public exports never read them.

Explicit `set-interest-scope` corrections are separate private manual evidence.
`require` mode suppresses a topic contribution without its application context;
`prefer` mode keeps general matches eligible as exploratory additions. Both
override inferred breadth, survive imports and retain user-reported project status
without treating project activity as a fixed preference. The effective private
profile is written to `interest_profile.json`; the public baseline stays intact.
Private scoring exposes primary/exploratory point contributions separately and
flags keyword context as triage requiring semantic review. A small exploratory
allowance is selection guidance; actual batch quotas and calibrated rankings are
still future work. Explicit skips continue to override exploratory eligibility.

## Migration and rollback

An empty store migrates from v0 to v1 in a single transaction. Reopening v1 is
idempotent; newer versions and unversioned nonempty databases are refused. This
milestone changes no existing public data schema or records. Before a future
migration, close import processes and back up the entire private directory (or
use SQLite's backup API). Restore that backup with its matching code version to
roll back. Do not delete the quota ledger to bypass cooldowns; retain it across
code rollbacks. No downgrade or destructive migration is performed automatically.

See [setup](youtube_setup.md) and [implementation status](implementation_status.md).
