# FrontierAtlas / GraphOne Technical Architecture & Production Design

**Document Version:** 1.0  
**Target System:** Global Artificial Intelligence & Venture Intelligence Graph  
**Assessment Role:** AI Engineer & Data Infrastructure Architect  

---

## Executive Summary & System Objectives
GraphOne / FrontierAtlas requires an enterprise-scale ingestion architecture capable of autonomously acquiring, structuring, normalizing, and resolving multi-dimensional datasets covering startups, founders, products, AI vacancies, research papers, and breaking signals. 

This document details the production design for scaling from tens of thousands of records to **500,000+ entities** with zero manual intervention, resilient LLM orchestration, sub-second deterministic entity resolution, and strict 24-hour signal freshness guarantees.

```
+-------------------------------------------------------------------------------------------------------+
|                                    FRONTIERATLAS SYSTEM ARCHITECTURE                                   |
+-------------------------------------------------------------------------------------------------------+
|                                                                                                       |
|  [ INGESTION SOURCES ]                                                                                |
|  * Research: ArXiv API, Papers with Code, Hugging Face Papers, GitHub Stargazer API                   |
|  * Directories: Y Combinator Catalog, Techstars, ProductHunt, Crunchbase Mirrors                      |
|  * Signals (24h Fresh): MIT Tech Review, HN AI Feed, Ars Technica, RemoteOK, Remotive, WeWorkRemotely |
|                                       │                                                               |
|                                       ▼                                                               |
|  [ ANTI-BOT & EDGE CAMOUFLAGE LAYER ]                                                                 |
|  * TLS Fingerprinting (JA3/JA4 emulation) + Dynamic User-Agent Pool (Chrome 128+)                    |
|  * Challenge Detection (Cloudflare Turnstile, Datadome Captchas, WAF 403/503 inspection)              |
|  * Headless Fallback: Playwright Async for Client-Side Hydrated SPA DOMs                              |
|                                       │                                                               |
|                                       ▼                                                               |
|  [ DISTRIBUTED CRAWLER CLUSTER (Celery / Redis / Ray Workers) ]                                       |
|  * Partitioned Work Queues (Kafka / Redis Streams) with Consistent Hashing by Domain                 |
|  * Distributed Deduplication: Scalable Counting Bloom Filter + Redis HyperLogLog                      |
|  * Checkpointing: Persistent visited URL state per partition; resumable after crash                   |
|                                       │                                                               |
|                                       ▼                                                               |
|  [ RESILIENT MULTI-TIER LLM EXTRACTION ENGINE ]                                                       |
|  * Semantic Chunking & DOM Pruning: Eliminates HTTP 413 (Payload Too Large)                           |
|  * Rate Limiter: Decorrelated Exponential Backoff with Full Jitter for HTTP 429                       |
|  * Multi-Tier Provider Fallback Chain:                                                                |
|       Tier 1: Google Gemini Flash (Primary)                                                           |
|          │ (on 429/500/timeout)                                                                       |
|          ▼                                                                                            |
|       Tier 2: Groq Llama 3 (Sub-100ms Inference)                                                      |
|          │ (on rate-limit / outage)                                                                   |
|          ▼                                                                                            |
|       Tier 3: DeepSeek Chat (Deep Reasoning Fallback)                                                 |
|          │ (on universal provider failure)                                                            |
|          ▼                                                                                            |
|       Safety Tier: Deterministic Regex & Semantic Parser (100% Zero-Downtime Guarantee)               |
|                                       │                                                               |
|                                       ▼                                                               |
|  [ DETERMINISTIC ENTITY RESOLUTION & NORMALIZATION ]                                                  |
|  * Unicode NFKC Normalization + Punctuation Stripping                                                 |
|  * Corporate Legal Suffix Removal (Inc, LLC, Ltd, Corp, Technologies, Labs, GmbH)                     |
|  * Canonical Alias Mapping (50+ Seed AI Giants: OpenAI, Anthropic, DeepMind, Mistral, etc.)           |
|  * Token Jaccard + Levenshtein Distance Matrix (Similarity Threshold >= 0.85)                         |
|  * Audited Mapping Log: Tracks Raw String -> Canonical Entity + Confidence Score                      |
|                                       │                                                               |
|                                       ▼                                                               |
|  [ MULTI-MODEL STORAGE & SERVING TIER ]                                                               |
|  * Primary Relational DB: PostgreSQL (ACID entities, metadata, schemas, indexing, audit trail)       |
|  * Graph Storage: Neo4j / Memgraph (Founder -> Startup -> Product -> Paper -> Investor Edges)         |
|  * Vector Store: Qdrant / pgvector (Semantic text embeddings, paper similarity, RAG search)           |
|  * In-Memory Cache: Redis Cluster (Rate-limiting token buckets, fresh URL deduplication keys)        |
|                                       │                                                               |
|                                       ▼                                                               |
|  [ SERVING & ANALYTICS APIs ]                                                                         |
|  * FastAPI REST & GraphQL Engine                                                                      |
|  * Google Sheets Automated Bi-Directional Synchronizer (6 Tab Canonical Output)                       |
|  * Real-Time Telemetry Dashboard (React, Tailwind CSS, Recharts)                                      |
+-------------------------------------------------------------------------------------------------------+
```

---

## 1. Scale Strategy: Ingesting 500,000+ Records Autonomously

To scale from thousands to **500,000+ startups, products, and research papers** without manual intervention or performance degradation, the architecture shifts from single-node loops to a **horizontally partitioned distributed crawler cluster**:

### 1.1 Distributed Partitioning & Work Queuing
- **Message Broker:** Apache Kafka / Redis Streams partitioned by domain hash (`hash(target_domain) % num_partitions`). This guarantees that requests to any single domain (e.g., `arxiv.org` or `ycombinator.com`) are routed to dedicated queue consumers, enforcing source-specific politeness limits without cross-worker locking.
- **Worker Scalability:** Lightweight worker pods managed by Kubernetes (KEDA). Workers scale up/down dynamically based on queue lag and HTTP 429 pressure.
- **Incremental Checkpointing:** Each worker maintains an LSM-tree based persistent state (or Redis Bitmaps) of visited canonical URL hashes (`SHA-256(canonical_url)`). If a node fails or crashes, jobs resume from the exact last offset without duplicate requests.

### 1.2 Multi-Vertical Continuous Discovery
- **Research Papers Vertical:** Automated pagination through ArXiv OAI-PMH harvest protocol and Papers with Code bulk metadata endpoints, cross-referencing repository URLs against the GitHub REST/GraphQL API to extract live stargazers, forks, and commit velocities.
- **Startups & Products:** Automated discovery loops across global corporate registries, SEC EDGAR Form D filings, open tech directories (YC, Techstars), and Crunchbase/OpenCorporates public mirrors.
- **Zero-Manual Healing:** Dead links or 404s trigger automated tombstone marking. Domain redirects (301/308) automatically canonicalize the target URL in the master entity index.

---

## 2. Managing Context Windows & Rate Limits (HTTP 413 & 429)

Across tens of thousands of concurrent extractions, LLMs face two fatal operational bottlenecks: **HTTP 413 (Payload Too Large / Context Overflow)** and **HTTP 429 (Too Many Requests / Rate Limiting)**.

### 2.1 Context Window Management & HTTP 413 Elimination
Raw web pages frequently contain between 100KB to 5MB of bloated HTML DOM trees, tracking pixels, SVGs, and base64 styles. Passing raw documents to LLMs causes immediate 413 errors and exorbitant inference bills.

**Our Two-Phase Intelligent Pruning Pipeline:**
1. **Structural DOM Pruning (Boilerplate Stripping):**
   - Strips `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<iframe>`, and `<noscript>`.
   - Extracts semantic containers (`<article>`, `<main>`, `<h1>-<h6>`, `<p>`, `<table>`).
   - Converts the cleaned DOM into condensed Markdown format.
2. **Priority Semantic Chunking & Token Budgeting:**
   - Every provider is allocated a strict character budget (e.g., 24,000 characters $\approx$ 6,000 tokens for Gemini Flash).
   - If document size exceeds budget:
     - **Head Window (40% budget):** Retains page title, meta description, and introductory context.
     - **High-Signal Keyword Window (40% budget):** Prioritizes paragraphs containing critical target tokens: `price`, `pricing`, `plan`, `free tier`, `enterprise`, `team`, `founder`, `abstract`, `github`.
     - **Tail Window (20% budget):** Captures closing specifications and corporate contact details.
   - **Guarantee:** Payloads are mathematically bounded; HTTP 413 errors are completely prevented at the ingest gateway.

### 2.2 Rate Limit (HTTP 429) Strategy: Decorrelated Full Jitter & Multi-Tier Fallback
To prevent the "thundering herd" problem and survive upstream API quotas:
1. **Decorrelated Exponential Backoff with Jitter:**
   $$\text{Sleep Time} = \min\left(M, \; \text{Uniform}(0, \; B \times 2^{\text{attempt}})\right)$$
   Where base delay $B = 1.0\text{s}$, maximum cap $M = 30.0\text{s}$. If upstream supplies a `Retry-After` header, the engine respects the exact upstream duration plus a randomized 200–500ms safety buffer.
2. **Dynamic Multi-Tier Fallback Cascade:**
   - **Tier 1 (Gemini 1.5 Flash):** High throughput, 1M context, low cost.
   - **Tier 2 (Groq Llama 3.3 70B):** Hardware LPU inference serving responses in $<150\text{ms}$. Triggered automatically if Gemini returns 429, 503, or times out after 15 seconds.
   - **Tier 3 (DeepSeek Chat):** Frontier reasoning provider for ambiguous schema structuring.
   - **Safety Tier (Deterministic Regex & DOM Parser):** If all cloud LLMs are unreachable or API keys are exhausted, a zero-cost deterministic rule engine extracts pricing tiers, employee counts, and titles. **Extraction never halts.**

---

## 3. Freshness Tracking: Zero-Duplicate Distributed Ingestion

Phase II demands extreme freshness: all ingested news articles and job postings must be guaranteed to have been published **within the previous 24 hours**, with **zero duplication** across distributed crawler workers.

```
                          DISTRIBUTED FRESHNESS GATEWAY
                                        │
                         [ Incoming URL & Raw Content ]
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │ 1. Distributed Bloom Filter (Redis ReJSON) │
                  │    Bit array check: Hash(URL)              │
                  └─────────────────────┬─────────────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        │ Already Seen?                 │
                       YES                              NO
                        │                               │
                        ▼                               ▼
                 [ DROP / SKIP ]         ┌───────────────────────────────┐
                                         │ 2. Canonical URL Normalization│
                                         │    Strip UTM, tracking tokens │
                                         └──────────────┬────────────────┘
                                                        │
                                                        ▼
                                         ┌───────────────────────────────┐
                                         │ 3. Strict 24h Timestamp Audit │
                                         │    Relative + RFC2822 to UTC  │
                                         └──────────────┬────────────────┘
                                                        │
                                        ┌───────────────┴───────────────┐
                                        │ Within Last 24 Hours?         │
                                       NO                               YES
                                        │                               │
                                        ▼                               ▼
                                 [ DROP / STALE ]        ┌───────────────────────────────┐
                                                         │ 4. Content SimHash (Near-Dup) │
                                                         │    Hamming distance <= 3?     │
                                                         └──────────────┬────────────────┘
                                                                        │
                                                                        ▼
                                                         [ ACCEPT & COMMIT TO DB/REDIS ]
```

### 3.1 Distributed State & Counting Bloom Filter
- **Redis Bloom Filter (`BF.ADD`):** Evaluates incoming URLs in $O(1)$ time with a 0.01% false positive probability across hundreds of millions of items.
- **Two-Tier Keying:**
  1. `crawler:visited:{source}:{SHA256(canonical_url)}` with a 7-day TTL.
  2. `crawler:content:simhash:{SimHash64}` to detect syndicated articles republished across multiple domains under different URLs.

### 3.2 Rigorous 24-Hour Freshness Pipeline
1. **Date Normalization Engine:** Normalizes all relative dates (*"2 hours ago"*, *"45m ago"*, *"yesterday"*), RFC 2822 RSS timestamps, and ISO strings into UTC ISO-8601 timestamps (`YYYY-MM-DDTHH:MM:SS+00:00`).
2. **Freshness Filter Equation:**
   $$t_{\text{now}} - 24\text{h} \le t_{\text{published}} \le t_{\text{now}} + 1\text{h}$$
   (The $+1\text{h}$ upper boundary handles server clock drift). Any article or job outside this window is immediately rejected.
3. **Intelligent Fallback Heuristics:**
   If publication meta-tags are omitted, the engine:
   - Inspects URL path date patterns (`/2026/11/21/...`).
   - Compares the HTTP `Last-Modified` and `ETag` headers.
   - Analyzes content freshness heuristics: if first discovered during current cycle and differs from cached domain snapshot, it is marked with lower freshness confidence rather than discarded.

---

## 4. Storage Strategy: PostgreSQL, Redis, Vector & Graph DB Justification

A global intelligence graph requires mapping rich multi-dimensional relationships: founders start companies, companies build products, products adopt pricing models, researchers author papers, and startups hire specific engineering roles.

| Storage Engine | Role in FrontierAtlas Architecture | Technical Justification |
| :--- | :--- | :--- |
| **PostgreSQL 16** | **Primary Relational Store & System of Record** | Provides ACID guarantees for canonical entities (`Startups`, `Products`, `ResearchPapers`, `Jobs`, `News`). Implements declarative schemas, B-tree indexes on `source_url` and `canonical_name`, unique constraints preventing duplicates, and foreign keys for relational integrity. |
| **Redis 7.2 (Cluster)** | **In-Memory Coordination, Caching & Queues** | Sub-millisecond distributed lock manager (`Redlock`), rate-limiting token buckets, Redis Bloom filter for URL deduplication, and worker coordination state. |
| **Neo4j / Memgraph** | **Graph Database (Entity Graph Relationships)** | Relational joins across 5 degrees of separation (*Startup $\to$ Founder $\to$ Paper $\to$ GitHub Repo $\to$ Job*) are computationally prohibitive in SQL. Neo4j’s native index-free adjacency traverses complex venture relationships in milliseconds. |
| **Qdrant / pgvector** | **Vector Similarity & Semantic Retrieval** | Stores 1536-dimensional embeddings of startup descriptions, product feature matrices, and paper abstracts. Enables semantic search (*"Find startups working on generative video editing with open weights"*). |

### Graph Data Model (Neo4j Cypher Schema)
```cypher
(:Startup {name, domain, employee_count})
  -[:BUILDS]-> (:Product {pricing_model, one_liner})
  -[:AUTHORED_BY]<- (:Author)-[:PUBLISHED]-> (:ResearchPaper {title, stars})
  -[:HIRING]-> (:Job {role_family, remote})
  -[:MENTIONED_IN]-> (:News {headline, published_date})
```

---

## 5. Anti-Bot Navigation & Stealth Crawling

High-value intelligence sources (TechCrunch, VentureBeat, ProductHunt, LinkedIn) deploy aggressive Web Application Firewalls (Cloudflare, Datadome, Akamai).

### 5.1 Architecture & Ethical Navigation Rules
1. **TLS Fingerprint Camouflage:** Uses `curl_cffi` / HTTP/2 client stacks to emulate legitimate desktop Chrome 128 JA3/JA4 fingerprints and HTTP/2 pseudo-header order (`:method`, `:authority`, `:scheme`, `:path`).
2. **Realistic Browser Headers:** Dynamically rotates desktop User-Agents, `Sec-Ch-Ua`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, and referrer headers.
3. **Challenge Detection:**
   - Detects Cloudflare Turnstile, "Just a moment...", Datadome captchas, and HTTP 403/503 challenge pages.
   - **Strict Policy:** Does **not** attempt illegal CAPTCHA defeat. Upon encountering a challenge page, the crawler logs the challenge event, tags the domain health as `PROTECTED_WAF`, applies polite backoff, and shifts to alternate authorized syndication feeds or official API endpoints.
4. **JavaScript Hydration via Playwright Async:**
   - For heavily client-rendered Single-Page Applications (SPAs) like React/Next.js directories, workers spin up headless Chromium instances with disabled automation flags (`navigator.webdriver = false`).

---

## 6. Verification & Deliverable Alignment

The architecture directly produces the 6 required Google Sheets tabs and verified engineering artifacts:

1. **Startups (1,000 rows):** Canonicalized entity names, employee counts, valid source URLs.
2. **Products (1,000 rows):** Canonical parent names, classified pricing tiers (`FREE`, `FREEMIUM`, `PAID`, `ENTERPRISE`).
3. **Research Papers (1,000 rows):** ArXiv/HF titles, author arrays, live GitHub star tracking.
4. **Jobs (All 24h fresh):** Strict 24-hour timestamp validation, role families, remote eligibility.
5. **News (All 24h fresh):** Strict 24-hour freshness, cleaned full-text bodies, original source attribution.
6. **Entity Mapping Log:** Complete audit trail of raw scraped strings vs. canonicalized representations with confidence scores.
