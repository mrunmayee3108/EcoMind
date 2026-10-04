# EcoMind — Project Knowledge

> **Concise Engineering Reference & System Knowledge**  
> *Target Audience: Project Owner & AI Coding Assistants*  
> *Current Status: Phase 3 Completed & Live Integrated (Provider-Agnostic Model Routing & Deterministic Tools)*  
> *Detailed System Diagrams & Execution Traces: see [ARCHITECTURE.md](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/ARCHITECTURE.md)*

---

## 1. Project Identity

- **Project**: EcoMind — Sustainable AI Inference Control Plane
- **One-Liner**: An intelligent control plane that routes user queries to the lowest-resource execution path (tool, cache, small model, medium model, or cloud model) that satisfies required quality and latency constraints.
- **The Core Problem**: Current AI systems send every query to massive cloud LLMs regardless of complexity, causing extreme computational over-provisioning and wasting electricity, water cooling, and carbon emissions.
- **The Core Idea**: Treat LLMs as an expensive fallback, not the default engine. If a deterministic tool or a smaller model can answer accurately, use it.
- **Important Positioning**: EcoMind is **NOT just a chatbot**. The research contribution is the **unified, explainable controller** that balances quality, latency, cost, and environmental impact.

---

## 2. The Core Idea in Simple Words

Consider the query: **"What is 25 × 40?"**
- **Conventional AI**: Sends the query to an 8B–70B parameter cloud LLM. Consumes hundreds of tokens, watt-hours of energy, and cooling water, with a non-zero risk of hallucination.
- **EcoMind Approach**: Runs a local AST-based deterministic calculator. Solves $25 \times 40 = 1000$ in $< 1 \text{ ms}$ on local CPU using **0 tokens** and **0 neural networks**.

Similarly, for **"convert 100 km to miles"**:
- **Conventional AI**: Consumes LLM inference cycles and tokens to perform arithmetic multiplication.
- **EcoMind Approach**: Uses deterministic `UnitConverter` to solve with mathematical precision in $< 0.1 \text{ ms}$ with **0 tokens**.

---

## 3. Development Status

| Phase | Description | Status | Implemented? | Key Components |
|---|---|---|---|---|
| **Phase 0** | Architecture & Planning | Completed | **Yes** | Research problem, multi-objective formulation, integrity rules |
| **Phase 1** | Application Skeleton | Completed | **Yes** | FastAPI backend, React 19 + Vite frontend, basic HTTP ping |
| **Phase 2** | Tools + Provider Layer | Completed | **Yes** | AST `Calculator`, `ToolRegistry`, `ModelProvider`, `GeminiProvider`, `LocalProvider`, `ModelProfile` catalog, 20 unit/API tests |
| **Phase 3** | Tool Expansion + Provider-Agnostic Routing | Completed | **Yes** | 5 deterministic tools, `ToolRegistry`, `QueryAnalyzer`, `RoutingPolicy`, `GroqProvider`, `ModelDispatcher`, live `/chat` integration, 75 tests |
| **Phase 4** | Semantic Cache & Lifecycle Controls | Completed | **Yes** | SentenceTransformers (`all-MiniLM-L6-v2`), FAISS vector index, SQLite metadata store, LRU & TTL eviction, Stage 2 conservative `CompatibilityChecker`, 97 tests |
| **Phase 5** | Environmental Estimator | Planned | **No** | Energy (Wh), water (mL), and carbon (gCO2e) peer-reviewed models |
| **Phase 6** | Multi-Objective Optimizer | Planned | **No** | Normalized Pareto cost optimization over quality, latency, carbon, cost |
| **Phase 7** | Eco Receipt | Planned | **No** | Itemized environmental invoice for each inference request |
| **Phase 8** | Sustainability Dashboard | Planned | **No** | Long-term analytics, carbon-avoidance visualization |
| **Phase 9** | Research Benchmark | Planned | **No** | 500-query evaluation suite (EcoMind-Router-500) |
| **Phase 10** | Empirical Evaluation | Planned | **No** | Baselines (Always-Large, Always-Small, No-Cache) and ablation studies |
| **Phase 11** | Research Paper | Planned | **No** | Academic publication documenting findings |

---

## 4. Current File Structure & Roles

```text
backend/
├── main.py                     # FastAPI entry point, CORS, mounts routes_chat
├── api/
│   ├── routes_chat.py          # /chat, /tools, /models, /cache endpoints with live routing
│   └── schemas.py              # Pydantic v2 schemas (ChatRequest, ChatResponse, TokenUsageSchema, CacheStatsSchema)
├── cache/
│   ├── semantic_cache.py       # High-level SemanticCache controller with two-stage lookup & storage
│   ├── embedding_service.py    # SentenceTransformers service with lazy loading & mockable encoder
│   ├── cache_store.py          # SQLite metadata persistence + FAISS IndexFlatIP cosine retrieval
│   └── compatibility_checker.py # Conservative Stage 2 multi-factor compatibility validator
├── tools/
│   ├── base.py                 # Abstract BaseTool and ToolResult dataclasses
│   ├── calculator.py           # Safe AST-based deterministic math engine (0 tokens)
│   ├── unit_converter.py       # Deterministic length, mass, and temperature converter (0 tokens)
│   ├── datetime_calculator.py  # Deterministic date arithmetic & calendar operations (0 tokens)
│   ├── statistics_tool.py      # Deterministic descriptive statistics (mean, median, stdev, etc.) (0 tokens)
│   ├── text_analyzer.py        # Deterministic text metrics (word/char/sentence count, frequency) (0 tokens)
│   └── tool_registry.py        # Central tool catalog and query candidate matcher
├── router/
│   ├── query_analyzer.py       # QueryAnalysis dataclass and heuristic task classification (7 categories)
│   └── routing_policy.py       # Route selection prioritizing deterministic tools before logical model tiers
├── models/
│   ├── provider.py             # Abstract ModelProvider, ProviderResponse, TokenUsage
│   ├── groq_provider.py        # Groq LPU provider using official Groq SDK with usage tracking
│   ├── gemini_provider.py      # Google GenAI SDK wrapper with authentic token tracking
│   ├── local_provider.py       # Ollama integration with local offline dev fallback
│   ├── dispatcher.py           # Provider-agnostic ModelDispatcher for logical tiers
│   └── model_profiles.py       # Model catalog across small, medium, and large tiers
├── config/
│   └── settings.py             # Pydantic BaseSettings loading from .env
└── tests/                      # 92 passing unit & integration tests
    ├── test_calculator.py          # Calculator arithmetic & security tests
    ├── test_unit_converter.py      # UnitConverter conversions, dimensions & edge cases
    ├── test_datetime_calculator.py  # DateTimeCalculator differences, offsets, weekdays
    ├── test_statistics_tool.py     # StatisticsTool mean, median, min, max, stdev, summary
    ├── test_text_analyzer.py       # TextAnalyzer word/char/sentence count & word frequency
    ├── test_tool_registry.py       # Registry registration & candidate matching
    ├── test_router.py              # QueryAnalyzer & RoutingPolicy tests (tools + tiers)
    ├── test_groq_provider.py       # GroqProvider capabilities & token extraction tests
    ├── test_dispatcher.py          # ModelDispatcher tier resolution & failure tests
    ├── test_models.py              # Model profiles & LocalProvider tests
    ├── test_api.py                 # FastAPI end-to-end integration tests (/chat, /tools, /models)
    └── test_semantic_cache.py      # Comprehensive Phase 4 semantic cache & regression tests (16 tests)
frontend/
├── src/App.tsx                 # Interactive Control Plane console with Phase 4 cache telemetry UI
└── package.json                # React 19, Vite, Tailwind CSS v4, Lucide React
```

---

## 5. Phase Summaries (0, 1, 2, 3, and 4)

### Phase 0: Planning & Integrity
- Defined the multi-objective optimization goal:
  $$\min \left( \alpha \cdot \bar{E} + \beta \cdot \bar{W} + \gamma \cdot \bar{C} + \delta \cdot \bar{L} + \epsilon \cdot \bar{\$} \right) \quad \text{s.t. } Q \ge Q_{\text{req}}$$
- **Integrity Rule**: Never fabricate environmental numbers or hardcode fake constants (e.g., "0.25 Wh"). Distinguish measured telemetry from scientific estimates.

### Phase 1: Skeleton
- Set up FastAPI backend on port 8000.
- Set up React 19 + Vite frontend on port 5173.
- Verified client-server HTTP communication.

### Phase 2: Tools + Provider Layer
1. **Deterministic Tools**:
   - `Calculator`: Parses expressions via Python's `ast` module. Disallows arbitrary code injection. Blocks excessive exponents ($> 1000$). Consumes **0 tokens**.
   - `ToolRegistry`: Matches math queries via `find_candidate_tool(query)`.
2. **Provider Abstraction**:
   - `ModelProvider`: Common interface (`generate`, `get_capabilities`).
   - `GeminiProvider`: Extracts authentic `usage_metadata` (prompt/candidate tokens) from Google's official SDK.
   - `LocalProvider`: Connects to Ollama (`http://localhost:11434`) with a 0.4s connection check; provides an offline development fallback if Ollama is absent.
   - `ModelProfile`: Stores small, medium, and large model profiles and official public pricing.

### Phase 3: Deterministic Tool Expansion & Provider-Agnostic Routing
1. **Deterministic Tools Expanded**: 5 tools (`Calculator`, `UnitConverter`, `DateTimeCalculator`, `StatisticsTool`, `TextAnalyzer`).
2. **Provider-Agnostic Architecture**: Strict separation of logical tiers (`small`, `medium`, `large`) from vendor providers (`GroqProvider`, `GeminiProvider`, `LocalProvider`).
3. **Automatic Routing**: `QueryAnalyzer` classifies queries into 7 task categories; `RoutingPolicy` selects deterministic tools before logical model tiers.

### Phase 4: Accuracy-First Semantic Cache (Completed & Live Integrated)
1. **Core Accuracy & Precision Mandate**:
   - **"The semantic cache is designed to prefer cache misses over potentially incorrect cache hits."**
   - Precision > Hit Rate. Semantic similarity alone is NOT sufficient for cache reuse.
   - We do NOT claim that caching guarantees zero accuracy loss; rather, the architecture allows empirical measurement of accuracy degradation vs model inference avoidance.
2. **Two-Stage Validation Pipeline**:
   - **Stage 1 (Semantic Retrieval)**: Computes L2-normalized query embeddings via SentenceTransformers (`all-MiniLM-L6-v2`) and performs exact inner-product (cosine) search using FAISS `IndexFlatIP`. If similarity is below configurable `CACHE_SIMILARITY_THRESHOLD` (default 0.90), it is an immediate CACHE MISS.
   - **Stage 2 (Compatibility Validation)**: Conservative deterministic validation via `CompatibilityChecker`:
     - *Freshness / Dynamic check*: Rejects time-sensitive queries (e.g., "current price", "today", "now") to prevent stale answers.
     - *Temporal & Numerical check*: Rejects queries that introduce specific years or numbers absent from the cached query (e.g., "in 1800").
     - *Scoping & Constraint check*: Rejects queries that add scoping qualifiers (e.g., "specifically for high-latency networks", "in terms of scalability").
     - *Entity / Concept check*: Rejects queries targeting different domain entities or concepts (e.g., "decorators" vs "generators").
     - *Reasoning Depth check*: Rejects queries requiring deep mathematical derivation when cached entry was high-level/basic.
3. **Execution Precedence**:
   - Deterministic tools execute FIRST. Queries matching tools (e.g. `calculate 25 times 100`) bypass cache search and model inference completely (0 tokens, 0 cache overhead).
4. **Cache Hit Safety**:
   - On CACHE HIT, stored answer is returned strictly as-is with 0 model calls, 0 tokens, and `large_model_avoided=True`.
5. **Persistence & Storage**:
   - Metadata persisted in SQLite (`semantic_cache.db`), vectors persisted in FAISS (`semantic_cache.index`).
6. **Lifecycle & Safe Eviction**:
   - Configurable limits: `MAX_CACHE_ENTRIES` (default 1000) and `CACHE_TTL_DAYS` (default 30).
   - Safe two-tier eviction: TTL expired entries are evicted first, followed by Least-Recently-Used (LRU, ordered by `last_used_at ASC, hit_count ASC, id ASC`).
   - SQLite and FAISS are kept in sync; vectors are removed via `remove_ids`.
7. **Telemetry & Endpoints**:
   - Telemetry reports `cache_status` (`not_checked`, `miss`, `hit`), `cache_similarity`, `cache_hits`, `cache_misses`, `storage_size_bytes`, `storage_size_kb`.
   - Admin/inspection endpoints: `GET /cache/stats` and `POST /cache/clear`.

---

## 6. What EcoMind Can and Cannot Do Right Now

### What It CAN Do Now
- Instantly evaluate arithmetic expressions via AST in $< 1 \text{ ms}$ with **0 tokens** and **0 LLM calls**.
- Instantly convert length, mass, and temperature units deterministically with **0 tokens** and **0 LLM calls**.
- Instantly compute date differences, offsets, weekdays, and leap-year queries in $< 0.1 \text{ ms}$ with **0 tokens** and **0 LLM calls**.
- Instantly calculate descriptive statistics (mean, median, min, max, standard deviation) over numeric lists with **0 tokens** and **0 LLM calls**.
- Instantly compute word count, character count, sentence count, and frequency distributions over text with **0 tokens** and **0 LLM calls**.
- Prioritize deterministic tools before cache lookup or model routing.
- Conservatively reuse previous model answers via two-stage Semantic Cache for equivalent queries with **0 tokens** and **0 model calls**.
- Reject false cache hits when queries add constraints (e.g. high-latency networks), temporal modifiers (e.g. in 1800), different entities (generators vs decorators), or require deeper mathematical reasoning.
- Prevent caching of dynamic or time-sensitive queries to eliminate stale answer risks.
- Classify queries into 7 task categories via `QueryAnalyzer` and route to deterministic tools or logical model tiers (`small`, `medium`, `large`) via `RoutingPolicy`.
- Dynamically resolve logical tiers to configured providers (`GroqProvider`, `GeminiProvider`, `LocalProvider` / Ollama) via `ModelDispatcher`.
- Extract and display authentic token counts, measured latency, and cache telemetry in the React frontend.
- Support manual execution path directives (`auto`, `deterministic_tool`, `semantic_cache`, `small_model`, `medium_model`, `large_model`).
- Introspect registered tools (`GET /tools`), model profiles (`GET /models`), and cache statistics (`GET /cache/stats`).

### What It CANNOT Do Yet (Future Phases)
- Estimate energy, water, and carbon metrics (Phase 5).
- Run automated multi-objective Pareto optimization (Phase 6).
- Generate itemized Eco Receipts (Phase 7).

---

## 7. Why Phase 5 Is Next

With deterministic tools (Phase 3) and an accuracy-first semantic cache (Phase 4) fully in place, the system has multiple execution paths: Deterministic Tools (0 tokens), Semantic Cache (0 tokens), Small Model, Medium Model, and Large Model. To enable intelligent multi-objective optimization (Phase 6), the system next requires scientific, peer-reviewed estimation models for **Energy (Wh), Water Cooling (mL), and Carbon (gCO2e)** based on hardware profiles and authentic token telemetry (Phase 5).
