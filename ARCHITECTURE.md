# EcoMind — System Architecture Reference

> **Comprehensive Architectural Specifications, Data Flow, and Request Traces**  
> *Repository State: Phase 3 (Deterministic Tools + Provider-Agnostic Model Routing)*

---

## 1. Planned Full Architecture (Target Vision)

```text
User Query
    │
    ▼
┌────────────────────────────────────────┐
│             Query Analyzer             │ (Phase 3: Task type & complexity detection)
└───────────────────┬────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────┐
│             Semantic Cache             │ (Phase 4: Embedding cosine similarity)
└─────────┬────────────────────┬─────────┘
          │ Cache Hit          │ Cache Miss
          ▼                    ▼
   [Return Cached]     ┌────────────────────────────────────────────────────────┐
   [Eco Receipt  ]     │              Candidate Route Generator                 │
                       └──────────────────────────┬─────────────────────────────┘
                                                  │
         ┌───────────────────┬────────────────────┼────────────────────┬────────────────────┐
         ▼                   ▼                    ▼                    ▼                    ▼
   Deterministic       Semantic Cache       Small Model          Medium Model         Large Model
       Tool            (Refresh Path)      (Local Ollama)       (Cloud Flash/Groq)   (Cloud Pro/Groq)
         │                   │                    │                    │                    │
         └───────────────────┴────────────────────┼────────────────────┴────────────────────┘
                                                  │
                                                  ▼
                               ┌────────────────────────────────────────┐
                               │        Sustainability Estimator        │ (Phase 5: Wh, mL water, gCO2e)
                               └──────────────────┬─────────────────────┘
                                                  │
                                                  ▼
                               ┌────────────────────────────────────────┐
                               │        Multi-Objective Optimizer       │ (Phase 6: Pareto cost trade-offs)
                               └──────────────────┬─────────────────────┘
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
                                      Answer + Eco Receipt (Phase 7)
```

---

## 2. Current Implemented Architecture (Phase 3 Actual)

```text
HTTP POST /chat { query, preferred_route }
                   │
                   ▼
       FastAPI Router (routes_chat.py)
                   │
    ┌──────────────┴─────────────────────────────────────────┐
    │                                                        │
    ▼ [route_pref in ("auto", "deterministic_tool")]         ▼ [route_pref in ("small_model", "medium_model", "large_model")]
ToolRegistry.find_candidate_tool(query)                      │ Explicit override maps directly
    │                                                        │ to logical tier: "small" / "medium" / "large"
    ├──► Tool Found? (5 Deterministic Tools)                 │
    │    └──► Tool.execute(query)                            │
    │         └──► Return ToolResult (0 tokens, < 1ms)       │
    │                                                        │
    └──► Tool Not Found (or route_pref == "auto")            │
         │                                                   │
         ▼                                                   │
     QueryAnalyzer.analyze(query)                            │
         │ (7 task categories, low/medium/high complexity)   │
         ▼                                                   │
     RoutingPolicy.select_route(analysis)                    │
         │ (outputs logical tier: "small" / "medium" / "large")
         ▼                                                   │
     ┌───────────────────────────────────────────────────────┘
     │
     ▼
ModelDispatcher.dispatch(tier, query)
     │
     ├── Resolves (tier) -> configured (provider, model)
     │     ├── small  -> settings.SMALL_PROVIDER,  settings.SMALL_MODEL
     │     ├── medium -> settings.MEDIUM_PROVIDER, settings.MEDIUM_MODEL
     │     └── large  -> settings.LARGE_PROVIDER,  settings.LARGE_MODEL
     │
     ▼
Provider Execution
     ├── GroqProvider    (Groq API / LPU inference + authentic usage metrics)
     ├── GeminiProvider  (Google GenAI SDK + authentic usage_metadata)
     └── LocalProvider   (Ollama daemon / offline testing fallback)
     │
     ▼
ProviderResponse (latency, tokens, metadata)
     │
     ▼
ChatResponse JSON
```

---

## 3. Component Interaction & Dependencies

```text
api/routes_chat.py
    ├── imports ──► tools.tool_registry (ToolRegistry)
    │                  └── imports ──► tools.calculator, unit_converter, datetime_calculator, etc.
    │                                     └── imports ──► tools.base (BaseTool, ToolResult)
    ├── imports ──► router.query_analyzer (QueryAnalyzer, QueryAnalysis)
    ├── imports ──► router.routing_policy (RoutingPolicy)
    ├── imports ──► models.dispatcher (ModelDispatcher, model_dispatcher)
    │                  ├── imports ──► models.groq_provider (GroqProvider)
    │                  ├── imports ──► models.gemini_provider (GeminiProvider)
    │                  ├── imports ──► models.local_provider (LocalProvider)
    │                  └── imports ──► models.provider (ModelProvider, ProviderResponse, TokenUsage)
    ├── imports ──► models.model_profiles (ModelProfile, ModelTier)
    ├── imports ──► config.settings (settings)
    └── imports ──► api.schemas (ChatRequest, ChatResponse, ...)
```

---

## 4. End-to-End Execution Traces

### Trace A: Deterministic Path
```text
Query: "convert 100 km to miles" (preferred_route: "auto")

[Client / Frontend]
   │  HTTP POST /chat {"query": "convert 100 km to miles", "preferred_route": "auto"}
   ▼
[FastAPI / routes_chat.py]
   │  Calls ToolRegistry.find_candidate_tool() -> UnitConverter
   ▼
[UnitConverter.execute]
   │  Computes 100 km * 0.621371 = 62.137119 miles
   │  Returns ToolResult(success=True, result=62.137119, calls_llm=False)
   ▼
[FastAPI / routes_chat.py]
   │  Returns ChatResponse:
   │    • answer: "62.137119"
   │    • route: "Deterministic Tool"
   │    • model: "Unit_converter"
   │    • token_usage: { prompt: 0, completion: 0, total: 0 }
   │    • large_model_avoided: True
```

### Trace B: Dynamic Model Routing Path (Small Tier)
```text
Query: "What is Python?" (preferred_route: "auto")

[Client / Frontend]
   │  HTTP POST /chat {"query": "What is Python?", "preferred_route": "auto"}
   ▼
[FastAPI / routes_chat.py]
   │  ToolRegistry.find_candidate_tool() -> None (Not a calculation or unit task)
   │  QueryAnalyzer.analyze() -> task_type="general_qa", complexity="low"
   │  RoutingPolicy.select_route() -> "small"
   ▼
[ModelDispatcher.dispatch]
   │  Resolves "small" -> configured provider: "groq", model: "openai/gpt-oss-20b"
   ▼
[GroqProvider.generate]
   │  Calls groq client.chat.completions.create(model="openai/gpt-oss-20b")
   │  Extracts authentic tokens from completion.usage
   ▼
[FastAPI / routes_chat.py]
   │  Returns ChatResponse:
   │    • route: "Small Model (Groq)"
   │    • model: "openai/gpt-oss-20b"
   │    • provider: "groq"
   │    • large_model_avoided: True
```

---

## 5. Standard Data Contracts

```text
ChatRequest (api/schemas.py)
 ├── query: str
 └── preferred_route: Optional[str] = "auto"

ToolResult (tools/base.py)
 ├── success: bool
 ├── result: Any
 ├── tool_name: str
 ├── execution_time_ms: float
 ├── error: Optional[str]
 └── metadata: Dict[str, Any]

ProviderResponse (models/provider.py)
 ├── content: str
 ├── model_name: str
 ├── provider_name: str
 ├── latency_ms: float
 ├── usage: Optional[TokenUsage]
 └── raw_metadata: Dict[str, Any]

ChatResponse (api/schemas.py)
 ├── query: str
 ├── answer: str
 ├── route: str
 ├── model: str
 ├── provider: str
 ├── execution_time_ms: float
 ├── token_usage: Optional[TokenUsageSchema]
 ├── large_model_avoided: bool
 └── metadata: Optional[Dict[str, Any]]
```
