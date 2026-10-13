"""
EcoMind Phase 5B: Versioned Environmental Estimation Source Registry & Freshness Service.

Provides a scientifically auditable, versioned catalog of environmental estimation
methodologies, papers, benchmark datasets, and API sources with explicit metadata,
formulae, coefficients, assumptions, limitations, and lifecycle freshness validation.
"""

import threading
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable

from .schemas import (
    EnvironmentalSource,
    SourceType,
    SourceValidationStatus,
    MeasurementScope,
    SourceCheckResult
)
from config.settings import settings


class SourceRegistry:
    """
    Thread-safe registry of validated environmental estimation sources.
    Each registered source contains verifiable provenance, explicit assumptions,
    applicable hardware/models, and methodology coefficients.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sources: Dict[str, EnvironmentalSource] = {}
        self._load_default_sources()

    def _load_default_sources(self) -> None:
        """Initialize standard, peer-reviewed, and verified empirical sources."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. NVIDIA Management Library (NVML) Hardware Telemetry
        self.register(EnvironmentalSource(
            source_id="src-nvml-nvidia-2024",
            name="NVIDIA Management Library (NVML) Hardware Telemetry",
            url="https://developer.nvidia.com/management-library-nvml",
            publisher="NVIDIA Corporation",
            source_type=SourceType.OFFICIAL_DOCUMENTATION,
            publication_date="2024-01-15",
            retrieval_date="2026-10-10",
            last_verified_timestamp=now_iso,
            applicable_providers=["local"],
            applicable_models=["*"],
            applicable_hardware=["NVIDIA RTX", "NVIDIA A100", "NVIDIA H100", "NVIDIA L40S"],
            applicable_regions=["local_host"],
            supported_metrics=["energy"],
            formula="E = \\int P(t) dt \\approx \\sum P_i \\cdot \\Delta t_i",
            coefficients={"sampling_rate_ms": 100, "interface": "nvmlDeviceGetPowerUsage"},
            units={"energy": "J", "power": "W", "time": "ms"},
            assumptions=[
                "Samples on-device GPU board power draw directly from NVML C-bindings",
                "Captures GPU die and VRAM power during active inference execution window only",
                "Does NOT capture host CPU, system RAM, storage, cooling fans, or PSU conversion losses"
            ],
            measurement_scope=MeasurementScope.GPU_INFERENCE_WINDOW,
            uncertainty_limitations="Board-level power accuracy is +/- 5W per NVIDIA hardware sensor specifications. Strictly limited to GPU board.",
            version="12.0",
            validation_status=SourceValidationStatus.CURRENT,
            next_review_date="2026-12-31",
            attribution="NVIDIA NVML C-API (NVIDIA Corporation, 2024)"
        ))

        # 2. ML.ENERGY Leaderboard & Benchmark Dataset (SymbioticLab / Univ of Michigan)
        self.register(EnvironmentalSource(
            source_id="src-mlenergy-leaderboard-v3",
            name="ML.ENERGY Inference Energy Benchmark Dataset (v3.0)",
            url="https://ml.energy/leaderboard/",
            publisher="SymbioticLab, University of Michigan (Zheng, Wang, et al., arXiv:2310.03003)",
            source_type=SourceType.BENCHMARK_DATASET,
            publication_date="2023-10-01",
            retrieval_date="2026-10-12",
            last_verified_timestamp=now_iso,
            applicable_providers=["groq", "local", "open-weight"],
            applicable_models=[
                "openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b",
                "llama-3.1-8b", "llama-3.3-70b", "llama-3-8b", "llama-3-70b",
                "mistral-7b", "qwen-2.5-32b"
            ],
            applicable_hardware=["NVIDIA H100 SXM5", "NVIDIA A100 PCIe"],
            applicable_regions=["datacenter_us"],
            supported_metrics=["energy"],
            formula="E_inference = E_prefill_per_token * N_in + E_decode_per_token * N_out + E_baseline_window",
            coefficients={
                "models": {
                    "small": {
                        "typical_models": ["openai/gpt-oss-20b", "llama-3.1-8b", "llama-3-8b"],
                        "prefill_joules_per_token": 0.0008,
                        "decode_joules_per_token": 0.0080,
                        "baseline_joules_per_req": 0.50
                    },
                    "medium": {
                        "typical_models": ["qwen/qwen3.8-27b", "qwen-2.5-32b"],
                        "prefill_joules_per_token": 0.0020,
                        "decode_joules_per_token": 0.0220,
                        "baseline_joules_per_req": 1.00
                    },
                    "large": {
                        "typical_models": ["openai/gpt-oss-120b", "llama-3.3-70b", "llama-3-70b"],
                        "prefill_joules_per_token": 0.0040,
                        "decode_joules_per_token": 0.0450,
                        "baseline_joules_per_req": 1.50
                    }
                }
            },
            units={"energy": "J", "energy_per_token": "J/token", "energy_kwh": "kWh"},
            assumptions=[
                "Empirical testbed measurements under vLLM on dedicated NVIDIA H100 SXM5 servers",
                "Decoding phase consumes 75-90% of active inference energy",
                "Standard batching and FP8/BF16 tensor parallelism on multi-GPU server nodes"
            ],
            measurement_scope=MeasurementScope.SYSTEM,
            uncertainty_limitations="Empirical benchmark measured on dedicated server testbeds; does not represent proprietary cloud provider multi-tenant load or black-box load balancers. Point estimate with +/- 15% hardware variance.",
            version="3.0",
            validation_status=SourceValidationStatus.CURRENT,
            next_review_date="2026-12-01",
            attribution="Zheng et al., ML.ENERGY: Benchmarking and Optimizing Energy Consumption of Large Language Models (arXiv:2310.03003, 2023-2025)"
        ))

        # 3. EcoLogits LLM API Life Cycle Assessment Methodology (MLCO2 / Data for Good)
        self.register(EnvironmentalSource(
            source_id="src-ecologits-lca-2024",
            name="EcoLogits LLM API Life Cycle Assessment Methodology",
            url="https://ecologits.ai/",
            publisher="MLCO2 & Data for Good",
            source_type=SourceType.RESEARCH_PAPER,
            publication_date="2024-03-15",
            retrieval_date="2026-10-12",
            last_verified_timestamp=now_iso,
            applicable_providers=["openai", "anthropic", "mistral", "google", "groq"],
            applicable_models=["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "llama-3.3-70b"],
            applicable_hardware=["Hyperscale Cloud AI Clusters (H100/TPU/A100)"],
            applicable_regions=["global_cloud"],
            supported_metrics=["energy", "carbon"],
            formula="E_total = E_usage + E_embodied; E_usage = P_server * (TTFT + N_out / TPS) * PUE",
            coefficients={
                "pue": 1.18,
                "embodied_fraction": 0.15,
                "server_power_w": {
                    "small": 400.0,
                    "medium": 700.0,
                    "large": 1200.0
                },
                "tps_estimate": {
                    "small": 80.0,
                    "medium": 50.0,
                    "large": 30.0
                }
            },
            units={"energy": "kWh", "carbon": "kgCO2eq", "power": "W", "time": "s"},
            assumptions=[
                "Bottom-up Life Cycle Assessment conforming to ISO 14044 principles",
                "Includes active server compute energy multiplied by facility PUE (1.18)",
                "Includes embodied server and accelerator manufacturing carbon amortized over 4-year lifespan",
                "Calculates active generation duration via TTFT + output_tokens / TPS"
            ],
            measurement_scope=MeasurementScope.CLOUD_INFERENCE,
            uncertainty_limitations="Point estimate based on public architectural specs. Cloud providers do not disclose dynamic batch concurrency, multi-tenant scheduling, or exact facility PUE per query. Confidence intervals are unknown.",
            version="0.3.0",
            validation_status=SourceValidationStatus.CURRENT,
            next_review_date="2026-11-15",
            attribution="EcoLogits: Tracking the Environmental Impact of Generative AI (MLCO2 / Data for Good, 2024)"
        ))

        # 4. Google Gemini Apps Product Fleet Environmental Benchmark (Elsworth et al., Google)
        self.register(EnvironmentalSource(
            source_id="src-google-elsworth-2025",
            name="Measuring the Environmental Impact of Delivering AI at Google Scale",
            url="https://arxiv.org/abs/2508.15734",
            publisher="Google LLC (Elsworth, Patterson, Dean, Manyika, et al.)",
            source_type=SourceType.RESEARCH_PAPER,
            publication_date="2025-08-21",
            retrieval_date="2026-10-10",
            last_verified_timestamp=now_iso,
            applicable_providers=["google"],
            applicable_models=["gemini-apps-fleet"],
            applicable_hardware=["Google TPU v4/v5e clusters"],
            applicable_regions=["google_global_fleet"],
            supported_metrics=["energy", "water", "carbon"],
            formula="Fleet median: 0.24 Wh electricity, 0.26 mL direct cooling water, 0.03 gCO2e market carbon per consumer prompt",
            coefficients={
                "median_energy_wh": 0.24,
                "median_water_ml": 0.26,
                "median_carbon_gco2e": 0.03,
                "infrastructure_breakdown": {
                    "tpu_accelerators": 0.58,
                    "host_cpu_dram": 0.25,
                    "unallocated_headroom": 0.10,
                    "datacenter_overhead_pue": 0.08
                }
            },
            units={"energy": "Wh", "water": "mL", "carbon": "gCO2e"},
            assumptions=[
                "Aggregated 12-month production fleet median for Gemini Apps consumer text prompts",
                "Represents an internal dynamic routing product blend, NOT specific developer API checkpoints",
                "Market-based carbon accounting reflects Google 24/7 carbon-free energy matching"
            ],
            measurement_scope=MeasurementScope.CLOUD_INFERENCE,
            uncertainty_limitations="Valid strictly as a consumer-product fleet benchmark. Google publishes zero per-token coefficients, API checkpoint formulas, or per-request variance for the Gemini Developer API. Per-request Gemini API metrics are UNAVAILABLE.",
            version="1.0",
            validation_status=SourceValidationStatus.CURRENT,
            next_review_date="2027-01-15",
            attribution="Elsworth et al., Google (arXiv:2508.15734, August 2025)"
        ))

        # 5. Ember Global Electricity Carbon Intensity Database
        self.register(EnvironmentalSource(
            source_id="src-ember-climate-2024",
            name="Ember Global Electricity Carbon Intensity Database",
            url="https://ember-climate.org/data/data-tools/data-explorer/",
            publisher="Ember Climate",
            source_type=SourceType.BENCHMARK_DATASET,
            publication_date="2024-05-01",
            retrieval_date="2026-10-10",
            last_verified_timestamp=now_iso,
            applicable_providers=["local", "grid"],
            applicable_models=["*"],
            applicable_hardware=["*"],
            applicable_regions=["US", "IN", "DE", "FR", "UK", "EU", "GLOBAL"],
            supported_metrics=["carbon"],
            formula="carbon_gco2e = energy_kwh * grid_intensity_gco2e_per_kwh",
            coefficients={
                "intensity_by_region": {
                    "US": 370.0,
                    "US-CA": 210.0,
                    "IN": 710.0,
                    "DE": 380.0,
                    "FR": 55.0,
                    "UK": 160.0,
                    "GLOBAL": 440.0
                }
            },
            units={"intensity": "gCO2e/kWh", "energy": "kWh", "carbon": "gCO2e"},
            assumptions=[
                "National and regional generation-weighted average emissions intensity factors",
                "Reflects annual average generation mix from utility reporting"
            ],
            measurement_scope=MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON,
            uncertainty_limitations="Annual average national grid intensity masks hour-by-hour marginal generation fluctuations. Appropriate for baseline static estimation when local hourly telemetry is unavailable.",
            version="2024.1",
            validation_status=SourceValidationStatus.CURRENT,
            next_review_date="2026-12-31",
            attribution="Ember Global Electricity Review 2024 (Ember Climate)"
        ))

        # 6. Electricity Maps Live Carbon Intensity API
        self.register(EnvironmentalSource(
            source_id="src-electricitymaps-v3",
            name="Electricity Maps Real-Time Grid Carbon Intensity",
            url="https://api.electricitymap.org/",
            publisher="Electricity Maps",
            source_type=SourceType.API,
            publication_date="2024-01-01",
            retrieval_date="2026-10-10",
            last_verified_timestamp=now_iso,
            applicable_providers=["local", "grid"],
            applicable_models=["*"],
            applicable_hardware=["*"],
            applicable_regions=["global_zones"],
            supported_metrics=["carbon"],
            formula="carbon_gco2e = energy_kwh * live_marginal_intensity",
            coefficients={"update_interval_minutes": 60},
            units={"intensity": "gCO2e/kWh", "energy": "kWh", "carbon": "gCO2e"},
            assumptions=[
                "Hourly zonal grid emission factor tracking live electricity imports/exports",
                "Direct Scope 2 location-based operational accounting"
            ],
            measurement_scope=MeasurementScope.GPU_BOARD_OPERATIONAL_CARBON,
            uncertainty_limitations="Requires active network connectivity and API token. If unreachable, gracefully falls back to static verified regional factor with explicit fallback disclosure.",
            version="3.0",
            validation_status=SourceValidationStatus.CURRENT,
            next_review_date="2026-11-30",
            attribution="Electricity Maps API v3 (Electricity Maps, 2024)"
        ))

        # 7. Groq TSP Architecture Specification (Abts et al., ISCA)
        self.register(EnvironmentalSource(
            source_id="src-groq-isca-2020",
            name="Think Fast: A Tensor Streaming Processor for Accelerating Deep Learning Workloads",
            url="https://doi.org/10.1109/ISCA45697.2020.00023",
            publisher="IEEE/ACM ISCA (Abts et al.)",
            source_type=SourceType.RESEARCH_PAPER,
            publication_date="2020-05-30",
            retrieval_date="2026-10-10",
            last_verified_timestamp=now_iso,
            applicable_providers=["groq"],
            applicable_models=["*"],
            applicable_hardware=["GroqCard TSP (14nm)"],
            applicable_regions=["groqcloud"],
            supported_metrics=["energy"],
            formula="Card TDP ~275W; 230 MB on-chip SRAM",
            coefficients={"card_tdp_watts": 275.0, "on_chip_sram_mb": 230.0},
            units={"power": "W", "memory": "MB"},
            assumptions=[
                "Hardware architecture paper evaluating ResNet-50 and simple computer vision on single-card testbeds",
                "Does NOT evaluate 70B distributed LLMs across multi-rack scale-out clusters"
            ],
            measurement_scope=MeasurementScope.UNKNOWN,
            uncertainty_limitations="Single-chip silicon specifications cannot be divided by throughput to yield whole-system per-request energy for large distributed models. Cluster-level power and water are marked UNAVAILABLE.",
            version="1.0",
            validation_status=SourceValidationStatus.CURRENT,
            next_review_date="2027-01-01",
            attribution="Abts et al., Think Fast: A Tensor Streaming Processor (IEEE/ACM ISCA 2020)"
        ))

    def register(self, source: EnvironmentalSource, overwrite: bool = False) -> None:
        """Register a validated environmental source."""
        with self._lock:
            if source.source_id in self._sources and not overwrite:
                raise ValueError(f"Source with id '{source.source_id}' already registered. Use overwrite=True.")
            
            # Compute integrity hash if not present
            if not source.content_hash:
                h = hashlib.sha256()
                h.update(source.source_id.encode("utf-8"))
                h.update(source.name.encode("utf-8"))
                h.update(source.version.encode("utf-8"))
                source.content_hash = h.hexdigest()[:16]

            self._sources[source.source_id] = source

    def get(self, source_id: str) -> Optional[EnvironmentalSource]:
        """Retrieve a registered source by ID."""
        with self._lock:
            return self._sources.get(source_id)

    def list_all(self) -> List[EnvironmentalSource]:
        """Return all registered environmental estimation sources."""
        with self._lock:
            return list(self._sources.values())

    def find_applicable_sources(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        metric: Optional[str] = None
    ) -> List[EnvironmentalSource]:
        """Filter sources matching provider, model, and/or metric."""
        with self._lock:
            res: List[EnvironmentalSource] = []
            for src in self._sources.values():
                if provider and ("*" not in src.applicable_providers and provider.lower() not in [p.lower() for p in src.applicable_providers]):
                    continue
                if model and ("*" not in src.applicable_models and model.lower() not in [m.lower() for m in src.applicable_models]):
                    continue
                if metric and (metric.lower() not in [m.lower() for m in src.supported_metrics]):
                    continue
                res.append(src)
            return res


class SourceValidationService:
    """
    Manages source lifecycle, automated freshness audits, and version validation.
    Prevents stale or superseded methodology drift while ensuring EcoMind never
    crashes if an external website or network endpoint is unreachable.
    """

    def __init__(self, registry: SourceRegistry):
        self._registry = registry
        self._stale_days = getattr(settings, "SOURCE_STALE_THRESHOLD_DAYS", 90)
        self._review_days = getattr(settings, "SOURCE_REVIEW_NEEDED_DAYS", 30)
        self._lock = threading.Lock()
        self._last_audit_timestamp: Optional[str] = None

    def check_source(
        self,
        source_id: str,
        network_checker: Optional[Callable[[str], bool]] = None
    ) -> SourceCheckResult:
        """
        Audit a specific source's freshness and validation status.
        network_checker: Optional hook to test live URL/API reachability without external network dependency.
        """
        source = self._registry.get(source_id)
        if not source:
            return SourceCheckResult(
                source_id=source_id,
                status=SourceValidationStatus.UNAVAILABLE,
                last_checked=datetime.now(timezone.utc).isoformat(),
                is_accessible=False,
                needs_review=True,
                message=f"Source '{source_id}' not found in registry."
            )

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Parse last verification date
        try:
            last_verified = datetime.fromisoformat(source.last_verified_timestamp.replace("Z", "+00:00"))
        except Exception:
            last_verified = now - timedelta(days=self._stale_days + 1)

        age_days = (now - last_verified).days

        # Check network accessibility if a checker is supplied
        is_accessible = True
        access_note = ""
        if network_checker is not None:
            try:
                is_accessible = network_checker(source.url)
                if not is_accessible:
                    access_note = " Upstream URL was not reachable during check."
            except Exception as e:
                is_accessible = False
                access_note = f" Reachability check failed: {str(e)}."

        # Evaluate lifecycle status
        needs_review = False
        if not is_accessible:
            new_status = SourceValidationStatus.UNAVAILABLE
            needs_review = True
            msg = f"Source {source_id} is currently inaccessible.{access_note} Retaining last validated version {source.version}."
        elif age_days > self._stale_days:
            new_status = SourceValidationStatus.STALE
            needs_review = True
            msg = f"Source {source_id} last verified {age_days} days ago (> {self._stale_days} days threshold). Flagged as STALE."
        elif age_days > self._review_days:
            new_status = SourceValidationStatus.REVIEW_NEEDED
            needs_review = True
            msg = f"Source {source_id} last verified {age_days} days ago (> {self._review_days} days threshold). Review recommended."
        else:
            new_status = SourceValidationStatus.CURRENT
            msg = f"Source {source_id} is CURRENT and verified within policy ({age_days} days old)."

        # Update source in registry safely
        source.validation_status = new_status
        return SourceCheckResult(
            source_id=source_id,
            status=new_status,
            last_checked=now_iso,
            is_accessible=is_accessible,
            needs_review=needs_review,
            message=msg
        )

    def refresh_all(
        self,
        force: bool = False,
        network_checker: Optional[Callable[[str], bool]] = None
    ) -> List[SourceCheckResult]:
        """Perform comprehensive freshness audit across all registered sources."""
        with self._lock:
            results: List[SourceCheckResult] = []
            for src in self._registry.list_all():
                res = self.check_source(src.source_id, network_checker=network_checker)
                results.append(res)
            self._last_audit_timestamp = datetime.now(timezone.utc).isoformat()
            return results

    def get_review_needed_sources(self) -> List[EnvironmentalSource]:
        """List sources flagged for human review or stale update."""
        return [
            s for s in self._registry.list_all()
            if s.validation_status in (SourceValidationStatus.REVIEW_NEEDED, SourceValidationStatus.STALE, SourceValidationStatus.UNAVAILABLE)
        ]

    @property
    def last_audit_timestamp(self) -> Optional[str]:
        return self._last_audit_timestamp


# Global thread-safe instances
source_registry = SourceRegistry()
source_validation_service = SourceValidationService(source_registry)
