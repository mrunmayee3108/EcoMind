"""
EcoMind Phase 5B: Grid Carbon Intensity Management & Operational Carbon Engine.

Strict Accounting Rules:
- GPU energy in Joules converted to kWh as: energy_kwh = energy_joules / 3_600_000.
- Operational carbon calculated as: carbon_gco2e = energy_kwh * grid_intensity_gco2e_per_kwh.
- Scope remains strictly GPU_BOARD_OPERATIONAL_CARBON when calculated from GPU board energy alone.
- Never claim live carbon intensity if using a static configured factor.
- Never silently substitute an arbitrary country-wide or global value for a known local region.
- If grid intensity is not configured or unavailable, return None without fabrication.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, Callable

from .schemas import (
    GridIntensityRecord,
    MeasurementScope,
)
from config.settings import settings


class GridIntensityManager:
    """
    Manages regional electricity carbon intensity factors and provenance.
    Supports user-configured static intensity, verified regional databases (Ember 2024),
    and pluggable dynamic live providers.
    """

    # Verified annual generation-weighted grid emission factors (Ember 2024 / IEA)
    # Unit: gCO2e per kWh
    VERIFIED_REGIONAL_FACTORS: Dict[str, float] = {
        "US": 370.0,
        "US-CA": 210.0,
        "IN": 710.0,
        "DE": 380.0,
        "FR": 55.0,
        "UK": 160.0,
        "EU": 270.0,
        "GLOBAL": 440.0
    }

    def __init__(self, dynamic_provider_fn: Optional[Callable[[str], Optional[float]]] = None):
        self._dynamic_provider_fn = dynamic_provider_fn

    def get_intensity(self, region: Optional[str] = None) -> Optional[GridIntensityRecord]:
        """
        Resolve carbon intensity factor with strict provenance tracking.
        Never claims 'live' when static. Never silently guesses unknown regions.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        target_region = (region or getattr(settings, "LOCAL_GRID_REGION", "DEFAULT")).upper()

        # 1. Check for user-configured static intensity in settings
        configured_factor = getattr(settings, "LOCAL_GRID_INTENSITY_GCO2E_PER_KWH", None)
        if configured_factor is not None and isinstance(configured_factor, (int, float)) and configured_factor > 0:
            return GridIntensityRecord(
                source_name="UserConfiguredStatic",
                region_code=target_region,
                intensity_gco2e_per_kwh=float(configured_factor),
                retrieval_timestamp=now_iso,
                applicable_timestamp=now_iso,
                units="gCO2e/kWh",
                is_live=False,
                version="1.0.0",
                fallback_used=False,
                attribution="User-configured setting LOCAL_GRID_INTENSITY_GCO2E_PER_KWH"
            )

        # 2. Check for dynamic live provider if enabled
        enable_dynamic = getattr(settings, "ENABLE_DYNAMIC_GRID_INTENSITY", False)
        if enable_dynamic and self._dynamic_provider_fn is not None:
            try:
                live_val = self._dynamic_provider_fn(target_region)
                if live_val is not None and live_val > 0:
                    return GridIntensityRecord(
                        source_name="DynamicElectricityMapsProvider",
                        region_code=target_region,
                        intensity_gco2e_per_kwh=float(live_val),
                        retrieval_timestamp=now_iso,
                        applicable_timestamp=now_iso,
                        units="gCO2e/kWh",
                        is_live=True,
                        version="3.0.0",
                        fallback_used=False,
                        attribution="Real-time regional carbon intensity from live grid provider"
                    )
            except Exception:
                # Dynamic provider unreachable; fallback handling below
                pass

        # 3. Check verified regional database if region is explicitly provided and recognized
        if target_region in self.VERIFIED_REGIONAL_FACTORS:
            factor = self.VERIFIED_REGIONAL_FACTORS[target_region]
            was_fallback = bool(enable_dynamic)  # Fallback if dynamic was enabled but failed
            return GridIntensityRecord(
                source_name="EmberGlobalElectricityReview2024",
                region_code=target_region,
                intensity_gco2e_per_kwh=factor,
                retrieval_timestamp=now_iso,
                applicable_timestamp="2024-05-01T00:00:00Z",
                units="gCO2e/kWh",
                is_live=False,
                version="2024.1",
                fallback_used=was_fallback,
                attribution=f"Ember Global Electricity Review (2024) regional factor for {target_region}"
            )

        # 4. If target_region is "DEFAULT" or unrecognized and no configured factor is set:
        # Return None. Prohibit silently applying an arbitrary country factor!
        return None

    def calculate_operational_carbon(
        self,
        energy_joules: Optional[float],
        region: Optional[str] = None
    ) -> Tuple[Optional[float], Optional[GridIntensityRecord]]:
        """
        Calculate operational carbon from energy in Joules and active grid intensity:
        energy_kwh = energy_joules / 3_600_000
        carbon_gco2e = energy_kwh * intensity
        """
        if energy_joules is None or energy_joules <= 0:
            return None, None

        rec = self.get_intensity(region=region)
        if rec is None:
            return None, None

        # Exact formula required by specification
        energy_kwh = energy_joules / 3_600_000.0
        carbon_gco2e = round(energy_kwh * rec.intensity_gco2e_per_kwh, 6)
        return carbon_gco2e, rec


# Global manager instance
grid_manager = GridIntensityManager()
