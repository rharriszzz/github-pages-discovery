# Making the Learning Queue genuinely useful — trial plan and research leads

*Prepared 2026-11-07. Public-safe design/research notes for rharriszzz/github-pages-discovery; related project: [arxiv-shelf](https://github.com/rharriszzz/arxiv-shelf).*

## 0. Recommendation in one paragraph

**Use what is already built before building a larger recommendation engine.** Keep arxiv-shelf as the independent paper/PDF/catalog application and github-pages-discovery as the private, question-first entry point for choosing specific videos, papers, articles, code examples and creators. The existing Learning Queue and creator-review dashboard have not yet had enough real human feedback to tell which research or UI changes help. Spend a few sessions making actual decisions, record both successful *and disappointing* recommendations, then implement only the improvements exposed by that trial. HackerTube supplies a valuable source of sustained, contextualized HN video recommendations; Tristan Hume's personal tier list supplies a model for intelligible short editorial judgments and *specific illustrative videos*. Neither should become an unexamined popularity score.

## 1. What the repositories already contain (inspection of current default branches)

| Project | Observed capability | Important limitation or next validation |
| --- | --- | --- |
| [arxiv-shelf](https://github.com/rharriszzz/arxiv-shelf) (default branch: **master**) | Desktop/local PDFs and metadata, searchable abstracts, 1–5 star ratings, portable append-only Git catalog, explicit Mac/PC GitHub sync, missing-file download, private browser edition plus public landing page | User round-trip (Mac → PC → Mac), current local-PDF accessibility, and whether the existing papers/rating interface helps with *selection*, not merely storage. Public repository already exposes catalog metadata and ratings; do not copy private Discovery feedback into it. |
| [github-pages-discovery](https://github.com/rharriszzz/github-pages-discovery) (default branch: **main**) | Seven public GitHub Pages samples; private creator review dashboard with **52 creator cards**; private SQLite evidence store; selective YouTube/Takeout/bookmark import infrastructure; read-only Shelf adapter; question-first Learning Queue with up to five mixed-source works and durable independent feedback | The original 52 cards and 18 specifically researched works were inspected technically, **not** evaluated by this user's actual reading/watching. The 7-site public survey is a demo, not exhaustive. Private research and feedback cannot be fully inspected from GitHub; do not assume every local import or OAuth step was completed. |

Pointers: [Discovery implementation status](https://github.com/rharriszzz/github-pages-discovery/blob/main/docs/implementation_status.md), [Learning Queue guide](https://github.com/rharriszzz/github-pages-discovery/blob/main/guides/learning-queue.md), [expanded creator research](https://github.com/rharriszzz/github-pages-discovery/blob/main/reports/creator-expanded.md), [Shelf README](https://github.com/rharriszzz/arxiv-shelf/blob/master/README.md).

**Architectural decision:** do *not* merge the two repositories now. Keep their independent execution, tests, release paths and data ownership. The existing read-only arXiv adapter is the right integration boundary. Consider a shared concept/feedback exchange format later, only if regular use demonstrates a need.

## 2. First experiment: use the software without changing it

Suggested procedure, repeat twice on different days:

1. In WSL2, from the Discovery checkout, start the Learning Queue:

       python3 -m pagefinder.local serve-learning --port 8767

   Open http://127.0.0.1:8767/ in Windows Chrome. If Shelf is in a non-default location, use the documented --arxiv-dir option. The Queue already refreshes local sources without network calls on startup. Do not run a new discovery crawl just for this test.

2. Ask five varied, *specific* questions, for example:
   - How can Fourier/FFT methods recover a signal or geometric pattern when observations contain mistakes?
   - What determines orbital data-center radiator area, radiator temperature and heat-pump feasibility?
   - How do fast Reversi engines evaluate mobility, stability and endgames, and how can an engine *teach* the reasoning?
   - How can one validate a fluid simulation and choose a Reynolds number corresponding to a physical system?
   - What is a good hands-on route from curvature tensors to physically meaningful general-relativity examples?
   
   These are proposed experiments, not claims that the current index has an answer for every one. Also ask one deliberately unfamiliar question to test **exploration rather than repetition**.

3. For each query, inspect the top three results. Open at least one promising work, but don't mark it completed merely because it was opened. Use the existing useful / saved / already read-watched / dismissed controls and a short reason. Review one video or article far enough to determine if the recommendation's description was accurate. A surprising, defensible adjacent result deserves credit; generic keyword matches should not.

4. Open the creator dashboard via the Queue's **Explore creators** link. Review 10–12 of the existing 52 cards, marking keep/later/skip and noting whether the associated **specific video or repository** is worth exploring. Compare familiar creator intersections to unfamiliar ones. Keep uncertain identities labeled uncertain.

5. Independently launch the arXiv Shelf (port 8765), find three papers of interest, rate or update two entries if useful, and check whether the Queue reflects these catalog changes after refreshing local sources. If working across Mac and PC, test the documented explicit Git sync round trip; don't let the Queue modify Shelf ratings or the catalog.

### Small evaluation log (private, not committed)

Keep one row per decision: query; candidate ID/URL; source (Shelf, earlier creator research, HN, Hume, etc.); rank; familiar/new/uncertain; opened; *useful yes/no/unknown*; reason; presentation defect; missing prerequisite; next action. One or two sentences are enough.

After ~15–25 actual recommendation judgments, summarize:
- **Useful-at-three:** for how many questions did at least one of the first three works help?
- **Novel-but-useful:** how often did a previously unknown work or concept pay off?
- **Wasted clicks:** how often did the title/description overpromise, repeat something already known, lead to a dead video, or mismatch the question?
- **Selection friction:** time spent finding the right card, deciphering a score, clicking through a creator profile, or deciding what to do next.
- **Source mix:** was the winning item a video, article, paper, code example, or interactive demonstration?
- **Missing items:** what should obviously have been recommended but wasn't?

Do not treat opening as watching, a saved item as endorsement, or absence from available YouTube history as proof it has never been watched. This is a **qualitative usability pilot**, not a statistically calibrated evaluation.

## 3. Lessons to borrow from the other sites

### HackerTube: sustained recommendations with the reasons attached

Primary references: [original site](https://hackertube.org/), [Karpathy's 2026-10-31 announcement](https://karpathy.bearblog.dev/hacker-tube/), [HN launch thread](https://news.ycombinator.com/item?id=50319510). The original site is a JavaScript-heavy application; the About route could not be fully extracted in this inspection, so the observations below are cross-checked against Karpathy's original announcement, his HN comments, and [independent descriptions of the export](https://hackertube.page/how-it-works), not presented as a direct quotation of the site's full About screen.

- The reported source distilled roughly **43 million HN comments** to **39,834 relevant mentions** of **6,454 videos** across about **150 topics** and 2007–2026. The downloadable underlying dataset is more useful to our project than copying the website's layout. Karpathy reports a Claude-assisted pipeline and provides a data export.
- **Repeated independent recommendations over distinct months** are a better evidence signal than a one-day viral spike or a high view count. But links can be citations, criticism or jokes; label sentiment and link to the actual discussion. Independent descriptions report a minimum of three people/months; verify the export's real schema and precise selection rule before implementing a score.
- Original site features worth trying: representative mid-video thumbnails rather than aggressive upload thumbnails; no required account; local browser history/likes/watch-later; keyboard shortcuts; *Longs* for long-form viewing; download for agent reuse.
- Karpathy's [HN changelog comment](https://news.ycombinator.com/item?id=50319510) reports added filters for upload date, duration and video type; **recently recommended** separate from **recently uploaded**; hidden gems; evergreen-only; damped likes/views; and opening a list as a temporary YouTube playlist (up to 50). The distinction between recommendation recency and upload recency is especially valuable for rediscovering older videos.
- HN participants also suggested owning one's ranking algorithm, bringing the discussion context alongside the link, and feed/RSS-style curation instead of relying on a platform's engagement feed. [hn.video](https://hn.video/) is an alternative small current-HN-video interface. A [book analogue](https://hackerbooks.org/) shows how this methodology can extend to other media, but it is not a reason to import all books into the Queue.
- Original export links mentioned in the HN discussion: [data page](https://hackertube.org/data), [data ZIP](https://hackertube.org/download/hackertube-data.zip). Treat those as **candidate download links to verify interactively**: they did not yield usable document content in this inspection. Check license, attribution, README/DATA.md, available fields, and YouTube API redistribution restrictions before caching or publishing anything.

### Tristan Hume: a clear explanation of personal taste

Read [My YouTube tier list, six years later (2026-11-01)](https://thume.ca/2026/11/01/youtube-tier-list-2026/). It is an *individual's* ranked preferences, not a universal quality ranking. Useful elements to borrow:

- Clear S/A/B/C/D navigation, with practical descriptions of what the tiers **mean** and an indication of changes since his 2020 list.
- A short explanation of *why the channel is worth watching*, rather than only generic subject tags, paired with **a particular representative video** and the channel link.
- Expandable detail for readers who want more; a compact initial view for fast scanning.
- Highlights about methods and explanatory style: Applied Science documents failures and experimental technique; Dan Gelbart teaches prototyping details; Clickspring explains craft and manufacture with unusually good visuals; Huygens Optics combines hands-on optics with wave explanations; Hyperspace Pirate experiments with refrigeration.
- Crucially, the user's personal judgment should supersede Hume's tier: even a C/D-tier channel on his list may be perfect for a particular question (Scott Manley on spaceflight is an example). Import a channel as a **lead to evaluate**, not as a confirmed positive preference or a fixed rating.

## 4. Candidate UI changes (after the trial, prioritized)

| Priority | Proposal | What it changes / how to test |
| --- | --- | --- |
| P1 | **Question → 3–5 specific works → one click to source** stays the primary page | Don't turn the first screen into a giant channel feed, category grid or ML dashboard. Keep goal/time/format controls optional. |
| P1 | **Explain the recommendation in a sentence** | Card states “This helps answer [specific question] by [method/idea]”; show source and uncertainty. Open a deeper evidence trail on demand. |
| P1 | **Compact readable list / expanded card toggle** | A dense, large-font, light-background list should show titles and reasons without needless search when all items fit; cards can reveal thumbnail, concepts, provenance, prerequisites and notes. Test which view requires fewer clicks. |
| P1 | **Unfamiliar / revisit / adjacent** as explicit discovery modes | “Unfamiliar” needs user feedback, not a model's unsupported declaration. “Revisit” comes from saved/recently interesting sources. “Adjacent” should name the conceptual bridge, not a vague similarity. |
| P2 | **Provenance badges expressed as text** | Examples: “from arXiv Shelf,” “recommended across 8 HN months,” “Hume's example video,” “operator link verified,” “new candidate—unreviewed.” A source's mention is not automatically its endorsement. |
| P2 | **Sort and filters that mean something** | Recently *recommended*, recent *upload*, evergreen, long lecture, format, time budget, watched/saved status. Avoid filters until the result set is large enough for them to help. |
| P2 | **Representative image, not sensational image** | Test mid-video thumbnails if legitimately available, with fallback to official thumbnails and no scraping of protected endpoints. Prefer a real illustrative frame for an article or project. No image is necessary for a compact table. |
| P2 | **Two-level creator view** | First: channel + two-line editorial explanation + 1–3 concrete representative works; second: GitHub affiliation evidence, source quotes/links, difficulty and adjacent method trails. |
| P2 | **One good follow-up** | After viewing a work, offer “next worked example,” “deeper treatment,” or “related project” (with an actual source), not an endless automatically expanding feed. |
| P3 | **Export/share a shortlist** | Markdown/JSON export of public-safe titles/URLs/reasons; user's private annotations stay local. Optional temporary YouTube playlist link for a *user-selected* list if provider behavior permits. |
| P3 | **Separate personal tiers or comparative view** | A lightweight keep/later/skip or favorite scale with written reasons is preferable to automatically assigning Hume-style S/A/B labels. Support “known excellent but already watched,” “good but too elementary,” and “interesting but needs prerequisites.” |
| P3 | **Question/project trails** | View a small chain such as “Fourier methods → inverse problems → missing observations → bead reconstruction,” each edge backed by a source and labeled verified vs hypothesis. Avoid a huge unlabeled graph. |

Avoid publicizing private YouTube history, Likes, Watch Later, playlist names, feedback or local paths. The published GitHub Pages site stays a **public-safe demo/catalog**, while personal recommendations and notes remain in the loopback app and private SQLite database. A static public site cannot silently share the private state of the desktop application.

## 5. Concrete video and channel leads to try

This is a **curated *test queue***, not a claim that the videos are new to the user, current on the channel, fully watched, or endorsed after full review. The first group has public evidence of repeated HN recommendations; the second comes from Tristan Hume's judgments. Verify metadata/availability and deduplicate by YouTube video ID before private import.

### A. Repeatedly recommended in Hacker News discussions (HackerTube dataset)

The links to the [independent HackerTube index](https://hackertube.me/) expose individual HN comments and evidence; these are **not** pages operated by Karpathy. Direct YouTube links use the video IDs shown on those pages.

| Specific video | Why it is a useful test | Source / YouTube |
| --- | --- | --- |
| **But what is the Fourier Transform?** — 3Blue1Brown | Visual signal-analysis explainer; test whether the system recognizes it may be *familiar or introductory*, and offers something deeper if so | [HN discussion evidence](https://hackertube.me/watch/spUNpyF58BY/) · [YouTube](https://www.youtube.com/watch?v=spUNpyF58BY) |
| **Indistinguishable From Magic: Manufacturing Modern Computer Chips** — Andor Gafotas | Semiconductor physics/manufacture; long-lived technical talk, with *historical* process-node details that need a freshness caveat | [HN discussion evidence](https://hackertube.me/watch/NGFhc8R_uO4/) · [YouTube](https://www.youtube.com/watch?v=NGFhc8R_uO4) |
| **The spelled-out intro to neural networks and backpropagation: building micrograd** — Andrej Karpathy | A complete software-plus-math explanation; compare to source code and papers for teaching value | [HN discussion evidence](https://hackertube.me/watch/VMj-3S1tku0/) · [YouTube](https://www.youtube.com/watch?v=VMj-3S1tku0) |
| **D/A and A/D — Digital Show and Tell** — Monty Montgomery | Signal processing, sampling and conversion; particularly good format bridge between video, hardware and software | [HN discussion evidence](https://hackertube.me/watch/cIQ9IXSUzuM/) · [YouTube](https://www.youtube.com/watch?v=cIQ9IXSUzuM) |
| **MIT's Pathway to Fusion Energy** — Zach Hartwig | Physics/energy engineering; explicitly distinguish an older research roadmap from today's status | [HN discussion evidence](https://hackertube.me/watch/L0KuAx1COEk/) · [YouTube](https://www.youtube.com/watch?v=L0KuAx1COEk) |
| **A Better Default Colormap for Matplotlib** — Nathaniel Smith and Stéfan van der Walt | Scientific visualization and perceptual correctness, transferable to numerical simulations and diagnostics | [HN discussion evidence](https://hackertube.me/watch/xAoljeRJ3lU/) · [YouTube](https://www.youtube.com/watch?v=xAoljeRJ3lU) |

### B. Interesting specific examples from Tristan Hume's 2026 tier list

| Channel / illustrative video | Why consider it |
| --- | --- |
| **[Applied Science](https://www.youtube.com/watch?v=NwhVJ7cv9B4)** — “See inside insects with an electron microscope and a femtosecond laser” | S-tier in Hume's list; sophisticated experimental instrumentation and careful documentation of how experiments work |
| **[Huygens Optics](https://www.youtube.com/watch?v=TPyQI7bJo6Q)** — “Making a Deformable Mirror” | Practical optics, wave physics and engineering |
| **[AlphaPhoenix](https://www.youtube.com/watch?v=o4TdHrMi6do)** — “A laser pointer at 2 billion fps makes the speed of light look... kinda weird” | A clever experimental apparatus makes wave/propagation phenomena visible |
| **[Know Art](https://www.youtube.com/watch?v=bp2IAlU53uw)** — “Why Centrifugal Fans SPEED UP When Blocked (Regular Fans Slow Down)” | A concrete fluid-machinery puzzle rather than an abstract “fluids” category |
| **[Breaking Taps](https://www.youtube.com/watch?v=GbcN0bPs-Ig)** — “I made tiny robot eyes” | Hardware + software plus an explanation of design tradeoffs |
| **[Dan Gelbart](https://www.youtube.com/watch?v=OuZjjActWmQ)** — “Unusual Shop Tips” | Prototyping and precision fabrication; Hume particularly recommends the multi-part instructional series |
| **[Animagraffs](https://www.youtube.com/watch?v=tBN2o4rAt5A)** — “How a Trans-Atlantic Steam Ship Worked” | Detailed 3-D engineering explanation, a good model for useful visual presentations |
| **[Tech Ingredients](https://www.youtube.com/watch?v=G1Syjh319VU)** — “We turned a household freezer into a high-speed blast chiller!” | Heat transfer, refrigeration, testing and useful physical apparatus |
| **[Sam Zeloof](https://www.youtube.com/watch?v=mvZ1dJuvenw)** — “Wire Bonding Basics - Manual Wedge Bonding ICs” | Semiconductor fabrication from a hands-on maker perspective |
| **[Hyperspace Pirate](https://www.youtube.com/watch?v=UXNcivV8JNw)** — “DIY Synthetic Fuel Part I - Making Syngas And A High Pressure Compressor” | Nonstandard cooling/thermodynamic and hardware experiments; assess individual videos carefully |
| **[CSI Starbase](https://www.youtube.com/watch?v=Cu16K_AMuaY)** — “What Makes Starship's Water Deluge System So Unique??” | Specific spacecraft ground-system engineering, diagrams and failure analyses |
| **[Scott Manley](https://www.youtube.com/watch?v=vPOUfcpOSDg)** — “Boom Supersonic's SuperPower Jet Engine Is Real!” | Aerospace engineering; he appears in Hume's D tier, illustrating why Hume's personal ranking is *not* a score of suitability for a particular user |

Further channels worth sampling *as channels rather than automatically importing all uploads*: [Clickspring](https://thume.ca/2026/11/01/youtube-tier-list-2026/) (machining and Antikythera mechanism); [Stuff Made Here](https://thume.ca/2026/11/01/youtube-tier-list-2026/) (engineering design process, algorithms, failures); [Joshua Bird](https://thume.ca/2026/11/01/youtube-tier-list-2026/) (clever electromechanical projects); [2swap](https://thume.ca/2026/11/01/youtube-tier-list-2026/) (beautiful mathematics); [3Blue1Brown](https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw) (visual mathematics). Select one representative video and assess depth before following a channel.

### C. Additional community-sourced leads, not necessarily videos

- [HackerTube's 2026 HN launch discussion](https://news.ycombinator.com/item?id=50319510): unusually useful discussion of feed ownership, recommendation context, RSS, time-vs-quality ranking and UI changes. Preserve links to individual comments, not just a vague “recommended on HN.”
- [hn.video](https://hn.video/): a simpler, more recent-HN-video feed. Useful comparator for recency filters, but not necessarily a source of sustained recommendations.
- [HackerBooks](https://hackerbooks.org/) and [its HN announcement](https://news.ycombinator.com/item?id=50326821): examples of evidence-backed book discovery. Future input, not a mandate to turn the project into a book catalog.
- [Tristan Hume's 2026 tier list](https://thume.ca/2026/11/01/youtube-tier-list-2026/): high-density editorial examples, with channel, specific work, reason, and 2020/2026 comparison. Suitable as a *reviewed public seed list*; his opinions should remain attributed.

## 6. Bounded follow-on implementation, if the manual test justifies it

**Phase A — UI friction only.** Fix the highest-frequency usability problems observed during the first 15–25 judgments. Do not rewrite the ranking algorithm first. Keep current results and decisions stable; add screenshot/regression tests for desktop and narrow-width layouts. Include a two-minute path from startup to opening a promising specific work.

**Phase B — HN data as an optional new source.** Validate the HackerTube export and attribution/license, inspect a small reproducible random+topic-stratified sample, classify positive recommendations versus citations/criticism, and import **only about 20–40 assessed candidates first** into the *private* Learning Queue using the existing source/evidence model. Preserve: video ID, original HN thread/comment URLs, dates, signal labels, distinct-recommender/month counts, source export version, title availability and uncertainty. Do not copy YouTube metadata into a public export if API terms forbid redistribution. There should be a source toggle or comparison field and no hidden implicit endorsement.

**Phase C — Hume seed manifest.** Create a separate modest **public, attributed** manifest of channels and representative video URLs from the tier list, with Hume's personal tier and explanation provenance **not** translated into the user's preference. A channel can be useful without a GitHub account. Allow direct channel-level and specific-work-level feedback. A YouTube–GitHub match is a bonus when supported, not an admission requirement.

**Phase D — evaluate retrieval rather than volume.** Compare the existing Queue against the same Queue + HN/Hume seeds using the *same held-out questions*, visible source labels and recorded user judgments. Report useful-at-three, genuinely novel-and-useful, skipped/repetitive works and time-to-good-link. An ablation of HN recurrence, Hume channel priors and the user's feedback would clarify whether each signal contributes. Only then contemplate semantic retrieval, broader crawls or automated fresh-feed maintenance.

**Phase E — lost videos from familiar creators.** This remains a separate, older planned goal. If the user's selected Takeout data supports it, test upload chronology for 3–5 well-known channels, compare available history to public upload lists, and label items **not found in available history** rather than “unwatched.” Do not infer playback minutes or percent completion; the ordinary export does not provide them. It may be more valuable than another wave of new creators if it recovers overlooked excellent works.

### Codex handoff when there is real feedback

Ask Codex to read this document along with [implementation status](../docs/implementation_status.md), [the Learning Queue guide](../guides/learning-queue.md) and [the existing merged plan](../MERGED_PROJECT_PLAN.md); inspect live working-tree changes and **private local feedback without publishing it**; summarize the empirical top three usability failures; propose the smallest tested change; implement only a reviewed slice; run unit tests, publication guard and browser checks; and commit/push after verifying no private evidence leaked. Existing 52-card reviews, append-only Shelf data, source snapshots, auth and private SQLite stores must be preserved.

## 7. Proposed “done” condition for this next iteration

Not “more channels indexed.” Instead: from a question that matters today, the user can open the Queue, choose one credible and appropriately challenging source from three to five intelligible recommendations, understand **why** it is there and **who** recommended it, and record whether it was worthwhile. The next launch should incorporate that judgment without creating an unmanageable feed. A failure that is labeled clearly and helps fix ranking is useful experimental progress.

## References and evidence limits

- [arxiv-shelf README and TODO](https://github.com/rharriszzz/arxiv-shelf) (master as inspected, 2026-11-07).
- [Discovery README](https://github.com/rharriszzz/github-pages-discovery), [implementation status](https://github.com/rharriszzz/github-pages-discovery/blob/main/docs/implementation_status.md), [Learning Queue guide](https://github.com/rharriszzz/github-pages-discovery/blob/main/guides/learning-queue.md), [creator experiment](https://github.com/rharriszzz/github-pages-discovery/blob/main/reports/creator-expanded.md) (main as inspected).
- [Andrej Karpathy, *HackerTube*, 2026-10-31](https://karpathy.bearblog.dev/hacker-tube/); [official site](https://hackertube.org/); [launch/HN thread](https://news.ycombinator.com/item?id=50319510); [independent dataset description](https://hackertube.page/how-it-works); [independent per-video HN evidence](https://hackertube.me/).
- [Tristan Hume, *My YouTube tier list, six years later*, 2026-11-01](https://thume.ca/2026/11/01/youtube-tier-list-2026/).

Inspection here used GitHub repository contents and public web pages. **No access was assumed to the user's actual private SQLite database, current machine's runtime, YouTube account, or watch history.** No full videos were watched; descriptions/metadata are leads for human assessment, not independent endorsements. Original HackerTube About UI was not fully extractable from its JavaScript app in this browsing environment; the official blog/HN posts and independently readable source-data explanations supplied the method details above.