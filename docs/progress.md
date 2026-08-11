\## Phase 1A — Live GitHub Repository Connection



\### Goal

Connect ProjectPulse AI to a real GitHub repository through the GitHub REST API and verify reliable repository metadata retrieval.



\### What was implemented

\- Created the Python project package under `src/projectpulse/`.

\- Added `requests` and `python-dotenv` dependencies.

\- Configured local environment variables through `.env`.

\- Added `GitHubClient` for authenticated GitHub REST API access.

\- Added validation for missing GitHub configuration.

\- Added timeout and connection error handling.

\- Added HTTP error handling for 401, 403, 404, and unexpected status codes.

\- Verified live metadata retrieval from the ProjectPulse AI repository.



\### Successful verification

Repository successfully fetched:



\- Repository: `AmeySomade/Project-Pulse-AI`

\- Default branch: `main`

\- Stars: `0`

\- Open issues: `0`



GitHub currently returned `Language: None`, which is acceptable at this early stage because the repository contains very little committed source code.



\### Issue encountered

The first API request returned:



`404 Repository not found`



The generated API URL incorrectly used:



`ProjectPulse Local Development`



as the GitHub repository owner.



\### Root cause

`ProjectPulse Local Development` was the personal access token name, but it was mistakenly entered as `GITHUB\_OWNER`.



\### Fix

Updated `GITHUB\_OWNER` in the local `.env` file to the actual GitHub username.



After the fix, the GitHub API successfully returned repository metadata.



\### Error-handling experiment

Tested the client with a deliberately nonexistent repository:



`projectpulse-definitely-not-real-404-test`



The GitHub API returned HTTP 404.



The client correctly converted it to:



`RuntimeError: Repository not found. Check GITHUB\_OWNER and GITHUB\_REPO.`



The exception chaining was later suppressed using `raise ... from None` so internal HTTP traceback noise is not exposed to the caller.



\### Result

Phase 1A successfully establishes the first live external-system integration for ProjectPulse AI.



ProjectPulse can now communicate with GitHub programmatically instead of operating only on static/local data.

## 2026-08-09 — GitHub Data Ingestion Pipeline

### Goal

Build the first production-style data ingestion pipeline for ProjectPulse using live GitHub repository activity.

### Completed

* Extended the GitHub API client to retrieve:

  * Issues
  * Pull requests
  * Commits
* Added pagination support for GitHub API responses.
* Added filtering so pull requests returned through the Issues API are not duplicated.
* Built a normalization layer that converts different GitHub objects into a common ProjectPulse document schema.
* Added JSON persistence for normalized documents.
* Added loading support for previously ingested documents.
* Created automated ingestion tests.

### Current Data

* Issues ingested: 0
* Pull requests ingested: 0
* Commits ingested: 2
* Total normalized documents: 2

### Validation

Automated tests:

* Document existence test — PASS
* Standard schema validation — PASS
* Unique document ID validation — PASS
* Storage round-trip validation — PASS

Result: **4/4 tests passed**

### Design Decisions

ProjectPulse stores normalized documents instead of directly using raw GitHub API responses. This provides a common internal schema that future retrieval, embedding, filtering, citation, and additional connector layers can consume without depending on GitHub-specific JSON structures.

Automated tests do not repeatedly call the live GitHub API. Live connectivity was verified separately, while deterministic local tests validate the ingestion contract and persistence layer.

### Issues / Learnings

GitHub's Issues API can also include pull requests. Pull request objects are therefore filtered from issue results and retrieved separately through the Pull Requests endpoint to avoid duplicate documents.

### Next

Build the retrieval/indexing layer over the normalized ProjectPulse documents.

@"

## 2026-08-10 - Semantic Retrieval Baseline

### Goal
Build the first RAG retrieval layer for ProjectPulse using normalized GitHub project data.

### Implemented
- Added document chunking with configurable chunk size and overlap.
- Preserved GitHub metadata across chunks.
- Added local semantic embeddings using sentence-transformers/all-MiniLM-L6-v2.
- Added persistent vector storage using ChromaDB.
- Added natural-language semantic retrieval.
- Added retrieval evaluation using Hit@1 and Mean Reciprocal Rank (MRR).
- Cached the embedding model to avoid loading model weights for every query.

### Architecture
GitHub API -> Normalization -> Chunking -> Embeddings -> ChromaDB -> Semantic Retriever

### Retrieval Baseline
Evaluation queries: 4
Indexed documents: 2
Indexed chunks: 2
Embedding dimensions: 384

Correct at Rank 1: 4/4
Hit@1: 1.000
MRR: 1.000

This is a development sanity baseline only because the current corpus contains just two GitHub documents. It should not be interpreted as 100% production retrieval accuracy.

### Retrieval Distances
- GitHub integration query: 0.3019
- Architecture query: 0.2593
- MVP scope query: 0.1370
- Authenticated repository access query: 0.4137

### Testing
- Chunking tests: 4/4 passed
- Existing ingestion tests: 4/4 passed
- Full regression suite: 8/8 passed

### Issue Encountered
Python imports initially failed with:
ModuleNotFoundError: No module named 'src'

Cause:
The project uses a src-layout, but modules were being executed/imported as though src itself were the Python package.

Fix:
Standardized imports around the projectpulse package and executed modules with:

`$env:PYTHONPATH="src"`
`python -m projectpulse.<module>`

### Performance Improvement
During the first retrieval evaluation, Sentence Transformer model weights were loaded once for every query.

The embedding model loader was changed to use an LRU cache, so the model is now loaded once per Python process and reused across queries.

Retrieval quality remained unchanged after optimization:
Hit@1: 1.000
MRR: 1.000

### Current Limitation
The evaluation corpus is extremely small: 2 documents and 4 evaluation queries. A larger GitHub corpus containing commits, issues, pull requests, README/documentation changes, and other project events will be required for a meaningful retrieval benchmark.

## August 11, 2026 — Agentic Query Planning and Multi-Step Retrieval

### Goal

Extend the existing semantic RAG baseline into an agentic retrieval pipeline capable of decomposing broad project questions into focused investigation queries and collecting evidence across multiple retrieval calls.

### Components Added

* `src/projectpulse/planner.py`

  * Deterministic query-planning baseline.
  * Detects intents such as project changes, blockers, timelines, pull requests, features, and project status.
  * Decomposes broad queries into focused retrieval sub-queries.

* `src/projectpulse/agentic_retriever.py`

  * Executes semantic retrieval for every planned sub-query.
  * Aggregates retrieved evidence.
  * Deduplicates repeated chunks using `chunk_id`.
  * Tracks which investigation queries matched each chunk.
  * Ranks evidence using query match count and semantic distance.

* `src/projectpulse/evaluate_agentic_retrieval.py`

  * Compares single-query semantic retrieval with multi-query agentic retrieval.
  * Measures evidence coverage, retrieval calls, semantic distance, and latency.

* `tests/test_planner.py`

* `tests/test_agentic_retriever.py`

### Bugs Found and Fixed

#### 1. `ProjectPulse` incorrectly triggered pull-request intent

A status query such as:

`What is the current status of ProjectPulse?`

was incorrectly classified as `pull_requests`.

Cause:

The planner originally searched for `"pr"` using substring matching. Since `ProjectPulse` begins with `"Pr"`, the abbreviation matched inside the project name.

Fix:

Replaced substring matching for `PR` and `PRs` with regex word-boundary matching.

A regression test was added to ensure that the word `ProjectPulse` does not trigger pull-request intent.

#### 2. Broad intent overrode specific intent

The query:

`Which PR was recently merged?`

was initially classified as `project_changes` because the broad keyword `recently` was checked before the more specific pull-request intent.

Fix:

Intent priority was changed so specific intents such as pull requests, blockers, timeline, and features are checked before broad project-change intent.

A regression test was added for this case.

### Test Results

Planner tests:

`8/8 passed`

Agentic retriever tests:

`4/4 passed`

The tests validate intent detection, query decomposition, empty-query handling, evidence deduplication, multi-query tracking, evidence ranking, and invalid retrieval parameters.

### Baseline vs Agentic Retrieval Evaluation

Queries evaluated: `3`

| Metric                         | Baseline |   Agentic |
| ------------------------------ | -------: | --------: |
| Average unique evidence chunks |     2.00 |      2.00 |
| Total retrieval calls          |        3 |        13 |
| Average latency                | 52.64 ms | 199.17 ms |

Evidence expansion:

`0.00%`

Agentic latency multiplier:

`3.78x`

### Interpretation

Agentic retrieval successfully decomposed broad questions and executed multiple focused semantic searches, but it did not increase unique evidence coverage on the current corpus.

The current vector store contains only two evidence chunks, meaning both baseline and agentic retrieval ultimately have access to the same limited evidence.

Therefore, the experiment identified corpus coverage—not query decomposition—as the current bottleneck.

The agentic approach also introduced a measurable performance trade-off:

* Retrieval calls increased from 3 total baseline calls to 13 agentic calls.
* Average latency increased from 52.64 ms to 199.17 ms.
* Agentic retrieval was approximately 3.78× slower.

This result establishes a measurable baseline for future experiments after the GitHub corpus is expanded with additional commits, issues, pull requests, and project documents.

### Current Limitation

The present two-chunk corpus is too small to fairly evaluate whether multi-query planning improves evidence recall or retrieval coverage.

A larger and more diverse corpus is required before making claims about retrieval-quality improvement.
