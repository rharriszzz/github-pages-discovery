# Cross-platform creator pilot — 2026-11-02

This is an additional experiment within the shared discovery project. The public
seven-site catalog, keyword comparator and broader lost-video/interest-graph plan
are preserved. Personalized recommendations, source membership, assessment reasons,
raw responses, screenshots and review decisions are outside Git. The detailed
research report and twelve review cards are in the private local dashboard.

## Method and bounded sample

Start from locally authorized curated/liked-video evidence in one direction and
interest-relevant public repositories in the other. Screen 50 channel-first records
and eight GitHub-first seeds. Channel-first screening uses official metadata,
sampled-video descriptions and a bounded identity query; only promising candidates
receive deeper multi-work inspection. This is an adaptive, targeted sample, not a
survey of all creators. Two channel records belong to one creator.

The acquisition examined **61 distinct channel IDs** (including representative-video
hosts and rejected/unconfirmed handle lookups) and **21 GitHub accounts** (including
alternatives and rejected matches). The 58 seed investigations include 56 distinct
channel URLs and 16 GitHub accounts; those are different denominators. Metadata
lookups are not all recommendations or full body-of-work assessments.

For recommendations, inspect two or three representative projects and two or three
videos/series using bounded README excerpts, public project documentation, video
metadata, descriptions and chapters. Up to ten listed uploads per promising channel
provide a bounded activity check. Five raw repository-metadata responses add push
timestamps omitted by the normalized connector. Record retrieval times and README
blob IDs. No remote code was installed or executed. Full videos and transcripts
were not evaluated, so audiovisual clarity and scientific/software correctness
remain provisional.

Reuse the private interest graph, explicit statements/corrections, bookshelf
concepts and cached public project documentation. Separate direct subjects, shared
methods, experimental approaches, adjacent concepts and unexpected connections.
Books, Likes and saved items do not establish proficiency or completion. Existing
keyword and private-context comparators remain visible triage aids; there is no
combined creator score and no popularity ordering.

## Outcomes and denominators

| Seed direction | Investigations | Verified affiliation | Probable | Uncertain | No match within bound | Review candidates | Operator intersections |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| YouTube first | 50 | 7 | 3 | 5 | 35 | 6 | 6 |
| GitHub first | 8 | 6 | 0 | 0 | 2 | 6 | 5 |
| Total | 58 | 13 | 3 | 5 | 37 | 12 | 11 |

The thirteen verified records include a sister-channel duplicate and a verified
**guest presenter**. They are not thirteen distinct channel operators. Twelve
candidates have substantial relevant work across the inspected artifacts; eleven
have supported channel/project operation or affiliation, and the twelfth is a
high-fit guest-presenter comparator. Some software is current while associated
videos are archival. This pilot does not establish recent activity on both
platforms for every candidate.

Seed provenance: 56/58 (96.6%) came from existing collections or searches directed
by existing interests; 2/58 (3.4%) were exploratory GitHub-first seeds. The twelve
review candidates contain ten existing-interest seeds and two exploratory seeds.
Unexpected concept connections can also arise from an existing seed; search origin
and conceptual novelty are separate dimensions. Familiarity with the proposed
aspect remains unknown until review, including candidates already encountered.

## Which direction was productive?

GitHub first produced five operator intersections from eight deliberately selected
seeds (62.5%), plus the guest-presenter comparator. YouTube first produced six
operator candidates from fifty screened channels (12%). GitHub first was more
productive **in this pilot** at finding inspectable artifacts paired with relevant
explanations. It began from unusually promising software creators, while the
channel cohort included excellent explainers who may publish no code. Unequal
selection and inspection depth preclude a general platform-superiority claim.

Combined evidence improved traceability: explanations can be connected to actual
artifacts, authorship can be checked, and independent method connections become
visible. Improvement in user-rated relevance, novelty, depth or learning
opportunities remains **unmeasured**. Human usefulness has not yet been evaluated.

The intersection is also restrictive. A channel can credit another person's
simulator, a developer can give excellent conference talks without operating the
host channel, and an active scientific library can have an archival video catalog.
These are retained as reference, presenter or single-platform candidates instead
of being discarded or mislabeled as owner matches.

## Identity failures and unproductive methods

- A linked simulator was explicitly credited to another developer. Treating every
  GitHub URL in a video description as ownership would have produced false matches.
  Research commentators also cite code they do not maintain.
- Matching handles led to a different channel; a repository-linked video established
  the correct channel ID. A shared name alone likewise surfaced an unrelated
  researcher. Neither name nor handle similarity became verified evidence.
- A plausible GitHub username was the wrong account. Several guessed repository
  paths returned 404. Official profiles and explicit README-to-video links were
  more productive than continuing to guess paths.
- Self-profile evidence without inspected official channel/project corroboration
  remains probable. A one-project lead did not become a multi-work recommendation.
- Four video-search queries returned no results. Official repository references and
  cached public-upload metadata resolved representative works more effectively.
- Collective names do not establish GitHub Organization type. Preserve the API's
  account classification and record collective/personal affiliations separately.
- Collaborators, original algorithm authors, code implementers and video presenters
  remain separate. Document second-order references without identity equivalence.

## Capacity and checkpoints

- **28 YouTube Data API attempts / 28 reserved units**, against a conservative
  100-unit local daily ceiling for the experiment. No `search.list` calls. The
  installation ledger includes earlier work separately; other clients sharing the
  Google project can consume additional remote quota. These metadata methods cost
  one unit per call ([videos](https://developers.google.com/youtube/v3/docs/videos/list),
  [channels](https://developers.google.com/youtube/v3/docs/channels/list),
  [playlist items](https://developers.google.com/youtube/v3/docs/playlistItems/list)).
- **53 logical GitHub connector calls**, including six unsuccessful calls. One URL
  was rejected before an HTTP request. Connector-internal HTTP counts and remaining
  remote quota are not exposed. Initial README calls were recorded retrospectively;
  subsequent connector calls used local admission before execution. Source reads
  are bounded and checkpointed, not a broad repository crawl.
- **64 web-search queries**, including the four unsuccessful video queries, plus
  primary-page opens/click follow-ups. This is logical research accounting, not a
  claim to know the browser provider's internal request count. Selected results are
  snapshotted privately; early exploratory/documentation opens remain in the session
  record. Search-engine coverage is selective.
- Playlist/Likes pages checkpoint atomically and reuse existing response caches.
  Upload inspection creates no viewing or engagement events. Reimports preserve
  durable reviews. Completed offline reruns spend zero additional API units.

## Next experiment and concepts

First collect the twelve decisions and reasons. Measure useful new **aspects** and
concepts, not recognition of account names. Suppress explicit rejections and avoid
repeating familiar creators unless a substantial new aspect is identified.

Then compare matched GitHub-only, YouTube-only and combined-evidence cards from the
same pool, randomizing evidence reveal and fixing inspection time. Balance direct,
method and adjacent cohorts and include code-only/explainer-only controls. Measure
precision, unfamiliar useful concepts, evidence confidence and useful discoveries
per inspected candidate/time; record selection failures. Ratings must remain
separate from familiarity and identity confidence.

Promising conceptual bridges include discrete differential operators and surface
parameterization; inverse imaging through controlled illumination; instrument
calibration; sparse identification of dynamics; memory representations and runtime
reflection; and executable mathematical microworlds. These are exploration
hypotheses with source trails in the private report, not newly assumed preferences.

Validate one bounded technical example and transcript segment for user-selected
candidates before scaling. Revisit probable affiliations, follow credited developers
as separate candidates, and preserve archival explanations when recent video
production is not necessary for learning.

## Validation

78 tests pass, including identity-evidence rejection, bounded sources, restart/cache
behavior, private storage and durable feedback. The loopback service rejects
foreign origins, unexpected Host headers, missing review tokens and arbitrary file
paths. Headless Chromium inspected desktop and 390-pixel layouts, subject/method/
direction/search filters, save/reload and feedback downloads using synthetic review
data. No JavaScript errors, mobile overflow or external page requests occurred.
The original public HTML/CSV/JSON regenerate without changes and the publication
guard passes.
