# Private Learning Queue

The Learning Queue answers “What should I read, watch or try next?” using specific
works from the local arXiv Shelf catalog and the existing private Discovery research.
It runs locally with Python 3.15 (recommended) or 3.14 and the standard library.
Follow the [Python setup guide](../docs/python_setup.md) and check that
`python3 --version` reports one of these releases before running commands.

## Launch from WSL2

From the Discovery repository, run:

```bash
python3 -m pagefinder.local serve-learning --port 8767
```

Open **http://127.0.0.1:8767/** in Windows Chrome. Keep the terminal running;
Ctrl+C stops the service. The default ports remain distinct: Shelf 8765, creator
review 8766, Learning Queue 8767. The Learning Queue also serves the existing
creator cards through **Explore creators**, with their original review endpoint.

Enter a subject or question and press Enter. Goal, time and format are optional.
The shortlist contains up to five supported works; narrow queries can return fewer.
No supported match produces an informative empty state. Time controls express a
session budget, not a promise that a full work fits it. Known video durations come
from metadata; unknown durations and reading times remain unknown.

## Local sources and refresh

The default read-only Shelf working tree is `~/git/arxiv-shelf`. To choose another:

```bash
python3 -m pagefinder.local serve-learning --port 8767 --arxiv-dir /path/to/arxiv-shelf
```

The explicit path is remembered privately. `ARXIV_SHELF_DIR` can override the
remembered path; an explicit command-line path takes precedence over both.
The adapter reads `catalog/*.json`, not `dist/catalog.json`. It mirrors Shelf's
schema-1 event ordering, aliases, metadata merging and rating-clear semantics.
Identifiers retain their versions; multiple versions of one paper are grouped
when selecting a shortlist. Unresolved identifiers are counted and not assigned
invented arXiv links. Star ratings are read-only and never imply completion.

PDF availability is checked separately using Shelf's local cache and an existing
contained file with a PDF header. Unverified means unknown, not necessarily absent.
No local PDF paths or filenames are returned to the browser. Open uses stable
arXiv links and does not bypass Shelf's protected PDF routes.

Discovery contributes the complete current creator collection's specific works,
metadata, source-linked concepts and existing creator feedback, plus earlier
project probes with retained README excerpts. Selected imported
bookmarks remain lower-confidence encounter evidence. Concept links are attached
to cited projects rather than copied indiscriminately across a creator's work.

Startup and **Refresh local sources** read local data only. Missing or malformed
sources leave their last successful cached partition searchable and display a
warning. Successful refreshes update source membership without deleting old
feedback. Sources and freshness are visible in the interface.

## Feedback and retrieval

Save for later, already read/watched, and usefulness are independent dimensions.
Notes persist in private SQLite. Completed and dismissed works are suppressed in
the Discover view; their saved/history views remain available, with reversible
controls. Saved/history views show up to 30 matching works; the question field
filters the selected view so older saved items remain findable. Queue feedback
changes neither creator reviews nor Shelf star ratings.
Opening a resource does not create a reading, viewing or completion event.

Retrieval uses work titles, abstracts/descriptions, documented concepts and
source-linked method bridges. Specific query anchors reject unrelated matches
that share only a generic word. Internal heuristic weights balance topical fit,
evidence, session effort and modest source diversity. Expand a card for separate
fit, method, explanatory, novelty, evidence and effort assessments. No calibrated
precision score or automatic personal-novelty claim is shown.

## Additional research

The first implementation includes a private assessed sample of **18 works**:
five specific videos, six code resources, three technical articles and four
collected papers. Official video metadata, documentation, selected implementation
excerpts and selected paper sections were independently revisited. Five real
queries were audited across rendering, numerical fluids, game search, audio and
mathematical physics. These are topical system checks; human usefulness has not
been measured. Full videos were not watched and candidate code was not executed.

Research accounting: one YouTube metadata request for five videos; eleven logical
GitHub connector calls including one unsuccessful branch guess; four web-tool
calls containing eighteen opens/clicks, including a failed rendering path later
resolved through an official full-text page. Provider-internal HTTP counts are
unavailable. There is no automatic background crawl, paid service or new OAuth scope.

The actual resources, citations, example results, limitations and raw evidence
remain private. Use **Research notes** in the application for the detailed report.
Future bounded research can be imported explicitly:

```bash
python3 -m pagefinder.local import-learning-research /path/outside/git/assessed-works.json
```

The version-1 manifest accepts 1–30 assessed works with safe source URLs,
timezone-aware verification dates, learning value, inspection scope and limitations.
Imports retain content-addressed snapshots. An index-only refresh is also available:

```bash
python3 -m pagefinder.local refresh-learning
```

## Storage, checks and troubleshooting

The index and independent feedback use additive `learning_works` and
`learning_feedback` tables in the existing private research database. Feature tables
reuse shared entities/evidence and leave existing reviews intact. They do not
replace the database or alter Shelf's files, sync settings or publication policy.
New entities and reports remain private; public catalog generation never reads them.

The loopback server shares creator-server Host/Origin checks, per-process request
tokens, bounded JSON bodies, no-store responses and fixed routes. It serves no
arbitrary files and loads no external assets. Startup and storage diagnostics use
the existing private CLI. If port 8767 is occupied, choose `--port 8768` and open
that address. If Windows cannot connect, keep the WSL terminal running and check
localhost forwarding. Source-read failures are shown without exposing local paths.

Tests cover catalog aliases, ratings, versions, idempotence, cached fallback,
query specificity, concept citations, feedback persistence, source boundaries and
HTTP protections. Browser verification uses real sources for browsing and a
separate synthetic database for changed decisions, so test feedback never becomes
an apparent user evaluation. Desktop, narrow layouts and Windows-to-WSL access
are checked separately.
