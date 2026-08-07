# ProjectPulse AI

ProjectPulse AI is an agentic RAG system for investigating live and continuously changing software project data.

Instead of answering only from static documents, the system will plan what information is needed, call external tools through MCP, retrieve relevant project context and memory, collect evidence, and generate grounded answers with citations.

## Current Goal

The first version will use GitHub as the live project source.

Example questions the system is intended to answer:

* What changed in this project this week?
* Why is the project delayed?
* What are the current blockers?
* Which important pull requests were merged?
* Did any deadlines change?
* What happened with a specific feature?
* How has the project changed since the previous project state?

## Planned Architecture

```text
User
  ↓
Streamlit
  ↓
FastAPI
  ↓
LangGraph Agent
  ↓
Query Understanding
  ↓
Memory Retrieval
  ↓
Investigation Planner
  ↓
MCP Client
  ↓
ProjectPulse MCP Server
  ↓
GitHub API
  ↓
Evidence Collection
  ↓
Answer Synthesis
  ↓
Cited Response
```

## Planned Capabilities

* Live GitHub project retrieval
* Custom MCP server
* Multi-step agent planning
* Dynamic tool selection
* Hybrid live and semantic retrieval
* Structured evidence collection
* Source citations
* Short-term conversation memory
* Selective long-term memory
* Memory conflict resolution
* Project-state comparison
* LangSmith observability
* Reproducible evaluation

## Technology Stack

* Python
* Streamlit
* FastAPI
* LangGraph
* LangChain
* Model Context Protocol
* GitHub REST API
* PostgreSQL
* pgvector
* Ollama / local LLM
* LangSmith

## Development Status

**Phase 0 — Project definition and architecture**

The project is being developed incrementally. Each meaningful feature will be implemented, tested, documented, and committed separately so that the repository reflects the actual engineering process.

## Evaluation Philosophy

Performance improvements will only be reported when they are measured using reproducible evaluation sets.

Planned evaluation areas include:

* tool-selection accuracy
* answer correctness
* citation correctness
* retrieval quality
* groundedness
* hallucination rate
* memory accuracy
* response latency

No unmeasured accuracy or performance claims will be included.

## Documentation

Detailed project scope and design decisions are maintained in:

`docs/project_scope.md`

## Frontend Plan

Development will begin with Streamlit so that the AI system can be built and tested quickly.

After the backend and agent architecture are stable, the frontend may be migrated to React / Next.js for a more production-style interface.
