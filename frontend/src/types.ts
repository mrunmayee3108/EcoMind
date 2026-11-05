export interface TokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  is_estimated: boolean;
}

export interface ChatResponse {
  query: string;
  answer: string;
  route: string;
  model: string | null;
  provider: string;
  execution_time_ms: number;
  token_usage: TokenUsage | null;
  large_model_avoided: boolean;
  cache_status?: string;
  cache_similarity?: number | null;
  metadata?: Record<string, any>;
  telemetry?: Record<string, any>;
  eco_receipt?: EcoReceipt;
}

export interface ToolInfo {
  name: string;
  description: string;
  type: string;
  calls_llm: boolean;
}

export interface ModelProfile {
  model_id: string;
  provider: string;
  tier: string;
  context_window: number;
  description: string;
  is_local: boolean;
}

export interface CostMetric {
  value_usd: number | null;
  provenance: string;
  pricing_source: string | null;
  details: string | null;
  is_zero_external_api_charge: boolean;
}

export interface EnergyMetric {
  value_joules: number | null;
  value_kwh: number | null;
  unit: string;
  scope: string;
  provenance: string;
  is_measured: boolean;
  is_estimated: boolean;
  device_platform: string | null;
  scope_disclaimer: string;
}

export interface CarbonMetric {
  value_gco2e: number | null;
  unit: string;
  scope: string | null;
  provenance: string;
  grid_intensity_gco2e_per_kwh: number | null;
  grid_source: string | null;
  formula: string | null;
}

export interface WaterMetric {
  value_liters: number | null;
  unit: string;
  accounting_scope: string;
  provenance: string;
  reason_unavailable: string;
}

export interface EnvironmentalBreakdown {
  energy: EnergyMetric;
  carbon: CarbonMetric;
  water: WaterMetric;
  source_id: string | null;
  source_name: string | null;
  source_version: string | null;
  estimator_name: string | null;
  estimator_version: string | null;
  assumptions: string[];
  uncertainty_info: string | null;
  unavailable_reasons: Record<string, string>;
}

export interface CandidateScore {
  candidate: string;
  tier: string | null;
  eligible: boolean;
  ineligibility_reason: string | null;
  quality_score: number;
  quality_threshold_met: boolean;
  estimated_latency_ms: number | null;
  estimated_cost_usd: number | null;
  estimated_energy_joules: number | null;
  normalized_quality: number;
  normalized_latency: number;
  normalized_cost: number;
  normalized_environment: number;
  pareto_rank: number | null;
  is_pareto_optimal: boolean;
  composite_score: number | null;
  missing_objectives: string[];
}

export interface OptimizerSummary {
  decision_id: string | null;
  selected_candidate: string;
  selected_tier: string | null;
  routing_rationale: string;
  quality_threshold_required: number;
  quality_threshold_met: boolean;
  pareto_frontier: string[];
  active_weights: Record<string, number>;
  candidate_scores: CandidateScore[];
  fallback_applied: boolean;
  fallback_reason: string | null;
}

export interface AvoidanceSummary {
  model_calls_avoided: number;
  tokens_avoided: number | null;
  baseline_route: string;
  reasoning: string;
  defensible_savings_reported: boolean;
  savings_notice: string;
}

export interface ReceiptExplainability {
  selection_summary: string;
  measurement_vs_estimation: string;
  unavailable_metrics_rationale: string;
  caveats_and_uncertainty: string;
}

export interface EcoReceipt {
  receipt_id: string;
  request_id: string;
  timestamp: string;
  status: string;
  execution_path: string;
  route: string;
  provider: string;
  model: string | null;
  query_preview: string | null;
  execution_time_ms: number;
  inference_latency_ms: number | null;
  latency_provenance: string;
  tokens: {
    input_tokens: number | null;
    output_tokens: number | null;
    total_tokens: number | null;
    provenance: string;
  };
  cost: CostMetric;
  environment: EnvironmentalBreakdown;
  avoidance?: AvoidanceSummary;
  optimizer?: OptimizerSummary;
  explainability: ReceiptExplainability;
}

export interface DashboardSummaryResponse {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  partial_requests: number;
  success_rate_percent: number;
  total_execution_time_ms: number;
  avg_latency_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_external_api_cost_usd: number;
  zero_external_api_cost_count: number;
  billed_external_api_cost_count: number;
  total_model_calls_avoided: number;
  total_tokens_avoided: number;
  routes_breakdown: Record<string, number>;
  providers_breakdown: Record<string, number>;
  execution_paths_breakdown: Record<string, number>;
  filter_start_date: string | null;
  filter_end_date: string | null;
}

export interface DashboardEnvironmentResponse {
  total_requests: number;
  records_with_measured_energy: number;
  records_with_estimated_energy: number;
  records_with_unavailable_energy: number;
  measured_energy_joules: number;
  measured_energy_kwh: number;
  estimated_energy_joules: number;
  estimated_energy_kwh: number;
  records_with_carbon: number;
  records_with_unavailable_carbon: number;
  carbon_from_measured_energy_gco2e: number;
  carbon_from_estimated_energy_gco2e: number;
  total_carbon_gco2e: number;
  records_with_water: number;
  total_water_liters: number | null;
  water_disclosure: string;
  measurement_scopes_breakdown: Record<string, number>;
  grid_sources_breakdown: Record<string, number>;
  environmental_sources_breakdown: Record<string, number>;
  scope_boundary_notice: string;
  filter_start_date: string | null;
  filter_end_date: string | null;
}

export interface RouteStatItem {
  route: string;
  request_count: number;
  avg_latency_ms: number;
  avg_inference_latency_ms: number | null;
  pareto_count: number;
  fallback_count: number;
  avoided_calls: number;
  total_cost_usd: number;
  total_energy_joules: number | null;
}

export interface DashboardRoutesResponse {
  total_evaluated_requests: number;
  pareto_optimal_selection_rate_percent: number;
  quality_threshold_compliance_percent: number;
  fallback_engagement_rate_percent: number;
  route_statistics: RouteStatItem[];
  fallback_reasons_breakdown: Record<string, number>;
  filter_start_date: string | null;
  filter_end_date: string | null;
}

export interface TimeseriesPoint {
  time_bucket: string;
  request_count: number;
  avg_latency_ms: number;
  total_tokens: number;
  measured_energy_joules: number;
  estimated_energy_joules: number;
  total_carbon_gco2e: number;
  total_cost_usd: number;
  model_calls_avoided: number;
}

export interface ReceiptSummaryItem {
  request_id: string;
  receipt_id: string;
  timestamp: string;
  status: string;
  execution_path: string;
  route: string;
  provider: string;
  model: string | null;
  query_preview: string | null;
  execution_time_ms: number;
  inference_latency_ms: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  is_zero_external_api_charge: boolean;
  energy_joules: number | null;
  is_energy_measured: boolean;
  is_energy_estimated: boolean;
  carbon_gco2e: number | null;
}

export interface PaginatedReceiptsResponse {
  items: ReceiptSummaryItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

