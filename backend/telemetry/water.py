"""
EcoMind Phase 5B: Rigorous Water Accounting Engine & Safeguards.

Methodology Mandate:
Distinguishes between:
1. Direct on-site water consumption (cooling towers, adiabatic evaporative coolers).
2. Data-centre operational water (facility HVAC, humidification).
3. Electricity-related water consumption (thermoelectric, hydroelectric utility generation).
4. Lifecycle water impacts (hardware raw extraction, fab manufacturing, supply chain).

Strict Integrity Safeguards:
- Never multiply energy by an arbitrary water coefficient.
- Never present an industry fleet average as measured per-request water.
- Retain UNAVAILABLE and explain the specific missing empirical parameters.
"""

from typing import Optional, Dict, Tuple
from .schemas import (
    ProvenanceStatus,
    MeasurementScope,
    WaterCategory
)


class WaterAccountingEngine:
    """
    Evaluates water footprint observability and enforces anti-fabrication safeguards.
    Cloud providers and local client execution maintain UNAVAILABLE status unless
    facility locations, cooling technology, and verified WUE/WIE factors exist.
    """

    def evaluate_water(
        self,
        provider: str,
        model: Optional[str] = None,
        scope: MeasurementScope = MeasurementScope.UNKNOWN
    ) -> Tuple[Optional[float], ProvenanceStatus, Dict[str, str]]:
        """
        Evaluate water consumption for an inference request.
        Returns: (water_liters, provenance, explanation_dict)
        """
        prov_clean = (provider or "").lower()

        # 1. Cloud Providers (Groq, Google Gemini API, OpenAI, Anthropic)
        if prov_clean in ("groq", "google", "openai", "anthropic", "cloud"):
            return (
                None,
                ProvenanceStatus.UNAVAILABLE,
                {
                    "status": "UNAVAILABLE",
                    "category": WaterCategory.UNAVAILABLE.value,
                    "reason": (
                        f"Cloud provider '{provider}' does not disclose physical data-center facility locations, "
                        "cooling technology (direct evaporative vs chilled-water vs air), or Water Usage Effectiveness (WUE). "
                        "Multiplying energy by an arbitrary water coefficient is scientifically barred."
                    ),
                    "missing_data": "Data center location, cooling mechanism, hourly WUE (L/kWh), and regional utility water intensity (WIE L/kWh)."
                }
            )

        # 2. Local Host / Client Hardware (e.g. Ollama on local NVIDIA GPU)
        if prov_clean in ("local", "ollama", "client"):
            return (
                None,
                ProvenanceStatus.UNAVAILABLE,
                {
                    "status": "UNAVAILABLE",
                    "category": WaterCategory.DIRECT_ON_SITE_COOLING.value,
                    "reason": (
                        "Local workstation/client hardware uses ambient air-cooling with 0.0 direct on-site evaporative water, "
                        "but indirect electricity-generation water is unmeasured without regional utility water-intensity factors."
                    ),
                    "missing_data": "Regional electric utility water consumption intensity (WIE in L/kWh)."
                }
            )

        # 3. Deterministic Tools & Semantic Cache
        if prov_clean in ("deterministic", "cache"):
            return (
                None,
                ProvenanceStatus.UNAVAILABLE,
                {
                    "status": "UNAVAILABLE",
                    "category": WaterCategory.UNAVAILABLE.value,
                    "reason": (
                        "Deterministic tools and semantic cache hits consume 0 model tokens. "
                        "Physical water footprint cannot be claimed as 0.0 L without host CPU/RAM telemetry and utility grid WIE data."
                    ),
                    "missing_data": "Host CPU energy measurement and utility water factor."
                }
            )

        # Default fallback
        return (
            None,
            ProvenanceStatus.UNAVAILABLE,
            {
                "status": "UNAVAILABLE",
                "category": WaterCategory.UNAVAILABLE.value,
                "reason": "No validated empirical water data source exists for this execution route.",
                "missing_data": "Direct cooling telemetry and utility water factors."
            }
        )


# Global water engine instance
water_accounting_engine = WaterAccountingEngine()
