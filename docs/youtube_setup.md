# Local YouTube setup and playlist review

The importer is ready for offline use. Google sign-in and a real inventory have
not run. Keep credentials, downloads and every generated personal report outside Git.

## 1. Prepare a read-only Desktop client

In [Google Cloud Console](https://console.cloud.google.com/), select/create a
project, enable YouTube Data API v3, configure the OAuth consent screen, and add
your Google account as a test user if the app is in Testing. Create an OAuth client
with application type **Desktop app**. Download its JSON file and save it locally as:

`~/.config/github-pages-discovery/youtube/client_secret.json`

Do not paste its contents or tokens into chat. A web-application client or API key
does not replace the Desktop client. The only requested scope is
`https://www.googleapis.com/auth/youtube.readonly`.

Install optional authentication dependencies in WSL:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-youtube.txt
.venv/bin/python -m pagefinder.local init
.venv/bin/python -m pagefinder.local auth
```

The OAuth browser must open on your PC. Under WSL2, configure Python's `BROWSER`
to use Windows Chrome if the system default does not launch it. For the standard
Chrome installation location, this is an example command (adjust if necessary):

```bash
BROWSER='"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" %s' \
  .venv/bin/python -m pagefinder.local auth --port 8765
```

The callback listener binds only to `127.0.0.1`, uses PKCE/state verification and
times out after 180 seconds. Windows-to-WSL localhost forwarding must work. If
Chrome shows a localhost connection failure, check WSL localhost forwarding and
firewall settings, then rerun. Do not change the bind address to a public interface
or paste callback codes. The authorization URL is opened in the browser and is
not printed to the terminal. The Google approval screen is required. Testing-mode
refresh tokens can expire; rerun `auth` when necessary. Select the intended YouTube
channel/account, and use a separate `--data-dir` for a different owner.

## 2. Fetch metadata only, then review purposes

```bash
.venv/bin/python -m pagefinder.local inventory --max-requests 100 --max-pages 100
```

This requests `playlists.list(mine=true, part=snippet,contentDetails,status)` in
pages of up to 50. It records accessible owned private, unlisted and public
playlists: ID, title, description, privacy and item count. No video membership,
Likes, history or Watch Later API imports run. A partial batch saves progress;
rerun the same command to resume. This API path does not include playlists you
merely saved from other creators or serve as a full account-content inventory.

Open `~/.local/share/github-pages-discovery/playlist_inventory.html` locally in
Chrome. It is a light-background offline table with filtering and no external
assets/network requests. JSON and spreadsheet-safe CSV reports accompany it.
Set each playlist's purpose and relevance, add notes, and mark it reviewed. A
favorites/reference collection can support a positive signal; an inbox or queue
is intent rather than endorsement or proof of watching. No labels are guessed.

Click **Download annotations**, save the JSON outside the repository, and apply it:

```bash
.venv/bin/python -m pagefinder.local annotate ~/Downloads/playlist_annotations.json
```

WSL can read a Windows download through its mounted location; pass that actual
path locally if applicable. Page edits are not durable until downloaded and
applied. Applying annotations preserves them across refreshes. Stop here for
interpretation and selection before a bulk content import.

## 3. Reuse caches and inspect coverage

```bash
.venv/bin/python -m pagefinder.local inventory --offline
.venv/bin/python -m pagefinder.local coverage
# Only when a new snapshot is wanted:
.venv/bin/python -m pagefinder.local inventory --refresh --max-requests 20
```

Complete inventories reuse their stored snapshot without requests. Incomplete
inventories resume; required uncached pages fail safely in offline mode. Refresh
keeps old responses and annotations. Do not repeat `--refresh` when resuming an
interrupted refresh: omit it so the active checkpoint is used. Rate-limit errors
save cooldowns; wait until the reported retry time rather than deleting state.
`--daily-units` defaults to 9,000 and can be lowered for a shared project. The
private inventory JSON includes invocation attempts/cache hits and cumulative
reserved quota units. These count this tool's attempts, not all project usage.

## 4. Optional selected Takeout source

Use [Google Takeout](https://takeout.google.com/) to export YouTube history and
the collections available for your account. Extract the selected JSON/HTML/CSV
files outside Git yourself. Then explicitly choose the source kind:

```bash
.venv/bin/python -m pagefinder.local import-takeout ~/Downloads/watch-history.json --kind history
.venv/bin/python -m pagefinder.local import-takeout ~/Downloads/liked-videos.csv --kind likes
.venv/bin/python -m pagefinder.local import-takeout ~/Downloads/watch-later.csv --kind watch_later
```

Curated playlist CSVs additionally require `--kind playlist --playlist-id <id>`
and a previously reviewed purpose for that ID. Imports cache the exact source,
deduplicate observations on rerun, and write private completeness/exclusion
reports under `imports/`. Unsupported/missing timestamps and deleted videos
are reported, never filled with invented data. No source export is assumed to
cover all viewing. Prefer JSON with explicit time-zone offsets; localized or
ambiguous HTML dates may remain unknown. No viewing progress is inferred.

## Official constraints checked 2026-11-02

- [Owned playlists and pagination](https://developers.google.com/youtube/data/reference/rest/v3/playlists/list): authorized `mine` selects the owner's playlists.
- [Desktop OAuth](https://developers.google.com/youtube/data/guides/auth/installed-apps): browser consent and a loopback callback; no password collection.
- [Likes](https://developers.google.com/youtube/data/reference/rest/v3/videos/list): the separate `myRating=like` result is capped at the most recent 1,000 even if totals are higher. This API importer is deferred.
- [History and Watch Later](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list): API access to their items is unsupported; use available Takeout sources.
- [Channel uploads](https://developers.google.com/youtube/data/reference/rest/v3/channels/list): a later pilot will use contentDetails uploads playlist IDs, then playlistItems, avoiding broad search. This covers currently accessible listings.
- [Quota costs](https://developers.google.com/youtube/v3/determine_quota_cost): list methods used here cost one unit; invalid requests also consume quota.

Run `python3 -m pagefinder.local --help` for private commands; the original
`python3 -m pagefinder report` still produces only the public site catalog.
