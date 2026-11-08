# EcoMind — Project Knowledge

> **Concise Engineering Reference & System Knowledge**  
> *Target Audience: Project Owner & AI Coding Assistants*  
> *Current Status: Phase 8 Completed & Verified (Sustainability Dashboard & Historical Analytics, SQLite Persistence, 201 Tests Passing)*  
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
| **Phase 5A** | Hardware-Agnostic Telemetry & Measurement | Completed | **Yes** | Generic `MeasurementProvider` abstraction (`NvidiaNvmlProvider`, `AndroidEnergyProvider`, `AppleEnergyProvider`, `UnavailableProvider`), explicit scopes, capabilities API, 117 tests |
| **Phase 5B** | Environmental Accounting Methodology & Upgrade | Completed | **Yes** | Multi-provider accounting, Versioned Source Registry (`registry.py`), Pluggable Cloud Energy Estimators (`cloud_estimator.py`), Ember 2024 Grid Manager (`grid.py`), 4-category Water Engine (`water.py`), Non-Zero Savings Rule (`savings.py`), 156 tests |
| **Phase 6** | Multi-Objective Optimizer | Completed | **Yes** | Normalized Pareto cost optimization over quality, latency, cost, and energy; Non-Zero dynamic weight renormalization; hard quality constraints; live `/chat` integration, 173 tests |
| **Phase 7** | Eco Receipt | Completed | **Yes** | Structured, machine-readable `EcoReceipt` attached to all `/chat` responses and retrievable via `GET /receipts/{id}`; itemized latency, tokens, cost, energy, carbon, water, and explainability; 191 tests |
| **Phase 8** | Sustainability Dashboard | Completed | **Yes** | SQLite historical store (`database/historical_telemetry.db`), 6 `/dashboard/*` REST analytics APIs, React 19 dashboard with 4 views & Eco Receipt modal, 201 tests |
| **Local Launcher** | Automated Windows Runner | Completed | **Yes** | Single batch file (`run_ecomind.bat`) with venv activation, npm package validation, port conflict checks, and live dual terminal launching |
| **UI/UX Redesign** | Modern Light SaaS Interface | Completed | **Yes** | Conversational AI Assistant, prompt suggestions, keyboard shortcuts, Answer Card, Response Insights, 4-tab Sustainability Dashboard, and Eco Receipt modal |
| **Cloud Estimation** | Evidence-Grounded Estimation | Completed | **Yes** | ML.ENERGY Leaderboard v3.0 / EcoLogits adapters active via `ENABLE_CLOUD_ENERGY_ESTIMATION=true` in `backend/.env` with strict `ESTIMATED` labeling |
| **Docker & Compose** | Containerized Reproducibility | Completed | **Yes** | Production Dockerfiles (`python:3.10-slim` non-root user & `node:20`/`nginx:alpine`), `docker-compose.yml`, named persistent SQLite volume `ecomind-database-volume` |
| **GitHub Actions CI** | Automated Continuous Integration | Completed | **Yes** | 3-job CI pipeline (`backend-ci` 201 tests, `frontend-ci` TypeScript & Vite build, `docker-verification` multi-stage build tests) on push and PR to `main` |

---

## 4. Current File Structure & Roles

```text
backend/
├── main.py                     # FastAPI entry point, CORS, mounts routes_chat & routes_dashboard
├── api/
│   ├── routes_chat.py          # /chat, /tools, /models, /cache, /telemetry endpoints with live routing
│   ├── routes_dashboard.py     # /dashboard/summary, /environment, /routes, /timeseries, /receipts
│   ├── schemas.py              # Pydantic v2 schemas (ChatRequest, ChatResponse, TokenUsageSchema, CacheStatsSchema)
│   └── schemas_dashboard.py    # Pydantic v2 schemas for dashboard analytics & paginated receipts
├── database/
│   ├── __init__.py             # Database package exports
│   └── historical_store.py     # Persistent SQLite Historical Store for durable telemetry & Eco Receipts
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
│   ├── routing_policy.py       # Route selection prioritizing deterministic tools before logical model tiers
│   └── optimizer.py            # Multi-Objective Routing Optimizer (Pareto dominance + normalized scalar cost)
├── receipt/
│   ├── __init__.py             # Eco Receipt module exports
│   ├── schemas.py              # EcoReceipt, CostMetric, EnergyMetric, CarbonMetric, WaterMetric, OptimizerSummary
│   └── receipt_generator.py    # Honest, explainable receipt generator with Non-Zero safeguards
├── models/
│   ├── provider.py             # Abstract ModelProvider, ProviderResponse, TokenUsage
│   ├── groq_provider.py        # Groq LPU provider using official Groq SDK with usage tracking
│   ├── gemini_provider.py      # Google GenAI SDK wrapper with authentic token tracking
│   ├── local_provider.py       # Ollama integration with generic measurement provider sampling
│   ├── dispatcher.py           # Provider-agnostic ModelDispatcher for logical tiers
│   └── model_profiles.py       # Model catalog across small, medium, and large tiers
├── telemetry/
│   ├── __init__.py             # Module exports
│   ├── schemas.py              # ProvenanceStatus, MeasurementScope, ComparisonType, SourceType, EnvironmentalSource, GridIntensityRecord, TelemetryRecord, TelemetrySummary, SavingsComparison
│   ├── measurement.py          # Generic MeasurementProvider ABC, NvidiaNvmlProvider, AndroidEnergyProvider, AppleEnergyProvider, UnavailableProvider
│   ├── gpu.py                  # Low-level NVML ctypes C-binding, nvidia-smi fallback, GpuEnergyMonitor backward compatibility
│   ├── registry.py             # Versioned EnvironmentalSource registry with freshness audits (VALID, REVIEW_NEEDED, STALE)
│   ├── cloud_estimator.py      # Pluggable CloudEnergyEstimator (MLEnergyEstimator v3.0, EcoLogitsEstimator LCA, CompositeCloudEstimator)
│   ├── grid.py                 # GridIntensityManager with live adapter + Ember Climate 2024 regional fallbacks
│   ├── water.py                # WaterAccountingEngine with 4-scope water categories & anti-fabrication gates
│   ├── savings.py              # Pair-Wise Non-Zero Savings Rule calculator with comparison types and quality degradation penalties
│   └── telemetry.py            # Central thread-safe TelemetryCollector integrating hardware, cloud estimators, grid & water engines
├── config/
│   └── settings.py             # Pydantic BaseSettings loading from .env
└── tests/                      # 201 passing unit & integration tests
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
    ├── test_semantic_cache.py      # Comprehensive Phase 4 semantic cache & regression tests (16 tests)
    ├── test_telemetry.py           # Comprehensive Phase 5A measurement architecture tests (15 tests)
    ├── test_environmental_accounting.py # Phase 5B multi-provider accounting & Non-Zero Rule tests (12 tests)
    ├── test_environmental_accounting_upgrade.py # Phase 5B Upgrade source registry, cloud estimators, grid & water tests (27 tests)
    ├── test_optimizer.py           # Phase 6 Multi-Objective Optimizer & Pareto tests (17 tests)
    ├── test_eco_receipt.py         # Phase 7 Eco Receipt Generation & Explainability tests (18 tests)
    └── test_dashboard.py           # Phase 8 Historical Store persistence, deduplication & analytics tests (10 tests)
frontend/
├── src/App.tsx                 # View switcher (Playground vs Dashboard) with Eco Receipt inspection modal
├── src/components/             # Dashboard views: Overview, Environment, Routes, ReceiptsExplorer, ReceiptModal
└── package.json                # React 19, Vite, Tailwind CSS v4, Lucide React, Recharts
run_ecomind.bat                 # Unified single-command launcher for Windows (FastAPI + Vite)
```

---

## 5. Phase Summaries (0, 1, 2, 3, 4, and 5A)

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
   - "The semantic cache is designed to prefer cache misses over potentially incorrect cache hits."
   - Precision > Hit Rate. Semantic similarity alone is NOT sufficient for cache reuse.
2. **Two-Stage Validation Pipeline**:
   - Stage 1: Cosine similarity retrieval via FAISS `IndexFlatIP` and SentenceTransformers (`all-MiniLM-L6-v2`).
   - Stage 2: Conservative deterministic validation across freshness, temporal/numerical modifiers, scoping constraints, entities, and reasoning depth.
3. **Execution Precedence**: Deterministic tools execute FIRST (0 tokens, 0 cache overhead).
4. **Lifecycle & Persistence**: SQLite metadata store + FAISS vector index; TTL + LRU safe eviction.

### Phase 5A: Hardware-Agnostic Telemetry & Measurement Architecture (Completed & Live Integrated)
1. **Core Philosophy & Developer Note**:
   > "EcoMind is measurement-capability aware. Physical energy is reported only when a trustworthy measurement source is available. The absence of a measurement is represented explicitly rather than replaced with a fabricated estimate."
2. **Generic Measurement Interface**:
   - `MeasurementProvider` abstract base interface.
   - `NvidiaNvmlProvider`: Live GPU power/energy sampling via direct NVML ctypes C-binding with `nvidia-smi` fallback. Labeled: `"MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"`.
   - `AndroidEnergyProvider`: Ingestion interface and architectural contract for future native Android client device telemetry; returns `UNAVAILABLE` without remote client transmission.
   - `AppleEnergyProvider`: Architectural interface for Apple Silicon / iOS client telemetry; returns `UNAVAILABLE` when unsupplied.
   - `UnavailableProvider`: Safe fallback when no hardware sensor is available.
3. **Explicit Non-Conflated Scopes**:
   - `GPU_INFERENCE_WINDOW`: On-device GPU die & VRAM power draw during inference window only.
   - `DEVICE`: Whole-device battery/power rail consumption on client hardware.
   - `SYSTEM`: Full server/host power consumption (CPU, RAM, motherboard, storage, PSU losses).
   - `CLOUD_INFERENCE`: Cloud API execution where hardware power is inaccessible.
   - `UNKNOWN`: Fallback or unspecified measurement boundary.
4. **Strict Provenance**:
   - `MEASURED`: Physical hardware sensors, high-resolution timers, deterministic tools (0 tokens), cache hits (0 tokens).
   - `PROVIDER_REPORTED`: Authentic vendor API token counts and client-transmitted payloads.
   - `UNAVAILABLE`: Absent physical measurements, cloud provider energy, failed requests.
   - Zero fabrication: `ESTIMATED` is not used in Phase 5A.
5. **System Capability Introspection**:
   - Exposes `GET /telemetry/capabilities` (`gpu_energy`, `system_energy`, `device_energy`, `provider_energy`).
   - Graceful degradation: uses best real measurement source available, returns `null` + `UNAVAILABLE` otherwise, never substitutes fake estimates.

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
- Reject false cache hits when queries add constraints, temporal modifiers, different entities, or require deeper reasoning.
- Prevent caching of dynamic or time-sensitive queries to eliminate stale answer risks.
- Classify queries into 7 task categories via `QueryAnalyzer` and route to deterministic tools or logical model tiers (`small`, `medium`, `large`) via `RoutingPolicy`.
- Dynamically resolve logical tiers to configured providers (`GroqProvider`, `GeminiProvider`, `LocalProvider` / Ollama) via `ModelDispatcher`.
- Extract and display authentic token counts, measured latency, and cache telemetry in the React frontend.
- Measure live physical GPU energy on NVIDIA hardware via NVML during local inference windows with explicit limitation labeling.
- Decouple telemetry collection from vendor-specific code via generic `MeasurementProvider` abstraction.
- Enforce explicit measurement scopes (`GPU_INFERENCE_WINDOW`, `DEVICE`, `SYSTEM`, `CLOUD_INFERENCE`, `UNKNOWN`) so energy measurements are never ambiguously conflated.
- Introspect physical measurement capabilities via `GET /telemetry/capabilities`.
- Ingest client device telemetry via `AndroidEnergyProvider` and `AppleEnergyProvider` interfaces without pretending the backend accesses remote phones directly.
- Support manual execution path directives (`auto`, `deterministic_tool`, `semantic_cache`, `small_model`, `medium_model`, `large_model`).
- Introspect registered tools (`GET /tools`), model profiles (`GET /models`), cache statistics (`GET /cache/stats`), and telemetry (`GET /telemetry/summary`, `GET /telemetry/recent`, `GET /telemetry/capabilities`).
- Audit versioned environmental accounting sources, citations, and freshness statuses via `GET /telemetry/sources` and `GET /telemetry/sources/{id}`.
- Trigger automatic freshness audits via `POST /telemetry/sources/refresh`.
- Estimate cloud energy via pluggable estimators (`MLEnergyEstimator` empirical v3.0, `EcoLogitsEstimator` LCA model) when `ENABLE_CLOUD_ENERGY_ESTIMATION=True`.
- Dynamically manage grid carbon intensity across regional grids (Ember Climate 2024 fallbacks for US, US-CA, IN, DE, FR, UK, EU, GLOBAL) via `GET /telemetry/grid`.
- Safeguard water metrics across 4 discrete scopes (direct evaporative, indirect power, supply chain, total lifecycle) and preserve anti-fabrication standards.
- Compute pair-wise savings comparisons via `POST /telemetry/savings/compare`, enforcing the Non-Zero Rule, comparison types, and quality degradation penalties.

### Phase 5B: Environmental Accounting Methodology & Upgrade (Completed & Live Integrated)
1. **Multi-Provider Accounting**:
   - Explicit `UNAVAILABLE` status for cloud providers without per-request energy telemetry.
   - On-device NVIDIA GPU power scoped to `GPU_INFERENCE_WINDOW`.
   - Local GPU-board operational carbon conditioned on positive `LOCAL_GRID_INTENSITY_GCO2E_PER_KWH`.
2. **Versioned Source Registry & Freshness Audits**:
   - Tracks empirical citations (ML.ENERGY v3.0, EcoLogits 2024, Elsworth et al. 2025 TPU v5e, Ember 2024, Electricity Maps) with SHA-256 integrity checks.
3. **Pluggable Cloud Energy Estimators**:
   - `MLEnergyEstimator` and `EcoLogitsEstimator` gated by `ENABLE_CLOUD_ENERGY_ESTIMATION`.
4. **Regional Grid & 4-Category Water Safeguards**:
   - Dynamic grid adapter with Ember Climate 2024 fallback.
   - Discrete water scopes: Scope 1 direct, Scope 2 indirect, Scope 3 embodied, and lifecycle water.
5. **The Non-Zero Rule for Pair-Wise Savings**:
   - Unavailable values are never treated as zero; proxy differences ($\Delta \text{Calls}, \Delta \text{Tokens}, \Delta \text{Latency}$) are reported alongside integrity notices.

### Phase 6: Multi-Objective Routing Optimizer (Completed & Live Integrated)
1. **Four Fundamental Objectives**:
   - Answer Quality ($Q$), Expected Latency ($L$), Estimated Cost ($\$$), and Environmental Impact ($E$).
2. **Strict Quality First (Hard Constraints)**:
   - Evaluates required quality threshold ($Q \ge Q_{\text{req}}$) based on complexity (`high` $\to 0.80$, `medium` $\to 0.65$, `low` $\to 0.50$).
   - Prunes candidates failing the threshold; required answer quality is never compromised to save resources.
3. **Pareto Dominance Filtering**:
   - Evaluates multi-dimensional dominance among eligible candidates; isolates non-dominated candidates on the Pareto frontier.
4. **Normalized Scalarized Cost Scoring**:
   - Absolute quality deficit: $\bar{Q}_{\text{deficit}} = 1.0 - Q$.
   - Normalized metrics for latency, cost, and energy.
   - Composite score: $S(R) = w_Q \cdot \bar{Q}_{\text{deficit}} + w_L \cdot \bar{L} + w_{\$} \cdot \bar{\$} + w_E \cdot \bar{E}$ with configurable weights in `settings.py`.
5. **Dynamic Weight Renormalization (The Non-Zero Rule)**:
   - When environmental impact or cost is `UNAVAILABLE`, its weight is removed and remaining weights are proportionally renormalized ($w'_i = w_i / \sum_{j \in \text{Available}} w_j$). Missing values are never fabricated or treated as zero.
6. **Execution Pipeline Integration**:
   - Integrated into `/chat`, `/router/config`, and `/router/optimize`. Emits granular `RoutingDecision` telemetry attached to response metadata and `TelemetryRecord`.

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
- Reject false cache hits when queries add constraints, temporal modifiers, different entities, or require deeper reasoning.
- Prevent caching of dynamic or time-sensitive queries to eliminate stale answer risks.
- Classify queries into 7 task categories via `QueryAnalyzer` and route to deterministic tools or logical model tiers (`small`, `medium`, `large`) via `RoutingPolicy`.
- Dynamically resolve logical tiers to configured providers (`GroqProvider`, `GeminiProvider`, `LocalProvider` / Ollama) via `ModelDispatcher`.
- Extract and display authentic token counts, measured latency, and cache telemetry in the React frontend.
- Measure live physical GPU energy on NVIDIA hardware via NVML during local inference windows with explicit limitation labeling.
- Decouple telemetry collection from vendor-specific code via generic `MeasurementProvider` abstraction.
- Enforce explicit measurement scopes (`GPU_INFERENCE_WINDOW`, `DEVICE`, `SYSTEM`, `CLOUD_INFERENCE`, `UNKNOWN`) so energy measurements are never ambiguously conflated.
- Introspect physical measurement capabilities via `GET /telemetry/capabilities`.
- Ingest client device telemetry via `AndroidEnergyProvider` and `AppleEnergyProvider` interfaces without pretending the backend accesses remote phones directly.
- Support manual execution path directives (`auto`, `deterministic_tool`, `semantic_cache`, `small_model`, `medium_model`, `large_model`).
- Introspect registered tools (`GET /tools`), model profiles (`GET /models`), cache statistics (`GET /cache/stats`), and telemetry (`GET /telemetry/summary`, `GET /telemetry/recent`, `GET /telemetry/capabilities`).
- Audit versioned environmental accounting sources, citations, and freshness statuses via `GET /telemetry/sources` and `GET /telemetry/sources/{id}`.
- Trigger automatic freshness audits via `POST /telemetry/sources/refresh`.
- Estimate cloud energy via pluggable estimators (`MLEnergyEstimator` empirical v3.0, `EcoLogitsEstimator` LCA model) when `ENABLE_CLOUD_ENERGY_ESTIMATION=True`.
- Dynamically manage grid carbon intensity across regional grids (Ember Climate 2024 fallbacks for US, US-CA, IN, DE, FR, UK, EU, GLOBAL) via `GET /telemetry/grid`.
- Safeguard water metrics across 4 discrete scopes (direct evaporative, indirect power, supply chain, total lifecycle) and preserve anti-fabrication standards.
- Compute pair-wise savings comparisons via `POST /telemetry/savings/compare`, enforcing the Non-Zero Rule, comparison types, and quality degradation penalties.
- Run automated multi-objective Pareto optimization across quality ($Q$), latency ($L$), cost ($\$$), and environmental impact ($E$) with dynamic weight renormalization via `POST /router/optimize` and `/chat`.
- Introspect router configurations, weights, and thresholds via `GET /router/config`.

### Phase 7: Eco Receipt Generation (Completed & Live Integrated)
1. **Machine-Readable Itemized Invoice**:
   - `EcoReceipt` schema attached to every `ChatResponse` and retrievable via `GET /receipts/{request_id}` and `GET /telemetry/receipt/{request_id}`.
2. **Defensible Monetary Cost Accounting**:
   - Accurately tracks $0.00 for deterministic tools and cache hits, 0.00 for local models, and calculates catalog pricing for cloud models without fabrication.
3. **Strict Environmental Transparency**:
   - Distinguishes measured (e.g. GPU board energy in `GPU_INFERENCE_WINDOW`) vs estimated (operational carbon conditioned on grid intensity) vs unmeasured values (`UNAVAILABLE`).
   - Unavailable values strictly remain `null` / `None` and are never coerced to zero.
4. **Honest Explainability & Anti-Fabrication Safeguards**:
   - Transparent selection summary based on Phase 6 optimizer decision metadata and weights.
   - Comprehensive disclosures of scope boundaries (GPU energy is not system energy) and non-optimality disclaimers.
   - Respects failed requests honestly without inventing completion metrics.

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
- Reject false cache hits when queries add constraints, temporal modifiers, different entities, or require deeper reasoning.
- Prevent caching of dynamic or time-sensitive queries to eliminate stale answer risks.
- Classify queries into 7 task categories via `QueryAnalyzer` and route to deterministic tools or logical model tiers (`small`, `medium`, `large`) via `RoutingPolicy`.
- Dynamically resolve logical tiers to configured providers (`GroqProvider`, `GeminiProvider`, `LocalProvider` / Ollama) via `ModelDispatcher`.
- Extract and display authentic token counts, measured latency, and cache telemetry in the React frontend.
- Measure live physical GPU energy on NVIDIA hardware via NVML during local inference windows with explicit limitation labeling.
- Decouple telemetry collection from vendor-specific code via generic `MeasurementProvider` abstraction.
- Enforce explicit measurement scopes (`GPU_INFERENCE_WINDOW`, `DEVICE`, `SYSTEM`, `CLOUD_INFERENCE`, `UNKNOWN`) so energy measurements are never ambiguously conflated.
- Introspect physical measurement capabilities via `GET /telemetry/capabilities`.
- Ingest client device telemetry via `AndroidEnergyProvider` and `AppleEnergyProvider` interfaces without pretending the backend accesses remote phones directly.
- Support manual execution path directives (`auto`, `deterministic_tool`, `semantic_cache`, `small_model`, `medium_model`, `large_model`).
- Introspect registered tools (`GET /tools`), model profiles (`GET /models`), cache statistics (`GET /cache/stats`), and telemetry (`GET /telemetry/summary`, `GET /telemetry/recent`, `GET /telemetry/capabilities`).
- Audit versioned environmental accounting sources, citations, and freshness statuses via `GET /telemetry/sources` and `GET /telemetry/sources/{id}`.
- Trigger automatic freshness audits via `POST /telemetry/sources/refresh`.
- Estimate cloud energy via pluggable estimators (`MLEnergyEstimator` empirical v3.0, `EcoLogitsEstimator` LCA model) when `ENABLE_CLOUD_ENERGY_ESTIMATION=True` (configured and active in `backend/.env`).
- Dynamically manage grid carbon intensity across regional grids (Ember Climate 2024 fallbacks for US, US-CA, IN, DE, FR, UK, EU, GLOBAL) via `GET /telemetry/grid`.
- Safeguard water metrics across 4 discrete scopes (direct evaporative, indirect power, supply chain, total lifecycle) and preserve anti-fabrication standards.
- Compute pair-wise savings comparisons via `POST /telemetry/savings/compare`, enforcing the Non-Zero Rule, comparison types, and quality degradation penalties.
- Run automated multi-objective Pareto optimization across quality ($Q$), latency ($L$), cost ($\$$), and environmental impact ($E$) with dynamic weight renormalization via `POST /router/optimize` and `/chat`.
- Introspect router configurations, weights, and thresholds via `GET /router/config`.
- Generate machine-readable, transparent **Eco Receipts** for all requests via `/chat` or `GET /receipts/{request_id}` with full explainability.
- Durably store historical requests, telemetry, and Eco Receipts in SQLite (`database/historical_telemetry.db`).
- Serve longitudinal analytics via 6 REST endpoints (`/dashboard/summary`, `/dashboard/environment`, `/dashboard/routes`, `/dashboard/timeseries`, `/dashboard/receipts`, `/dashboard/receipts/{request_id}`).
- Deliver a modern, light-themed SaaS user interface (React 19 + TypeScript + Tailwind CSS v4) featuring a welcoming AI Assistant, conversational prompt suggestions, human-friendly **Response Insights**, and a 4-tab Sustainability Dashboard with Eco Receipt inspection.
- Launch the entire full-stack platform locally through a unified single-command script (`run_ecomind.bat`).
- Run the full-stack system reproducibly in any environment using Docker and Docker Compose (`docker-compose up --build`) with automatic reverse-proxying, non-root backend execution, and persistent SQLite storage.
- Automatically validate all 201 backend tests, strict TypeScript types, frontend builds, and Docker container builds on every push and pull request via GitHub Actions CI (`.github/workflows/ci.yml`).

---

## 7. Current System State & Production Readiness

With deterministic tools (Phase 3), accuracy-first semantic cache (Phase 4), hardware-agnostic physical measurement (Phase 5A), auditable environmental accounting and cloud estimation (Phase 5B), the multi-objective Pareto routing optimizer (Phase 6), itemized Eco Receipts (Phase 7), persistent SQLite telemetry storage and the 4-tab Sustainability Dashboard (Phase 8), unified single-command launcher (`run_ecomind.bat`), modern light-theme SaaS interface, Docker containerization with Compose orchestration, and an automated GitHub Actions CI pipeline, **EcoMind is fully functional, complete, and verified across all 201 backend tests with 0 frontend compilation warnings or errors.**

