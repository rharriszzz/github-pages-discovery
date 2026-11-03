# Expanded creator discovery — 2026-11-03

This extends the [original pilot](creator-pilot.md), whose results remain intact.
All creator identities, personalized explanations, account-derived sources,
feedback, raw evidence and screenshots remain in private local storage. This
report contains methodology, aggregate outcomes and software validation only.

## Frame, inspection depth and results

| Direction | New screens | Multi-work cards | Verified cross-platform affiliation | Probable affiliation | Single-platform comparisons | Verified operator/software intersections |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| YouTube first | 150 | 22 | 17 | 1 | 4 | 16 |
| GitHub first | 51 | 18 | 13 | 0 | 5 | 11 |
| Expanded round | 201 | 40 | 30 | 1 | 9 | 27 |

The complete dashboard contains **52 cards**, including the original twelve,
and 259 investigation records including the original 58. “New” means newly
researched, not previously unfamiliar. The GitHub frame includes individual and
collective accounts; it is not a count of distinct people. Verified affiliation
includes two guest-presenter cases and one teaching-materials case, so it does
not imply that every match is a channel operator publishing software.

Screening is deliberately cheaper than recommendation assessment. Of the new
records, 128 remain at channel/collection metadata screening, 26 at repository
screening, seven at account metadata screening, and 40 have multi-work cards.
The 170 records without an established cross-platform match include nine useful
single-platform comparisons; they are not 170 thorough identity searches or
negative quality judgments. Seven account screens have no successful README
inspection and remain lower-confidence leads.

Eight failed repository leads and one canonical-owner duplicate were excluded
from the final GitHub frame. Seven replacement repositories and two bounded
second-order dependencies broadened that frame to 51 canonical account leads.
Failed paths, redirects and exclusions are retained privately. Wider metadata
acquisition and representative-video host lookups exceed the screened frame;
neither is counted as an additional recommendation.

## Strategy changes and productive paths

The expansion uses additional bounded, authorized collection evidence plus
intentional related-problem seeds. It follows actual collaborator credits,
credited algorithm sources and dependency authors when primary documentation
supports the connection. Secondary exploration stops at two hops. Relationships
such as “uses,” “ports,” “coauthors,” “presents on” and “operates” remain distinct.

Code-first sources still produce a higher curated card yield here: 18/51 versus
22/150 for channel-first screening. The cohorts differ in selection difficulty,
inspection depth and their suitability for a two-platform intersection. These
fractions do not establish general platform superiority or improved relevance.
They also include deliberately retained single-platform comparisons.

Each screen has one primary retrieval method; paths can overlap intellectually.
These are adaptive cohorts, and several small neighborhoods received much deeper
inspection than broad collection screens.

| Primary retrieval method | New screens | New cards |
| --- | ---: | ---: |
| Collection encounters plus profile triage | 114 | 3 |
| Related technical problems | 36 | 19 |
| Profile/method GitHub seeds | 41 | 14 |
| Credited method source | 1 | 1 |
| Collaborator/reference trail | 2 | 2 |
| Dependency author | 7 | 1 |

The strongest neighborhood paths produce inspectable mathematical methods rather
than just similar subject labels. Broad collection screening also surfaces many
performance, news and commentary channels with no demonstrated code intersection.

Repeated failures confirm that guessing handles or repository paths is expensive
relative to following official profiles, directory listings and exact project
links. A linked third-party library is not evidence of creator ownership. Missing
README files, moved repositories, incomplete teaching repositories and retired
hardware designs remain explicit limitations.

## Concept discovery and diversity

The expanded cards span 39 curated subject labels and 75 method labels, with
40 source-linked concept entries. These labels describe the selected works;
they do not establish 40 unfamiliar concepts or increased personal relevance.
The original cards have 24 subject and 25 method labels. Labels are manually
assigned, overlap, and are not a standardized taxonomy; the larger counts are
not a controlled diversity comparison. Seventeen new cards have adjacent or
unexpected trails, compared with nine original cards. Deliberate single-platform
controls broaden the explanation styles.

Useful evidence patterns include boundary-query Monte Carlo PDE estimators,
interval-based implicit geometry, inverse imaging and regularization, discrete
geometric operators, equality saturation, and the linear-algebra structure of
audio processing. The private cards link both the existing project/interest basis
and the creator’s supporting work. Proposed transfer to a different project stays
a hypothesis; an educational model or aesthetic rendering is not silently treated
as a calibrated physical inference.

The original private feedback is preserved independently from familiarity.
Expanded usefulness, unfamiliar useful concepts and comparative relevance still
require human evaluation. No improvement in relevance is claimed. The matched,
randomized evidence-reveal experiment described in the pilot remains future work.
Full videos and transcripts were not assessed. Explanatory assessments rely on
bounded metadata, descriptions, written explanations and selected code excerpts;
they remain provisional until a full explanation and small example are reviewed.

## Budgets and provenance

- **116 YouTube attempt reservations**, including six sandbox transport failures.
  The installation ledger ended at 145 reserved units against a conservative
  150-unit local daily ceiling. Successful metadata methods are inexpensive;
  no `search.list`, playback or playlist-write calls ran. Provider-charged units
  for transport failures are not exposed. The usual project allocation is 10,000
  daily units, but provider responses and other project users take precedence.
  See [official quota accounting](https://developers.google.com/youtube/v3/determine_quota_cost).
- **192 logical GitHub connector calls**, including eight rejected URL forms that
  did not reach GitHub. There are 185 retained response artifacts and seven
  session-only exploratory/search calls. The initial calls and three exploratory
  reads were admitted retrospectively; later batches used local admission, capped
  at 240 calls/hour. One code search was outside that ledger. Connector-internal
  HTTP counts, retry behavior and remote rate headers are unavailable.
- **26 web-search queries** across seven search invocations, plus primary-page
  opens/clicks: 23 logical browser calls total. Twenty calls have retained private
  artifacts; two early searches and one primary-page batch remain in the session
  record. Browser-internal HTTP counts are unavailable. Throttled YouTube web
  embeds were replaced by exact-ID Data API metadata checks.
- Source responses, README/blob hashes, representative-video metadata and rejected
  paths are stored in private content-addressed snapshots. Reimports reuse cached
  evidence. No remote candidate code, hardware build or paid model call ran.

## Dashboard, durability and WSL2 validation

The collection now merges checkpointed batches while retaining the active legacy
pilot and immutable source snapshots. Stable creator IDs keep previous reviews
attached. Reimports do not reset decisions, and downloading/importing untouched
cards does not create artificial reviews or rewrite existing review timestamps.
Multi-review updates use one transaction and roll back on write failure.

The dashboard separates familiar-interest and unexpected-connection sections;
new cards appear first within each. Subject, method, direction, affiliation,
round, review status and platform filters combine with search. Work links and
long explanations expand on demand. Single-platform cards and presenter roles
are labeled independently of identity confidence.

Startup performs collection preflight before advertising a URL. Diagnostics
identify read-only storage, permission/sandbox denial, occupied ports, missing
files, space shortages and SQLite access problems without dumping private paths
or exception payloads. Request-time storage errors return a useful 503 response.
Browser disconnects do not break subsequent requests.

Validation: **89 tests**, unchanged seven-site public regeneration, publication
guards and whitespace checks. Chromium inspected desktop and 390-pixel layouts,
filters, expandable evidence, report navigation, downloads and durable feedback
save/reload using a synthetic collection. An unchanged-save and full feedback
export/import against the real collection preserved its existing review rows.
No JavaScript errors, external asset requests or mobile overflow were observed.
Windows PowerShell received HTTP 200 from the WSL2 loopback service and confirmed
the expanded dashboard content. This verifies Windows-to-WSL access; it is not a
claim of a separate manual Windows Chrome/Edge visual inspection.
