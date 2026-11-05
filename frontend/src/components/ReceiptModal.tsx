import React, { useState } from 'react';
import { 
  X, 
  FileText, 
  Zap, 
  Cpu, 
  Leaf, 
  ShieldCheck, 
  Clock, 
  Code, 
  Layers, 
  Info, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';
import type { EcoReceipt } from '../types.ts';

interface ReceiptModalProps {
  receipt: EcoReceipt | null;
  onClose: () => void;
}

export const ReceiptModal: React.FC<ReceiptModalProps> = ({ receipt, onClose }) => {
  const [showRawJson, setShowRawJson] = useState(false);

  if (!receipt) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden my-8 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Eco Receipt</h3>
                <span className={`text-[11px] px-2 py-0.5 rounded-full font-semibold border ${
                  receipt.status === 'SUCCESS' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                  receipt.status === 'PARTIAL' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
                  'bg-red-500/10 text-red-400 border-red-500/30'
                }`}>
                  {receipt.status}
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                  {receipt.execution_path}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Receipt ID: {receipt.receipt_id} • Request ID: {receipt.request_id}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors flex items-center gap-1.5 border border-slate-700"
            >
              <Code className="w-3.5 h-3.5" />
              <span>{showRawJson ? 'Formatted View' : 'Raw JSON'}</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-200">
          {showRawJson ? (
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-emerald-400 overflow-x-auto">
              <pre>{JSON.stringify(receipt, null, 2)}</pre>
            </div>
          ) : (
            <>
              {/* Executive Explainability Summary */}
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4" />
                  Execution Rationale & Explainability
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {receipt.explainability.selection_summary}
                </p>
                <p className="text-[11px] text-slate-400 leading-relaxed border-t border-slate-800/80 pt-2">
                  <strong className="text-slate-300">Measurement Provenance:</strong> {receipt.explainability.measurement_vs_estimation}
                </p>
              </div>

              {/* Primary Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" /> Latency
                  </span>
                  <div className="text-base font-bold text-white mt-1">
                    {receipt.execution_time_ms.toFixed(2)} <span className="text-xs font-normal text-slate-400">ms</span>
                  </div>
                  <span className="text-[10px] text-slate-500 uppercase">{receipt.latency_provenance}</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <Zap className="w-3.5 h-3.5 text-amber-400" /> Tokens
                  </span>
                  <div className="text-base font-bold text-white mt-1">
                    {receipt.tokens.total_tokens !== null ? (
                      receipt.tokens.total_tokens
                    ) : (
                      <span className="text-slate-500 font-normal">Unmeasured</span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 uppercase">{receipt.tokens.provenance}</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <Cpu className="w-3.5 h-3.5 text-purple-400" /> External API Cost
                  </span>
                  <div className="text-base font-bold text-white mt-1">
                    {receipt.cost.value_usd !== null ? (
                      `$${receipt.cost.value_usd.toFixed(6)}`
                    ) : (
                      <span className="text-slate-500 font-normal">N/A</span>
                    )}
                  </div>
                  <span className="text-[10px] text-emerald-400">
                    {receipt.cost.is_zero_external_api_charge ? '$0 API Charge' : receipt.cost.provenance}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <Leaf className="w-3.5 h-3.5 text-emerald-400" /> Route & Provider
                  </span>
                  <div className="text-xs font-semibold text-white mt-1 truncate">
                    {receipt.route}
                  </div>
                  <span className="text-[10px] text-slate-400 truncate block">
                    {receipt.provider} {receipt.model ? `(${receipt.model})` : ''}
                  </span>
                </div>
              </div>

              {/* Environmental Breakdown Details */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Leaf className="w-3.5 h-3.5 text-emerald-400" />
                  Environmental Footprint & Scope Accounting
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {/* Energy */}
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300">Operational Energy</span>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                        receipt.environment.energy.is_measured ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        receipt.environment.energy.is_estimated ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {receipt.environment.energy.provenance}
                      </span>
                    </div>
                    <div className="text-lg font-bold text-white">
                      {receipt.environment.energy.value_joules !== null ? (
                        <>
                          {receipt.environment.energy.value_joules.toFixed(4)} <span className="text-xs font-normal text-slate-400">J</span>
                          <span className="text-xs text-slate-500 font-normal ml-2">
                            ({(receipt.environment.energy.value_kwh ?? 0).toExponential(3)} kWh)
                          </span>
                        </>
                      ) : (
                        <span className="text-sm font-normal text-slate-500">Unavailable</span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Scope: {receipt.environment.energy.scope}
                    </p>
                    {receipt.environment.energy.scope_disclaimer && (
                      <p className="text-[10px] text-slate-500 italic">
                        {receipt.environment.energy.scope_disclaimer}
                      </p>
                    )}
                  </div>

                  {/* Carbon */}
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300">Operational Carbon</span>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                        receipt.environment.carbon.provenance === 'ESTIMATED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {receipt.environment.carbon.provenance}
                      </span>
                    </div>
                    <div className="text-lg font-bold text-white">
                      {receipt.environment.carbon.value_gco2e !== null ? (
                        <>
                          {receipt.environment.carbon.value_gco2e.toFixed(6)} <span className="text-xs font-normal text-slate-400">gCO2e</span>
                        </>
                      ) : (
                        <span className="text-sm font-normal text-slate-500">Unavailable</span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Grid factor: {receipt.environment.carbon.grid_intensity_gco2e_per_kwh ? `${receipt.environment.carbon.grid_intensity_gco2e_per_kwh} gCO2e/kWh` : 'N/A'}
                    </p>
                    {receipt.environment.carbon.grid_source && (
                      <p className="text-[10px] text-slate-500">
                        Source: {receipt.environment.carbon.grid_source}
                      </p>
                    )}
                  </div>

                  {/* Water */}
                  <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300">Water Consumption</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                        {receipt.environment.water.provenance}
                      </span>
                    </div>
                    <div className="text-lg font-bold text-slate-500">
                      {receipt.environment.water.value_liters !== null ? (
                        `${receipt.environment.water.value_liters} L`
                      ) : (
                        <span className="text-sm font-normal text-slate-500">Unavailable</span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 leading-tight">
                      {receipt.environment.water.reason_unavailable}
                    </p>
                  </div>
                </div>
              </div>

              {/* Avoidance & Optimizer Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Avoidance Summary */}
                {receipt.avoidance && (
                  <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
                    <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-teal-400" />
                      Operational Avoidance Facts
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <div>
                        <span className="text-slate-400">Calls Avoided: </span>
                        <strong className="text-emerald-400">{receipt.avoidance.model_calls_avoided}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400">Baseline Route: </span>
                        <span className="text-slate-300 font-mono">{receipt.avoidance.baseline_route}</span>
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      {receipt.avoidance.reasoning}
                    </p>
                    {receipt.avoidance.savings_notice && (
                      <p className="text-[10px] text-amber-400/90 italic pt-1 border-t border-slate-800">
                        Notice: {receipt.avoidance.savings_notice}
                      </p>
                    )}
                  </div>
                )}

                {/* Optimizer Evaluation Summary */}
                {receipt.optimizer && (
                  <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
                    <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Cpu className="w-3.5 h-3.5 text-purple-400" />
                        Multi-Objective Optimizer (Phase 6)
                      </span>
                      {receipt.optimizer.fallback_applied ? (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Fallback
                        </span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Optimal
                        </span>
                      )}
                    </div>
                    <div className="text-xs space-y-1">
                      <div>
                        <span className="text-slate-400">Selected Candidate: </span>
                        <strong className="text-white">{receipt.optimizer.selected_candidate}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400">Quality Threshold Enforced: </span>
                        <span className="text-slate-300 font-mono">{receipt.optimizer.quality_threshold_required}</span>
                        <span className="text-emerald-400 text-[11px] ml-1.5">
                          {receipt.optimizer.quality_threshold_met ? '(Satisfied)' : '(Not Met)'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Pareto Frontier: </span>
                        <span className="text-slate-300 font-mono">{receipt.optimizer.pareto_frontier.join(', ') || 'None'}</span>
                      </div>
                    </div>
                    {receipt.optimizer.routing_rationale && (
                      <p className="text-[11px] text-slate-400 border-t border-slate-800 pt-1.5">
                        {receipt.optimizer.routing_rationale}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Integrity Disclaimers */}
              <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
                <div className="flex items-center gap-1 text-slate-300 font-semibold">
                  <Info className="w-3.5 h-3.5 text-slate-400" /> Caveats & Uncertainty Notice
                </div>
                <p>{receipt.explainability.caveats_and_uncertainty}</p>
                {receipt.explainability.unavailable_metrics_rationale && (
                  <p className="text-slate-500">{receipt.explainability.unavailable_metrics_rationale}</p>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <span className="font-mono">
            EcoMind Sustainability Assurance • Timestamp: {new Date(receipt.timestamp).toLocaleString()}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs transition-colors"
          >
            Close Receipt
          </button>
        </div>
      </div>
    </div>
  );
};
