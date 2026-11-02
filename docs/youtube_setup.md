# First-time Google Cloud setup for the local YouTube inventory

This walkthrough assumes you have never used Google Cloud. You will create a
Google project, register this local program, approve read-only access to your
YouTube account, and open a private playlist inventory. **Stop after reviewing
playlist purposes; this does not start a bulk video import.**

Use **Windows Chrome** for website steps and your **WSL terminal** for command
blocks. Paste commands without adding a `$` prompt. Google sometimes moves buttons;
the navigation below follows its current Google Auth Platform documentation,
checked 2026-11-02. Alternate older labels are noted where useful.

## Before you start: what the unfamiliar words mean

| Term | Meaning here |
| --- | --- |
| Google Cloud Console | Google's website for configuring programs that use its services. |
| Project | A named container for this program's API settings and request allowance. |
| API | The supported interface the Python program uses to ask YouTube for data. |
| OAuth | Google's approval process: sign in on Google's page and authorize specified access. |
| Consent screen | The page explaining what the program wants permission to read. |
| Scope | A particular permission. We request only `youtube.readonly`. |
| Desktop client | Google's registration for a program running on your computer. |
| Client JSON | A downloaded configuration file identifying that registration. |
| Token | A separate file Google creates after approval, allowing subsequent requests. |

Google Cloud holds the registration; the research database and reports stay on
your PC. This walkthrough creates no cloud server, storage bucket or deployed
website. You do not need Cloud Shell or the `gcloud` command-line tool.

There are two private locations. In WSL, `~` means your Linux home directory:

| Location | Contents |
| --- | --- |
| `~/.config/github-pages-discovery/youtube/` | Client configuration and authorization token |
| `~/.local/share/github-pages-discovery/` | Database, cached responses, source snapshots and reports |

Neither belongs inside this repository. Do not paste client-file contents or
tokens into chat, or upload them to GitHub. You enter your Google password only
on Google's sign-in page; the Python program does not ask for it.

## 1. Sign in and create the Google Cloud project

1. In Windows Chrome, open the [Google Cloud Console](https://console.cloud.google.com/).
2. Sign in. For the simplest setup, use the Google account whose YouTube playlists
   you want to examine. Check the account picture at the top right if you have
   several accounts open.
3. If this is your first visit, complete any required country/terms welcome form
   after reading it. A **Start free** trial banner is separate from project setup;
   skip that banner for this walkthrough. These instructions do not ask you to
   activate billing. If you cannot proceed without a payment form, record which
   page you reached before deciding how to proceed.
4. Near the top left, find the project selector beside the Google Cloud logo. It
   may say **Select a project** or show an existing project name. Click it, then
   **New Project**. You can also open [New Project](https://console.cloud.google.com/projectcreate).
5. For **Project name**, enter `Pages Discovery Local`. Accept the generated
   **Project ID**; it need not exactly match that name. If offered a location,
   choose **No organization** for a personal account. Managed work/school accounts
   may impose different choices.
6. Click **Create**, wait for completion, and select the new project using the
   project selector. Creating it does not always switch the active project.

**Checkpoint:** The top project selector shows `Pages Discovery Local`. Check it
again when opening later links: all settings must belong to this same project.
[Google's project creation instructions](https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects)
explain the name, ID and organization fields.

## 2. Enable YouTube Data API v3

1. Open the navigation menu, usually the three horizontal lines at the top left.
   Choose **APIs & Services → Library**. Alternatively open the
   [API Library](https://console.cloud.google.com/apis/library).
2. Search for `YouTube Data API v3`.
3. Open that exact result and click **Enable**. If it already says **Manage**, it
   is enabled. You may have to wait briefly before the management page appears.
4. Keep this project selected. Ignore suggestions for unrelated APIs or services.

Enabling an API makes it available to this project; it does not yet authorize
access to your private playlists. That approval comes later. This is the enable
step in [Google's YouTube setup instructions](https://developers.google.com/youtube/data/getting-started).

**Checkpoint:** Under **APIs & Services → Enabled APIs & services**, you can find
`YouTube Data API v3`.

## 3. Set up the Google Auth Platform

Open [Google Auth Platform](https://console.cloud.google.com/auth/overview).
You can also find it through the navigation menu. Older instructions call the
entry point **APIs & Services → OAuth consent screen**.

If the platform is not configured, click **Get started**. Fill the initial wizard
using these choices:

| Field or page | Value to use |
| --- | --- |
| App name | `Personal Discovery Research` |
| User support email | Your own Google email from the dropdown |
| Audience | **External** |
| Contact information | Your own email address |
| Finish | Read the policy, agree if acceptable, and complete creation |

Use **Next** between pages, then **Create** or the final completion button. These
fields register the program; you are not setting up a company or customer service.
The support/contact address can be the same address you already use.

**External** means the app can work with a Google account outside a managed
organization. It does not mean your playlists become public. Personal accounts
normally use this option. **Internal** is intended for an organization's users.

If setup already exists, use the **Branding**, **Audience** and **Data Access**
pages to check it instead of creating a second project.
[Google's Auth Platform introduction](https://support.google.com/cloud/answer/15544987)
describes these sections.

**Checkpoint:** The Auth Platform navigation includes Branding, Audience, Clients
and Data Access. You are no longer at the unconfigured welcome page.

## 4. Add yourself as a test user and declare read-only access

### Audience: who may approve the app

Open **Audience**. Keep the publishing status at **Testing** for this initial
personal setup. Under **Test users**, click **Add users**, enter the exact Google
email address you will use for authorization, and click **Save**.

Being the project owner does not replace adding yourself as a test user. If you
sign in to YouTube with another Google account, add that account too. For a Brand
Account, the test user is the Google account managing it.

Testing is sufficient for the first inventory; you do not need to publish the app
to the public. For this YouTube permission, testing authorizations and refresh
tokens expire after seven days, so a later request may require another sign-in.
[Google's audience documentation](https://support.google.com/cloud/answer/15549945)
explains testing access and expiration.

### Data Access: what the app may read

Open **Data Access**, then **Add or remove scopes**. Find/select this exact scope:

```text
https://www.googleapis.com/auth/youtube.readonly
```

It may be described as **View your YouTube account**. If the list is long, filter
for `youtube.readonly`; if there is a manual-entry box, paste the full address
above. Apply the selection with **Update**, then **Save** if that button appears.
Avoid similarly named permissions that allow managing, editing or deleting data.

The address above names a permission; you do not open it as a website. The program
requests that same permission during sign-in.
[Google's consent/scopes guide](https://developers.google.com/workspace/guides/configure-oauth-consent)
describes the Data Access controls.

**Checkpoint:** Your email appears among test users, and Data Access lists the
YouTube read-only permission. Leave the app in Testing.

## 5. Create and download the Desktop client

1. Still in Google Auth Platform, open **Clients**, then **Create client**. Direct
   link: [Clients](https://console.cloud.google.com/auth/clients). Older console
   layouts use **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Choose **Desktop app** as the application type. Even though approval happens
   in Chrome, the Python program is a desktop client, not a Chrome extension.
3. Give the client a recognizable name, such as `WSL Personal Discovery`.
4. Click **Create**. In the creation dialog/details, choose **Download JSON** and
   save the file. Download it before closing the dialog; Google limits later
   access to newly created client secrets.
5. In Chrome, press **Ctrl+J** to open Downloads, then **Show in folder** for this
   download. Leave that File Explorer window open for the next step.

The filename will be long, often beginning with `client_secret_` and ending in
`.json`. Do not copy individual client ID/secret fields into the source code.
The program reads the downloaded file.

Desktop clients do not require manually entered JavaScript origins or redirect
URLs. If those fields appear, check that you chose Desktop app. An API key or
service account is a different credential and does not fit these instructions.
[Google's client management instructions](https://support.google.com/cloud/answer/15549257)
cover creation and application types.

**Checkpoint:** You have downloaded one Desktop-client JSON file to your PC.

## 6. Put the downloaded file in the private WSL folder

In your **WSL terminal**, run:

```bash
mkdir -p ~/.config/github-pages-discovery/youtube
cd ~/.config/github-pages-discovery/youtube
explorer.exe .
```

The last command opens the current Linux folder in Windows File Explorer. The
period is required. This is Microsoft's documented
[WSL-to-File-Explorer method](https://learn.microsoft.com/en-us/windows/wsl/filesystems#view-your-current-directory-in-windows-file-explorer).

You now have two Explorer windows: the Windows Downloads folder from step 5 and
the destination WSL folder. Copy the downloaded JSON from the first to the second.
Rename the destination file **exactly** `client_secret.json`. In Explorer, turn on
**View → Show → File name extensions** if necessary; avoid accidentally naming
it `client_secret.json.json`.

Back in WSL, check the filename and restrict its permissions:

```bash
ls -l ~/.config/github-pages-discovery/youtube/client_secret.json
chmod 700 ~/.config/github-pages-discovery/youtube
chmod 600 ~/.config/github-pages-discovery/youtube/client_secret.json
cd ~/git/github-pages-discovery
```

`ls` displays the file's name and attributes, not its contents. If it says **No
such file or directory**, fix the copy/name before continuing. Keep these files
out of the project folder, even though credential filenames are also gitignored.

**Checkpoint:** The exact file exists in the private configuration folder, and
your terminal has returned to this repository.

## 7. Prepare the Python environment in WSL

From the repository directory, run these commands one at a time:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-youtube.txt
.venv/bin/python -m pagefinder.local init
```

The first creates a local Python environment. The second installs Google's
authentication libraries and their dependencies into it. The third creates the
private research database. Using `.venv/bin/python` explicitly avoids needing to
learn environment activation commands.

If the first command says `ensurepip` or `venv` is unavailable on Ubuntu, install
the missing package, then repeat the commands:

```bash
sudo apt update
sudo apt install python3-venv
```

`sudo` may ask for your **Linux** password; typing it normally shows no characters.
This is unrelated to your Google password. If Ubuntu names a version-specific
venv package in its error, use that package name instead.

**Checkpoint:** `init` reports a private SQLite location outside Git. Installing
libraries and initializing storage do not fetch your playlists.

## 8. Authorize the program in Windows Chrome

Keep Chrome open and run this in WSL:

```bash
BROWSER='"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" %s' \
  .venv/bin/python -m pagefinder.local auth --port 8765
```

Paste both lines together, including the backslash. This selects the common
Windows Chrome installation location for this command. `%s` tells the browser
launcher where to put Google's authorization address. If Chrome is installed
elsewhere, use its actual executable path; see troubleshooting below.

Leave the terminal running while completing the browser steps:

1. Choose the Google account you added as a test user. Complete Google's normal
   sign-in if asked.
2. If offered YouTube channel/account choices, select the one owning the desired
   playlists. One Google login can manage multiple YouTube identities.
3. A testing/unverified-app warning may appear. For the app you just registered,
   inspect the project/developer information and continue using the offered test
   access or **Advanced → Go to…** option if present. Do not use these instructions
   to approve an unfamiliar app. Workspace/Advanced Protection policies may block
   approval instead of offering a continuation.
4. Review the permission: it should allow viewing your YouTube account, without
   editing/deleting access. Select its checkbox if shown, then **Continue/Allow**.
5. The browser returns to an address beginning `http://127.0.0.1:8765/` and shows
   **Authorization received. Close this tab and return to the terminal.**

`127.0.0.1` means your own computer. A temporary listener in WSL receives Google's
response; it is not a public website. The listener closes after authorization.
The command waits up to 180 seconds. If it times out, rerun it and complete the
browser steps again. This is Google's
[Desktop loopback authorization flow](https://developers.google.com/youtube/data/guides/auth/installed-apps).

**Checkpoint:** The terminal says **Read-only authorization saved outside Git.**
The separate `token.json` now exists beside `client_secret.json`; do not display
or share either file. No playlist request has run yet.

## 9. Fetch the playlist inventory and open it locally

Run:

```bash
.venv/bin/python -m pagefinder.local inventory --max-requests 100 --max-pages 100
```

This fetches names, IDs, descriptions, privacy and item counts for accessible
playlists **owned by the selected YouTube channel**, including private/unlisted
ones. It does not enumerate playlists merely saved from other creators. It does
not fetch thousands of video memberships, Likes, history or Watch Later items.

Google returns up to 50 playlists per page. A playlist with 12,000 videos still
contributes only its metadata/count here. If the terminal reports a partial
inventory, repeat the same command to resume its checkpoint. A rate-limit stop
will report when to retry; wait rather than deleting the cache.

To find the report in Windows:

```bash
cd ~/.local/share/github-pages-discovery
explorer.exe .
cd ~/git/github-pages-discovery
```

In the Explorer window, double-click `playlist_inventory.html`. The page runs
locally, with no remote assets. Its neighboring JSON/CSV files contain the same
private inventory in other useful formats. Do not copy them into `docs/`.

**Checkpoint:** You see playlist names/counts and whether this request completed.
If the list is empty or unfamiliar, check the YouTube identity chosen in step 8.
For another owner, use a separate private `--data-dir`; do not mix account data.

## 10. Annotate purposes, save them, and stop for review

Use the local table's filter to find playlists. For each one, choose a **Purpose**
and **Relevance**, add notes if useful, and tick **Reviewed**:

| Purpose | Example interpretation |
| --- | --- |
| favorites | Videos deliberately kept because you liked them |
| reference | Material kept for useful explanations or techniques |
| inbox / queue | Things collected to consider or watch later |
| archive | A historical collection whose present relevance may vary |
| other | Explain the purpose in Notes |
| unknown | Leave unreviewed until you can interpret it |

Relevance is your choice of positive, neutral, negative or unknown as an interest
signal. A queue can contain speculative choices; saving something is not proof
you watched it. Notes can explain mixed-purpose playlists.

Click **Download annotations**. Browser edits are not durable until downloaded
and applied. Find `playlist_annotations.json` through Chrome Downloads, and copy
it into the private research folder opened in step 9. Then apply it from WSL:

```bash
.venv/bin/python -m pagefinder.local annotate ~/.local/share/github-pages-discovery/playlist_annotations.json
```

The command reports the number applied and regenerates the local report. Reload
the HTML page to confirm the labels persisted. If Chrome added `(1)` to the
download name, rename it or use that exact filename in the command.

**This is the first milestone.** Review which collections actually express your
interests before choosing any playlist contents to import. No screenshots of huge
playlists are needed. Keep private titles/annotations local unless you explicitly
want to discuss particular examples.

## Later: cache reuse, refresh and optional Takeout

These commands are available after the first inventory:

```bash
.venv/bin/python -m pagefinder.local inventory --offline
.venv/bin/python -m pagefinder.local coverage
.venv/bin/python -m pagefinder.local inventory --refresh --max-requests 20
```

`--offline` reads the stored inventory without contacting Google. Completed
inventories otherwise reuse their snapshot too. Use `--refresh` when you want
updated metadata; it keeps previous responses and your annotations. To resume an
interrupted refresh, omit `--refresh` so it continues the active checkpoint.

Request budgets persist across runs. Default YouTube admission is 9,000 units per
Pacific calendar day, with smaller per-run limits. A metadata page costs one unit;
the provider's default allowance for these endpoints is 10,000 units daily.
These units measure requests, not dollars. Other tools using your project can
consume its allowance too. See [Google's quota documentation](https://developers.google.com/youtube/data/determine_quota_cost).

History and Watch Later items are unavailable through the Data API. A later step
can use selected exports from [Google Takeout](https://takeout.google.com/).
Extract exports outside Git and explicitly choose their kind, for example:

```bash
.venv/bin/python -m pagefinder.local import-takeout ~/Downloads/watch-history.json --kind history
```

That path refers to **WSL** Downloads; a Windows download must first be copied
there or to another private WSL location. Likes and Watch Later use `--kind likes`
and `--kind watch_later`. Curated playlist imports need a reviewed playlist ID.
Imports preserve source snapshots, count unrecognized rows and report incomplete
coverage. They never infer playback minutes or viewing completion from timestamps.
The separate Likes API, not implemented here, returns at most the recent 1,000
items; [Google documents that cap](https://developers.google.com/youtube/data/reference/rest/v3/videos/list).

## Troubleshooting by the symptom you see

| Symptom | What to check next |
| --- | --- |
| Cannot find Google Auth Platform | Use the direct Auth overview link in step 3; older navigation says OAuth consent screen. |
| `access_denied` / app is testing | In Audience, add the exact account currently signing in as a test user; save and retry. |
| API disabled / `accessNotConfigured` | Enable YouTube Data API v3 in the project that owns your downloaded client, then retry after a brief wait. |
| `Desktop client_secret.json is missing` | Repeat step 6's `ls`; check folder and `.json.json` mistakes. |
| `OAuth client must be a Desktop application` | Create/download the Desktop app client, rather than using a web-client or API-key file. |
| Chrome never opens | Check the executable path below; Linux's default browser may differ from Windows Chrome. |
| Chrome shows localhost connection refused | Keep the WSL auth command running and retry before its timeout. If it still fails, Windows-to-WSL localhost forwarding needs diagnosis. Do not expose the listener publicly. |
| Authorization worked last week, now fails | Testing grants expire after seven days. Rerun step 8, then retry the inventory; the existing cache remains. |
| Partial inventory / request budget reached | Rerun the inventory without `--refresh`; for a cooldown, wait until its reported time. |

To check the common Chrome location without launching authorization:

```bash
ls -l '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
```

If missing, try `Program Files (x86)` in that path, or inspect your Chrome
shortcut's executable location and use its WSL equivalent in `BROWSER`. For
forwarding problems, Microsoft's [WSL networking guide](https://learn.microsoft.com/en-us/windows/wsl/networking)
explains localhost behavior. Share the step number and error wording if you need
help; omit account identifiers, configuration contents and authorization URLs.

See [architecture](architecture.md) for storage details and
[implementation status](implementation_status.md) for what has actually been tested.
