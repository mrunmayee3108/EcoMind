import os
import json
import sqlite3
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union

from config.settings import settings
from telemetry.schemas import TelemetryRecord, ProvenanceStatus
from receipt.schemas import EcoReceipt, ExecutionPath

logger = logging.getLogger("ecomind.historical_store")

class HistoricalStore:
    """
    SQLite-backed persistent store for historical request telemetry and Eco Receipts.
    Provides reliable, durable, and indexed storage to eliminate in-memory eviction loss,
    enforce anti-fabrication data integrity, and power dashboard analytics.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path if db_path is not None else settings.HISTORICAL_DB_PATH
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_storage()

    def _init_storage(self):
        """Initialize SQLite database connection and ensure tables and indexes exist."""
        with self._lock:
            if self.db_path != ":memory:":
                db_dir = os.path.dirname(os.path.abspath(self.db_path))
                os.makedirs(db_dir, exist_ok=True)

            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()

    def _create_tables(self):
        """Create historical_requests schema and search indexes."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_requests (
                request_id TEXT PRIMARY KEY,
                receipt_id TEXT UNIQUE,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                execution_path TEXT NOT NULL,
                route TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                query_preview TEXT,
                execution_time_ms REAL NOT NULL,
                inference_latency_ms REAL,
                latency_provenance TEXT DEFAULT 'MEASURED',
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                tokens_provenance TEXT,
                cost_usd REAL,
                cost_provenance TEXT,
                is_zero_external_api_charge INTEGER NOT NULL DEFAULT 0,
                energy_joules REAL,
                energy_kwh REAL,
                energy_scope TEXT,
                energy_provenance TEXT,
                is_energy_measured INTEGER NOT NULL DEFAULT 0,
                is_energy_estimated INTEGER NOT NULL DEFAULT 0,
                carbon_gco2e REAL,
                carbon_provenance TEXT,
                grid_intensity_gco2e_per_kwh REAL,
                grid_source TEXT,
                water_liters REAL,
                water_provenance TEXT,
                water_accounting_scope TEXT,
                water_reason_unavailable TEXT,
                environmental_source_id TEXT,
                model_calls_avoided INTEGER DEFAULT 0,
                tokens_avoided INTEGER,
                selected_candidate TEXT,
                quality_threshold_met INTEGER DEFAULT 1,
                is_pareto_optimal INTEGER DEFAULT 0,
                fallback_applied INTEGER DEFAULT 0,
                fallback_reason TEXT,
                receipt_json TEXT NOT NULL,
                telemetry_json TEXT
            );
        """)

        # Performance indexes for dashboard filtering and aggregation
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_timestamp ON historical_requests(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_execution_path ON historical_requests(execution_path);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_status ON historical_requests(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_provider ON historical_requests(provider);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_route ON historical_requests(route);")
        self._conn.commit()

    def save_record(
        self,
        telemetry: TelemetryRecord,
        receipt: EcoReceipt,
        query_preview: Optional[str] = None
    ) -> bool:
        """
        Persist a completed request and its Eco Receipt into SQLite.
        Handles duplicates via INSERT OR REPLACE to guarantee idempotence.
        Safely truncates query previews to avoid storing sensitive inputs.
        """
        try:
            # Query preview length constraint
            clean_preview = None
            if query_preview:
                max_len = getattr(settings, "HISTORICAL_MAX_QUERY_PREVIEW_LEN", 120)
                clean_preview = query_preview[:max_len].strip()
                receipt.query_preview = clean_preview
            elif receipt.query_preview:
                max_len = getattr(settings, "HISTORICAL_MAX_QUERY_PREVIEW_LEN", 120)
                clean_preview = receipt.query_preview[:max_len].strip()
                receipt.query_preview = clean_preview

            receipt_dict = receipt.model_dump()
            receipt_json = json.dumps(receipt_dict, default=str)
            telemetry_dict = telemetry.model_dump()
            telemetry_json = json.dumps(telemetry_dict, default=str)

            # Extract fields
            req_id = receipt.request_id
            rcpt_id = receipt.receipt_id
            ts = receipt.timestamp
            status = receipt.status.upper()
            exec_path = receipt.execution_path.value if hasattr(receipt.execution_path, "value") else str(receipt.execution_path)
            route = receipt.route
            provider = receipt.provider
            model = receipt.model

            exec_time_ms = receipt.execution_time_ms
            inf_latency_ms = receipt.inference_latency_ms
            lat_prov = receipt.latency_provenance.value if hasattr(receipt.latency_provenance, "value") else str(receipt.latency_provenance)

            p_tok = receipt.tokens.input_tokens
            c_tok = receipt.tokens.output_tokens
            t_tok = receipt.tokens.total_tokens
            tok_prov = receipt.tokens.provenance.value if hasattr(receipt.tokens.provenance, "value") else str(receipt.tokens.provenance)

            cost_val = receipt.cost.value_usd
            cost_prov = receipt.cost.provenance.value if hasattr(receipt.cost.provenance, "value") else str(receipt.cost.provenance)
            is_zero_cost = 1 if receipt.cost.is_zero_external_api_charge else 0

            energy_j = receipt.environment.energy.value_joules
            energy_kwh = receipt.environment.energy.value_kwh
            energy_scope = receipt.environment.energy.scope.value if hasattr(receipt.environment.energy.scope, "value") else str(receipt.environment.energy.scope)
            energy_prov = receipt.environment.energy.provenance.value if hasattr(receipt.environment.energy.provenance, "value") else str(receipt.environment.energy.provenance)
            is_energy_meas = 1 if receipt.environment.energy.is_measured else 0
            is_energy_est = 1 if receipt.environment.energy.is_estimated else 0

            carbon_g = receipt.environment.carbon.value_gco2e
            carbon_prov = receipt.environment.carbon.provenance.value if hasattr(receipt.environment.carbon.provenance, "value") else str(receipt.environment.carbon.provenance)
            grid_int = receipt.environment.carbon.grid_intensity_gco2e_per_kwh
            grid_src = receipt.environment.carbon.grid_source

            water_l = receipt.environment.water.value_liters
            water_prov = receipt.environment.water.provenance.value if hasattr(receipt.environment.water.provenance, "value") else str(receipt.environment.water.provenance)
            water_scope = receipt.environment.water.accounting_scope
            water_unav = receipt.environment.water.reason_unavailable
            env_source_id = receipt.environment.source_id

            avoided_calls = receipt.avoidance.model_calls_avoided if receipt.avoidance else 0
            avoided_tokens = receipt.avoidance.tokens_avoided if receipt.avoidance else None

            selected_cand = receipt.optimizer.selected_candidate if receipt.optimizer else route
            q_met = 1 if (receipt.optimizer and receipt.optimizer.quality_threshold_met) else 1
            is_pareto = 1 if (receipt.optimizer and selected_cand in receipt.optimizer.pareto_frontier) else 0
            fallback_app = 1 if (receipt.optimizer and receipt.optimizer.fallback_applied) else 0
            fallback_rsn = receipt.optimizer.fallback_reason if receipt.optimizer else None

            with self._lock:
                cursor = self._conn.cursor()
                cursor.execute("""
                    INSERT INTO historical_requests (
                        request_id, receipt_id, timestamp, status, execution_path,
                        route, provider, model, query_preview, execution_time_ms,
                        inference_latency_ms, latency_provenance, prompt_tokens,
                        completion_tokens, total_tokens, tokens_provenance,
                        cost_usd, cost_provenance, is_zero_external_api_charge,
                        energy_joules, energy_kwh, energy_scope, energy_provenance,
                        is_energy_measured, is_energy_estimated, carbon_gco2e,
                        carbon_provenance, grid_intensity_gco2e_per_kwh, grid_source,
                        water_liters, water_provenance, water_accounting_scope,
                        water_reason_unavailable, environmental_source_id,
                        model_calls_avoided, tokens_avoided, selected_candidate,
                        quality_threshold_met, is_pareto_optimal, fallback_applied,
                        fallback_reason, receipt_json, telemetry_json
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?
                    )
                    ON CONFLICT(request_id) DO UPDATE SET
                        receipt_id=excluded.receipt_id,
                        timestamp=excluded.timestamp,
                        status=excluded.status,
                        execution_path=excluded.execution_path,
                        route=excluded.route,
                        provider=excluded.provider,
                        model=excluded.model,
                        query_preview=excluded.query_preview,
                        execution_time_ms=excluded.execution_time_ms,
                        inference_latency_ms=excluded.inference_latency_ms,
                        prompt_tokens=excluded.prompt_tokens,
                        completion_tokens=excluded.completion_tokens,
                        total_tokens=excluded.total_tokens,
                        tokens_provenance=excluded.tokens_provenance,
                        cost_usd=excluded.cost_usd,
                        cost_provenance=excluded.cost_provenance,
                        is_zero_external_api_charge=excluded.is_zero_external_api_charge,
                        energy_joules=excluded.energy_joules,
                        energy_kwh=excluded.energy_kwh,
                        energy_scope=excluded.energy_scope,
                        energy_provenance=excluded.energy_provenance,
                        is_energy_measured=excluded.is_energy_measured,
                        is_energy_estimated=excluded.is_energy_estimated,
                        carbon_gco2e=excluded.carbon_gco2e,
                        carbon_provenance=excluded.carbon_provenance,
                        grid_intensity_gco2e_per_kwh=excluded.grid_intensity_gco2e_per_kwh,
                        grid_source=excluded.grid_source,
                        water_liters=excluded.water_liters,
                        water_provenance=excluded.water_provenance,
                        water_accounting_scope=excluded.water_accounting_scope,
                        water_reason_unavailable=excluded.water_reason_unavailable,
                        environmental_source_id=excluded.environmental_source_id,
                        model_calls_avoided=excluded.model_calls_avoided,
                        tokens_avoided=excluded.tokens_avoided,
                        selected_candidate=excluded.selected_candidate,
                        quality_threshold_met=excluded.quality_threshold_met,
                        is_pareto_optimal=excluded.is_pareto_optimal,
                        fallback_applied=excluded.fallback_applied,
                        fallback_reason=excluded.fallback_reason,
                        receipt_json=excluded.receipt_json,
                        telemetry_json=excluded.telemetry_json;
                """, (
                    req_id, rcpt_id, ts, status, exec_path,
                    route, provider, model, clean_preview, exec_time_ms,
                    inf_latency_ms, lat_prov, p_tok,
                    c_tok, t_tok, tok_prov,
                    cost_val, cost_prov, is_zero_cost,
                    energy_j, energy_kwh, energy_scope, energy_prov,
                    is_energy_meas, is_energy_est, carbon_g,
                    carbon_prov, grid_int, grid_src,
                    water_l, water_prov, water_scope,
                    water_unav, env_source_id,
                    avoided_calls, avoided_tokens, selected_cand,
                    q_met, is_pareto, fallback_app,
                    fallback_rsn, receipt_json, telemetry_json
                ))
                self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to persist historical request {telemetry.request_id}: {e}", exc_info=True)
            return False

    def get_receipt(self, identifier: str) -> Optional[EcoReceipt]:
        """
        Retrieve an EcoReceipt by request_id OR receipt_id.
        Returns parsed Pydantic EcoReceipt model or None.
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT receipt_json FROM historical_requests WHERE request_id = ? OR receipt_id = ? LIMIT 1;",
                (identifier, identifier)
            )
            row = cursor.fetchone()
            if not row:
                return None
            try:
                data = json.loads(row["receipt_json"])
                return EcoReceipt(**data)
            except Exception as e:
                logger.error(f"Failed to deserialize receipt {identifier}: {e}")
                return None

    def get_telemetry(self, request_id: str) -> Optional[TelemetryRecord]:
        """Retrieve original TelemetryRecord by request_id."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT telemetry_json FROM historical_requests WHERE request_id = ? LIMIT 1;",
                (request_id,)
            )
            row = cursor.fetchone()
            if not row or not row["telemetry_json"]:
                return None
            try:
                data = json.loads(row["telemetry_json"])
                return TelemetryRecord(**data)
            except Exception as e:
                logger.error(f"Failed to deserialize telemetry {request_id}: {e}")
                return None

    def list_receipts(
        self,
        page: int = 1,
        page_size: int = 25,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        execution_path: Optional[str] = None,
        status: Optional[str] = None,
        route: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve paginated list of receipt summary records with configurable filters.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, getattr(settings, "HISTORICAL_MAX_PAGE_SIZE", 100)))
        offset = (page - 1) * page_size

        where_clauses = []
        params = []

        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("timestamp <= ?")
            params.append(end_date)
        if execution_path:
            where_clauses.append("execution_path = ?")
            params.append(execution_path)
        if status:
            where_clauses.append("status = ?")
            params.append(status.upper())
        if route:
            where_clauses.append("route = ?")
            params.append(route)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(f"SELECT COUNT(*) as total FROM historical_requests{where_sql};", params)
            total_count = cursor.fetchone()["total"]

            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

            query = f"""
                SELECT
                    request_id, receipt_id, timestamp, status, execution_path,
                    route, provider, model, query_preview, execution_time_ms,
                    inference_latency_ms, total_tokens, cost_usd, is_zero_external_api_charge,
                    energy_joules, is_energy_measured, is_energy_estimated, carbon_gco2e
                FROM historical_requests
                {where_sql}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?;
            """
            cursor.execute(query, params + [page_size, offset])
            rows = cursor.fetchall()

            items = []
            for r in rows:
                items.append({
                    "request_id": r["request_id"],
                    "receipt_id": r["receipt_id"],
                    "timestamp": r["timestamp"],
                    "status": r["status"],
                    "execution_path": r["execution_path"],
                    "route": r["route"],
                    "provider": r["provider"],
                    "model": r["model"],
                    "query_preview": r["query_preview"],
                    "execution_time_ms": round(r["execution_time_ms"], 2),
                    "inference_latency_ms": round(r["inference_latency_ms"], 2) if r["inference_latency_ms"] is not None else None,
                    "total_tokens": r["total_tokens"],
                    "cost_usd": round(r["cost_usd"], 8) if r["cost_usd"] is not None else None,
                    "is_zero_external_api_charge": bool(r["is_zero_external_api_charge"]),
                    "energy_joules": round(r["energy_joules"], 4) if r["energy_joules"] is not None else None,
                    "is_energy_measured": bool(r["is_energy_measured"]),
                    "is_energy_estimated": bool(r["is_energy_estimated"]),
                    "carbon_gco2e": round(r["carbon_gco2e"], 6) if r["carbon_gco2e"] is not None else None
                })

            return {
                "items": items,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

    def get_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Produce high-level KPI and performance summary across historical requests.
        Strictly respects null semantics for missing metrics.
        """
        where_clauses = []
        params = []
        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("timestamp <= ?")
            params.append(end_date)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self._lock:
            cursor = self._conn.cursor()

            # Aggregate basic counts and execution latencies
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_requests,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_requests,
                    SUM(CASE WHEN status = 'PARTIAL' THEN 1 ELSE 0 END) as partial_requests,
                    SUM(execution_time_ms) as total_execution_time_ms,
                    AVG(execution_time_ms) as avg_execution_time_ms,
                    SUM(prompt_tokens) as total_prompt_tokens,
                    SUM(completion_tokens) as total_completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost_usd) as total_external_api_cost_usd,
                    SUM(CASE WHEN is_zero_external_api_charge = 1 THEN 1 ELSE 0 END) as zero_external_api_cost_count,
                    SUM(CASE WHEN cost_usd > 0 THEN 1 ELSE 0 END) as billed_external_api_cost_count,
                    SUM(model_calls_avoided) as total_model_calls_avoided,
                    SUM(tokens_avoided) as total_tokens_avoided
                FROM historical_requests
                {where_sql};
            """, params)
            base_agg = cursor.fetchone()

            total_reqs = base_agg["total_requests"] or 0
            succ_reqs = base_agg["successful_requests"] or 0
            fail_reqs = base_agg["failed_requests"] or 0
            part_reqs = base_agg["partial_requests"] or 0
            success_rate = (succ_reqs / total_reqs * 100.0) if total_reqs > 0 else 0.0

            # Routes breakdown
            cursor.execute(f"""
                SELECT route, COUNT(*) as cnt
                FROM historical_requests
                {where_sql}
                GROUP BY route
                ORDER BY cnt DESC;
            """, params)
            routes_breakdown = {row["route"]: row["cnt"] for row in cursor.fetchall()}

            # Providers breakdown
            cursor.execute(f"""
                SELECT provider, COUNT(*) as cnt
                FROM historical_requests
                {where_sql}
                GROUP BY provider
                ORDER BY cnt DESC;
            """, params)
            providers_breakdown = {row["provider"]: row["cnt"] for row in cursor.fetchall()}

            # Execution paths breakdown
            cursor.execute(f"""
                SELECT execution_path, COUNT(*) as cnt
                FROM historical_requests
                {where_sql}
                GROUP BY execution_path
                ORDER BY cnt DESC;
            """, params)
            execution_paths_breakdown = {row["execution_path"]: row["cnt"] for row in cursor.fetchall()}

            return {
                "total_requests": total_reqs,
                "successful_requests": succ_reqs,
                "failed_requests": fail_reqs,
                "partial_requests": part_reqs,
                "success_rate_percent": round(success_rate, 2),
                "total_execution_time_ms": round(base_agg["total_execution_time_ms"] or 0.0, 2),
                "avg_latency_ms": round(base_agg["avg_execution_time_ms"] or 0.0, 2),
                "total_prompt_tokens": base_agg["total_prompt_tokens"] or 0,
                "total_completion_tokens": base_agg["total_completion_tokens"] or 0,
                "total_tokens": base_agg["total_tokens"] or 0,
                "total_external_api_cost_usd": round(base_agg["total_external_api_cost_usd"] or 0.0, 8),
                "zero_external_api_cost_count": base_agg["zero_external_api_cost_count"] or 0,
                "billed_external_api_cost_count": base_agg["billed_external_api_cost_count"] or 0,
                "total_model_calls_avoided": base_agg["total_model_calls_avoided"] or 0,
                "total_tokens_avoided": base_agg["total_tokens_avoided"] or 0,
                "routes_breakdown": routes_breakdown,
                "providers_breakdown": providers_breakdown,
                "execution_paths_breakdown": execution_paths_breakdown,
                "filter_start_date": start_date,
                "filter_end_date": end_date
            }

    def get_environmental_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate environmental metrics with strict data integrity.
        Separates physical measurements from validated estimation models and unmeasured nulls.
        """
        where_clauses = []
        params = []
        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("timestamp <= ?")
            params.append(end_date)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self._lock:
            cursor = self._conn.cursor()

            # Energy and carbon aggregations
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN is_energy_measured = 1 THEN 1 ELSE 0 END) as records_with_measured_energy,
                    SUM(CASE WHEN is_energy_estimated = 1 THEN 1 ELSE 0 END) as records_with_estimated_energy,
                    SUM(CASE WHEN energy_joules IS NULL THEN 1 ELSE 0 END) as records_with_unavailable_energy,
                    SUM(CASE WHEN is_energy_measured = 1 THEN energy_joules ELSE 0.0 END) as measured_energy_joules,
                    SUM(CASE WHEN is_energy_estimated = 1 THEN energy_joules ELSE 0.0 END) as estimated_energy_joules,
                    SUM(CASE WHEN carbon_gco2e IS NOT NULL THEN 1 ELSE 0 END) as records_with_carbon,
                    SUM(CASE WHEN carbon_gco2e IS NULL THEN 1 ELSE 0 END) as records_with_unavailable_carbon,
                    SUM(CASE WHEN is_energy_measured = 1 AND carbon_gco2e IS NOT NULL THEN carbon_gco2e ELSE 0.0 END) as carbon_from_measured_energy_gco2e,
                    SUM(CASE WHEN is_energy_estimated = 1 AND carbon_gco2e IS NOT NULL THEN carbon_gco2e ELSE 0.0 END) as carbon_from_estimated_energy_gco2e,
                    SUM(CASE WHEN carbon_gco2e IS NOT NULL THEN carbon_gco2e ELSE 0.0 END) as total_carbon_gco2e,
                    SUM(CASE WHEN water_liters IS NOT NULL THEN 1 ELSE 0 END) as records_with_water,
                    SUM(water_liters) as total_water_liters
                FROM historical_requests
                {where_sql};
            """, params)
            agg = cursor.fetchone()

            # Measurement scopes breakdown
            cursor.execute(f"""
                SELECT energy_scope, COUNT(*) as cnt
                FROM historical_requests
                {where_sql}
                GROUP BY energy_scope
                ORDER BY cnt DESC;
            """, params)
            scopes_breakdown = {row["energy_scope"] or "UNKNOWN": row["cnt"] for row in cursor.fetchall()}

            # Grid sources breakdown
            cursor.execute(f"""
                SELECT grid_source, COUNT(*) as cnt
                FROM historical_requests
                {where_sql}
                WHERE grid_source IS NOT NULL
                GROUP BY grid_source
                ORDER BY cnt DESC;
            """, params)
            grid_sources_breakdown = {row["grid_source"]: row["cnt"] for row in cursor.fetchall()}

            # Environmental source IDs breakdown
            cursor.execute(f"""
                SELECT environmental_source_id, COUNT(*) as cnt
                FROM historical_requests
                {where_sql}
                WHERE environmental_source_id IS NOT NULL
                GROUP BY environmental_source_id
                ORDER BY cnt DESC;
            """, params)
            env_sources_breakdown = {row["environmental_source_id"]: row["cnt"] for row in cursor.fetchall()}

            measured_j = agg["measured_energy_joules"] or 0.0
            estimated_j = agg["estimated_energy_joules"] or 0.0
            measured_kwh = measured_j / 3_600_000.0
            estimated_kwh = estimated_j / 3_600_000.0

            return {
                "total_requests": agg["total_requests"] or 0,
                "records_with_measured_energy": agg["records_with_measured_energy"] or 0,
                "records_with_estimated_energy": agg["records_with_estimated_energy"] or 0,
                "records_with_unavailable_energy": agg["records_with_unavailable_energy"] or 0,
                "measured_energy_joules": round(measured_j, 4),
                "measured_energy_kwh": round(measured_kwh, 8),
                "estimated_energy_joules": round(estimated_j, 4),
                "estimated_energy_kwh": round(estimated_kwh, 8),
                "records_with_carbon": agg["records_with_carbon"] or 0,
                "records_with_unavailable_carbon": agg["records_with_unavailable_carbon"] or 0,
                "carbon_from_measured_energy_gco2e": round(agg["carbon_from_measured_energy_gco2e"] or 0.0, 6),
                "carbon_from_estimated_energy_gco2e": round(agg["carbon_from_estimated_energy_gco2e"] or 0.0, 6),
                "total_carbon_gco2e": round(agg["total_carbon_gco2e"] or 0.0, 6),
                "records_with_water": agg["records_with_water"] or 0,
                "total_water_liters": round(agg["total_water_liters"] or 0.0, 6) if agg["total_water_liters"] is not None else None,
                "water_disclosure": "Direct physical water consumption is reported as UNAVAILABLE in the absence of verified facility WUE telemetry.",
                "measurement_scopes_breakdown": scopes_breakdown,
                "grid_sources_breakdown": grid_sources_breakdown,
                "environmental_sources_breakdown": env_sources_breakdown,
                "scope_boundary_notice": "Measured physical energy covers active GPU inference windows only (excluding idle baseline and host CPUs unless instrumented).",
                "filter_start_date": start_date,
                "filter_end_date": end_date
            }

    def get_routes_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Produce routing optimizer evaluation metrics, Pareto optimality rates, and fallback audit.
        """
        where_clauses = []
        params = []
        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("timestamp <= ?")
            params.append(end_date)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self._lock:
            cursor = self._conn.cursor()

            # Global optimizer counters
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(is_pareto_optimal) as pareto_optimal_count,
                    SUM(quality_threshold_met) as quality_met_count,
                    SUM(fallback_applied) as fallback_count
                FROM historical_requests
                {where_sql};
            """, params)
            global_opt = cursor.fetchone()
            tot = global_opt["total_requests"] or 0
            pareto_cnt = global_opt["pareto_optimal_count"] or 0
            q_met_cnt = global_opt["quality_met_count"] or 0
            fb_cnt = global_opt["fallback_count"] or 0

            pareto_rate = (pareto_cnt / tot * 100.0) if tot > 0 else 0.0
            q_met_rate = (q_met_cnt / tot * 100.0) if tot > 0 else 100.0
            fb_rate = (fb_cnt / tot * 100.0) if tot > 0 else 0.0

            # Route specific metrics
            cursor.execute(f"""
                SELECT
                    route,
                    COUNT(*) as request_count,
                    AVG(execution_time_ms) as avg_latency_ms,
                    AVG(inference_latency_ms) as avg_inference_latency_ms,
                    SUM(is_pareto_optimal) as pareto_count,
                    SUM(fallback_applied) as fallback_count,
                    SUM(model_calls_avoided) as avoided_calls,
                    SUM(cost_usd) as total_cost_usd,
                    SUM(energy_joules) as total_energy_joules
                FROM historical_requests
                {where_sql}
                GROUP BY route
                ORDER BY request_count DESC;
            """, params)
            route_stats = []
            for r in cursor.fetchall():
                route_stats.append({
                    "route": r["route"],
                    "request_count": r["request_count"],
                    "avg_latency_ms": round(r["avg_latency_ms"] or 0.0, 2),
                    "avg_inference_latency_ms": round(r["avg_inference_latency_ms"] or 0.0, 2) if r["avg_inference_latency_ms"] is not None else None,
                    "pareto_count": r["pareto_count"] or 0,
                    "fallback_count": r["fallback_count"] or 0,
                    "avoided_calls": r["avoided_calls"] or 0,
                    "total_cost_usd": round(r["total_cost_usd"] or 0.0, 8),
                    "total_energy_joules": round(r["total_energy_joules"] or 0.0, 4) if r["total_energy_joules"] is not None else None
                })

            # Fallback reasons breakdown
            cursor.execute(f"""
                SELECT fallback_reason, COUNT(*) as cnt
                FROM historical_requests
                {where_sql}
                WHERE fallback_applied = 1 AND fallback_reason IS NOT NULL
                GROUP BY fallback_reason
                ORDER BY cnt DESC;
            """, params)
            fallback_reasons = {row["fallback_reason"]: row["cnt"] for row in cursor.fetchall()}

            return {
                "total_evaluated_requests": tot,
                "pareto_optimal_selection_rate_percent": round(pareto_rate, 2),
                "quality_threshold_compliance_percent": round(q_met_rate, 2),
                "fallback_engagement_rate_percent": round(fb_rate, 2),
                "route_statistics": route_stats,
                "fallback_reasons_breakdown": fallback_reasons,
                "filter_start_date": start_date,
                "filter_end_date": end_date
            }

    def get_timeseries(
        self,
        interval: str = "hour",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Produce bucketed timeseries metrics for activity, latency, tokens, energy, and avoidance.
        Interval can be 'hour' (YYYY-MM-DDTHH) or 'day' (YYYY-MM-DD).
        """
        where_clauses = []
        params = []
        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("timestamp <= ?")
            params.append(end_date)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Format ISO timestamp string
        bucket_len = 13 if interval == "hour" else 10

        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(f"""
                SELECT
                    SUBSTR(timestamp, 1, {bucket_len}) as time_bucket,
                    COUNT(*) as request_count,
                    AVG(execution_time_ms) as avg_latency_ms,
                    SUM(total_tokens) as total_tokens,
                    SUM(CASE WHEN is_energy_measured = 1 THEN energy_joules ELSE 0.0 END) as measured_energy_joules,
                    SUM(CASE WHEN is_energy_estimated = 1 THEN energy_joules ELSE 0.0 END) as estimated_energy_joules,
                    SUM(carbon_gco2e) as total_carbon_gco2e,
                    SUM(cost_usd) as total_cost_usd,
                    SUM(model_calls_avoided) as model_calls_avoided
                FROM historical_requests
                {where_sql}
                GROUP BY time_bucket
                ORDER BY time_bucket ASC;
            """, params)

            series = []
            for r in cursor.fetchall():
                series.append({
                    "time_bucket": r["time_bucket"],
                    "request_count": r["request_count"],
                    "avg_latency_ms": round(r["avg_latency_ms"] or 0.0, 2),
                    "total_tokens": r["total_tokens"] or 0,
                    "measured_energy_joules": round(r["measured_energy_joules"] or 0.0, 4),
                    "estimated_energy_joules": round(r["estimated_energy_joules"] or 0.0, 4),
                    "total_carbon_gco2e": round(r["total_carbon_gco2e"] or 0.0, 6),
                    "total_cost_usd": round(r["total_cost_usd"] or 0.0, 8),
                    "model_calls_avoided": r["model_calls_avoided"] or 0
                })

            return series

    def clear(self):
        """Purge all records from SQLite store (primarily for test teardown)."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM historical_requests;")
            self._conn.commit()

    def count(self) -> int:
        """Return total row count in historical_requests table."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM historical_requests;")
            return cursor.fetchone()["cnt"]

# Global singleton historical store
historical_store = HistoricalStore()
