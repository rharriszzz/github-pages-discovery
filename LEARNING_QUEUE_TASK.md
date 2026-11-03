# Codex implementation task — a practical private Learning Queue

Prepared 2026-11-03 for `rharriszzz/github-pages-discovery`.

## User outcome — not another research report

Build a simple, useful personal **"What should I read or watch next?"** interface. I should be able to open it in Windows Chrome (with the service running in WSL2), enter a question or subject I want to understand, optionally say how much time I have, and receive a **small, evidence-backed set of specific works** I can open immediately.

Use **both existing sources** from the start:
1. My **local arXiv Shelf catalog** (papers, titles, abstracts, identifiers, existing ratings; catalog may contain papers no longer downloaded locally).
2. The **private GitHub Pages Discovery research collection**, including the original 12 creator cards, 40 newer creator cards, representative *video* and *repository* links, concept trails, bookmarked/reviewed evidence where accessible, and my existing reviews.

**Do not assume everything worth learning is on arXiv.** Papers, videos, GitHub repositories, worked examples, personal technical articles, interactive demos, and unfamiliar concepts are all first-class learning material. The app must not force the user through a paper or creator profile when a specific tutorial, video, or code example is the appropriate starting point.

The existing discovery experiment produced 52 creator cards and many underlying investigations, but most detailed personalized material was intentionally **not published**. Inspect the existing private local database and `creator_research_report.md` / `creator_review.json` / source snapshots on this computer, where available. Do not mistake the public aggregate reports for the complete research. If an underlying local artifact is absent, say so and reconstruct only from verifiable sources; never invent missing private findings.

## 0. Reconnaissance and safety first

- Check the local working tree, branches, unpushed changes, project documentation, existing CLI and creator-dashboard code, and current tests. Preserve previously collected creator evidence, source snapshots and all reviews. Do not replace or reset the SQLite database.
- Inspect `~/git/arxiv-shelf` **if present**, otherwise locate its working tree via safe local configuration or ask only if strictly necessary. Its default branch is `master`; Discovery is `main`. The arXiv Shelf repo is independently functional, with `catalog/` append-only event JSON and `catalog.Catalog.read_state()`, plus local PDF scanning and a separate browser edition.
- The arXiv Shelf GitHub repository is **public** and currently includes the portable paper catalog and ratings. Do not copy personalized Discovery details into it, rewrite its publication arrangement, sync it, modify its ratings, or change either repository's GitHub visibility as part of this task.
- Discovery's SQLite and other personalized evidence live outside Git, ordinarily under `~/.local/share/github-pages-discovery/`. They must stay outside Git and the public `docs/` deployment. Do not publish source histories, playlist memberships, private notes, or local PDF paths. Add tests for this boundary.
- Preserve existing creator review functionality; choose a UI architecture that reuses local server components and data models instead of duplicating code.

## 1. The first-run workflow should be effortless

The first screen is **not** a list of hundreds of creators. It asks:

> **What would you like to learn or investigate?** [free-text query]

Provide lightweight optional controls:
- **Goal:** quick overview / understand deeply / revisit something saved / explore adjacent ideas.
- **Time available:** short (~10–15 min) / medium (~30–45 min) / substantial (one hour or more). These are user time budgets; individual durations can be unknown.
- **Format:** any / watch / read / interactive example or code.

The form should work with no filters selected. Search can draw from familiar names, papers, GitHub projects, video descriptions, concepts and their evidence trails. If no exact hits, show a clearly labeled adjacent suggestion or an informative empty state rather than a bogus match.

Results: initially **3–5 high-quality suggestions**, not a huge scrolling page. For each:
- Specific work title and **working source link**, content type, author/creator, and provenance ("Your arXiv Shelf", "Earlier creator research", or "Newly researched").
- A compact, intelligible reason: **what you would learn**, why it relates to the query, and where the relation comes from.
- Practical effort/time estimate or **duration unknown**, and prerequisites where known. Do not invent video lengths, reading time, difficulty or review status.
- Actions: **Open**, **Save for later**, **Already read/watched**, **Useful**, **Not for me**, with optional notes. Open should not automatically mark it as completed.
- One optional **related concept** or deeper follow-up path, separated from direct recommendations, so the screen remains manageable.

Make reviewed/dismissed items less likely to recur, but do not erase them. Explicit decisions override weak inferred preference. "Saved", "liked", "watched", "rated" and "already familiar" have different meanings; do not translate one automatically into another. Clearly distinguish "locally collected paper" from "PDF currently on this machine".

Keep the usual creator cards accessible as a secondary "Explore creators" view. Creator or paper drill-down may show richer evidence on demand, but the primary flow is **query → shortlist → open a specific resource**.

## 2. Integration contract: read-only arXiv Shelf adapter

Build a small isolated adapter that loads the current portable arXiv Shelf `catalog/` event store with its correct alias and rating semantics, preferably using its existing `Catalog.read_state()` through a carefully contained import or equivalent tested parsing. Do **not** read an outdated `dist/catalog.json` snapshot by default. Do not rewrite `catalog/` or use the Git sync button.

Expose just normalized local metadata needed for recommendations: stable arXiv ID/version, title, authors, abstract, publication date, star rating (including unrated), and whether its local PDF is known **only if safely verified**. No local absolute paths in browser output. Never assume a paper has been read because it was downloaded or rated.

The arXiv Shelf working directory must be configurable and may be absent. Fail gracefully: Discovery-only recommendations still work. Allow manual refresh, cache/checkpoint safely and show data freshness. If arXiv Shelf is running on localhost 8765, opening via its legitimate UI might be possible; otherwise use stable arXiv abstract/PDF links. Do not bypass arXiv Shelf's local session-token PDF protections.

The adapter should preserve paper IDs and version semantics and avoid duplicate entries from multiple catalog event files or multiple local filenames. Ratings are read-only to Discovery in phase one. Make synchronization/ratings-writeback a separately reviewed future option.

## 3. Reuse private Discovery research and add substantive research

Inspect current private source snapshots, `creator_collection`, creator dossiers/research reports, `learning_concepts` and retained links to actual GitHub projects and YouTube videos. Treat public `reports/creator-expanded.md` as aggregate coverage, not the complete corpus.

**Do some fresh, bounded research, not just UI development.** Research and independently revalidate a manageable sample of **about 12–20 concrete learning resources**. Start with sources already cited in the private 52-card creator set and selected arXiv Shelf entries, then add a few genuinely useful adjacent resources when warranted.

At a minimum, attempt a balanced selection of:
- 4–6 *specific* YouTube talks/series/videos already linked in creator research;
- 4–6 *specific* GitHub projects/demonstrations/technical articles;
- 3–5 arXiv Shelf papers, including some rated or clearly relevant to current research;
- several concept bridges that connect these sources (not merely similar title words).

Counts are targets: avoid filler or duplicate evidence. Prefer official creator/channel/repository/publisher sources, stable URLs, meaningful titles and actual inspectable explanations or documentation. If only metadata is available, say evidence is limited; do not claim to have fully watched videos or verified all technical claims. Preserve source URLs and retrieval dates in the **private** research cache. Respect API quotas, robots and rate limits; do not execute candidate repositories or indiscriminately download PDFs or transcripts.

Use this research to demonstrate *real* cross-source recommendations. For example, a query about Reversi evaluation might surface an existing creator's search-engine implementation, a useful lecture, and (only if relevant) a paper; a question about vortex simulations may surface code, an explanatory video, or a mathematical method. Do not manufacture these examples if the corpus does not support them.

## 4. Ranking and explainability

- Use source-linked subjects, methods, learning questions, explicit human reviews, bibliographic metadata, and lightweight text retrieval as a transparent first implementation. A vector database or external LLM service is **not required**. If richer reasoning is proposed, compare it with the simple baseline on real test queries before adding it.
- Rank **topical fit**, **methodological fit**, **explanatory usefulness**, **novelty**, **evidence strength**, and **effort for this session** separately. Don't present a numeric precision score before calibration.
- Diversify the shortlist across source types and creators when it improves usefulness; never impose arbitrary diversity that hides clearly better material. Distinguish a user's *current research question* from their long-term general interests.
- Preserve provenance and uncertainty for every explanation. Don't label a subject as an established preference just because a single book or historical video mentioned it.
- Avoid conflating candidates with entire creators: a user is selecting a particular work to open, not deciding whether the creator deserves a general endorsement.

## 5. Architecture and UI

Prefer an incremental addition to the current private Python/SQLite and vanilla HTML/CSS/JavaScript architecture. A practical name is **Learning Queue**. Expose a simple command or launcher, e.g.:

`python3 -m pagefinder.local serve-learning --port 8767`

or reuse the existing loopback server with an obvious Learning Queue home page and Creators secondary navigation. Choose the least disruptive approach after inspecting tests and existing ports (arXiv Shelf generally uses 8765, creator dashboard 8766). Support opening the address in Windows Chrome from WSL2. Provide one short documented command and, if useful, a Windows-friendly launcher. Do not require the user to run separate rebuild/import steps every time they want a recommendation.

Use a light background, readable typography, succinct cards, fast search, good keyboard interaction, responsive desktop/tablet layout, obvious feedback controls, and expandable details. Avoid research jargon and long score explanations on the main page.

Local search and review must work **offline against cached material**. External research should be an explicit refresh/action, not an uncontrolled background crawl. No unsolicited scheduled tasks, paid services or OAuth scope expansion. No private information served on a public interface; bind to loopback and keep existing Host/Origin/CSRF protections.

## 6. Deliverable phases and acceptance

**A. Data bridge** — Inspect and import the local arXiv Shelf *read-only*, plus the full existing private Discovery creator collection, into a unified work-level search index. Preserve source IDs, user ratings and reviews without copying private information into Git. Test idempotent refresh, duplicate handling and missing-source behavior.

**B. Working interface** — Deliver a useful local Learning Queue with free-text question, optional goal/time/format, immediate 3–5 source-linked suggestions, actions and saved state. Ensure browsing is quick and clear. Keep existing creator review operational.

**C. Research demonstration** — Populate a bounded set of researched individual works (as described above) and evaluate 5 representative *real queries* drawn from my interests: e.g., inverse rendering, numerical vortex validation, Reversi search, music transcription, and mathematical physics. At least some recommendations should be from GitHub/YouTube **without requiring arXiv**. Record unsupported queries honestly.

**D. Verification** — Use tests for adapter/alias/rating behavior, search/retrieval, explanation links, review durability, private-data boundaries, local socket/HTTP access, startup errors and offline mode. Inspect the page in a browser on desktop and at narrow width; verify Windows-to-WSL localhost if available. No fake test fixtures masquerading as real discoveries.

**E. Reports and handoff** — Produce a concise private report documenting the actual sample resources, source trails, ranked example results, limitations, time/effort unknowns, cached research and what further research would improve. Publish only privacy-safe implementation documentation and aggregate stats. Commit and push reviewed public-safe code and documentation to **Discovery's private repository**; do not alter arXiv Shelf unless a small interface is demonstrably needed, and ask before making changes there.

## 7. Practical success test

The user should be able to open the application, type a question such as "What is a good way to understand numerical stability in fluid simulations?", get a shortlist that includes a specific readable/watchable resource, click it, and later return to see which resources were saved or marked useful.

**Do not turn this phase into a giant taxonomy project, a blanket paper recommender, an arXiv-first funnel, a new hosted website, or an all-repository merge.** The goal is a working, pleasant-to-use learning chooser grounded in the collections and research already available.

After implementation, report what actually works, the exact WSL2 launch command and address, which real sources were used, the number of independently verified items, remaining limitations, and any user action needed. If a dependency or private artifact is absent, complete the rest of the useful work and state the limitation.
