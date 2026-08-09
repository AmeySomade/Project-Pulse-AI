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
