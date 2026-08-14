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

## August 12, 2026 — MCP Tool Integration and LangGraph Orchestration

### Goal

Connect ProjectPulse's existing retrieval capabilities to the Model Context Protocol (MCP) and orchestrate those tools through LangGraph without rewriting the retrieval pipeline.

### Components Added

* `src/projectpulse/mcp_server.py`
  * Added a local ProjectPulse MCP server using FastMCP.
  * Exposes `search_project_history` for focused semantic retrieval.
  * Exposes `investigate_project` for planner-driven multi-step retrieval.
  * Uses `stdio` transport for local client/server communication.

* `src/projectpulse/mcp_client.py`
  * Added an MCP client using `MultiServerMCPClient`.
  * Launches the ProjectPulse MCP server as a separate Python subprocess.
  * Discovers MCP tools dynamically through the protocol.
  * Loads discovered MCP tools as LangChain-compatible tools.
  * Verified real MCP tool invocation over `stdio`.

* `src/projectpulse/langgraph_agent.py`
  * Added a LangGraph `StateGraph`.
  * Reuses the existing deterministic ProjectPulse planner for intent detection.
  * Routes focused/general questions to `search_project_history`.
  * Routes complex project questions to `investigate_project`.
  * Invokes the selected capability through the MCP tool interface rather than directly calling retrieval functions.

* `tests/test_langgraph_agent.py`
  * Added isolated LangGraph routing tests using lightweight fake MCP tools.
  * Avoids launching ChromaDB, Sentence Transformers, and MCP subprocesses during every unit-test run.

### Architecture

Current execution path:

`User Query -> LangGraph -> Planner -> Conditional Route -> MCP Tool -> Existing ProjectPulse Retrieval`

Focused query path:

`Query -> general intent -> search_project_history -> MCP -> semantic retriever`

Complex query path:

`Query -> status/changes/blockers/timeline/etc. -> investigate_project -> MCP -> planner + multi-query retrieval`

### MCP Verification

The MCP client successfully discovered both exposed ProjectPulse tools:

* `search_project_history`
* `investigate_project`

Result:

`2/2 expected MCP tools discovered`

Real MCP invocation was verified for both capabilities.

#### Direct Retrieval Test

Query:

`What work was done on GitHub integration?`

Result:

* MCP tool selected: `search_project_history`
* Results returned: `2`
* Rank 1 evidence: `feat: add authenticated GitHub repository integration`
* Rank 1 semantic distance: `0.301940381526947`

#### Multi-Step Investigation Test

Query:

`What changed in ProjectPulse and what is the current project status?`

Planner result:

* Detected intent: `status`
* Generated sub-queries: `4`
* Unique evidence chunks returned: `2`

Result:

`MCP CLIENT VERIFICATION PASSED`

### LangGraph Routing Verification

Two end-to-end graph routes were manually verified.

#### Focused Query

Query:

`What work was done on GitHub integration?`

Detected intent:

`general`

Selected MCP tool:

`search_project_history`

#### Complex Query

Query:

`What changed in ProjectPulse and what is the current project status?`

Detected intent:

`status`

Selected MCP tool:

`investigate_project`

Result:

`LANGGRAPH + MCP VERIFICATION PASSED`

### Automated Testing

New LangGraph routing tests:

`4/4 passed`

The tests validate:

* General queries route to direct semantic retrieval.
* Status queries route to multi-step investigation.
* Missing required MCP capabilities fail fast.
* Empty queries are rejected.

Full ProjectPulse regression suite:

`24/24 passed`

Regression runtime:

`5.49 seconds`

No previously implemented ingestion, chunking, planner, or agentic-retrieval tests regressed after introducing MCP and LangGraph.

### Design Decisions

#### MCP wraps existing capabilities instead of replacing them

The semantic retriever and agentic retriever remain the source of retrieval behavior.

MCP provides a standardized tool boundary around those capabilities.

This keeps ProjectPulse modular:

`Orchestration != Tool Protocol != Retrieval Implementation`

The retrieval layer can therefore evolve independently from the agent orchestration layer.

#### LangGraph owns orchestration

LangGraph is responsible for:

* maintaining workflow state;
* interpreting the planner result;
* selecting the execution branch;
* invoking the appropriate MCP capability.

Retrieval logic remains outside the graph.

#### ToolNode intentionally not used yet

The current ProjectPulse version does not yet have an LLM producing native tool calls.

Using LangGraph `ToolNode` at this stage would require manually manufacturing model-style tool-call messages.

Instead, the current graph uses deterministic conditional routing based on the existing planner.

When an LLM with native tool calling is introduced, the architecture can evolve to:

`LLM -> tool call -> ToolNode -> MCP tool`

without rewriting the MCP server or retrieval layer.

#### Unit tests do not launch the real MCP stack

Real MCP discovery and execution were verified separately through the integration client.

LangGraph unit tests use fake MCP tools so the regression suite remains fast and deterministic rather than repeatedly starting:

* an MCP subprocess;
* ChromaDB;
* Sentence Transformers.

### Dependencies Added

Pinned Day 4 dependencies:

* `langgraph==1.2.11`
* `langchain==1.3.15`
* `langchain-mcp-adapters==0.3.2`
* `mcp[cli]==1.29.0`

### Issue / Learning

Importing the MCP server produced a Pydantic settings warning related to an unresolved forward reference in the MCP dependency stack.

The warning was non-fatal.

Verification showed that:

* the FastMCP server object was created successfully;
* MCP tool discovery succeeded;
* both MCP tools executed successfully;
* LangGraph orchestration succeeded;
* all automated tests passed.

The warning is therefore recorded as a dependency-level observation rather than treated as an application failure.

### Current Limitation

Tool selection is currently deterministic.

The existing ProjectPulse planner detects intent and LangGraph uses conditional edges to choose an MCP tool.

An LLM is not yet autonomously reasoning over tool descriptions or generating native tool calls.

The current implementation therefore establishes the MCP and LangGraph orchestration foundation without claiming fully autonomous LLM-driven tool selection.

The retrieval corpus also remains limited to two indexed GitHub evidence chunks, so MCP and LangGraph improve architecture and extensibility but do not yet improve retrieval coverage.

### Result

ProjectPulse now has a functioning protocol-based agent architecture:

`LangGraph orchestration -> MCP tools -> ProjectPulse retrieval`

The system successfully crosses a real process boundary using MCP `stdio`, dynamically discovers available ProjectPulse tools, invokes them through the protocol, and routes user questions to the appropriate capability through LangGraph.

This completes the MCP + LangGraph integration foundation.


---

## Day 5 - Selective Short-Term and Long-Term Memory

### Objective

Extend the existing ProjectPulse LangGraph + MCP architecture with memory while avoiding the common anti-pattern of storing every conversation message permanently.

The memory system was designed around two different responsibilities:

`short-term conversation context != persistent project knowledge`

### Architecture

The LangGraph workflow was extended from:

`Planner -> MCP tool -> Result`

to:

`Load memory -> Planner -> MCP tool -> Update short-term memory -> Result`

The memory layer contains two components.

#### Short-Term Memory

`ShortTermMemory` maintains a bounded window of recent user and assistant interactions.

Properties:

* exists only during the running Python process;
* maintains recent conversational context;
* automatically removes older entries when the configured limit is exceeded;
* stores only a bounded representation of retrieval results to avoid uncontrolled context growth.

The default LangGraph configuration keeps the six most recent conversation items.

#### Long-Term Memory

`MemoryStore` provides persistent JSON-backed memory.

Long-term memory is intentionally selective.

The current MVP stores information belonging to four categories:

* decision;
* blocker;
* preference;
* status.

Examples of information worth persisting include architecture decisions, implementation blockers, persistent user preferences, and completed project milestones.

Normal questions and conversational noise are not stored.

### Selective Memory Policy

A lightweight rule-based classifier currently determines whether information should enter long-term memory.

Examples:

`We decided to use MCP for tool integration.`

is classified as:

`decision`

while:

`What changed in ProjectPulse?`

is not persisted.

This prevents the memory store from becoming an unbounded transcript of every user interaction.

### Persistent Memory Design

Long-term memories are stored as structured records containing:

* deterministic memory ID;
* content;
* category;
* UTC creation timestamp;
* source query;
* optional metadata.

Memory IDs are generated using a SHA-256 fingerprint derived from normalized content and category.

This allows duplicate persistent memories to be detected without relying on random identifiers.

Writes use a temporary JSON file followed by replacement of the target file so partially written memory files are less likely to corrupt the persistent store.

### Memory Retrieval

The current MVP uses lightweight token-overlap retrieval.

For each user query:

1. query tokens are extracted;
2. stored memories are compared using token overlap;
3. memories with no overlap are discarded;
4. matching memories are ranked by overlap and recency;
5. the top relevant memories are placed into LangGraph state.

The graph now exposes:

`recent_context`

for temporary conversation history,

`relevant_memories`

for previously stored long-term knowledge relevant to the query, and

`stored_memory`

when the current user input creates a new persistent memory.

### LangGraph Integration

A new `load_memory` node executes before planning.

It:

1. validates the incoming query;
2. retrieves relevant existing long-term memories;
3. stores the current user turn in short-term memory;
4. applies the selective persistence policy;
5. exposes memory context to the remaining graph.

After either MCP execution branch, an `update_short_term_memory` node stores a bounded representation of the tool result.

The existing MCP routing logic remains unchanged.

General queries continue to use:

`search_project_history`

while complex project queries continue to use:

`investigate_project`.

Memory therefore extends orchestration without coupling itself to the MCP transport or retrieval implementation.

### Automated Verification

Memory unit tests:

`11 passed`

The tests cover:

* bounded short-term memory;
* decision classification;
* blocker classification;
* preference classification;
* status classification;
* rejection of normal questions;
* rejection of irrelevant statements;
* persistence across MemoryStore instances;
* memory deduplication;
* selective persistence;
* relevant memory search.

LangGraph memory integration tests:

`5 passed`

The integration tests verify:

* relevant long-term memory enters graph state;
* important user statements are persisted;
* normal questions are not persisted;
* short-term context survives across graph calls;
* invalid memory retrieval configuration is rejected.

Full regression suite:

`40 passed`

No existing ingestion, chunking, planner, agentic retrieval, MCP-routing, or LangGraph behavior regressed after adding memory.

### Import-Path Issue

During Day 5 testing, the project exposed inconsistent historical test imports.

Some tests imported:

`src.projectpulse...`

while newer application-style imports use:

`projectpulse...`

Temporarily setting `PYTHONPATH=src` fixed the new imports but caused older `src.projectpulse` imports to fail.

The root cause was therefore test import configuration rather than memory implementation.

A project-level `pytest.ini` was added with both the repository root and `src` directory on the pytest Python path.

This allows both historical and current import styles to work while preserving the existing test suite.

A future cleanup can standardize all imports to the package-style:

`projectpulse...`

### Runtime Memory Handling

The persistent runtime file:

`data/projectpulse_memory.json`

is excluded from Git.

This prevents machine-specific conversational memory from being committed to the repository while keeping static ingestion evidence such as the existing GitHub document corpus versionable.

### Design Decisions

#### Memory is separate from retrieval

Project history retrieved from GitHub and agent memory represent different information sources.

GitHub retrieval answers:

`What evidence exists in the project history?`

Memory answers:

`What useful context has the agent learned previously?`

They therefore remain separate components.

#### Memory does not modify MCP queries yet

Relevant memories are currently loaded into LangGraph state but are not blindly concatenated into retrieval queries.

This avoids contaminating semantic retrieval with potentially unrelated conversation history.

A later answer-synthesis layer can explicitly combine:

`retrieved project evidence + relevant memory + recent context`

when generating a final response.

#### JSON persistence is intentional for the MVP

The current memory corpus is small.

A JSON-backed implementation keeps behavior:

* inspectable;
* deterministic;
* easy to test;
* easy to debug.

Moving immediately to another vector database would add infrastructure without yet demonstrating measurable retrieval benefit.

The interface allows the persistence and retrieval implementation to be replaced later.

### Current Limitations

The long-term memory classifier is currently rule based.

It may miss useful information that does not contain one of the configured signals, and keyword matching can occasionally classify ambiguous statements incorrectly.

Long-term memory retrieval currently uses token overlap rather than embeddings.

Memory does not yet have:

* semantic similarity retrieval;
* importance scoring;
* memory decay;
* conflict resolution;
* entity/user namespaces;
* LLM-based memory extraction;
* memory-aware answer synthesis.

These are intentionally left as future improvements rather than being presented as capabilities already implemented.

### Result

ProjectPulse now supports both temporary conversational context and selective persistent project memory.

The architecture is now:

`LangGraph orchestration -> memory context + MCP tools -> ProjectPulse retrieval`

Memory is integrated into the workflow without replacing or coupling itself to the existing MCP and retrieval layers.

This completes the Day 5 memory foundation.

## Day 6 — LangSmith Observability and Agentic Retrieval Tracing

### Goal

Add production-style observability to the ProjectPulse agent pipeline using LangSmith without changing the retrieval or routing behavior of the system.

The objective was to make the execution path inspectable across:

`LangGraph -> MCP tools -> agentic retrieval`

and identify where latency is introduced during multi-step investigation.

### Baseline LangGraph Tracing

LangSmith tracing was enabled using:

`LANGSMITH_TRACING=true`

with traces grouped under the project:

`projectpulse-ai-dev`

The existing LangGraph workflow was automatically captured without adding tracing decorators to graph nodes.

A ProjectPulse status query produced the visible execution path:

`load_memory -> plan_route -> investigation -> update_short_term_memory`

The conditional routing function:

`choose_route`

was also visible underneath the planning stage.

This confirmed that LangGraph already provides useful node-level observability and that adding duplicate tracing decorators to existing graph nodes would only create unnecessary noise.

### MCP Tool Visibility

The first LangSmith trace exposed the LangGraph nodes but initially treated the `investigation` node as a black box.

The system internally performs an MCP tool call, but the real `investigate_project` tool was not initially nested underneath the graph node.

An initial attempt wrapped MCP calls with custom LangSmith `@traceable` functions.

This produced separate traces rather than correctly nested child runs.

### Python 3.10 Async Trace Context Issue

ProjectPulse currently runs on:

`Python 3.10.10`

During async execution, the custom tracing context was not automatically preserved between the LangGraph node and the child operation.

The attempted trace hierarchy became disconnected.

Instead of upgrading Python mid-project and risking dependency instability, the tracing configuration was explicitly propagated using LangGraph's `RunnableConfig`.

The graph nodes now accept:

`RunnableConfig`

and pass:

`config=config`

directly into the actual MCP-discovered LangChain tools.

This produced the desired trace hierarchy:

`investigation -> investigate_project`

and for focused retrieval:

`direct_search -> search_project_history`

This approach is also cleaner than creating artificial wrapper spans because LangSmith now displays the actual MCP tool names.

### Test Double Regression and Fix

Passing `RunnableConfig` into the real MCP tools caused two unit tests to fail.

The failures were:

`test_general_query_routes_to_direct_search`

and:

`test_status_query_routes_to_investigation`

The production MCP/LangChain tool interface now accepted:

`ainvoke(arguments, config=config)`

while the `FakeMCPTool` used by the tests only implemented:

`ainvoke(arguments)`

This caused:

`TypeError: FakeMCPTool.ainvoke() got an unexpected keyword argument 'config'`

The production implementation was left unchanged because the new interface was intentional.

Instead, the fake test implementation was updated to accept:

`config=None`

This restored compatibility between the test double and the real tool interface.

Final test result:

`40 passed`

### Agentic Retrieval Instrumentation

The next observability layer was added around the agentic retrieval pipeline.

Custom LangSmith spans were introduced for:

`agentic_investigation`

`create_investigation_plan`

`collect_evidence`

`semantic_subquery_retrieval`

Each planner-generated sub-query now produces an individual retriever span.

For the query:

`What changed in ProjectPulse and what is the current project status?`

the planner generated four sub-queries.

LangSmith exposed the following trace:

`agentic_investigation`
`-> create_investigation_plan`
`-> collect_evidence`
`   -> semantic_subquery_retrieval`
`   -> semantic_subquery_retrieval`
`   -> semantic_subquery_retrieval`
`   -> semantic_subquery_retrieval`

This makes the multi-query behavior observable instead of treating the entire investigation as one opaque operation.

### Observed Latency

One captured investigation trace reported:

`agentic_investigation: 6.28 s`

`create_investigation_plan: ~0.00 s`

`collect_evidence: 6.23 s`

Individual semantic retrieval spans were:

`Retrieval 1: 5.87 s`

`Retrieval 2: 0.08 s`

`Retrieval 3: 0.17 s`

`Retrieval 4: 0.10 s`

The first retrieval accounted for the large majority of the observed latency.

During the same execution environment, the embedding model printed a Hugging Face model-weight loading step before retrieval.

Therefore, the current evidence strongly suggests that the first-call latency includes cold-start/model initialization overhead rather than representing steady-state semantic retrieval latency.

This should be validated with repeated warm-run measurements before treating the 5.87 second value as normal retrieval performance.

### Retrieval Behavior Verification

The agentic pipeline was tested independently with tracing disabled.

Result:

`Intent: status`

`Subqueries: 4`

`Evidence: 2`

`PASSED`

The same pipeline was then executed independently with LangSmith tracing enabled.

Result:

`Intent: status`

`Subqueries: 4`

`Evidence: 2`

`PASSED`

This confirmed that:

* planner execution remains functional;
* all four retrieval calls execute;
* evidence aggregation remains functional;
* LangSmith instrumentation does not change retrieval results.

### MCP Process Boundary

ProjectPulse communicates with the MCP server through a real `stdio` process boundary.

Client-side LangGraph tracing now correctly exposes the actual MCP tool call:

`investigation -> investigate_project`

Server-side custom agentic retrieval tracing can also expose the internal planning and retrieval stages.

However, a complete distributed trace linking server-side custom spans directly into the same client-side trace has not yet been implemented.

Cross-process trace-context propagation across the MCP `stdio` boundary remains a future observability improvement.

This limitation is documented rather than presenting the two process-level trace views as one fully distributed trace.

### Current Observability Architecture

ProjectPulse now provides observability at multiple levels:

`LangGraph workflow`
`-> planner / routing`
`-> MCP tool invocation`
`-> agentic investigation`
`-> investigation planning`
`-> evidence aggregation`
`-> individual semantic retrieval calls`

This makes it possible to distinguish orchestration latency from retrieval latency and inspect how a complex project query is decomposed into multiple evidence searches.

### Current Limitations

The retrieval corpus still contains only two indexed GitHub evidence chunks.

Therefore, deeper observability improves diagnosis and architectural visibility but does not improve retrieval coverage.

The current latency measurements are also based on a small number of local executions and should not yet be interpreted as production benchmarks.

Cold-start and warm-run latency have not yet been formally benchmarked.

Distributed trace-context propagation across the MCP `stdio` process boundary is also not yet implemented.

### Result

ProjectPulse now has working LangSmith observability for both LangGraph orchestration and agentic retrieval internals.

The system can show:

`user query`
`-> memory loading`
`-> intent detection`
`-> conditional routing`
`-> real MCP tool invocation`
`-> agentic query planning`
`-> individual semantic retrieval operations`
`-> evidence aggregation`

The implementation also produced a real debugging case involving Python 3.10 async trace propagation and a test-double interface regression, both of which were diagnosed and fixed without changing application behavior.

All existing tests remain green:

`40 passed`

This completes the Day 6 LangSmith observability foundation.
