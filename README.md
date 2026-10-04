# EcoMind — Sustainability-aware AI Inference Control Plane

## Project Overview & Core Problem
Modern AI systems often send every user query to a relatively large model even when the query could be answered using deterministic tools, a semantic cache, or a smaller model. EcoMind is a sustainability-aware inference control plane that investigates whether an intelligent router can select a lower-resource execution path while maintaining a required level of answer quality and latency.

The system considers query complexity, model capability, estimated energy, water, carbon impact, and latency to optimize the execution route.

## System Architecture & Flow
1. **User Query**: Received via the API.
2. **Query Analyzer**: Heuristically classifies task type and complexity.
3. **Semantic Cache Check**: If the query is highly similar to a previous query, return the cached answer.
4. **Candidate Generation**: Generates eligible execution paths (Deterministic Tools, Cache, Small Model, Medium Model, Large Model).
5. **Multi-Objective Optimizer**: Evaluates candidates based on quality requirements, latency constraints, and environmental estimates.
6. **Provider Execution**: Dispatches to the chosen model or deterministic tool.
7. **Eco Receipt Generation**: Returns the answer with a detailed environmental impact breakdown.

## Environmental Methodology & Research Integrity
- **Authentic Telemetry**: We record actual measured values (execution latency, API prompt/candidate tokens).
- **Zero Fabrication**: Environmental values (energy, water, carbon) are never fabricated or populated with fake hardcoded constants. They will be integrated via peer-reviewed estimation models in Phase 5.
- **Large-Model Inference Avoidance**: Deterministic tools (e.g. AST Calculator) solve calculable tasks with 0 token consumption, bypassing neural network inference entirely.

## Project Structure
```text
backend/
├── main.py                     # FastAPI application entrypoint
├── api/
│   ├── routes_chat.py          # /chat, /tools, /models endpoints
│   └── schemas.py              # Pydantic v2 request/response schemas
├── models/
│   ├── provider.py             # ModelProvider base class & ProviderResponse
│   ├── gemini_provider.py      # Google GenAI provider with authentic token usage
│   ├── local_provider.py       # Ollama integration & offline development fallback
│   └── model_profiles.py       # Catalog for small, medium, large tiers
├── tools/
│   ├── base.py                 # BaseTool & ToolResult abstractions
│   ├── calculator.py           # Safe AST-based deterministic calculator
│   ├── unit_converter.py       # Deterministic length/mass/temperature converter
│   ├── datetime_calculator.py  # Deterministic date arithmetic & calendar operations
│   ├── statistics_tool.py      # Deterministic descriptive statistics (mean, median, stdev, etc.)
│   ├── text_analyzer.py        # Deterministic text metrics (word/char/sentence count, frequency)
│   └── tool_registry.py        # Central tool registry & candidate matcher
├── config/
│   └── settings.py             # Application settings & environment variables
└── tests/
    ├── test_calculator.py          # Unit tests for Calculator arithmetic & safety
    ├── test_unit_converter.py      # Unit tests for UnitConverter dimensions & edge cases
    ├── test_datetime_calculator.py  # Unit tests for date differences, offsets, weekdays
    ├── test_statistics_tool.py     # Unit tests for mean, median, min, max, stdev, summary
    ├── test_text_analyzer.py       # Unit tests for word/char/sentence count & word frequency
    ├── test_tool_registry.py       # Unit tests for ToolRegistry & candidate matching
    ├── test_router.py              # Unit tests for initial query analysis & routing
    ├── test_models.py              # Unit tests for ModelProfile & providers
    └── test_api.py                 # Integration tests for FastAPI endpoints
frontend/                       # React 19 + Vite 8 + Tailwind CSS v4 dashboard
```

## Setup & Installation

### Environment Variables
Create a `.env` file in the `backend/` directory:
```env
ENVIRONMENT=development
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_DEFAULT_MODEL=gemini-2.5-flash
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_PROVIDER_FALLBACK=True
```

### Running Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

### Running Tests
```bash
cd backend
python -m unittest discover tests
```

### Running Frontend
```bash
cd frontend
npm install
npm run dev
```

## Current Project Status
- **Phase 0 — Architecture / Planning**: Completed.
- **Phase 1 — Skeleton (React + FastAPI)**: Completed.
- **Phase 2 — Deterministic Tools + Provider Layer**: Completed and verified.
  - Implemented safe AST-based `Calculator` (zero LLM calls, strict operator whitelist, exponential magnitude protection).
  - Implemented `ToolRegistry` with candidate query matching.
  - Implemented standardized `ModelProvider` abstract base class with `ProviderResponse` and authentic `TokenUsage`.
  - Implemented `GeminiProvider` using official `google-genai` SDK with real token metadata extraction.
  - Implemented `LocalProvider` supporting Ollama with offline dev fallback.
  - Implemented `ModelProfile` catalog defining small, medium, and large model tiers.
  - Integrated interactive Phase 2 playground in React frontend.
- **Phase 3 — Deterministic Tool Expansion & Query Routing**: Completed and verified.
  - Expanded deterministic tool layer to 5 tools: `Calculator`, `UnitConverter`, `DateTimeCalculator`, `StatisticsTool`, and `TextAnalyzer`.
  - Upgraded `ToolRegistry` to register and detect candidates across all 5 deterministic tools with strict, conservative matching.
  - Enhanced `QueryAnalyzer` to classify 7 task categories: `calculation`, `unit_conversion`, `date_time`, `statistics`, `text_analysis`, `reasoning`, and `general_qa`.
  - Updated `RoutingPolicy` to prioritize deterministic tools before routing to model tiers (`small`, `medium`, `large`).
  - Added full test coverage for all tools, query classification, routing policies, and FastAPI endpoints.
- **Phase 4 — Accuracy-First Semantic Cache & Lifecycle Controls**: Completed and verified (97 tests passing).
  - Implemented precision-first semantic cache with two-stage validation:
    - **Stage 1 (Semantic Retrieval)**: Fast cosine vector search using `SentenceTransformers` (`all-MiniLM-L6-v2`) and `FAISS` `IndexFlatIP`.
    - **Stage 2 (Compatibility Validation)**: Conservative deterministic validation across task types, core domain entities, added scoping constraints, temporal/numerical modifiers, freshness/dynamic risks, and reasoning depth.
  - Configurable similarity threshold (`CACHE_SIMILARITY_THRESHOLD`, default 0.90) allowing empirical precision/recall evaluation across 0.85, 0.90, 0.95, 0.97, 0.99.
  - **Deterministic Tools Precedence**: Deterministic tools always execute first before cache lookup or model invocation (0 tokens, 0 cache overhead).
  - **Cache Hit Safety**: Stored answers are returned strictly as-is with zero modification, zero summarization, 0 model calls, and 0 tokens.
  - **Lifecycle & Storage Controls**: Configurable entry cap (`MAX_CACHE_ENTRIES`), expiration policy (`CACHE_TTL_DAYS`), LRU eviction, disk storage telemetry, and manual reset capability.
  - **Telemetry**: Exposes `cache_status` (`not_checked`, `miss`, `hit`), `cache_similarity`, `cache_hits`, `cache_misses`, disk footprint (`storage_size_bytes`, `storage_size_kb`), and reports 0 tokens on cache hit.
  - **Persistence**: SQLite metadata storage + FAISS vector index persistence.

### Tool & Semantic Cache Execution Flow
```text
User Query
    ↓
1. Deterministic Tool Detection
    ├── Matched → Appropriate Deterministic Tool (0 tokens, < 1ms) → Answer
    └── No Tool Match
          ↓
2. Semantic Cache Check (Two-Stage Verification)
    ├── Stage 1: Vector Search (FAISS IndexFlatIP Cosine Similarity >= Threshold)
    └── Stage 2: Compatibility Validation (Entities, Constraints, Temporal, Dynamic, Depth)
          ├── PASS BOTH → Cache HIT (0 model calls, 0 tokens, authentic cached answer)
          └── FAIL EITHER → Cache MISS
                                ↓
                        3. Query Analyzer (Task type & complexity classification)
                                ↓
                        4. Routing Policy (small / medium / large)
                                ↓
                        5. Model Dispatcher (Groq / Gemini / Ollama)
                                ↓
                        6. Store Result in Semantic Cache (if cacheable & bounded) & Return Answer
```

### Accuracy-First Semantic Cache Policy
> **Precision-First Guarantee**:
> "The semantic cache is designed to prefer cache misses over potentially incorrect cache hits."
> We do NOT optimize for maximum cache hit rate at the cost of answer correctness. Semantic similarity alone is NOT sufficient for cache reuse. A cache miss is completely acceptable; a false cache hit is unacceptable.
> We do not claim that caching guarantees zero accuracy loss; rather, the system is designed to allow empirical evaluation of answer correctness versus cache reuse rate.

### Semantic Cache Storage & Lifecycle Architecture

#### 1. Storage Location
* **Metadata & Query Records (SQLite)**: `backend/database/semantic_cache.db`
* **Vector Index (FAISS)**: `backend/database/semantic_cache.index`
* Both locations are configurable via `CACHE_DB_PATH` and `CACHE_INDEX_PATH` in `backend/config/settings.py` or `.env`.

#### 2. Entry Schema
Each stored cache entry consists of:
* **Identification**: `id` (primary key mapped 1-to-1 with FAISS vector ID).
* **Queries**: Original user `query` and normalized representation (`normalized_query`).
* **Answer**: Model completion string returned identically on cache hit.
* **Semantic Metadata**: `task_type`, detected `entities` (JSON), detected scoping `constraints` (JSON), and `analysis_json` (complexity, reasoning requirement).
* **Execution Telemetry**: Original `route`, `provider`, `model`, authentic token usage (`prompt_tokens`, `completion_tokens`, `total_tokens`), and execution latency (`execution_time_ms`).
* **Lifecycle Tracking**: `created_at` timestamp, `last_used_at` timestamp (updated on every cache hit), `hit_count`, and `is_dynamic` flag.
* **Embedding Vector**: 384-dimensional unit-normalized float32 vector indexed in FAISS `IndexIDMap(IndexFlatIP)`.

#### 3. Configurable Limits
Configured in `backend/config/settings.py` and overridable via `.env`:
* `MAX_CACHE_ENTRIES`: Maximum number of entries allowed in cache before eviction triggers (default: `1000`).
* `CACHE_TTL_DAYS`: Retention lifetime in days for cached entries (default: `30` days).
* `CACHE_SIMILARITY_THRESHOLD`: Cosine similarity cutoff for Stage 1 retrieval (default: `0.90`).

#### 4. Eviction Behavior
When `add_entry` is called and the cache has reached `MAX_CACHE_ENTRIES`, safe two-tier eviction runs automatically:
1. **TTL Expiration**: Entries whose `created_at` exceeds `CACHE_TTL_DAYS` are evicted first.
2. **Least Recently Used (LRU)**: If the cache is still at capacity, entries are ordered by `last_used_at ASC, hit_count ASC, id ASC`. The least recently accessed, lowest-hit items are removed.
3. **Atomic Synchronization**: Evicted IDs are deleted from SQLite and removed from the FAISS vector index via `remove_ids`, immediately saving the trimmed index to disk. Frequently and recently accessed queries are strictly preserved.

#### 5. Manual Cache Clear & Administration
* **Clear via HTTP**:
  ```bash
  curl -X POST http://localhost:8000/cache/clear
  ```
  Returns `{"message": "Semantic cache cleared successfully.", "total_entries": 0}`.
* **Telemetry & Stats via HTTP**:
  ```bash
  curl -X GET http://localhost:8000/cache/stats
  ```
  Returns live cache statistics:
  - `total_entries`: Number of active cached queries.
  - `cache_hits`: Total cache hits served.
  - `cache_misses`: Total cache misses evaluated.
  - `storage_size_bytes` & `storage_size_kb`: Combined on-disk storage footprint of `.db` and `.index`.
  - `max_entries` & `ttl_days`: Configured lifecycle boundaries.
  - `avoided_model_calls` & `avoided_tokens`: Cumulative resource savings.
* **Programmatic Clear**:
  ```python
  from cache.semantic_cache import semantic_cache
  semantic_cache.clear()
  ```

#### 6. Current Limitations
* **Local Single-Node Storage**: SQLite + FAISS index reside locally on disk; distributed clusters (e.g., Redis Cluster or Milvus) are not required for single-node deployments.
* **Dynamic Query Exclusion**: Queries identified as time-sensitive, dynamic, or real-time (e.g. current Bitcoin price, live scores) are deliberately uncacheable to prevent serving stale information.
* **Embedding Model Binding**: The vector index is tailored to 384-dimensional embeddings from `all-MiniLM-L6-v2`; switching embedding models requires index reinitialization.
* Peer-reviewed environmental estimation (energy, water, carbon) belongs to Phase 5.
* Multi-objective Pareto optimization across quality, latency, cost, and carbon belongs to Phase 6.
* Itemized Eco Receipts belong to Phase 7.
