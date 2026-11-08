# EcoMind — System Architecture Reference

> **Comprehensive Architectural Specifications, Data Flow, and Request Traces**  
> *Repository State: Phase 8 (Sustainability Dashboard & Historical Analytics)*

---

## 1. Planned Full Architecture (Target Vision)

```text
User Query
    │
    ▼
┌────────────────────────────────────────────────────────┐
│                   Query Analyzer                       │ (Phase 3: Task type & complexity detection)
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Semantic Cache                       │ (Phase 4: Two-Stage FAISS cosine similarity
└─────────────────┬────────────────────┬─────────────────┘  + Stage 2 conservative compatibility check)
                  │ Cache Hit          │ Cache Miss
                  ▼                    ▼
           [Return Cached]     ┌────────────────────────────────────────────────────────┐
           [Eco Receipt  ]     │              Candidate Route Generator                 │
                               └──────────────────────────┬─────────────────────────────┘
                                                          │
          ┌───────────────────┬───────────────────────────┼────────────────────┬────────────────────┐
          ▼                   ▼                           ▼                    ▼                    ▼
    Deterministic       Semantic Cache                  Small Model          Medium Model         Large Model
        Tool            (Refresh Path)                 (Local Ollama)       (Cloud Flash/Groq)   (Cloud Pro/Groq)
          │                   │                           │                    │                    │
          └───────────────────┴───────────────────────────┼────────────────────┴────────────────────┘
                                                          │
                                                          ▼
                                       ┌────────────────────────────────────────┐
                                       │ Hardware Telemetry & Accounting Engine │ (Phase 5A: NVML physical GPU,
                                       └──────────────────┬─────────────────────┘  Phase 5B: Scopes & non-zero savings)
                                                          │
                                                          ▼
                                       ┌────────────────────────────────────────┐
                                       │        Multi-Objective Optimizer       │ (Phase 6: Quality constraints,
                                       └──────────────────┬─────────────────────┘  Pareto frontier & scalarized score)
                                                          │
                                                          ▼
                                       ┌────────────────────────────────────────┐
                                       │             Model Dispatcher           │ (Phase 3: Provider-Agnostic)
                                       └──────────────────┬─────────────────────┘
                                                          │
                                                          ▼
                                       ┌────────────────────────────────────────┐
                                       │          Optional Verifier             │ (Quality check / self-consistency)
                                       └──────────────────┬─────────────────────┘
                                                          │
                                                          ▼
                                               Answer + Eco Receipt (Phase 7: Itemized Invoice)
```

### Architecture Lifecycle & Phase Status

| Architecture Layer | Phase | Implementation Status | Key Modules |
|---|---|---|---|
| **Control Plane Core & API** | Phase 1 & 2 | **Completed & Verified** | [`main.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/main.py), [`routes_chat.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/routes_chat.py) |
| **Deterministic Tool Subsystem** | Phase 2 & 3 | **Completed & Verified** | [`tool_registry.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/tools/tool_registry.py), 5 deterministic tools (0 tokens) |
| **Provider-Agnostic Model Routing** | Phase 3 | **Completed & Verified** | [`query_analyzer.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/router/query_analyzer.py), [`routing_policy.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/router/routing_policy.py), [`dispatcher.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/models/dispatcher.py) |
| **Precision-First Semantic Cache** | Phase 4 | **Completed & Verified** | [`semantic_cache.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/cache/semantic_cache.py), [`cache_store.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/cache/cache_store.py), [`compatibility_checker.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/cache/compatibility_checker.py) |
| **Hardware Telemetry Layer** | Phase 5A | **Completed & Verified** | [`measurement.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/measurement.py), [`gpu.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/gpu.py), [`telemetry.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/telemetry.py) |
| **Environmental Accounting & Registry** | Phase 5B | **Completed & Verified** | [`registry.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/registry.py), [`cloud_estimator.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/cloud_estimator.py), [`grid.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/grid.py), [`water.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/water.py), [`savings.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/savings.py), Non-Zero Rule, 156 tests |
| **Multi-Objective Optimizer** | Phase 6 | **Completed & Verified** | [`optimizer.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/router/optimizer.py), [`routing_policy.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/router/routing_policy.py), [`routes_chat.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/routes_chat.py), Pareto filtering, dynamic weight renormalization, 173 tests |
| **Eco Receipt Generation** | Phase 7 | **Completed & Verified** | [`receipt/schemas.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/receipt/schemas.py), [`receipt_generator.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/receipt/receipt_generator.py), itemized resource invoices, explainability, 191 tests |
| **Sustainability Dashboard** | Phase 8 | **Completed & Verified** | [`database/historical_store.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/database/historical_store.py), [`routes_dashboard.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/routes_dashboard.py), [`schemas_dashboard.py`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas_dashboard.py), React 19 dashboard with 4 analytics views & receipt modal, 201 tests |
| **Local Launcher & Modern UI/UX** | Post-Phase 8 | **Completed & Verified** | [`run_ecomind.bat`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/run_ecomind.bat), light SaaS theme, conversational AI assistant, prompt suggestions, response insights, and ML.ENERGY cloud estimation |

---

## 2. Current Implemented Architecture (Phase 8 Actual)

The diagram below reflects the active control plane execution graph implemented across the backend:

```text
HTTP POST /chat { query, preferred_route }
                   │
                   ▼
     FastAPI Router ([routes_chat.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/routes_chat.py))
                   │
  ┌────────────────┴────────────────────────────────────────────────────────────────────────┐
  │                                                                                         │
  ▼ [route_pref in ("auto", "deterministic_tool")]                                          │
[Step 1] Deterministic Tool Check                                                           │
ToolRegistry.find_candidate_tool(query)                                                     │
  │                                                                                         │
  ├──► Tool Match Found?                                                                    │
  │    ├── AST Calculator (Math expressions)                                                │
  │    ├── UnitConverter (Length, mass, temp)                                               │
  │    ├── DateTimeCalculator (Dates, offsets)                                              │
  │    ├── StatisticsTool (Mean, median, stdev)                                             │
  │    └── TextAnalyzer (Word/char/sentence metrics)                                        │
  │         │                                                                               │
  │         ▼                                                                               │
  │    Tool.execute(query) ──► ToolResult                                                   │
  │         • 0 model tokens consumed (MEASURED)                                            │
  │         • Latency < 1 ms via time.perf_counter (MEASURED)                               │
  │         • Avoidance: 1 model call avoided vs. baseline                                  │
  │         ▼                                                                               │
  │    TelemetryCollector.record_success(...) ──► ChatResponse JSON                         │
  │                                                                                         │
  └──► Tool Not Found (or route_pref == "auto")                                             │
       │                                                                                    │
       ▼                                                                                    │
[Step 2] Semantic Cache Lookup (route_pref in ("auto", "semantic_cache"))                   │
SemanticCache.lookup(query)                                                                 │
  │                                                                                         │
  ├── Stage 1: Cosine Retrieval (all-MiniLM-L6-v2 + FAISS IndexFlatIP)                      │
  │            Candidate similarity >= threshold (0.90 default)                             │
  │                                                                                         │
  └── Stage 2: Conservative Deterministic Validation (CompatibilityChecker)                 │
               ├── Dynamic/time-sensitive queries rejected                                  │
               ├── Scoping and entity matching verified                                     │
               ├── Temporal/numerical modifier delta rejected                               │
               └── Reasoning depth requirements matched                                    │
                    │                                                                       │
                    ├──► [CACHE HIT] (status == "hit")                                      │
                    │    • Return stored answer immediately                                 │
                    │    • 0 tokens, 0 model inference calls (MEASURED)                     │
                    │    • Latency ~3-5 ms (MEASURED)                                       │
                    │    • Avoidance: 1 model call avoided vs. baseline                     │
                    │    ▼                                                                  │
                    │    TelemetryCollector.record_success(...) ──► ChatResponse JSON       │
                    │                                                                       │
                    └──► [CACHE MISS] (status == "miss")                                    │
                         │                                                                  │
                         ▼                                                                  │
[Step 3] Model Tier Selection                                                               │
  ├── If route_pref in ("small_model", "medium_model", "large_model"):                      │
  │   └── User override maps directly to logical tier: "small" / "medium" / "large"        │
  │                                                                                         │
  └── If route_pref == "auto":                                                              │
      QueryAnalyzer.analyze(query)                                                          │
        │ (7 task categories, low/medium/high complexity, reasoning flag)                   │
        ▼                                                                                   │
      RoutingPolicy.select_route(analysis)                                                  │
        │ (selects logical tier: "small", "medium", or "large")                             │
        ▼                                                                                   │
  ┌─────────────────────────────────────────────────────────────────────────────────────────┘
  │
  ▼
[Step 4] Provider-Agnostic Model Dispatcher ([dispatcher.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/models/dispatcher.py))
ModelDispatcher.dispatch(tier, query)
  │
  ├── Resolves logical tier -> configured (provider, model) in [settings.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/config/settings.py)
  │     ├── small  ──► settings.SMALL_PROVIDER,  settings.SMALL_MODEL  (e.g. groq: gpt-oss-20b)
  │     ├── medium ──► settings.MEDIUM_PROVIDER, settings.MEDIUM_MODEL (e.g. google: gemini-2.5-flash)
  │     └── large  ──► settings.LARGE_PROVIDER,  settings.LARGE_MODEL  (e.g. groq: llama-3.3-70b)
  │
  ▼
[Step 5] Provider Execution & Telemetry Capture
  ├── GroqProvider (Groq LPU API)
  │     • Authentic token usage from response.usage (PROVIDER_REPORTED)
  │     • Wall-clock latency measured via time.perf_counter (MEASURED)
  │     • Cloud energy: ESTIMATED via MLEnergyEstimator / EcoLogits when ENABLE_CLOUD_ENERGY_ESTIMATION=True
  │       (labeled ESTIMATED, Scope: CLOUD_INFERENCE, +/-20% uncertainty)
  │     • Cloud water & carbon: UNAVAILABLE without remote datacenter facility disclosures (Anti-fabrication safeguard)
  │
  ├── GeminiProvider (Google GenAI SDK)
  │     • Authentic tokens from response.usage_metadata (PROVIDER_REPORTED)
  │     • Wall-clock latency measured via time.perf_counter (MEASURED)
  │     • Cloud energy: ESTIMATED via MLEnergyEstimator / EcoLogits when ENABLE_CLOUD_ENERGY_ESTIMATION=True
  │     • Cloud water & carbon: UNAVAILABLE without remote datacenter facility disclosures
  │
  └── LocalProvider (Local Ollama Daemon + MeasurementProvider Sampling)
        • Authentic tokens from Ollama eval_count (PROVIDER_REPORTED)
        • Wall-clock latency measured via time.perf_counter (MEASURED)
        • Physical GPU energy sampled via NVML C-binding (MEASURED, GPU_INFERENCE_WINDOW)
        • Operational carbon conditionally estimated via LOCAL_GRID_INTENSITY_GCO2E_PER_KWH
          (ESTIMATED, GPU_BOARD_OPERATIONAL_CARBON)
  │
  ▼
[Step 6] Cache Auto-Population (if route_pref == "auto" and successful)
SemanticCache.store_result(...) ──► Persisted into SQLite + FAISS index
  │
  ▼
[Step 7] Central Telemetry Recording ([telemetry.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/telemetry.py))
TelemetryCollector.record_success(...)
  • Emits TelemetryRecord with strict provenance (MEASURED, PROVIDER_REPORTED, ESTIMATED, UNAVAILABLE)
  • Appends to thread-safe in-memory ring buffer (1000 items)
  • Attaches full TelemetryRecord to ChatResponse
  │
  ▼
ChatResponse JSON
```

---

## 3. Component Interaction & Module Architecture

```text
backend/
├── main.py
│    └── Mounts FastAPI APIRouter from api/routes_chat.py
│
├── api/
│    ├── routes_chat.py ───────── Controls request flow, tool dispatch, cache lookup, model routing, telemetry
│    └── schemas.py ───────────── Pydantic v2 data contracts (ChatRequest, ChatResponse, TokenUsageSchema, etc.)
│
├── tools/
│    ├── base.py ──────────────── Abstract BaseTool and ToolResult dataclasses
│    ├── calculator.py ────────── AST-based deterministic calculator (0 tokens, 0 neural networks)
│    ├── unit_converter.py ────── Deterministic length, mass, and temperature conversion
│    ├── datetime_calculator.py ── Deterministic date differences, offsets, weekdays, leap-years
│    ├── statistics_tool.py ───── Deterministic descriptive statistics (mean, median, stdev, etc.)
│    ├── text_analyzer.py ─────── Deterministic text metrics (word/char/sentence count, frequency)
│    └── tool_registry.py ─────── Central tool catalog & find_candidate_tool query matcher
│
├── cache/
│    ├── semantic_cache.py ────── Precision-first SemanticCache controller orchestrating Stage 1 & Stage 2
│    ├── embedding_service.py ─── SentenceTransformers service (all-MiniLM-L6-v2) with mockable encoder
│    ├── cache_store.py ───────── SQLite metadata persistence + FAISS IndexFlatIP cosine retrieval
│    └── compatibility_checker.py Conservative Stage 2 validator (freshness, scoping, entities, modifiers)
│
├── router/
│    ├── query_analyzer.py ────── Task classification (7 categories) and complexity heuristic
│    └── routing_policy.py ────── Priority-ordered route selector (deterministic tools before model tiers)
│
├── models/
│    ├── provider.py ──────────── Abstract ModelProvider, ProviderResponse, TokenUsage
│    ├── groq_provider.py ─────── Groq LPU API client with authentic usage token tracking
│    ├── gemini_provider.py ───── Google GenAI SDK client with authentic usage_metadata tracking
│    ├── local_provider.py ────── Ollama HTTP integration with MeasurementProvider sampling hooks
│    ├── dispatcher.py ────────── Provider-agnostic ModelDispatcher resolving tiers to providers
│    └── model_profiles.py ────── Model catalog definitions across small, medium, and large tiers
│
├── telemetry/
│    ├── schemas.py ───────────── ProvenanceStatus, MeasurementScope, ComparisonType, SourceType,
│    │                            EnvironmentalSource, GridIntensityRecord, TelemetryRecord,
│    │                            AvoidanceTelemetry, MetricSavings, SavingsComparison
│    ├── measurement.py ───────── Generic MeasurementProvider ABC (NvidiaNvmlProvider,
│    │                            AndroidEnergyProvider, AppleEnergyProvider, UnavailableProvider)
│    ├── gpu.py ───────────────── NVML ctypes C-binding with nvidia-smi fallback
│    ├── registry.py ──────────── Versioned EnvironmentalSource registry with freshness audits (VALID, REVIEW_NEEDED, STALE)
│    ├── cloud_estimator.py ───── Pluggable CloudEnergyEstimator (MLEnergyEstimator v3.0, EcoLogitsEstimator LCA, Composite)
│    ├── grid.py ──────────────── GridIntensityManager with live adapter + Ember Climate 2024 regional fallbacks
│    ├── water.py ─────────────── WaterAccountingEngine with 4-scope water categories & anti-fabrication gates
│    ├── savings.py ───────────── Pair-Wise Non-Zero Rule savings calculator with comparison types & quality penalties
│    └── telemetry.py ─────────── Central thread-safe TelemetryCollector ring-buffer & capability resolver
│
└── config/
     └── settings.py ──────────── Application settings loaded from environment/.env
```

---

## 4. End-to-End Execution Traces

### Trace A: Deterministic Tool Path (Zero Tokens, Sub-Millisecond)
```text
Query: "convert 100 km to miles" (preferred_route: "auto")

[Client / Frontend]
   │  HTTP POST /chat {"query": "convert 100 km to miles", "preferred_route": "auto"}
   ▼
[FastAPI / routes_chat.py]
   │  Calls ToolRegistry.find_candidate_tool() -> UnitConverter
   ▼
[UnitConverter.execute]
   │  Computes 100 km * 0.621371 = 62.137119 miles deterministically
   │  Returns ToolResult(success=True, result=62.137119, execution_time_ms=0.08)
   ▼
[TelemetryCollector.record_success]
   │  Tokens: prompt=0, completion=0, total=0 (MEASURED)
   │  Latency: total=0.45 ms, inference=0.08 ms (MEASURED)
   │  Avoidance: model_calls_avoided=1, baseline="large_model"
   │  Environment: physical energy/water/carbon = UNAVAILABLE (zero fabrication)
   ▼
[FastAPI / routes_chat.py]
   │  Returns ChatResponse:
   │    • answer: "62.137119"
   │    • route: "Unit_converter / Deterministic Tool"
   │    • provider: "deterministic", model: "None"
   │    • token_usage: { prompt: 0, completion: 0, total: 0, is_estimated: false }
   │    • large_model_avoided: True
   │    • cache_status: "not_checked"
   │    • telemetry: TelemetryRecord (with AvoidanceTelemetry)
```

---

### Trace B: Precision-First Semantic Cache Hit Path (Zero Tokens, Sub-10ms)
```text
Query: "What are the primary colors?" (preferred_route: "auto", previously answered and cached)

[Client / Frontend]
   │  HTTP POST /chat {"query": "What are the primary colors?", "preferred_route": "auto"}
   ▼
[FastAPI / routes_chat.py]
   │  ToolRegistry.find_candidate_tool() -> None (Not a calculation/converter task)
   │  SemanticCache.lookup("What are the primary colors?")
   ▼
[SemanticCache & CompatibilityChecker]
   │  Stage 1: Vector embedding generated; FAISS IndexFlatIP cosine similarity = 0.96 (>= 0.90)
   │  Stage 2: CompatibilityChecker validates:
   │            • Temporal/dynamic check: PASS (static educational question)
   │            • Scoping modifiers: PASS (identical intent)
   │            • Entities and numbers: PASS
   │            • Reasoning depth: PASS
   │  Status: "hit", entry retrieved from SQLite
   ▼
[TelemetryCollector.record_success]
   │  Tokens: prompt=0, completion=0, total=0 (MEASURED)
   │  Latency: total=3.82 ms, inference=0.0 ms (MEASURED)
   │  Avoidance: model_calls_avoided=1, baseline="large_model"
   │  Environment: physical energy/water/carbon = UNAVAILABLE (zero fabrication)
   ▼
[FastAPI / routes_chat.py]
   │  Returns ChatResponse:
   │    • answer: "The primary colors are red, yellow, and blue..."
   │    • route: "semantic_cache"
   │    • provider: "cache", model: None
   │    • token_usage: { prompt: 0, completion: 0, total: 0, is_estimated: false }
   │    • large_model_avoided: True
   │    • cache_status: "hit", cache_similarity: 0.96
   │    • telemetry: TelemetryRecord (with AvoidanceTelemetry)
```

---

### Trace C: Dynamic Cloud Model Routing Path (Groq / Gemini)
```text
Query: "Summarize the history of Unix in three sentences" (preferred_route: "auto")

[Client / Frontend]
   │  HTTP POST /chat {"query": "Summarize the history of Unix...", "preferred_route": "auto"}
   ▼
[FastAPI / routes_chat.py]
   │  ToolRegistry.find_candidate_tool() -> None
   │  SemanticCache.lookup() -> "miss"
   │  QueryAnalyzer.analyze() -> task_type="summarization", complexity="low"
   │  RoutingPolicy.select_route() -> logical tier: "small"
   ▼
[ModelDispatcher.dispatch("small")]
   │  Resolves tier "small" -> provider="groq", model="openai/gpt-oss-20b"
   ▼
[GroqProvider.generate]
   │  Calls Groq LPU API client.chat.completions.create(...)
   │  Measures inference duration via time.perf_counter: 185.2 ms (MEASURED)
   │  Extracts authentic tokens from completion.usage: prompt=28, completion=64, total=92 (PROVIDER_REPORTED)
   ▼
[SemanticCache.store_result]
   │  Stores prompt, answer, embedding vector, and token telemetry in SQLite + FAISS
   ▼
[TelemetryCollector.record_success]
   │  Tokens: prompt=28, completion=64, total=92 (PROVIDER_REPORTED)
   │  Latency: total=198.4 ms (MEASURED), inference=185.2 ms (MEASURED)
   │  Environment: energy/water/carbon = UNAVAILABLE, scope=CLOUD_INFERENCE (zero fabrication)
   ▼
[FastAPI / routes_chat.py]
   │  Returns ChatResponse:
   │    • route: "Small Model (Groq)"
   │    • model: "openai/gpt-oss-20b"
   │    • provider: "groq"
   │    • token_usage: { prompt: 28, completion: 64, total: 92, is_estimated: false }
   │    • large_model_avoided: True
   │    • cache_status: "miss"
   │    • telemetry: TelemetryRecord (CLOUD_INFERENCE, UNAVAILABLE physical energy)
```

---

### Trace D: Local Model Execution with On-Device GPU Telemetry & Conditional Carbon
```text
Query: "Draft an outline for a project proposal" (preferred_route: "small_model" configured for local Ollama)

[Client / Frontend]
   │  HTTP POST /chat {"query": "Draft an outline...", "preferred_route": "small_model"}
   ▼
[ModelDispatcher.dispatch("small")]
   │  Resolves tier "small" -> provider="local", model="llama3.1:8b"
   ▼
[LocalProvider.generate + NvidiaNvmlProvider sampling]
   │  NvidiaNvmlProvider begins background sampling of GPU power via NVML C-binding
   │  Calls Ollama daemon endpoint: POST http://localhost:11434/api/generate
   │  Extracts authentic tokens: prompt=15, completion=120, total=135 (PROVIDER_REPORTED)
   │  NvidiaNvmlProvider stops sampling upon completion:
   │    • average_power_watts: 112.4 W
   │    • energy_joules: 348.6 J (MEASURED, GPU_INFERENCE_WINDOW scope)
   │    • sample_count: 31 samples over 3100 ms
   ▼
[TelemetryCollector.record_success]
   │  Tokens: prompt=15, completion=120, total=135 (PROVIDER_REPORTED)
   │  Latency: total=3140 ms, inference=3100 ms (MEASURED)
   │  Physical Energy: 348.6 J (MEASURED, GPU_INFERENCE_WINDOW via NvidiaNvmlProvider)
   │  Local Grid Carbon (Conditional):
   │    • If LOCAL_GRID_INTENSITY_GCO2E_PER_KWH = 400.0:
   │      carbon_gco2e = (348.6 / 3,600,000) * 400.0 = 0.038733 gCO2e
   │      provenance = ESTIMATED, scope = GPU_BOARD_OPERATIONAL_CARBON
   │    • If LOCAL_GRID_INTENSITY_GCO2E_PER_KWH <= 0 or unconfigured:
   │      carbon_gco2e = null, provenance = UNAVAILABLE
   │  Water: UNAVAILABLE (zero fabrication)
   ▼
[FastAPI / routes_chat.py]
   │  Returns ChatResponse with complete on-device physical measurement telemetry
```

---

### Trace E: Pair-Wise Environmental Savings Comparison (Enforcing Non-Zero Rule)
```text
Client Request: POST /telemetry/savings/compare
Payload: {
  "selected_request_id": "<req-deterministic-tool-uuid>",
  "baseline_request_id": "<req-large-cloud-model-uuid>",
  "quality_threshold_met": true
}

[FastAPI / routes_chat.py -> telemetry/savings.py: calculate_savings]
   │
   ├── Baseline Route: "Large Model (Groq)" (Cloud API)
   │     • Tokens: total=150 (PROVIDER_REPORTED)
   │     • Latency: 480.0 ms (MEASURED)
   │     • Energy: UNAVAILABLE, Water: UNAVAILABLE, Carbon: UNAVAILABLE
   │
   ├── Selected Route: "Calculator / Deterministic Tool"
   │     • Tokens: total=0 (MEASURED)
   │     • Latency: 0.8 ms (MEASURED)
   │     • Energy: UNAVAILABLE, Water: UNAVAILABLE, Carbon: UNAVAILABLE
   │
   ├── [Evaluation of Non-Zero Rule]:
   │     selected.energy (UNAVAILABLE) OR baseline.energy (UNAVAILABLE) == True
   │     ──► energy_savings.provenance = UNAVAILABLE, savings_value = null
   │     ──► water_savings.provenance  = UNAVAILABLE, savings_value = null
   │     ──► carbon_savings.provenance = UNAVAILABLE, savings_value = null
   │     ──► Notice: "Physical environmental savings are UNAVAILABLE for this comparison
   │                  (zero fabrication). Authentic operational proxies are reported."
   │
   └── [Evaluation of Operational Proxies]:
         • model_calls_avoided: 1 (avoided neural network call)
         • tokens_saved: 150 (baseline 150 - selected 0)
         • tokens_provenance: MEASURED
         • latency_delta_ms: 479.2 ms (480.0 - 0.8)
   ▼
Returns SavingsComparison JSON with authentic operational proxies and zero fabricated numbers
```

---

## 5. Environmental Accounting Methodology & Scientific Integrity (Phase 5B)

EcoMind follows a strict scientific integrity mandate documented in [`docs/research/phase_5b_environmental_accounting.md`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/docs/research/phase_5b_environmental_accounting.md).

### 5.1 The Four Provenance Classifications

All metrics emitted by the control plane carry an explicit [ProvenanceStatus](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py#L5):

| Provenance Status | Description | System Usage |
|---|---|---|
| **`MEASURED`** | Directly measured on active hardware using high-resolution timers, hardware sensors, or exact mathematical counts. | Wall-clock latency (`time.perf_counter`), deterministic tool tokens ($0$), semantic cache tokens ($0$), on-device GPU power/energy via NVML C-binding. |
| **`PROVIDER_REPORTED`** | Authentic operational metrics returned directly by model APIs and daemon protocols. | Prompt, completion, and total tokens from Groq (`chat.completion.usage`), Google Gemini (`response.usage_metadata`), and Ollama (`prompt_eval_count`, `eval_count`). |
| **`ESTIMATED`** | Scientifically grounded estimates derived transparently from measured energy and verified operational parameters. | Local GPU-board operational carbon derived strictly from measured GPU energy and user-configured grid carbon intensity (`LOCAL_GRID_INTENSITY_GCO2E_PER_KWH`). |
| **`UNAVAILABLE`** | Physical values that cannot be authentically measured on the current system or for opaque cloud providers. | Physical energy, water, and carbon for cloud API calls (Groq, Gemini); physical energy when hardware sensor is absent; failed requests. |

### 5.2 Explicit Measurement Scopes

Energy and carbon values are never ambiguously conflated across hardware boundaries. Every measurement specifies a [MeasurementScope](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py#L20):

* **`GPU_INFERENCE_WINDOW`**: Physical power draw of the on-device NVIDIA GPU die and VRAM strictly during the model inference window. Explicitly excludes host CPU, motherboard, storage, fans, and power supply losses.
* **`GPU_BOARD_OPERATIONAL_CARBON`**: Operational carbon emissions derived exclusively from `GPU_INFERENCE_WINDOW` energy.
* **`DEVICE`**: Whole-device battery/power rail draw on client hardware (e.g. Android battery fuel gauge).
* **`SYSTEM`**: Complete server or workstation power consumption (CPU, RAM, motherboard, storage, cooling, PSU).
* **`CLOUD_INFERENCE`**: Execution on third-party cloud infrastructure where physical hardware power is opaque.
* **`UNKNOWN`**: Fallback or unspecified boundary.

### 5.3 The Pair-Wise Non-Zero Savings Rule

When comparing an executed route against a baseline route:

$$\text{If either } M(R_{\text{selected}}) = \text{UNAVAILABLE} \quad \text{or} \quad M(R_{\text{baseline}}) = \text{UNAVAILABLE}:$$

$$\Delta M = M(R_{\text{baseline}}) - M(R_{\text{selected}}) \equiv \mathbf{UNAVAILABLE}$$

* **No Synthetic Zeros**: Unmeasured energy or water is never treated as $0.0$.
* **Proxy Reporting**: When physical savings are unavailable, genuine operational proxies ($\Delta \text{Model Calls}$, $\Delta \text{Tokens}$, $\Delta \text{Latency}$) are reported alongside an integrity notice.
* **Quality Gate**: If the selected route fails the required answer quality threshold ($\text{Quality} < Q_{\text{req}}$), resource savings cannot be credited without flagging a quality degradation penalty.

---

## 6. Standard Data Contracts & Schemas

### 6.1 Control Plane Request & Response

```text
ChatRequest ([api/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py))
 ├── query: str
 └── preferred_route: Optional[str] = "auto"
      ("auto", "deterministic_tool", "semantic_cache", "small_model", "medium_model", "large_model")

ChatResponse ([api/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py))
 ├── query: str
 ├── answer: str
 ├── route: str
 ├── model: Optional[str]
 ├── provider: str
 ├── execution_time_ms: float
 ├── token_usage: Optional[TokenUsageSchema]
 ├── large_model_avoided: bool
 ├── cache_status: str ("hit", "miss", "not_checked")
 ├── cache_similarity: Optional[float]
 ├── metadata: Optional[Dict[str, Any]]
 └── telemetry: Optional[TelemetryRecord]
```

### 6.2 Telemetry Record & Accounting Schemas

```text
TelemetryRecord ([telemetry/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py))
 ├── request_id: str (UUIDv4)
 ├── timestamp: str (ISO-8601 UTC)
 ├── route: str
 ├── provider: str
 ├── model: Optional[str]
 ├── success: bool
 ├── error_message: Optional[str]
 ├── tokens: TokenTelemetry
 │    ├── input_tokens: Optional[int]
 │    ├── output_tokens: Optional[int]
 │    ├── total_tokens: Optional[int]
 │    └── provenance: ProvenanceStatus
 ├── latency: LatencyTelemetry
 │    ├── inference_latency_ms: Optional[float]
 │    ├── execution_time_ms: float
 │    └── provenance: ProvenanceStatus (MEASURED)
 ├── environment: EnvironmentalTelemetry
 │    ├── energy_joules: Optional[float]
 │    ├── water_liters: Optional[float] (Always null / UNAVAILABLE in Phase 5B)
 │    ├── carbon_gco2e: Optional[float] (Conditional on LOCAL_GRID_INTENSITY_GCO2E_PER_KWH)
 │    ├── carbon_scope: Optional[MeasurementScope] (GPU_BOARD_OPERATIONAL_CARBON)
 │    ├── grid_intensity_gco2e_per_kwh: Optional[float]
 │    ├── provenance: ProvenanceStatus
 │    ├── energy_provenance: ProvenanceStatus
 │    ├── carbon_provenance: ProvenanceStatus
 │    ├── water_provenance: ProvenanceStatus
 │    ├── gpu_telemetry: Optional[GpuTelemetry]
 │    ├── measurement: Optional[PhysicalMeasurement]
 │    ├── measurement_capabilities: MeasurementCapabilities
 │    └── note: str
 └── avoidance: Optional[AvoidanceTelemetry]
      ├── model_calls_avoided: int (1 for tools/cache, 0 for models)
      ├── tokens_avoided: Optional[int]
      ├── baseline_route: str ("large_model")
      └── reasoning: str
```

### 6.3 Pair-Wise Savings Comparison Schemas

```text
SavingsCompareRequest ([api/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py))
 ├── selected_request_id: str
 ├── baseline_request_id: str
 └── quality_threshold_met: bool = True

SavingsComparison ([telemetry/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py))
 ├── selected_route: str
 ├── baseline_route: str
 ├── quality_threshold_met: bool
 ├── model_calls_avoided: int
 ├── tokens_saved: Optional[int]
 ├── tokens_provenance: ProvenanceStatus
 ├── latency_delta_ms: Optional[float]
 ├── energy_savings: MetricSavings
 │    ├── baseline_value: Optional[float]
 │    ├── selected_value: Optional[float]
 │    ├── savings_value: Optional[float]
 │    ├── savings_pct: Optional[float]
 │    ├── unit: str ("J")
 │    ├── provenance: ProvenanceStatus
 │    ├── scope: Optional[MeasurementScope]
 │    └── note: str
 ├── water_savings: MetricSavings (Always UNAVAILABLE in Phase 5B)
 ├── carbon_savings: MetricSavings (MEASURED/ESTIMATED only if both routes have valid carbon)
 └── notice: str
```

### 6.4 Multi-Objective Routing Decision Schemas (Phase 6)

```text
CandidateScore ([telemetry/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py))
 ├── candidate_id: str ("deterministic_tool", "semantic_cache", "small", "medium", "large")
 ├── name: str
 ├── quality_score: float
 ├── expected_latency_ms: float
 ├── estimated_cost_usd: float
 ├── estimated_energy_joules: Optional[float]
 ├── energy_provenance: ProvenanceStatus (MEASURED, ESTIMATED, UNAVAILABLE)
 ├── is_pareto_optimal: bool
 ├── meets_quality_threshold: bool
 ├── scalarized_cost: float
 └── rank: int

RoutingDecision ([telemetry/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py))
 ├── decision_id: str (UUIDv4)
 ├── timestamp: str (ISO-8601 UTC)
 ├── selected_route: str
 ├── selected_candidate_name: str
 ├── rationale: str
 ├── quality_threshold_required: float
 ├── quality_threshold_met: bool
 ├── pareto_frontier_size: int
 ├── total_candidates_evaluated: int
 ├── active_weights: Dict[str, float]
 ├── normalized_scores: List[CandidateScore]
 ├── fallback_applied: bool
 └── fallback_reason: Optional[str]
```

### 6.5 Eco Receipt Schemas (Phase 7)

```text
EcoReceipt ([backend/receipt/schemas.py](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/receipt/schemas.py))
 ├── receipt_id: str ("rcpt_<uuid>")
 ├── request_id: str (UUIDv4)
 ├── timestamp: str (ISO-8601 UTC)
 ├── status: str ("SUCCESS", "FAILED", "PARTIAL")
 ├── execution_path: ExecutionPath ("deterministic_tool", "semantic_cache", "model_inference")
 ├── route: str
 ├── provider: str
 ├── model: Optional[str]
 ├── query_preview: Optional[str]
 ├── execution_time_ms: float
 ├── inference_latency_ms: Optional[float]
 ├── latency_provenance: ProvenanceStatus (MEASURED)
 ├── tokens: TokenTelemetry
 ├── cost: CostMetric (USD, provenance: ESTIMATED/UNAVAILABLE, pricing source, details, is_zero_external_api_charge)
 ├── environment: EnvironmentalBreakdown
 │    ├── energy: EnergyMetric (Joules, kWh, scope, provenance, platform, disclaimer)
 │    ├── carbon: CarbonMetric (gCO2e, scope, provenance, grid intensity factor & source)
 │    ├── water: WaterMetric (Liters, accounting scope, provenance: UNAVAILABLE)
 │    ├── source_id & source_name (Registry citations)
 │    ├── assumptions & uncertainty_info
 │    └── unavailable_reasons: Dict[str, str]
 ├── avoidance: Optional[AvoidanceSummary]
 ├── optimizer: Optional[OptimizerSummary] (Phase 6 candidate scores, weights, Pareto frontier)
 └── explainability: ReceiptExplainability
      ├── selection_summary: str
      ├── measurement_vs_estimation: str
      ├── unavailable_metrics_rationale: str
      └── caveats_and_uncertainty: str
```

---

### 6.6 Dashboard & Historical Storage Schemas (Phase 8)

```text
HistoricalRequestRow (backend/database/historical_store.py)
 ├── request_id: str (PRIMARY KEY)
 ├── receipt_id: str (UNIQUE)
 ├── timestamp: str (ISO-8601 UTC, INDEXED)
 ├── status: str ("SUCCESS", "FAILED", "PARTIAL", INDEXED)
 ├── execution_path: str ("deterministic_tool", "semantic_cache", "model_inference", INDEXED)
 ├── route: str (INDEXED)
 ├── provider: str (INDEXED)
 ├── model: Optional[str]
 ├── query_preview: Optional[str] (Truncated to 120 chars for privacy)
 ├── execution_time_ms: float
 ├── inference_latency_ms: Optional[float]
 ├── latency_provenance: str ("MEASURED")
 ├── prompt_tokens, completion_tokens, total_tokens: Optional[int]
 ├── cost_usd: Optional[float], is_zero_external_api_charge: int
 ├── energy_joules, energy_kwh: Optional[float]
 ├── is_energy_measured, is_energy_estimated: int
 ├── carbon_gco2e: Optional[float], grid_intensity_gco2e_per_kwh: Optional[float]
 ├── water_liters: Optional[float], water_reason_unavailable: str
 ├── model_calls_avoided, tokens_avoided: Optional[int]
 ├── is_pareto_optimal, fallback_applied: int, fallback_reason: Optional[str]
 ├── receipt_json: str (Full serialized EcoReceipt)
 └── telemetry_json: str (Full serialized TelemetryRecord)

DashboardSummaryResponse (backend/api/schemas_dashboard.py)
 ├── total_requests, successful_requests, failed_requests, partial_requests: int
 ├── success_rate_percent, total_execution_time_ms, avg_latency_ms: float
 ├── total_prompt_tokens, total_completion_tokens, total_tokens: int
 ├── total_external_api_cost_usd, zero_external_api_cost_count, billed_external_api_cost_count: float/int
 ├── total_model_calls_avoided, total_tokens_avoided: int
 └── routes_breakdown, providers_breakdown, execution_paths_breakdown: Dict[str, int]
```

---

## 7. Control Plane REST API Reference

| Endpoint | Method | Input Schema | Output Schema | Architectural Role |
|---|---|---|---|---|
| `/chat` | `POST` | [`ChatRequest`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py) | [`ChatResponse`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py) | Central execution endpoint: evaluates tools, cache, and model dispatcher; records authentic telemetry; attaches `EcoReceipt`. |
| `/tools` | `GET` | *None* | `List[ToolInfoSchema]` | Introspects registered deterministic tools and their execution metadata. |
| `/models` | `GET` | *None* | `List[ModelProfileSchema]` | Returns active model configurations and public pricing profiles. |
| `/cache/stats` | `GET` | *None* | [`CacheStatsSchema`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py) | Introspects semantic cache hit rate, entries, evictions, and vector dimensions. |
| `/cache/clear` | `POST` | *None* | `Dict[str, Any]` | Resets the SQLite cache table and FAISS index. |
| `/telemetry/capabilities` | `GET` | *None* | [`MeasurementCapabilities`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py) | Introspects host system physical measurement capabilities (`gpu_energy`, `system_energy`, `device_energy`, `provider_energy`). |
| `/telemetry/recent` | `GET` | `limit: int = 50` | `List[TelemetryRecord]` | Retrieves recent telemetry records with provenance and avoidance facts. |
| `/telemetry/summary` | `GET` | *None* | [`TelemetrySummary`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py) | Aggregates request counts, route breakdowns, provider distributions, and hardware measurement totals. |
| `/telemetry/savings/compare` | `POST` | [`SavingsCompareRequest`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py) | [`SavingsComparison`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py) | Computes pair-wise savings between two requests, strictly enforcing the Non-Zero Rule, comparison types, and quality gates. |
| `/telemetry/sources` | `GET` | *None* | `List[EnvironmentalSource]` | Returns all registered environmental accounting sources, methodology notes, and validation statuses. |
| `/telemetry/sources/{id}` | `GET` | *Path Parameter* | `EnvironmentalSource` | Inspects citation details, empirical coefficients, and review recommendations for a specific source. |
| `/telemetry/sources/refresh` | `POST` | *None* | `List[SourceCheckResult]` | Runs an automated freshness audit across all registered environmental coefficients and flags stale/review-needed entries. |
| `/telemetry/grid` | `GET` | *None* | `GridIntensityRecord` | Returns the active grid carbon intensity ($gCO_2e/\text{kWh}$), region, live provider status, and fallback state. |
| `/telemetry/clear` | `POST` | *None* | `Dict[str, Any]` | Flushes the in-memory telemetry buffer. |
| `/router/config` | `GET` | *None* | [`RouterConfigResponse`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py) | Introspects active router weights ($w_Q, w_L, w_{\$}, w_E$), quality thresholds, and Pareto enablement status. |
| `/router/optimize` | `POST` | [`RouteOptimizationRequest`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas.py) | [`RoutingDecision`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/telemetry/schemas.py) | Standalone endpoint to simulate or invoke multi-objective routing optimization over arbitrary candidate sets. |
| `/receipts/{request_id}` | `GET` | *Path Parameter* | [`EcoReceipt`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/receipt/schemas.py) | Retrieves machine-readable Eco Receipt for any completed or failed request ID from SQLite (or memory fallback). |
| `/telemetry/receipt/{request_id}` | `GET` | *Path Parameter* | [`EcoReceipt`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/receipt/schemas.py) | Canonical telemetry alias for retrieving an Eco Receipt. |
| `/dashboard/summary` | `GET` | `start_date, end_date` | [`DashboardSummaryResponse`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas_dashboard.py) | High-level operational KPIs, success rate, cumulative latency, tokens, API costs, avoided calls, and route distributions. |
| `/dashboard/environment` | `GET` | `start_date, end_date` | [`DashboardEnvironmentResponse`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas_dashboard.py) | Environmental footprint aggregations with strict measured vs estimated energy, carbon, water disclosures, and grid sources. |
| `/dashboard/routes` | `GET` | `start_date, end_date` | [`DashboardRoutesResponse`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas_dashboard.py) | Multi-objective routing efficiency, candidate distributions, Pareto frontier compliance, and fallback justification audit. |
| `/dashboard/timeseries` | `GET` | `interval, start_date, end_date` | `List[TimeseriesPoint]` | Chronological hourly or daily bucketed timeseries for volume, mean latency, tokens, measured/estimated energy, and avoidance. |
| `/dashboard/receipts` | `GET` | `page, page_size, filters` | [`PaginatedReceiptsResponse`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/api/schemas_dashboard.py) | Filterable, paginated Eco Receipt summary catalog with date-range and execution-path filtering. |
| `/dashboard/receipts/{id}` | `GET` | *Path Parameter* | [`EcoReceipt`](file:///c:/Users/Mrunmayee%20Potdar/Desktop/projects/EcoMind/backend/receipt/schemas.py) | Retrieves full structured Eco Receipt directly from persistent SQLite storage with in-memory fallback. |

---

## 8. Frontend Architecture & UI/UX Design System

EcoMind features a production-grade, light-themed SaaS frontend built with **React 19**, **TypeScript**, **Vite 8**, **Tailwind CSS v4**, and **Recharts**.

### 8.1 Visual & Structural Guidelines
- **Palette**: Clean light neutral canvas (`#f8fafc`), white card elevations (`#ffffff`), slate text hierarchies (`#0f172a`, `#475569`, `#94a3b8`), and primary emerald/teal accents (`#059669`, `#0d9488`).
- **Brand Identity**: Application title **EcoMind** with tagline *"Smarter AI. Lighter Footprint."*. Developer phase labels are excluded from end-user UI.
- **Human-Friendly Terminology**:
  - *Deterministic Tool* $\rightarrow$ **Instant Built-in Tool**
  - *Semantic Cache* $\rightarrow$ **Saved Response**
  - *Execution Telemetry* $\rightarrow$ **Response Insights**
  - *Multi-Objective Routing Optimizer* $\rightarrow$ **How EcoMind Works**
  - *Eco Receipts Explorer* $\rightarrow$ **Activity History**

### 8.2 Component Hierarchy
```text
frontend/src/
├── App.tsx                     # Top navigation, System Ready pill, view state switcher
│    │
│    ├── [View 1: AI Assistant / Playground]
│    │    ├── Hero greeting & natural prompt suggestion chips
│    │    ├── Textarea input with Enter-to-submit and Shift+Enter newline
│    │    ├── Collapsible "Processing Preferences" (Automatic, Built-in Tool, Saved Response, Model Tiers)
│    │    ├── Primary Answer Card with Copy feedback button
│    │    ├── Compact "Response Insights" (Latency, Avoided Tokens, Energy Status, Cost, "View Eco Receipt")
│    │    └── Value proposition cards explaining algorithmic savings
│    │
│    ├── [View 2: Sustainability Dashboard]
│    │    ├── Time range selector ('24h', '7d', '30d', 'All Time') & refresh action
│    │    ├── DashboardOverview.tsx      # 4 KPI cards, Recharts area chart, method breakdown bars
│    │    ├── DashboardEnvironment.tsx   # GPU-measured vs model-estimated energy, carbon & water disclosures
│    │    ├── DashboardRoutes.tsx        # Pareto balance rate, quality compliance, route statistics table
│    │    └── ReceiptsExplorer.tsx       # Paginated, filterable activity history table with modal trigger
│    │
│    └── ReceiptModal.tsx       # Invoice-style modal with plain-English summary, key tiles, & JSON copy
```
