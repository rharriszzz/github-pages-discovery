# Discovery: UI and suggestion concepts worth combining

*Working design notebook — 2026-11-07. Applies primarily to [github-pages-discovery](https://github.com/rharriszzz/github-pages-discovery), while continuing to read [arxiv-shelf](https://github.com/rharriszzz/arxiv-shelf) through its existing adapter. **No large crawl is the next step.*** 

## Purpose and scope

Design a **better way to encounter, choose, understand and revisit worthwhile material** using the research and collections that already exist. First combine and evaluate interaction ideas; **do not** begin by growing the database. This file is an evolving list of preferences, outside inspirations and proposed combinations, **not a claim that every idea is endorsed or implemented**.

The user already knows and uses **YouTube channels, YouTube playlists and Chrome bookmark folders**. Those are good established tools. This project should *complement* them, not invent replacement channel subscriptions, duplicate playlist/folder organizers, or require migrating the user's existing organization. A good result opens the original source with one click and makes it obvious **why this item deserves attention**.

Status legend:
- **USER — explicit**: directly requested or repeatedly affirmed.
- **USER — inferred**: consistent with previous requests, but **not** an explicit feature approval.
- **EXTERNAL — observed**: a design from an outside site or a specific participant's suggestion; **not** automatically the user's preference.
- **PROPOSAL**: synthesis to evaluate; no user approval assumed.
- **DEFER**: outside the next iteration.

## 1. Concepts the user has actually expressed a preference for

| ID | Concept | Status / implications |
| --- | --- | --- |
| U01 | **Choose what to read, watch or investigate next.** | **USER — explicit.** The real product is better choices, not a large searchable archive as an end in itself. |
| U02 | **Videos, software, articles, demonstrations and papers all qualify.** | **USER — explicit.** Do not privilege arXiv; some worthwhile creators never publish papers. Do not require a YouTube–GitHub affiliation to recommend a great explainer. |
| U03 | **Use the existing work and research already collected.** | **USER — explicit.** Local Shelf plus Discovery's saved creator work and unpublished/private research, when available, are the starting inventory; do not erase or recrawl them. |
| U04 | **Keep the interface pleasant for fast visual scanning.** | **USER — explicit (from prior site decisions).** Light/readable pages, sufficiently large type, clear links, reasonable whitespace. Avoid search controls when a short list is entirely visible. |
| U05 | **Link to the useful destination directly.** | **USER — explicit (from prior project-site work).** A picture/title should take the reader to the meaningful page, not force multiple intermediate clicks. For a recommendation, prefer a *specific video, article or example*, with creator detail available separately. |
| U06 | **Keep separate projects and a sensible common entry point.** | **USER — explicit (prior site organization).** Discovery can be the entry point; arXiv Shelf remains a working, independently useful paper application. Do not merge repositories simply to get a joint UI. |
| U07 | **Preserve meaningful explanations and progress in Markdown.** | **USER — explicit.** This notebook records decisions, alternatives and evidence so future Codex sessions can understand the reasons behind them. |
| U08 | **Do not conduct a large crawl now.** | **USER — explicit, current priority.** Design and combine UI/recommendation concepts first, using existing examples and at most hand-selected fixtures. |
| U09 | **YouTube channels/playlists and Chrome bookmark folders are familiar existing workflows.** | **USER — explicit.** Treat as sources and destinations, not missing features to recreate. No tutorial about how to use them is needed. |

### Closely aligned with earlier work, but not yet separately approved

| ID | Concept | Status / question to test |
| --- | --- | --- |
| I01 | Question-first recommendations with a few concrete works | **USER — inferred / already in the Learning Queue.** Still valuable, but avoid forcing the user to articulate a question every time they simply want an interesting new video. |
| I02 | Save/useful/already-known/not-for-me with durable short notes | **USER — inferred / implemented.** The next UI should present these economically; do not confuse a saved bookmark or playlist entry with completed viewing. |
| I03 | Reasons, evidence, novelty and the *method* connecting works | **USER — inferred from Discovery requirements.** Keep “why this, for this question?” concise; deeper provenance can expand on demand. |
| I04 | Understandable quality judgments over popularity and huge scores | **USER — inferred.** A concise human-readable assessment is better than pretending an uncalibrated rank is a precise probability. |

**Important:** U01–U09 describe user direction. I01–I04 should be validated in the combined presentation rather than silently elevated into unconditional requirements.

## 2. Outside interfaces and recommendations: useful ideas that *other people* like

These are *candidate features*, not the user's declared tastes.

| ID | Origin | Observed idea | Why it might be worth borrowing | Caveat |
| --- | --- | --- | --- | --- |
| H01 | [Karpathy's HackerTube](https://hackertube.org/about) and [his explanation](https://karpathy.bearblog.dev/hacker-tube/) | Curate videos that people have **recommended repeatedly over years**, not merely viral clips or high-view uploads | Independent, long-lived signals can find excellent old lectures | HN is one biased community, not an independent measure of truth or relevance |
| H02 | HackerTube | Keep the **specific HN discussion/comment** behind each recommendation and distinguish recommendations from neutral citations or criticism | Recommender's reasoning may matter more than a numerical score | Automated stance labels can be wrong; link primary comment |
| H03 | HackerTube | **For You**, categories, long-form/“Longs” and locally remembered preferences | Supports relaxed browsing when there is no specific question | Do not re-create YouTube's whole home feed or duplicate its watch history |
| H04 | HackerTube and [Karpathy's blog](https://karpathy.bearblog.dev/hacker-tube/) | Representative mid-video frames instead of exaggerated upload thumbnails | More candid preview of what the video actually contains | Extra effort, quality and usage/terms questions; optional enhancement |
| H05 | HackerTube / [HN launch discussion](https://news.ycombinator.com/item?id=50319510) | Keyboard shortcuts, filters for duration, format and upload age; **recently recommended** vs **recently uploaded**; evergreen and hidden-gem filters | Different discovery occasions require different signals | Hide controls until they actually improve browsing |
| H06 | HN participants and HackerTube | Open a curated group as a temporary **YouTube playlist** | Lets users keep playback in the already-familiar YouTube app | Candidate convenience, not a replacement for user's existing playlists; user-selected only |
| H07 | HN participants | User-controlled ranking, portable exports, subscription/RSS-like curated feeds, and preserving linked discussion context | Transparency and control rather than opaque engagement optimization | A feed engine or continuous collection process is **not** the next task |
| T01 | [Tristan Hume's 2026 YouTube tier list](https://thume.ca/2026/11/01/youtube-tier-list-2026/) | **A few sentences explaining each channel's appeal**, plus a **representative video** | Useful when deciding whether a creator's style and depth fit the goal | Hume's tastes and S/A/B/C/D labels are *his*, not the user's |
| T02 | Hume | Very scannable **tier headings and quick index**; expandable “more” detail | Good overview first, depth second | Personal tiers can be too coarse for a particular video or question |
| T03 | Hume | Comparing judgments now versus years earlier | Models how interest or perceived quality can change | Optional; don't require reviewing/rating every channel |
| K01 | [Karpathy's append-and-review note](https://karpathy.bearblog.dev/the-append-and-review-note/) | Capture items with almost no metadata and occasionally resurface the worthwhile ones | Low-friction save-and-revisit is useful | **External** idea only; not evidence that the user wants a new notes system |

See also: [HackerTube HN thread](https://news.ycombinator.com/item?id=50319510), [original public-data explanation](https://hackertube.page/how-it-works) (an **unofficial** derivative site) and [Discovery's earlier detailed study](LEARNING_DISCOVERY_NEXT_STEPS_2026-11-07.md). HackerTube's original About page is JS-heavy and was not directly readable in full through text extraction; use Karpathy's own blog/HN posts for specific claims about his implementation. External community comments often disagree; these rows describe some contributors' requests, not a unanimous consensus.

## 3. Proposed synthesis: one tool with two natural ways to enter

**PROPOSAL C01 — Two entrances, the same underlying collection:**

1. **Browse:** “Show me something worth watching/reading.” Scan a curated list without having to supply a query. Switch among **Interesting now / Enduring favorites / Overlooked older work / Adjacent ideas** only if those modes can be supported honestly by existing evidence.
2. **Investigate:** “Help me understand [a specific question].” Keep the existing Learning Queue's question, optional time budget and read/watch/code format. Give just a few source-linked works.

Both routes share one set of item identities, human judgments and source records. Neither route should force the user through a creator profile or require choosing a category before seeing anything.

**PROPOSAL C02 — The primary unit is an individual work, with an optional creator/channel view.** YouTube already organizes videos by channel and playlist. This tool should organize *explanations and decisions* around individual works and the problems they illuminate. Creator cards can show the “why follow this creator” summary and two or three especially representative works.

**PROPOSAL C03 — A short, explainable recommendation row** should answer:
- **What is it?** Title, creator/author and type (video, paper, article, code, interactive).
- **Why is it here?** One plain-language reason, with a specific method or learning payoff.
- **Who/what put it here?** Shelf, prior user save, Hume, cited HN comments, prior research, or a clearly labeled unreviewed suggestion.
- **How much commitment?** Verified video duration when available; lecture/course-series flag; reading time only if known.
- **What now?** Open the *original work* directly; optionally “save,” “familiar,” “useful,” or “skip.” These controls are not a new playlist/folder manager.

The first screen can show **compact text rows**. An optional expandable card can reveal representative video, short source explanation, why the item is still relevant, topic/method, prerequisites, source discussions and follow-up links. Offer **compact / detailed** view rather than replacing the whole UI with thumbnails.

**PROPOSAL C04 — Two independent recommendation signals:** 
- **Personally relevant:** related to a current research question, an item the user explicitly marked useful, or work already in Shelf/Discovery; explain the exact relation.
- **Broadly recommended:** HN repeatedly recommended it, or a trusted external curator singled it out; explain who, why and when.

Do **not** mix these into a mysterious universal quality score. A video can be strongly recommended by HN but irrelevant to today's problem; a personally vital article can have no HN mentions.

**PROPOSAL C05 — Familiarity and usefulness are separate.** In particular, distinguish:
- “Saved in YouTube/Chrome” (existing organizational state, when actually imported),
- “Already watched/read” (user confirmation or source-supported history),
- “Useful / not useful” (the user's judgment),
- “Interested, but not now” (intent),
- “Not seen in available history” (**not** “unwatched”).

Avoid showing repeatedly the same elementary explanation to someone who has already studied the subject. The app must work acceptably without YouTube OAuth or a history import.

**PROPOSAL C06 — Navigable intellectual trails, not a compulsory graph.** A recommendation may have one **next useful connection**: e.g., signal/noise → inverse problems → image reconstruction; or heat transfer → refrigeration cycles → orbital radiators. Label it as documented or conjectural, and link to the *specific* explanatory work. A short chain is preferable to a giant web of loosely connected terms.

## 4. Text-only UI sketch (discussion aid, **not** a request to implement yet)

```text
DISCOVER                              Browse  |  Investigate  |  Saved

Browse:  Interesting now  /  Enduring  /  Overlooked  /  Adjacent

[WORK TITLE]  by [creator]                              [video · 42 min]
  Why: a careful demonstration of [idea], relevant to [question].
  Evidence: suggested by HN in several distinct months; discussions linked
  Open source ↗    Details ▾    Save · Familiar · Useful · Skip

[WORK TITLE]  by [author]                                  [article]
  Why: addresses the missing assumption behind [technical question].
  Evidence: connected to a paper in Shelf; methods explained in article
  Read source ↗   Details ▾    Save · Familiar · Useful · Skip

Investigate: [ What are you trying to understand?                 ]
             optional: Time [any]   Format [any]
  → 3–5 concrete works with the same concise reasons and controls
```

This is a *conceptual* illustration: titles and evidence are placeholders, **not actual recommendation results**. A final layout should be tested at ordinary desktop and narrower widths, including a version that uses only text and links.

## 5. Navigation and interaction rules

1. **No need to duplicate YouTube or Chrome.** Open the original video in YouTube, the article on its site, the paper in Shelf/arXiv, and the code at its real repository. Existing playlist and bookmark-folder management remains where it already works.
2. **Browse should not require a search query.** Search is valuable for long catalogs and precise research questions, not as the mandatory way to see a dozen already-curated items.
3. **One immediate action per work:** opening the work, not a three-click series of profiles, evidence drawers and intermediate pages.
4. **Show provenance without clutter.** Short reason on the row, original citation/recommender quote and full discussion in detail view. Distinguish recommendation from mere mention.
5. **Prioritize editorial substance over feed mechanics.** Explain depth, prerequisites, intellectual payoff, and whether a work is outdated. Do not optimize for watch minutes, view counts or clickthrough.
6. **Keep already-collected work visible and usable.** Support reopening a paper or saved work. Preserve past human reviews and source identities during any UI refactoring.
7. **No unexpected import or publication.** Private Youtube/Chrome data, annotations, tokens, history and ratings stay in existing private-local boundaries. An external source link is not permission to fetch a person's private playlist or upload anything.
8. **Keep controls scarce.** Modes should solve different decisions; omit duplicate filters and decorative status counters. Provide a default view with useful content before presenting options.
9. **Respect the difference between freshness and relevance.** New upload, renewed HN discussion, personal revisit, and recently added to our own index are four different dates/events.
10. **Do not require new services or a crawler** to render a convincing prototype from the materials already present.

## 6. Next work: UI specification first, no crawl

This is the actual next phase, **replacing any implication in earlier plans that the next task should expand acquisition**.

**Step 1 — Consolidate the idea list.** Review U01–U09, I01–I04, H/T/K and C01–C06. Keep the distinction between personally endorsed, outside inspiration and proposed synthesis. Add explicit user decisions as they emerge; do not label a proposal “approved” by default.

**Step 2 — Make two or three minimal UI alternatives using existing private-local data**, without gathering new channel/video lists:
- A **compact mixed-source reading list** (title, explanation, provenance, direct link).
- A **Hume-like creator overview** (editorial reason and specific example video) with optional detail.
- A **HackerTube-like browse mode** (evergreen and recency evidence, optional preview), *only if existing records have real evidence for the labels*.

Prefer screenshots of the actual local implementation during evaluation; never fabricate screenshots and describe them as real. These are mockup/experiment options, not authorization to replace the existing interface now.

**Step 3 — Compare and combine, not expand.** Inspect actual sample questions and the current 52-card/18-work corpus locally. Check: how fast is it to find an interesting work? Does the reason make sense? Does it open directly? Can the user find something worthwhile without a specific query? Are compact and detailed views understandable? Does the tool avoid redundant organization alongside YouTube/Chrome?

**Step 4 — Implement the smallest combined UI slice only after design review.** Reuse the present Learning Queue endpoint, private storage and source/feedback model. No new crawler, scheduled feed, bulk video import, full-history fetch, broad ontology rewrite, model-powered ranking or merger of repositories. Run normal tests, screenshot/browser checks, public/private isolation checks and preserve existing feedback.

### Explicitly deferred

- Another 150-channel or 100-site campaign, or importing all of HackerTube's exported video rows.
- Recreating Youtube subscriptions, playlists, Watch Later, playback, or Chrome folders as our own system.
- Large-scale personalized scoring retraining, embeddings, transcripts for every video, live feed ingestion or background monitoring.
- Automatic multi-device synchronization of private browsing history/feedback beyond an explicitly agreed design.
- Expanding the public catalog before the selection UI is useful.

## 7. Decision log — update this instead of growing competing prompts

| Date | Decision | Status |
| --- | --- | --- |
| 2026-11-07 | Keep both repositories; use Discovery as a cross-media selection layer over Shelf and existing research. | Working architecture |
| 2026-11-07 | **No large crawl next**; concentrate on combining the best presentation and suggestion concepts. | Explicit user direction |
| 2026-11-07 | User is experienced with YT channels/playlists and Chrome bookmark folders; complementary discovery is the goal. | Explicit user direction |
| Pending | Browse and Investigate as equal entry points? | Proposed |
| Pending | Compact list by default with expandable editorial/visual detail? | Proposed |
| Pending | HN longevity + named-curator explanation as separate evidence facets? | Proposed |
| Pending | Which external ideas add enough value to justify implementing them? | Needs evaluation |

## Related documentation

- [Previous broad next-steps and candidate sources](LEARNING_DISCOVERY_NEXT_STEPS_2026-11-07.md): useful reference, but its discovery/crawl phases are **deferred** by this file.
- [Learning Queue user guide](../guides/learning-queue.md) and [implementation status](implementation_status.md): what is currently implemented versus proposed.
- [Merged Discovery research plan](../MERGED_PROJECT_PLAN.md): background goals, not instructions to start its large research stages now.
- [HackerTube original](https://hackertube.org/about), [Karpathy's explanation](https://karpathy.bearblog.dev/hacker-tube/), [Hacker News participants' ideas](https://news.ycombinator.com/item?id=50319510), [Tristan Hume's channel reviews](https://thume.ca/2026/11/01/youtube-tier-list-2026/), and [the separate append-and-review idea](https://karpathy.bearblog.dev/the-append-and-review-note/).

**Success condition for the design:** a reader immediately sees *something worth exploring*, understands *why it appears*, can follow its original link in one click, and can remember a personal judgment without creating a redundant new way to organize YouTube or Chrome.
