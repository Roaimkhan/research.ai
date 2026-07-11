# AI Research Agent with Advanced Memory System

## Problem
In long-running research tasks, AI agents suffer from context window overflow, forgetting crucial past findings, and difficulty in resolving contradicting research claims over time.

## Architecture
This project implements a multi-layered memory system using a 5-module agentic workflow:
1. **Extraction**: Raw conversation and tools outputs distilled into candidate facts.
2. **Operations**: Conflict resolution, contradiction detection, confidence scoring, and memory decay.
3. **Persistent Memory**: Combined Vector (Qdrant), Keyword (BM25), and Graph (NetworkX) indices.
4. **Retrieval & Fusion**: Cognitive retrieval combining multi-index searches and ranking.
5. **Generation**: Citation-backed answer formulation.

## Novelty
- Dual-rate decay formula distinguishing episodic (rapid decay) from semantic (consolidated facts) memories.
- Structural contradiction detector comparing research claims using confidence scores instead of simple timestamps.

## Benchmarks
Evaluated against LoCoMo/LongMemEval subsets. See `benchmarks/results.json` for detailed metrics.

## Roadmap
- [ ] Implement contradiction detector comparing research assertions.
- [ ] Connect custom tools and MCP servers for live research retrieval.
- [ ] Optimize fusion scoring weight grid search.
