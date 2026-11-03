# Major technologies

This project combines a Python command-line application, local SQLite databases,
browser-based reports and GitHub Pages hosting. The core application uses the
Python standard library; live YouTube authentication adds optional dependencies.

## At a glance

| Technology | Role in this project | Required when |
| --- | --- | --- |
| Python 3.11+ | Commands, imports, discovery, validation and report generation | Running the application |
| SQLite | Private evidence, concepts, reviews, checkpoints and HTTP request accounting | Private research and cached network work |
| HTML, CSS and JavaScript | Searchable reports and the interactive creator dashboard | Browsing reports |
| GitHub REST API | Public repository discovery and account metadata | Live GitHub discovery |
| YouTube Data API v3 | Authorized playlist inventory, selected Likes and public channel/video metadata | Live YouTube research |
| OAuth 2.0 and Google authentication libraries | Read-only account authorization and authenticated requests | Connecting a YouTube account |
| JSON, CSV and Markdown | Structured inputs, source snapshots, exports and research documentation | Data exchange and reporting |
| Git, GitHub Actions and GitHub Pages | Version control, automated checks and public static hosting | Collaboration and publication |

## Python and the command-line application

Two entry points keep public catalog work and private research distinct:

```bash
python3 -m pagefinder --help
python3 -m pagefinder.local --help
```

The public commands discover sites, enrich records and generate the catalog.
The private commands import selected sources, maintain evidence and reviews,
and serve the creator dashboard. Both use `argparse` for command-line options.

Standard-library modules handle most work: `urllib` makes public HTTP requests,
`urllib.robotparser` interprets robots rules, `html.parser` extracts bounded HTML
content, and `json`, `csv` and `datetime` handle formats and timestamps. `pathlib`
and `tempfile` support file handling and atomic private writes.

Code: [public discovery](pagefinder/core.py), [public commands](pagefinder/__main__.py)
and [private commands](pagefinder/local.py).

## SQLite, evidence and caching

The private `research.sqlite3` database stores entities, source evidence,
observations, concepts, relationships, candidates, review decisions and import
checkpoints. It uses foreign keys, transactions and a schema version so imports
and feedback can remain consistent across runs. The concept graph is represented
by ordinary database tables and exported reports.

Separate `http.sqlite3` databases retain response versions, request reservations
and cooldowns. Public responses live under the repository's ignored `.cache/`
directory; account-derived responses stay in private storage. SQLite transactions
coordinate request budgets between processes sharing the same ledger.

SHA-256 hashes identify source snapshots and support stable IDs and deduplication.
They provide content identity, not encryption. Private directories and files use
restricted filesystem permissions, and private storage paths inside Git working
trees are rejected.

Code: [evidence store](pagefinder/research.py), [network cache and budgets](pagefinder/net.py)
and [private file handling](pagefinder/privacy.py).

## Browser reports and the local review server

Python generates HTML reports with CSS and JavaScript. The browser interface uses
native controls, DOM filtering, expandable `<details>` sections and JSON downloads.
The creator dashboard uses `fetch` to save decisions and notes to the local server;
offline previews can export feedback for later import.

The review server uses Python's `http.server` and binds to `127.0.0.1`. It exposes
fixed dashboard, report and review routes, with Host/Origin checks and a per-process
review token. It loads no third-party assets. The dashboard is also usable from a
Windows browser when the server runs in WSL2 with working localhost forwarding.

Code: [creator reports](pagefinder/creators.py), [server](pagefinder/creator_server.py),
[JavaScript](pagefinder/creator_review.js) and [CSS](pagefinder/creator_review.css).

## GitHub and YouTube integrations

Official references:

- [GitHub REST API reference](https://docs.github.com/en/rest).
- [YouTube Data API reference](https://developers.google.com/youtube/data/reference/rest).
- [Google OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app).

The public GitHub client calls the REST API for bounded repository searches and
metadata. It reads GitHub account type from API data. Authentication can come from
`GH_TOKEN`, `GITHUB_TOKEN` or an existing GitHub CLI (`gh`) login. GitHub CLI is
optional; the application also supports unauthenticated requests and offline cache
reuse. Site enrichment separately retrieves bounded HTML from allowed GitHub Pages
hosts and checks robots rules.

The YouTube client calls selected Data API v3 endpoints for playlist inventory,
explicitly selected Likes or reviewed-positive playlists, and channel/video
metadata. Authorization requests the single `youtube.readonly` scope through a
Desktop OAuth flow with a temporary loopback callback and PKCE. Tokens and Desktop
client configuration stay outside Git.

The optional packages in [requirements-youtube.txt](requirements-youtube.txt) are:

- `google-auth` for credentials and authenticated sessions.
- `google-auth-oauthlib` for the Desktop authorization flow.
- `requests` for the HTTP transport used by Google's authenticated session.

Offline imports, reports and the test suite work without these packages. Setup
instructions are in [YouTube setup](docs/youtube_setup.md). The research experiments
also used GitHub connector tools and web research to collect evidence; imported
manifests retain those sources, while the application does not require those tools
to browse or review saved results.

Code: [YouTube client and authentication](pagefinder/youtube.py),
[bounded creator sources](pagefinder/creator_sources.py) and
[research manifest imports](pagefinder/creators.py).

## Formats and recommendation methods

JSON carries configuration, selected Chrome bookmarks, API responses, source
snapshots and feedback. CSV supports tabular imports and spreadsheet exports.
Selected Google Takeout JSON, HTML and CSV inputs are parsed locally. Markdown
holds research plans, implementation notes and reports.

The public catalog ranks records using explainable weighted keyword matches.
Private profile comparisons add curated interests and explicit context corrections.
Creator recommendations come from assessed research manifests with source-linked
concepts, affiliation evidence and separate quality facets. The application has no
runtime language-model, embedding or vector-database dependency; scoring remains
an uncalibrated aid to human review.

Code: [keyword scoring](pagefinder/core.py), [private interests](pagefinder/interests.py),
[Takeout imports](pagefinder/takeout.py) and [bookmark imports](pagefinder/bookmarks.py).

## Testing and public deployment

The automated suite uses standard-library `unittest`, temporary databases,
synthetic source fixtures, mocked transports and local HTTP checks. Chromium with
Playwright was used separately to inspect the creator dashboard and feedback
workflow; it is not required for normal operation or the unit-test suite.

[GitHub Actions tests](.github/workflows/test.yml) run the suite, regenerate the
public catalog, check publication boundaries and ensure checked-in outputs match.
The [Pages workflow](.github/workflows/pages.yml) validates and uploads only `docs/`
to GitHub Pages. The published site is static; private dashboards and databases
stay on the local machine.

```bash
python3 -m unittest discover -s tests -v
python3 -m pagefinder report
python3 -m pagefinder.publication
```

For deeper design details, see [architecture](docs/architecture.md). For completed
work and limitations, see [implementation status](docs/implementation_status.md).
