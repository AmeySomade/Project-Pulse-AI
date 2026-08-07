# ProjectPulse AI — Project Scope

## 1. Project Overview

ProjectPulse AI is an agentic RAG system designed to answer questions about live and continuously changing software project data.

Unlike traditional RAG systems that retrieve information from static documents, ProjectPulse investigates project state dynamically by planning what information is required, calling external tools through MCP, collecting evidence, using relevant memory, and generating cited answers.

The first version of the project will use GitHub as the live project data source.

---

## 2. Problem Statement

Software project information is often distributed across:

* Issues
* Pull requests
* Commits
* Milestones
* Comments
* Repository documentation
* CI/CD workflow results

A user trying to understand project status may need to manually inspect several different sources.

For example:

> Why is Project X delayed?

Answering this properly may require checking:

* current milestone deadlines
* unresolved issues
* blocked tasks
* pull request status
* recent comments
* failed workflows
* previous project state

ProjectPulse AI will automate this investigation using an AI agent.

---

## 3. Core Objective

The system should be able to answer questions such as:

* What changed in this project this week?
* Why is this project delayed?
* What are the current blockers?
* Which important pull requests were merged?
* Did any deadlines change?
* What happened with a particular feature?
* How does the current project state differ from the previous state?

The final response should be grounded in evidence and include citations to the original sources.

---

## 4. Initial Data Source

Version 1 will use GitHub as the live data source.

The system will eventually retrieve:

* repository information
* issues
* issue comments
* pull requests
* commits
* milestones
* releases
* GitHub Actions workflow results
* repository documentation

Additional sources such as Jira, Notion, Slack, or Linear may be added later.

---

## 5. Planned Architecture

The initial architecture will contain:

User
↓
Streamlit Interface
↓
FastAPI Backend
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
Citations

The system will also contain semantic retrieval and persistent memory.

---

## 6. Agentic Behaviour

The agent should not immediately answer a complex project question.

Instead, it should:

1. Understand the user's intent.
2. Determine which project information is required.
3. Generate investigation subquestions.
4. Select appropriate tools.
5. Execute multiple tool calls when necessary.
6. Collect structured evidence.
7. Determine whether more evidence is required.
8. Synthesize the evidence.
9. Generate a cited response.
10. Evaluate whether useful information should be stored in memory.

---

## 7. Retrieval Strategy

ProjectPulse will use hybrid retrieval.

### Live Retrieval

Live tools will retrieve frequently changing information directly from GitHub.

Examples:

* open issues
* current pull requests
* latest commits
* current milestones
* workflow status

### Semantic Retrieval

Vector search will be used for information where semantic similarity is useful.

Examples:

* README files
* architecture documents
* historical discussions
* long issue threads
* project notes

The agent will decide which retrieval method is appropriate for each question.

---

## 8. Memory Design

The system will eventually support multiple levels of memory.

### Working Memory

Temporary information required during one agent investigation.

### Short-Term Memory

Conversation context required to understand follow-up questions.

### Long-Term Memory

Useful durable information that may be required across different sessions.

Examples include:

* important project priorities
* stable project goals
* major decisions
* user preferences
* important historical context

The system must not store every conversation message as long-term memory.

A memory manager will decide whether information should be stored, updated, ignored, or replaced.

---

## 9. Evidence and Citations

Every important retrieved fact should be represented as structured evidence.

Evidence should contain information such as:

* evidence ID
* source type
* source identifier
* title
* timestamp
* source URL
* retrieved content
* retrieval timestamp

Final answers should connect claims to supporting evidence.

---

## 10. Observability

LangSmith will eventually be used to inspect the agent execution path.

The system should make it possible to observe:

* original question
* rewritten query
* planner-generated questions
* retrieved memory
* tools selected
* tool inputs
* tool outputs
* evidence retrieved
* memory decisions
* final cited answer

---

## 11. Evaluation Goals

ProjectPulse will be evaluated using reproducible test questions.

Potential metrics include:

* answer correctness
* citation correctness
* tool-selection accuracy
* retrieval precision
* retrieval recall
* groundedness
* hallucination rate
* memory retrieval accuracy
* stale-memory conflict resolution
* task completion rate
* response latency
* number of tool calls

All reported improvements must come from measured experiments.

No performance or accuracy improvements will be claimed without reproducible evaluation results.

---

## 12. Development Strategy

The project will be developed incrementally.

Each meaningful feature will:

1. be implemented as a small checkpoint
2. be tested before continuing
3. be documented when necessary
4. be committed to GitHub with a meaningful commit message

The repository history should reflect the genuine development of the project.

---

## 13. MVP Scope

The first usable version should:

* connect to a GitHub repository
* retrieve live project information
* expose GitHub capabilities through MCP tools
* allow an agent to dynamically select tools
* investigate multi-step project questions
* collect structured evidence
* generate cited answers
* support semantic retrieval
* maintain short-term memory
* maintain selective long-term memory
* detect changes between project states
* expose agent execution traces

---

## 14. Initial Technology Stack

* Python
* Streamlit
* FastAPI
* LangGraph
* LangChain
* Model Context Protocol (MCP)
* GitHub REST API
* PostgreSQL
* pgvector
* Ollama / local LLM
* local embedding model
* LangSmith
* Git
* GitHub

A React / Next.js frontend may replace Streamlit after the backend and AI system are stable.
