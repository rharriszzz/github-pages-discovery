# Research plan — GitHub Pages ownership and interest overlap

Date: 2026-11-02. This document distinguishes verified observations, proposed methodology, and unknowns.

## The actual research questions

1. Among **discovered** public `*.github.io` websites, what proportion belongs to GitHub **User** accounts versus **Organization** accounts? Show counts with denominators and discovery methods. It is not defensible to extrapolate that ratio to all GitHub Pages sites from a keyword-biased sample.
2. What subjects do the sites cover, and how do those subjects intersect the user's interests? Distinguish exact topic matches, adjacent methodological matches, and superficial keyword coincidences.
3. What genuinely useful websites and *people/projects* warrant further reading? Account `type` alone does not identify the actual people behind the site.
4. Which findings would expand the user's interests rather than merely recapitulate them? Example: numerical CFD validation tools could matter to the Navier–Stokes projects without mentioning an identical vortex setup.

## Discovery strategies, in order

### A. Proof-of-concept / seed list

Start with the seven researched pages in `data/sites.json`, grouped by repo and account. These are known examples; the page content is a manual research summary, not a scraped HTML artifact.

### B. Targeted repository discovery

Search repositories by broad domain words, `in:readme`/topic qualifiers and `github.io in:name`. GitHub repository-search API returns limited result windows; **record `total_count`, pagination and truncation**. Require an account/repository mapping, validate the canonical site, and deduplicate URLs and account IDs. Account type comes from the GitHub API owner metadata. Filter inactive, unrelated boilerplate and repeated starter-template clones. Sample both high and low rankings.

### C. Less biased discovery sample

Explore **Common Crawl** public data, while documenting that crawl coverage is not universal and not a randomized census of the web. A large number of observed distinct subdomains exists, but any given crawl omits sites. Investigate index querying or published public datasets, their costs, staleness, terms, and reproducibility. Do not mistake a crawler index for all active Pages sites.

Consider GitHub repository `created:` windows as an additional sampling frame, but never treat search rank as random. Even date partitions with 1,000-result caps need documented coverage checks. Record sampling method and measured drop rates for every batch. It may be productive to study a few thousand sites well instead of vaguely claiming to study all sites.

### D. Deeper interpretation of interesting sites

For top candidates, inspect page title, descriptions, internal headings, associated repository README/topics, a small number of recent non-fork public repos by the same account, and recent update date. Extract short evidence passages or source links. Distinguish `site relevance`, `owner's portfolio relevance`, `novelty`, `quality/rigor` and `current activity`; these are distinct axes. Do not infer sensitive personal attributes.

## Ownership taxonomy

- `github_account_type`: `User`, `Organization`, or `Unknown`, from GitHub API field with provenance.
- `site_relation`: personal/organization homepage, project page, custom-domain redirect (uncertain), or unknown.
- `maintainer_structure`: **unknown by default**. If a site explicitly says 'maintained by lab/team X', quote source and label as a claim by the site, not an independently verified legal identity.
- `discovery_source`, `retrieval_timestamp`, `site_status`, `repository`, `canonical_url`, and `content_confidence` as separate, auditable fields.

## Proposed evaluation

Create at least 100 diverse manually reviewed sites drawn from multiple search/sampling frames. Two dimensions:

- Classification: GitHub User/Organization ground truth (near-exact if API says so); homepage/project mapping accuracy; site reached; duplicate detection.
- Interest: 0 = unrelated, 1 = adjacent, 2 = directly relevant, 3 = particularly useful. Evaluate precision among top 20/50/100, coverage across each user interest, novelty and selection bias. A numerical score alone is insufficient.

Make it straightforward to label a site `keep`, `skip`, `needs review`, with notes. Never overwrite manual decisions with a new automatic ranking. Preserve examples where the tool fails and why.

## Engineering budget / politeness

- GitHub's documented REST primary limit is generally 60 requests/hour unauthenticated or 5,000/hour with a user token, but search endpoints have separate restrictions, and secondary rate limiting also applies. The Actions `GITHUB_TOKEN` can have different limits.
- API calls checkpoint and stop on 403/429, expose `Retry-After` / rate-limit reset information, and do not circumvent limits. Prefer caching, deduplication, and conditional requests.
- Fetch only a bounded amount of public content from each site and honor robots.txt. Reject off-domain redirects until a reviewer approves them. Respect robots and avoid high crawl concurrency.
- An automatic page load can change content or run scripts. Fetching plain HTML is safer than browser execution for the first pass. Never execute code found on a discovered site.

## What the initial pilot cannot establish

- The total number of existing GitHub Pages websites.
- A representative User/Organization fraction.
- How many owners share the user's interests, since the seven initial examples were deliberately chosen for overlap.
- That a site uses the main linked GitHub repo as its actual deployment source.
- That a one-paragraph site description characterizes all the owner's interests.

## Deliverable milestones

1. **Milestone 1 (included)**: working starter implementation, verified-owner sample, transparent heuristic, export, docs, unit tests.
2. **Milestone 2**: small live crawl with robust error categories, tested HTTP/robots behavior, GitHub REST validation, site-source mapping, more tests and verified 100+ diverse site records.
3. **Milestone 3**: coverage-aware multi-source discovery and stratified evaluation, manual labeling, better relevance ranking with concrete citations and explanatory rationales.
4. **Milestone 4**: periodic incremental updates, change detection and a polished public catalog with filters by topic, owner and usefulness; only if the previous milestones are credible.
