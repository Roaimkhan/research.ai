# Research.ai — A Research Assistant with Real Persistent Memory

Built for **Qwen Cloud Global AI Hackathon — Track 1: MemoryAgent**

---

## The Problem

Every AI assistant today forgets you the moment the session ends. Ask it about a paper today, come back tomorrow, and you're re-explaining everything from scratch — what you've read, what you concluded, what contradicted what. For researchers juggling dozens of papers across weeks, this isn't a minor annoyance — it's the difference between an assistant that compounds your understanding over time and one that's permanently stuck at zero.

Generic "RAG + vector database" memory doesn't fix this. It retrieves *similar text*, not *relevant truth* — it can't tell you which of two contradicting papers is more current, it can't distinguish a one-off detail from a durable fact, and it blows through context budgets stuffing in everything that's vaguely related instead of what actually matters.

**Synapse is a research-assistant agent that remembers like a researcher does** — distinguishing what happened (episodic), what's true (semantic), how to behave (procedural), and what's relevant right now (working) — and gets *measurably* more accurate the more you use it.

---

## What Makes This Different

Most memory-agent submissions in this category are a single vector store wrapped in a chat loop. Synapse instead implements:

- **Four distinct memory systems**, each with its own storage shape, decay behavior, and retrieval logic — not one generic "memory blob"
- **Conflict-Aware Retrieval (CAR)** — factual freshness is resolved with a deterministic `max(serial)` operation in plain Python, not an LLM guessing which fact is more current (which is where most memory agents silently hallucinate)
- **Query-time graph reasoning** — episodic relationships are computed on demand from a single Postgres source of truth, avoiding the dual-write consistency bugs that plague systems maintaining a separate persistent graph store
- **A real context-window budget** — retrieved memories are ranked, fused, and packed to fit a token budget, with graceful compression rather than silent truncation
- **Autonomous experience accumulation via MCP** — the agent doesn't just wait to be told things; it can search arXiv, fetch papers, and re-verify its own stale beliefs against fresh sources
- **Benchmarked, not just demoed** — evaluated against a LoCoMo/LongMemEval subset with real Recall@k and token-cost numbers, not just a scripted "look, it remembered!" moment

---

## Architecture

```
                     ┌─────────────────────────────┐
                     │        User Query            │
                     └──────────────┬───────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │      Query Router             │  ← does this need memory at all?
                     └──────────────┬───────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │  Coreference Resolver         │  ← resolves "that", "it" via working memory
                     └──────────────┬───────────────┘
                                    ▼
              ┌─────────────────────┴─────────────────────┐
              ▼                                            ▼
   ┌─────────────────────┐                      ┌─────────────────────┐
   │  Semantic Retrieval   │                      │  Episodic Retrieval  │
   │  (Postgres + pgvector │                      │  (Postgres graph +   │
   │   + CAR resolver)     │                      │   NetworkX traversal)│
   └──────────┬───────────┘                      └──────────┬───────────┘
              └─────────────────────┬─────────────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │       Fusion & Ranking         │
                     └──────────────┬───────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │     Context Packer             │  ← fits ranked results into token budget
                     └──────────────┬───────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │  Working Memory (assembled)   │  ← + procedural skills + persona
                     └──────────────┬───────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │   Qwen Response Generation    │  ← + MCP tools (arXiv, web search)
                     └──────────────┬───────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │   Extraction (query + reply)  │
                     └──────────────┬───────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │        Write-Back              │  ← routes to semantic/episodic/procedural
                     └─────────────────────────────┘
```

Orchestrated as a **LangGraph state graph** — conditional edges, not a monolithic ReAct loop — so control flow is deterministic, inspectable, and independently testable node by node.

---

## The Four Memory Systems

| Type | What it holds | Storage | Lifecycle |
|---|---|---|---|
| **Working** | Active context: persona rules, current plan, retrieved facts for this turn | In-memory blocks, session-scoped (LangGraph checkpointer) | Overwritten every turn |
| **Episodic** | Specific events — "read paper X on date Y" | Postgres (rows), traversed via query-time NetworkX subgraphs | Decays by activation weight, consolidated over time |
| **Semantic** | Durable facts and preferences — "Mem0 achieves ~6.7K tokens/query" | Postgres + pgvector, resolved via CAR (`max(serial)`) | Never overwritten — new evidence appends a new row; freshest always wins at read time |
| **Procedural** | How to behave — "always cite the source paper when comparing benchmarks" | Flat file registry (SKILL.md, YAML frontmatter) | Static, human-curated |

### Why Conflict-Aware Retrieval (CAR) instead of LLM-judged conflict resolution

Standard memory agents ask the LLM "which of these facts is correct?" — but LLMs exhibit a documented failure mode called **prior-override**, defaulting to their pretrained knowledge over the context you actually gave them. CAR sidesteps this entirely: every new fact for a given `concept` gets the next monotonic `serial` number on write. At read time, resolution is one line of deterministic Python — `max(rows, key=lambda r: r["serial"])` — no LLM judgment, no hallucination risk, no prior-override possible.

### Why a single Postgres instance instead of a dedicated graph database

Rather than maintaining a separately-persisted graph engine (introducing a second source of truth to keep in sync), Synapse stores all episodic events and relationships as rows in Postgres and treats graph traversal as a **stateless, query-time computation**: pull the relevant subgraph out of Postgres, load it into a throwaway NetworkX object, run spreading-activation traversal, discard it. This eliminates cross-system consistency risk entirely while still enabling associative recall — e.g., surfacing a schedule-conflict memory in response to a query about anxiety, even when the two never share literal text.

---

## Retrieval Pipeline

1. **Query Router** — classifies whether the query needs memory at all, and which stores are relevant, before spending any retrieval cost
2. **Coreference Resolver** — de-references ambiguous queries ("what's the formula for that?") using recent working-memory context before retrieval runs
3. **Fan-out retrieval** — semantic and episodic stores are queried in parallel, each wrapped in error handling so one store's failure doesn't take down the other
4. **Fusion** — merges semantic confidence scores and episodic graph-proximity weights into a single ranked list
5. **Context Packer** — greedily fills the token budget with top-ranked results, compressing or summarizing the long tail instead of silently dropping it
6. **Explicit no-context fallback** — if nothing relevant is found, the agent says so honestly instead of letting the LLM fabricate a plausible-sounding memory

---

## Autonomous Tools (MCP)

- **arXiv search** — pulls in new papers relevant to the conversation, feeding them directly into the extraction pipeline as if they were conversation turns
- **Paper fetch** — retrieves full text/abstracts to verify a claim when a contradiction is flagged
- **Staleness verification** — before answering with an old or preprint-sourced fact, autonomously re-checks it against fresh search results and flags contradictions
- **Citation graph** — grounds episodic graph edges in real citation relationships rather than inferred concept overlap alone

---

## Benchmarks

Evaluated against a subset of the LoCoMo / LongMemEval public benchmarks:

| Metric | Result |
|---|---|
| Recall@5 | *[fill in after running benchmarks/run_locomo_subset.py]* |
| Mean tokens/query | *[fill in]* |
| Mean latency | *[fill in]* |

*(Full methodology and raw output in `benchmarks/results.json`)*

---

## Tech Stack

- **LLM & orchestration:** Qwen Cloud (extraction, memory-op decisions, response generation, consolidation) via LangGraph state graph
- **Storage:** PostgreSQL + pgvector (unified episodic + semantic store)
- **Graph computation:** NetworkX (stateless, query-time traversal)
- **Keyword retrieval:** BM25
- **Tool integration:** Model Context Protocol (MCP) — arXiv, web search, citation graph
- **Serving:** FastAPI
- **Demo UI:** Streamlit — live chat + real-time memory panel (what was stored, retrieved, forgotten, and token cost per turn)

---

## Repository Structure

See `ARCHITECTURE.md` for the full module breakdown and design rationale.

```
src/
├── clients/       # Qwen Cloud API wrapper
├── tools/         # MCP registry, tool schemas, executor
├── checkpoint/    # Session/thread state (LangGraph)
├── extraction/    # Raw text → structured candidate facts
├── memory/        # Working, episodic, semantic, procedural stores
├── ops/           # Memory-op routing, conflict/contradiction detection, decay
├── retrieval/     # Router, coreference resolver, fusion, context packer
├── consolidation/ # Episodic → semantic distillation
└── generation/    # Final response assembly
```

---

## Roadmap / Beyond the Hackathon

- Package the memory subsystem as a standalone SDK usable by any LLM agent, not just this one
- Expand procedural memory from static skill files to feedback-driven behavioral weighting
- Multi-user shared knowledge graphs for lab/team research settings
- Fine-grained confidence decay tied to citation counts and retraction tracking

---

## Team

*Roaim khan / Memory Sytem*
*Muhammad Ahmed Qasim / UI UX - Decay Formula*
