# Environmental Accounting Methodology & Multi-Provider Architecture Design (Phase 5B)

> **Integrity Mandate**: Zero Fabrication. No unverified coefficients, no forced numbers, no conflation of single-chip hardware specs with whole-system request energy, no fixed latency assumptions, and no assumption of cloud data-center locations.

---

## 1. Executive Summary & Verification Findings

EcoMind is an intelligent AI inference control plane designed to route queries across deterministic tools, semantic caching, and small, medium, or large model tiers. Its objective is to minimize electricity, cooling water, and greenhouse gas (GHG) emissions while maintaining latency and answer quality.

In **Phase 5A**, EcoMind established an authentic hardware measurement layer:
- Physical sampling of local NVIDIA GPU board power via NVML C-bindings (`GPU_INFERENCE_WINDOW` scope).
- Dynamic wall-clock latency measurement via high-resolution system timers (`time.perf_counter`) on every request.
- Authentic token extraction from provider response metadata (`PROVIDER_REPORTED`).
- Verification that deterministic tools and semantic cache hits consume **0 model tokens** and execute **0 neural-network inference calls**.
- Explicit representation of unmeasured cloud energy, water, and carbon as `null` with `UNAVAILABLE` provenance.

This **Phase 5B research specification** establishes a scientifically defensible foundation for multi-provider environmental accounting across Google Gemini, Groq, OpenAI, Anthropic, and Local/Open-Source models. Following a line-by-line verification of the literature, provider disclosures, and hardware realities:

1. **Unsupported Coefficients & Tier Multipliers Removed**: We eliminate speculative model-tier multipliers (e.g., $0.5\times$, $3.5\times\text{--}5.0\times$) for Gemini API models and speculative token-energy rates (e.g., $2.0\text{ J/token}$) for Groq.
2. **Fleet Averages Decoupled from Per-Request API Calls**: Google's published Gemini Apps median metrics ($0.24\text{ Wh}$, $0.26\text{ mL}$) are documented accurately as a consumer-product fleet average, not a per-request estimation formula for the Gemini Developer API.
3. **Multi-Chip Cluster Overhead Documented**: We qualify Groq single-chip specifications and document that whole-system per-request energy cannot be inferred from silicon specs when large models are distributed across hundreds of chips.
4. **Tool and Cache Accounting Corrected**: Zero model tokens does not mean zero electricity or zero indirect water. Unmeasured tool and cache energy/water are marked `UNAVAILABLE`, while authentic execution proxies (avoided tokens, avoided model calls relative to an explicit baseline) are reported as measured facts.
5. **No Assumed Fixed Latencies**: All execution latencies are dynamically measured per-request via high-resolution system timers (`time.perf_counter`); no static latency values are assumed.
6. **Geographic Honesty in Carbon Accounting**: Cloud provider data-center locations are unknown at runtime. We prohibit silently applying US national grid averages as known locations.
7. **Strict GPU Scope Labeling**: Local GPU energy and derived carbon are strictly labeled as GPU-board metrics (`GPU_INFERENCE_WINDOW`), not whole-system measurements.
8. **Defensible Minimal MVP Defined**: We outline an architecture where providers and metrics independently report supported measurements, bounded estimates, or `UNAVAILABLE`.

---

## 2. Summary of Verified vs. Unsupported Evidence

| Metric / Claim | Previous Status in Draft | Verified Ground Truth | Corrective Action Taken |
|---|---|---|---|
| **Google Gemini Apps Footprint** | Used $0.24\text{ Wh}$ energy, $0.26\text{ mL}$ water, $0.03\text{ gCO}_2\text{e}$ market carbon as per-request basis for Gemini API calls. | **Product Fleet Median Only**: Measured by Elsworth et al. (Google, Aug 2025, [arXiv:2508.15734](https://arxiv.org/abs/2508.15734)) across consumer **Gemini Apps text prompts**. Does *not* disclose per-token coefficients, API checkpoint formulas, or per-request variances. | **Decoupled from API requests**. Documented as a consumer-product fleet benchmark. Per-request environmental metrics for Gemini API calls marked `UNAVAILABLE`. |
| **Gemini Model-Tier Multipliers** | Flash-Lite $= 0.5\times$, Pro $= 3.5\times\text{--}5.0\times$ scaled from 0.24 Wh. | **Speculative & Unsupported**: Google publishes no model-tier multipliers or parameter-scaling coefficients for its developer API. | **REMOVED entirely**. No arbitrary multipliers are applied. |
| **Groq 2 J/token Baseline & Chip Claims** | Proposed $2.0\text{ J/token}$ active baseline ($[1.0, 4.0]\text{ J/token}$ bounds); cited fixed rack power. | **Chip Spec $\neq$ Whole-System Request Energy**: Derived from dividing single-chip TDP by peak throughput. Serving 70B models requires distributing weights across hundreds of chips. Groq has not published verified cluster-level power, idle allocation, or facility PUE. | **REMOVED**. Groq whole-system energy and water are marked `UNAVAILABLE`. |
| **Groq Operational Water** | Undefined. | **Confirmed Zero Disclosure**: Groq publishes zero corporate sustainability reports, zero facility locations, and zero WUE metrics. | **Strictly marked `UNAVAILABLE`**. Zero fabrication. |
| **OpenAI 0.34 Wh & 0.32 mL** | Cited as verified per-query metrics for OpenAI models. | **Unverified Executive Remark**: From a June 2025 blog post by Sam Altman. Lacks audited methodology, model specification, prompt length, concurrency, or facility location. | **Classified as unverified remark**. Not used as an API estimation model. OpenAI API environmental metrics marked `UNAVAILABLE`. |
| **Anthropic Environmental Data** | Parametric proxy estimates (0.15–0.90 Wh). | **External Proxy Only**: Anthropic publishes zero corporate environmental disclosures or Scope 1–3 inventories. | **Documented as third-party proxy**. Anthropic native metrics marked `UNAVAILABLE`. |
| **Deterministic Tool & Cache Impact** | Claimed 0.0 Wh energy, 0.0 mL water, 0.0 gCO₂e, and fixed execution latencies. | **Physically False & Hardcoded**: CPU/RAM draws power during execution, inducing indirect water and carbon. Latencies vary by hardware and payload. | **CORRECTED**: Model tokens = 0 (`MEASURED`); latencies dynamically measured via `time.perf_counter`; physical energy, water, and carbon marked `UNAVAILABLE` unless hardware counters are sampled. |
| **Cloud Carbon via US Grid Average** | Multiplied energy by US average ($370\text{ gCO}_2\text{e/kWh}$). | **Methodologically Flawed**: Cloud APIs conceal physical data-center locations behind global load balancers. Location is unknown. | **CORRECTED**: Prohibited assuming US grid average as a known location. Cloud carbon marked `UNAVAILABLE` unless location is explicitly supplied as a user-configured assumption. |

---

## 3. Provider-by-Provider, Metric-by-Metric Feasibility Matrix

| Execution Route / Provider | Electricity Energy (Wh) | Direct Cooling Water (mL) | Indirect Electricity Water (mL) | Operational Carbon ($\text{gCO}_2\text{e}$) | Execution Facts & Proxies |
|---|---|---|---|---|---|
| **Deterministic Tools** (`Calculator`, `UnitConverter`, etc.) | **`UNAVAILABLE`** (unless CPU RAPL measured) | **`UNAVAILABLE`** | **`UNAVAILABLE`** | **`UNAVAILABLE`** | **`MEASURED`**: Dynamic latency via `time.perf_counter`, 0 model tokens, 1 avoided LLM call (vs. model baseline) |
| **Semantic Cache** (`FAISS` + `all-MiniLM-L6-v2`) | **`UNAVAILABLE`** (unless CPU/GPU RAPL measured) | **`UNAVAILABLE`** | **`UNAVAILABLE`** | **`UNAVAILABLE`** | **`MEASURED`**: Dynamic latency via `time.perf_counter`, 0 model tokens, 1 avoided LLM call (vs. model baseline) |
| **Local Model (Ollama)** (e.g. `llama3.1:8b` on RTX GPU) | **`MEASURED`** for GPU (`GPU_INFERENCE_WINDOW`); Host CPU is `UNAVAILABLE` | **`UNAVAILABLE`** (Air-cooled client has 0 direct, but indirect water unmeasured) | **`UNAVAILABLE`** (unless local grid WIE configured) | **`ESTIMATED (CONDITIONAL)`** for GPU board only if local grid factor configured; else `UNAVAILABLE` | **`MEASURED`**: Dynamic latency, GPU Watts/Joules; `PROVIDER_REPORTED`: Tokens |
| **Google Gemini API** (`flash-lite`, `flash`, `pro`) | **`UNAVAILABLE`** for per-request API calls (Fleet median 0.24 Wh cited as reference) | **`UNAVAILABLE`** for per-request API calls (Fleet median 0.26 mL cited as reference) | **`UNAVAILABLE`** | **`UNAVAILABLE`** (Fleet median 0.03 g market cited as reference) | **`PROVIDER_REPORTED`**: Prompt, candidate, and total tokens; `MEASURED`: Dynamic latency |
| **Groq LPU API** (`llama-3.3-70b`, `gpt-oss-20b`) | **`UNAVAILABLE`** (Multi-chip cluster idle allocation undisclosed) | **`UNAVAILABLE`** (Zero vendor disclosures) | **`UNAVAILABLE`** | **`UNAVAILABLE`** (Facility location undisclosed) | **`PROVIDER_REPORTED`**: Prompt, completion, total tokens; `MEASURED`: Dynamic latency |
| **OpenAI API** (`gpt-4o-mini`, `gpt-4o`) | **`UNAVAILABLE`** (Per-query micro-disclosure unverified for API models) | **`UNAVAILABLE`** (Zero API water disclosures) | **`UNAVAILABLE`** | **`UNAVAILABLE`** (Facility location undisclosed) | **`PROVIDER_REPORTED`**: Prompt, completion, total tokens; `MEASURED`: Dynamic latency |
| **Anthropic API** (`claude-3-5-sonnet`, `haiku`) | **`UNAVAILABLE`** (Zero corporate disclosures) | **`UNAVAILABLE`** (Zero corporate disclosures) | **`UNAVAILABLE`** | **`UNAVAILABLE`** (Facility location undisclosed) | **`PROVIDER_REPORTED`**: Input and output tokens; `MEASURED`: Dynamic latency |

---

## 4. Rigorous Examination of Evidence & Literature

### 4.1 Google Gemini: Fleet-Wide Median vs. API Inapplicability

* **Primary Reference**: *Measuring the Environmental Impact of Delivering AI at Google Scale* (Elsworth, Patterson, Dean, Manyika, et al., Google, August 21, 2025, [arXiv:2508.15734](https://arxiv.org/abs/2508.15734)).
* **What Was Actually Measured**:
  - The operational serving infrastructure for the **Gemini Apps consumer product** (web/mobile user interface) during production traffic over a 12-month period.
  - Full-stack boundary: active TPU accelerators (**58%**), host CPU/DRAM (**25%**), unallocated/idle provisioned headroom (**10%**), and data-center overhead via PUE (**8%**).
  - Excluded boundaries: model pre-training, data storage, external networking, and end-user client devices.
* **Published Numerical Results**:
  - **Energy**: **0.24 Wh** per median text prompt.
  - **Water**: **0.26 mL** per median text prompt (on-site evaporative cooling).
  - **Carbon**: **0.03 gCO₂e** per median text prompt (market-based accounting using Google's carbon-free energy matching).
* **Limitations & Why This Cannot Be Applied to Gemini API Requests**:
  1. *Product vs. API Mismatch*: Gemini Apps serves an internal, dynamically routed product blend. The Gemini Developer API serves specific, distinct model checkpoints (`gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`) with user-specified system prompts, extended context windows (up to 1M–2M tokens), and differing batching regimes.
  2. *Absence of Per-Token Coefficients*: Elsworth et al. disclose only the **median prompt** of the consumer product. They do not publish per-input-token or per-output-token coefficients, nor do they disclose parameter-tier scaling ratios.
  3. *Scientific Conclusion*: Citing 0.24 Wh as a general corporate fleet benchmark is valid. Applying 0.24 Wh to an individual API request, or multiplying it by arbitrary factors for Flash-Lite and Pro, is unverified and scientifically unsound. Per-request environmental metrics for Gemini API calls must be marked **`UNAVAILABLE`**.

---

### 4.2 Groq LPU: Architecture vs. Cluster Scaling Reality

* **Primary References**:
  1. *Think Fast: A Tensor Streaming Processor (TSP) for Accelerating Deep Learning Workloads* (Abts et al., IEEE/ACM ISCA 2020, [DOI: 10.1109/ISCA45697.2020.00023](https://doi.org/10.1109/ISCA45697.2020.00023)).
  2. *A Software-defined Tensor Streaming Multiprocessor for Scale-out Deep Learning* (Abts et al., IEEE/ACM ISCA 2022, [DOI: 10.1145/3470496.3527405](https://doi.org/10.1145/3470496.3527405)).
* **What the Primary Literature Actually Proves**:
  - A single GroqCard contains a 14nm TSP with **230 MB of on-chip SRAM** and a card TDP of ~275W.
  - The chip avoids external High-Bandwidth Memory (HBM) by storing weights on-chip and scheduling operations statically via the compiler down to the clock cycle.
  - Benchmarks in the ISCA 2020 paper evaluated computer vision (ResNet-50) and simple NLP models on single-chip testbeds; they did not benchmark modern 70B autoregressive LLMs.
* **Why Hardware Specs Do Not Yield Whole-System Request Energy**:
  1. *Multi-Chip Scale-Out*: A 70-billion parameter model (`llama-3.3-70b`) requires ~70 GB (FP8) to ~140 GB (FP16) of weight memory. Third-party architectural analyses estimate that housing these weights requires distributing the model across hundreds of interconnected Groq chips (commonly estimated at ~500–600 cards in a multi-rack mesh topology).
  2. *Cluster Baseline & Idle Power*: In a multi-rack scale-out cluster, unamortized baseline power (chassis power supplies, host processors, network switches, and cooling fans) represents a significant continuous draw. If an inference query runs at low concurrency, unamortized cluster idle power dominates active compute energy.
  3. *Absence of Whole-System Measurements*: Groq has not published peer-reviewed measurements of whole-system per-request energy, dynamic rack power allocation, cluster utilization, or facility PUE for its GroqCloud service.
  4. *Water Disclosures*: Groq publishes zero data on data-center cooling technology, facility locations, or water consumption.
  5. *Scientific Conclusion*: Proposed single-chip metrics (such as 1–3 J/token) represent active silicon estimates and cannot be treated as whole-system per-request energy. Whole-system energy and direct cooling water for Groq must be marked **`UNAVAILABLE`**.

---

### 4.3 OpenAI & Anthropic: Disclosure Audits

* **OpenAI Evidence Audit**:
  - *Sam Altman Blog Post (June 2025)*: Stated that an average ChatGPT query consumes ~0.34 Wh electricity and ~0.000085 gallons (~0.32 mL) water.
  - *Limitations*: This is an unverified executive remark, not an audited technical study. It specifies neither the model (GPT-4o vs. o1 vs. legacy GPT-3.5), prompt length, decoding depth, server concurrency, nor data-center location.
  - *Epoch AI Study (2024)*: Modeled GPT-4o queries analytically at ~0.30 to 0.40 Wh based on assumed parameter sizes and cluster utilization. This is an external model, not an empirical measurement.
  - *Corporate Reporting*: OpenAI publishes no audited Scope 1, 2, or 3 greenhouse gas inventories.
  - *Scientific Conclusion*: OpenAI API environmental metrics cannot be verified from API metadata and must be marked **`UNAVAILABLE`**.
* **Anthropic Evidence Audit**:
  - Anthropic has published no corporate sustainability reports, no Scope 1–3 inventories, and no technical model-card disclosures regarding energy or water.
  - Relies on third-party cloud infrastructure (AWS and Google Cloud).
  - External estimators (e.g. EcoLogits) use parameter proxies that carry unquantified error margins.
  - *Scientific Conclusion*: Anthropic API environmental metrics must be marked **`UNAVAILABLE`**.

---

### 4.4 Open-Source & Local Models: Empirical Hardware Grounding

* **Primary References**:
  1. *ML.ENERGY Leaderboard & Zeus Framework* (You et al., SymbioticLab, University of Michigan, USENIX NSDI 2023, [https://ml.energy](https://ml.energy)).
  2. *MLPerf Inference Benchmark Suite* (MLCommons, [https://mlcommons.org](https://mlcommons.org)).
  3. *Power Hungry Processing: Watts Driving the Cost of AI Deployment?* (Luccioni, Jernite, & Strubell, ACM FAccT 2024, [arXiv:2311.16863](https://arxiv.org/abs/2311.16863)).
* **Empirical Benchmarks & Specific Testbed Context**:
  - In SymbioticLab's published ML.ENERGY benchmark evaluations on specific testbed hardware (NVIDIA H100 SXM5 nodes running vLLM under controlled synthetic workloads):
    - *Llama 3 8B*: Measured active generation energy of **~0.15 to 0.35 J/token** under optimal batching ($\ge 16$), increasing to **~2.0 to 4.5 J/token** at batch size 1 due to static GPU idle draw.
    - *Llama 3 70B (across 4×H100)*: Measured **~1.8 to 3.5 J/token** under high batching, jumping to **~15.0 to 35.0 J/token** at batch size 1.
  - *Limitations*: These figures represent specific laboratory benchmark configurations on dedicated hardware testbeds. They do not represent universal constants and cannot be generalized across differing server topologies, CPU hosts, or multi-tenant serving frameworks without direct measurement.
  - Autoregressive decode energy is empirically $3\times\text{--}8\times$ higher per token than prefill energy due to memory bandwidth constraints.
* **Measurement Scope Distinctions on Local Hardware**:
  - **NVIDIA NVML** (as implemented in EcoMind Phase 5A): Measures instantaneous power across the PCIe/SXM board. Scope: `GPU_INFERENCE_WINDOW`. Accurately captures GPU die, on-board VRAM, and board VRM losses.
  - **Exclusions**: NVML does not capture host CPU power, motherboard chipset draw, system DRAM channels, storage, cooling fans, or power supply unit (PSU) conversion losses.
  - **Whole-System Telemetry**: Capturing full-system energy requires Intel RAPL (`/sys/class/powercap/intel-rapl` for CPU/DRAM) or physical hardware meters (e.g., Yokogawa WT310E, WattsUp Pro, server IPMI/BMC power registers).
  - *Scientific Conclusion*: Local GPU energy sampled via NVML is genuinely **`MEASURED`**, but its scope must remain strictly labeled as `GPU_INFERENCE_WINDOW`. It must not be labeled as "total system energy."

---

### 4.5 Deterministic Tools & Semantic Cache: Correcting Impact Accounting

* **The Fallacy of "Zero Impact"**:
  - In previous drafts, tools and cache hits were characterized as having "0.0 Wh energy, 0.0 mL water, and 0.0 gCO₂e."
  - This is scientifically false. Executing Python AST parsing, executing mathematical logic, or computing a 384-dimensional embedding in `all-MiniLM-L6-v2` via FAISS draws electrical power on the host CPU/GPU and consumes system DRAM cycles.
  - That electricity generation induces indirect water consumption at power plants (Scope 2 water) and releases greenhouse gases.
* **Dynamic Latency Measurement**:
  - Execution latencies are **not fixed constants** (such as "$< 0.1\text{ ms}$" or "$1\text{--}5\text{ ms}$").
  - In EcoMind, execution latency is dynamically measured per-request via high-resolution system timers (`time.perf_counter`) and reported authentically.
* **The Reality of Model Avoidance**:
  - What deterministic tools and semantic cache hits *genuinely* achieve is **neural-network model call avoidance** and **model token avoidance** relative to an explicit counterfactual model routing baseline.
* **Accounting Mandate**:
  - **Execution Facts (MEASURED)**:
    - Model tokens consumed: identically **0**.
    - Model inference calls: identically **0** (1 model call avoided relative to an explicit model baseline).
    - Request execution latency: dynamically measured in milliseconds via `time.perf_counter`.
  - **Environmental Metrics**: Without active CPU power meters (RAPL) or physical wall meters, the electricity, water, and carbon consumed by the host CPU during tool/cache execution are **`UNAVAILABLE`**. They must not be fabricated as zero.

---

### 4.6 Water Accounting: Scope Separation & Calculation Boundaries

* **Primary Standards & Research**:
  1. *Making AI Less 'Thirsty': Uncovering and Addressing the Secret Water Footprint of AI Models* (Li, Yang, Islam, & Ren, ACM CACM 2023, [arXiv:2304.03271](https://arxiv.org/abs/2304.03271)).
  2. *Water Usage Effectiveness (WUE)* (The Green Grid / ISO/IEC 30134-9).
* **The Two Physical Scopes**:
  $$\text{Total Water Footprint} = W_{\text{direct (on-site cooling)}} + W_{\text{indirect (electricity generation)}}$$
  1. **Scope 1: Direct On-Site Cooling Water ($W_{\text{direct}}$)**:
     - Water evaporated in cooling towers to reject data-center heat into the atmosphere.
     - Units: Milliliters ($\text{mL}$) or Liters ($\text{L}$).
     - Formula: $W_{\text{direct}}(\text{L}) = E_{\text{IT}}(\text{kWh}) \times \text{WUE}_{\text{site}}(\text{L/kWh})$.
     - *Physical Reality*: Facilities using air-cooled chillers or direct expansion have $\text{WUE}_{\text{site}} \approx 0.0\text{ L/kWh}$. Facilities using evaporative cooling towers typically consume $1.0\text{ to }1.8\text{ L/kWh}$.
  2. **Scope 2: Indirect Electricity-Related Water ($W_{\text{indirect}}$)**:
     - Water consumed at off-site thermoelectric power plants (condenser cooling) and surface evaporation from hydroelectric reservoirs supplying the power grid.
     - Formula: $W_{\text{indirect}}(\text{L}) = E_{\text{total}}(\text{kWh}) \times \text{WIE}_{\text{grid}}(\text{L/kWh})$.
     - *Physical Reality*: US average Water Intensity of Electricity ($\text{WIE}_{\text{grid}}$) is $1.5\text{ to }2.5\text{ L/kWh}$ (NREL / Torcellini et al.).
* **Calculation Boundary Rules**:
  - **Never apply WUE to an incompatible energy boundary**: WUE applies strictly to IT equipment energy ($E_{\text{IT}}$). Multiplying GPU-only board energy by a facility WUE produces an incorrect, truncated water estimate.
  - **Never infer cooling technology without disclosure**: Assuming a cloud provider uses evaporative cooling vs. air cooling without documentation is speculation.
  - **Accounting Status**: Because Groq, OpenAI, and Anthropic disclose zero cooling technologies or facility locations, direct cooling water must be marked **`UNAVAILABLE`**.

---

### 4.7 Carbon Accounting: Energy Boundaries & Geographic Reality

* **Primary Standards**:
  - *GHG Protocol Scope 2 Guidance* (World Resources Institute / WBCSD, [Link](https://ghgprotocol.org/scope-2-guidance)).
* **The Operational Formulation**:
  $$C_{\text{operational}}(\text{gCO}_2\text{e}) = \frac{E_{\text{system}}(\text{Wh})}{1000} \times I_{\text{grid}}(\text{gCO}_2\text{e/kWh})$$
* **Boundary Alignment Mandate**:
  - If energy is measured only at the GPU board level ($E_{\text{gpu\_nvml}}$), the resulting carbon calculation is strictly **`GPU-board operational carbon`**, not total inference carbon.
  - Total operational carbon requires whole-system energy: $E_{\text{system}} = (E_{\text{accelerator}} + E_{\text{host}} + E_{\text{idle}}) \times \text{PUE}$.
* **Geographic Reality vs. Hidden Cloud Locations**:
  - Grid carbon intensity ($I_{\text{grid}}$) varies by over $10\times$ depending on physical location:
    - Clean grids (e.g., France $\approx 55\text{ g/kWh}$, Sweden $\approx 25\text{ g/kWh}$, California $\approx 210\text{ g/kWh}$).
    - Fossil-heavy grids (e.g., US Midwest $\approx 580\text{ g/kWh}$, Texas $\approx 380\text{ g/kWh}$, Germany $\approx 380\text{ g/kWh}$).
  - Cloud APIs dynamically route requests across global server fleets. The user cannot see whether a request executed in Oregon, Iowa, Belgium, or Taiwan.
  - **Rule**: EcoMind must **never silently substitute the US National Grid Average** ($370\text{ gCO}_2\text{e/kWh}$) as the "known" location of a cloud provider. Doing so manufactures false precision.
  - **Accounting Status**: Unless the execution region is explicitly known (e.g., local host machine in a user-configured region) or provided via a documented user assumption, operational carbon for cloud APIs must be reported as **`UNAVAILABLE`**.

---

## 5. Corrected Minimal Defensible Multi-Provider Accounting MVP

The Minimal Viable Product (MVP) for Phase 5B must establish multi-provider accounting **without forcing unsupported environmental numbers**:

```text
                                  ┌───────────────────────────┐
                                  │   INCOMING USER QUERY     │
                                  └─────────────┬─────────────┘
                                                │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
  [DETERMINISTIC TOOLS]          [SEMANTIC CACHE]             [MODEL ROUTING]
  - 0 model tokens (MEASURED)    - 0 model tokens (MEASURED)  - Small / Med / Large Tiers
  - 1 call avoided vs baseline   - 1 call avoided vs baseline - Provider execution
  - Dynamic latency (MEASURED)   - Dynamic latency (MEASURED) - Authentic tokens (REPORTED)
  - Energy: UNAVAILABLE          - Energy: UNAVAILABLE        - Dynamic latency (MEASURED)
  - Water: UNAVAILABLE           - Water: UNAVAILABLE         
  - Carbon: UNAVAILABLE          - Carbon: UNAVAILABLE        
                                                                       │
                                      ┌────────────────────────────────┴────────────────┐
                                      ▼                                                 ▼
                             [LOCAL GPU EXECUTION]                             [CLOUD API EXECUTION]
                             - NVML GPU Energy: MEASURED                       - Groq Energy: UNAVAILABLE
                               Scope: GPU_INFERENCE_WINDOW                     - Groq Water: UNAVAILABLE
                             - Direct Water: UNAVAILABLE                       - Gemini Energy: UNAVAILABLE
                             - Carbon: CONDITIONAL                             - Gemini Water: UNAVAILABLE
                               (only if local grid is configured;               - Carbon: UNAVAILABLE
                                strictly GPU board scope)
```

### Core Architecture Rules of the Minimal MVP:
1. **Raw Telemetry vs. Estimates**: Maintain strict separation between raw physical measurements (`PhysicalMeasurement`), provider metadata (`TokenTelemetry`), and environmental projections.
2. **Independent Provider Evaluation**: Every provider and metric evaluates independently:
   - If defensible data exists $\to$ report metric with explicit scope, source, and bounds.
   - If defensible data does not exist $\to$ report `null` with `UNAVAILABLE` status.
   - **Never transfer coefficients between providers.**
3. **Execution Facts as Primary Savings Proxies**:
   - For deterministic tools and semantic cache hits, EcoMind reports authentic execution facts relative to an explicit baseline:
     $$\Delta \text{Model Calls} = 1 \quad (\text{avoided relative to counterfactual model baseline})$$
     $$\Delta \text{Tokens} = \text{Tokens}_{\text{baseline}} - 0 = \text{Tokens}_{\text{baseline}} \quad (\text{avoided})$$
     $$\Delta \text{Cost (USD)} = \text{Cost}_{\text{baseline}} - 0 = \text{Cost}_{\text{baseline}} \quad (\text{avoided})$$
   - These are genuine, verified operational facts. They are never converted into fabricated Wh or mL savings.

---

## 6. The Pair-Wise Savings Integrity Rule

To ensure that environmental savings claims remain scientifically irrefutable:

### The Non-Zero Rule
$$\text{If either } M(R_{\text{selected}}) = \text{UNAVAILABLE} \quad \text{or} \quad M(R_{\text{baseline}}) = \text{UNAVAILABLE}:$$
$$\Delta M = M(R_{\text{baseline}}) - M(R_{\text{selected}}) \equiv \mathbf{UNAVAILABLE}$$

* **Rule 1**: An unmeasured or unavailable metric must **never be treated as zero**. Subtracting an unmeasured value from a baseline does not yield savings; it yields an undefined difference.
* **Rule 2**: When environmental savings are `UNAVAILABLE`, EcoMind displays proxy savings ($\Delta \text{Tokens}$, $\Delta \text{Model Calls}$, $\Delta \text{Cost}$) with a clear UI notice: *"Environmental metrics are unmeasured for this provider; proxy resource savings displayed."*
* **Rule 3 (Quality Gate)**: Environmental savings can only be credited if the selected route produced an answer satisfying the query's required quality threshold ($\text{Quality} \ge Q_{\text{req}}$). If a small model hallucinates on a complex reasoning task, resource savings cannot be claimed without noting the quality degradation penalty.

---

## 7. Open Research Questions & Limitations

1. **Cloud Multi-Tenancy & Dynamic Batching**: Cloud providers dynamically batch user requests. A query executed at batch size 32 consumes a fraction of the per-token accelerator energy of a query executed at batch size 1. Because public APIs expose zero concurrency metadata, all cloud energy models suffer from unobservable batch variance.
2. **Internal Chain-of-Thought Tokens**: Advanced reasoning models (e.g., Google Gemini 2.5 Pro, OpenAI o1) generate internal thinking tokens. If API usage metadata reports only visible candidate tokens, the energy consumed during internal reasoning passes remains unaccounted for.
3. **Host System Power on Local Hardware**: Local GPU inference is cleanly measured via NVML, but host CPU, system DRAM, and motherboard power draw remain unmeasured without OS-specific drivers (Intel RAPL on Linux, or external hardware power meters).
4. **Spatial-Temporal Cloud Carbon Accounting**: Cloud providers do not expose the physical data-center node handling individual API calls. Until providers offer real-time per-request location tagging, location-based carbon accounting for cloud APIs remains unresolvable without arbitrary geographic assumptions.
5. **Embodied Carbon Allocation**: Amortizing the embodied carbon of manufacturing chips, servers, and data-center buildings over individual inference queries requires knowing hardware lifespan, total lifetime query volume, and chip fabrication emissions (Scope 3). Academic estimates vary by over $5\times$.

---

## 8. Decisions Requiring User Approval Before Implementation

Before proceeding to implement Phase 5B in code, please review and approve the following architectural decisions:

1. **Strict UNAVAILABLE Status for Cloud APIs**:  
   *Question*: Given that neither Google Gemini nor Groq discloses per-request API energy, data-center locations, or cooling water, should EcoMind strictly report their runtime energy, water, and carbon as `null` with `UNAVAILABLE` status?  
   *Recommendation*: **Yes**. Preserves absolute scientific integrity and prevents data fabrication.

2. **Tool and Cache Accounting Policy**:  
   *Question*: For deterministic tools and semantic cache hits, should EcoMind report model tokens as $0$ (`MEASURED`), avoided model calls as $1$ relative to a counterfactual model baseline (`MEASURED`), dynamically measure latency via `time.perf_counter`, and mark physical energy, water, and carbon as `UNAVAILABLE` (unless local CPU/GPU hardware counters are actively sampled)?  
   *Recommendation*: **Yes**. Accurately credits model and token avoidance without fabricating physical Joules or milliliters.

3. **Local GPU Measurement Scope Labeling**:  
   *Question*: For local Ollama models running on NVIDIA GPUs, should EcoMind report NVML energy as `MEASURED` with the mandatory scope label `"MEASURED GPU ENERGY (INFERENCE WINDOW ONLY - NOT TOTAL SYSTEM ENERGY)"`?  
   *Recommendation*: **Yes**. Continues the Phase 5A precedent of non-conflation.

4. **Conditional Carbon Calculation for Local Execution**:  
   *Question*: Should EcoMind calculate location-based carbon *only* when the user has explicitly configured their regional grid emission factor (e.g., via `LOCAL_GRID_INTENSITY_GCO2E_PER_KWH` in `.env`), returning `UNAVAILABLE` otherwise, and strictly label it as GPU-board carbon?  
   *Recommendation*: **Yes**. Prevents assuming a default geographic region without evidence and prevents conflating board carbon with whole-system carbon.

5. **Enforcement of the Pair-Wise Savings Integrity Rule**:  
   *Question*: Should savings calculations strictly return `UNAVAILABLE` whenever data on either side of a route comparison is missing, displaying authentic token and model-call avoidance as proxies instead?  
   *Recommendation*: **Yes**. Prevents false claims of 100% water or carbon reductions against unmeasured routes.

---

## 9. Changelog: Revisions from Previous Draft

* **Removed speculative Gemini tier multipliers**: Eliminated the unverified assumption that Flash-Lite is $0.5\times$ and Pro is $3.5\times\text{--}5.0\times$ the Gemini Apps median.
* **Decoupled Gemini Apps fleet median from API requests**: Clarified that Google's 0.24 Wh and 0.26 mL median figures represent the Gemini Apps consumer product, not an individual per-request formula for the Gemini Developer API.
* **Qualified Groq hardware and power claims**: Removed unverified claims of "500–576 chips" and "100+ kW rack power" as confirmed facts; documented that whole-system per-request energy cannot be inferred from single-chip specs and marked Groq energy/water as `UNAVAILABLE`.
* **Eliminated assumed static latencies**: Replaced hardcoded latency values ($< 0.1\text{ ms}$, $1\text{--}5\text{ ms}$) with explicit dynamic measurement via `time.perf_counter`.
* **Defined avoided model calls relative to an explicit baseline**: Specified that model-call avoidance is valid strictly relative to a counterfactual model routing baseline (e.g., Always-Large).
* **Strictly qualified local GPU measurements**: Mandated that local GPU energy and derived carbon are labeled as GPU-board metrics (`GPU_INFERENCE_WINDOW`), not whole-system measurements.
* **Removed silent US grid average assumption**: Prohibited assuming cloud data centers run on the US national grid average. Cloud carbon marked `UNAVAILABLE` unless geographic location is authenticated.
* **Reassessed OpenAI and Anthropic claims**: Classified Sam Altman's 0.34 Wh / 0.32 mL quote as an unverified executive remark, not an API estimation model. Documented Anthropic's complete corporate disclosure opacity.
* **Formalized the Pair-Wise Non-Zero Rule**: Established that if either side of a comparison is `UNAVAILABLE`, the environmental differential $\Delta$ is strictly `UNAVAILABLE`.
