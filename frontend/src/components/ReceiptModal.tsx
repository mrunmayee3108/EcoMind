import React, { useState, useEffect } from 'react';
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
  AlertTriangle,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Droplets,
  DollarSign
} from 'lucide-react';
import type { EcoReceipt } from '../types.ts';

interface ReceiptModalProps {
  receipt: EcoReceipt | null;
  onClose: () => void;
}

export const ReceiptModal: React.FC<ReceiptModalProps> = ({ receipt, onClose }) => {
  const [showRawJson, setShowRawJson] = useState(false);
  const [copied, setCopied] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!receipt) return null;

  const handleCopyJson = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(receipt, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is blocked
    }
  };

  const getMethodLabel = (path: string) => {
    switch (path) {
      case 'deterministic_tool':
        return { label: 'Instant Built-in Tool', badge: 'bg-teal-50 text-teal-700 border-teal-200' };
      case 'semantic_cache':
        return { label: 'Saved Response', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
      default:
        return { label: 'AI Model Inference', badge: 'bg-indigo-50 text-indigo-700 border-indigo-200' };
    }
  };

  const methodInfo = getMethodLabel(receipt.execution_path);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/40 backdrop-blur-sm overflow-y-auto animate-fadeIn">
      <div 
        className="bg-white border border-slate-200 rounded-3xl w-full max-w-3xl shadow-2xl overflow-hidden my-auto flex flex-col max-h-[90vh] transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-start justify-between bg-gradient-to-r from-emerald-50/40 via-white to-slate-50/60">
          <div className="flex items-start gap-3.5">
            <div className="h-11 w-11 rounded-2xl bg-emerald-600 flex items-center justify-center text-white shadow-md shadow-emerald-600/20 shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-lg font-bold text-slate-900 tracking-tight">Eco Receipt</h3>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
                  receipt.status === 'SUCCESS' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                  receipt.status === 'PARTIAL' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                  'bg-rose-50 text-rose-700 border-rose-200'
                }`}>
                  {receipt.status === 'SUCCESS' ? 'Completed' : receipt.status}
                </span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${methodInfo.badge}`}>
                  {methodInfo.label}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-mono mt-1">
                Receipt #{receipt.receipt_id} • {new Date(receipt.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            aria-label="Close receipt"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="px-6 py-6 overflow-y-auto space-y-6 flex-1 text-slate-700">
          
          {/* Query Preview */}
          {receipt.query_preview && (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                User Prompt
              </span>
              <p className="text-sm text-slate-800 font-medium italic">
                "{receipt.query_preview}"
              </p>
            </div>
          )}

          {/* Explainability Banner */}
          <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-200/80 flex items-start gap-3">
            <div className="p-1.5 rounded-lg bg-emerald-600/10 text-emerald-700 shrink-0 mt-0.5">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="space-y-1">
              <h4 className="text-xs font-semibold text-emerald-900">
                Why this route was chosen
              </h4>
              <p className="text-xs text-emerald-800 leading-relaxed">
                {receipt.explainability.selection_summary}
              </p>
            </div>
          </div>

          {/* Key Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Latency */}
            <div className="p-3.5 rounded-2xl bg-slate-50/80 border border-slate-200/80">
              <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-600" /> Response Time
              </span>
              <div className="text-base font-bold text-slate-900 mt-1">
                {receipt.execution_time_ms.toFixed(1)} <span className="text-xs font-normal text-slate-500">ms</span>
              </div>
              <span className="text-[10px] text-slate-400 font-medium uppercase">
                {receipt.latency_provenance.toLowerCase()}
              </span>
            </div>

            {/* Tokens */}
            <div className="p-3.5 rounded-2xl bg-slate-50/80 border border-slate-200/80">
              <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-600" /> AI Tokens
              </span>
              <div className="text-base font-bold text-slate-900 mt-1">
                {receipt.tokens.total_tokens !== null ? (
                  receipt.tokens.total_tokens
                ) : (
                  <span className="text-slate-400 font-normal">Unmeasured</span>
                )}
              </div>
              <span className="text-[10px] text-slate-400 font-medium uppercase">
                {receipt.tokens.provenance.toLowerCase()}
              </span>
            </div>

            {/* Cost */}
            <div className="p-3.5 rounded-2xl bg-slate-50/80 border border-slate-200/80">
              <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5 text-emerald-600" /> API Charges
              </span>
              <div className="text-base font-bold text-slate-900 mt-1">
                {receipt.cost.is_zero_external_api_charge ? (
                  <span className="text-emerald-700">$0.00</span>
                ) : receipt.cost.value_usd !== null ? (
                  `$${receipt.cost.value_usd.toFixed(6)}`
                ) : (
                  <span className="text-slate-400 font-normal">N/A</span>
                )}
              </div>
              <span className="text-[10px] text-slate-400 font-medium">
                {receipt.cost.is_zero_external_api_charge ? 'No external fees' : 'Estimated rate'}
              </span>
            </div>

            {/* Route & Provider */}
            <div className="p-3.5 rounded-2xl bg-slate-50/80 border border-slate-200/80">
              <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-600" /> Processing Route
              </span>
              <div className="text-xs font-bold text-slate-900 mt-1 truncate" title={receipt.route}>
                {receipt.route}
              </div>
              <span className="text-[10px] text-slate-500 truncate block">
                {receipt.provider} {receipt.model ? `(${receipt.model})` : ''}
              </span>
            </div>
          </div>

          {/* Environmental Footprint Section */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Leaf className="w-3.5 h-3.5 text-emerald-600" />
              Environmental Footprint & Measurement Boundaries
            </h4>
            
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Energy */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">Operational Energy</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                    receipt.environment.energy.is_measured ? 'bg-emerald-100 text-emerald-800 border-emerald-300' :
                    receipt.environment.energy.is_estimated ? 'bg-amber-100 text-amber-800 border-amber-300' :
                    'bg-slate-100 text-slate-600 border-slate-200'
                  }`}>
                    {receipt.environment.energy.provenance}
                  </span>
                </div>
                <div className="text-lg font-bold text-slate-900">
                  {receipt.environment.energy.value_joules !== null ? (
                    <>
                      {receipt.environment.energy.value_joules.toFixed(3)} <span className="text-xs font-normal text-slate-500">J</span>
                      <span className="block text-xs text-slate-500 font-normal mt-0.5">
                        ({(receipt.environment.energy.value_kwh ?? 0).toExponential(3)} kWh)
                      </span>
                    </>
                  ) : (
                    <span className="text-sm font-normal text-slate-400">Unavailable</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 leading-tight">
                  Scope: {receipt.environment.energy.scope.replace(/_/g, ' ')}
                </p>
                {receipt.environment.energy.scope_disclaimer && (
                  <p className="text-[10px] text-slate-400 italic pt-1 border-t border-slate-200/60">
                    {receipt.environment.energy.scope_disclaimer}
                  </p>
                )}
              </div>

              {/* Carbon */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">Carbon Emissions</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                    receipt.environment.carbon.provenance === 'ESTIMATED' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                    'bg-slate-100 text-slate-600 border-slate-200'
                  }`}>
                    {receipt.environment.carbon.provenance}
                  </span>
                </div>
                <div className="text-lg font-bold text-slate-900">
                  {receipt.environment.carbon.value_gco2e !== null ? (
                    <>
                      {receipt.environment.carbon.value_gco2e.toFixed(6)} <span className="text-xs font-normal text-slate-500">gCO₂e</span>
                    </>
                  ) : (
                    <span className="text-sm font-normal text-slate-400">Unavailable</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 leading-tight">
                  Grid Factor: {receipt.environment.carbon.grid_intensity_gco2e_per_kwh 
                    ? `${receipt.environment.carbon.grid_intensity_gco2e_per_kwh} gCO₂e/kWh` 
                    : 'Unspecified'}
                </p>
                {receipt.environment.carbon.grid_source && (
                  <p className="text-[10px] text-slate-400 pt-1 border-t border-slate-200/60 truncate">
                    Source: {receipt.environment.carbon.grid_source}
                  </p>
                )}
              </div>

              {/* Water */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800 flex items-center gap-1">
                    <Droplets className="w-3.5 h-3.5 text-blue-500" /> Water Cooling
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-medium">
                    {receipt.environment.water.provenance}
                  </span>
                </div>
                <div className="text-lg font-bold text-slate-400">
                  {receipt.environment.water.value_liters !== null ? (
                    `${receipt.environment.water.value_liters} L`
                  ) : (
                    <span className="text-sm font-normal text-slate-400">Unavailable</span>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 leading-tight pt-1">
                  {receipt.environment.water.reason_unavailable}
                </p>
              </div>
            </div>
          </div>

          {/* Operational Avoidance & Smart Routing Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Avoidance Facts */}
            {receipt.avoidance && (
              <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200/80 space-y-2">
                <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-teal-600" />
                  Resource Avoidance relative to Baseline
                </div>
                <div className="flex items-center gap-4 text-xs pt-0.5">
                  <div>
                    <span className="text-slate-500">Model Calls Avoided: </span>
                    <strong className="text-emerald-700">{receipt.avoidance.model_calls_avoided}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Baseline Route: </span>
                    <span className="text-slate-700 font-mono text-[11px]">{receipt.avoidance.baseline_route}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-600">
                  {receipt.avoidance.reasoning}
                </p>
                {receipt.avoidance.savings_notice && (
                  <p className="text-[11px] text-amber-700/90 italic pt-1 border-t border-slate-200/80">
                    {receipt.avoidance.savings_notice}
                  </p>
                )}
              </div>
            )}

            {/* Smart Routing Optimizer */}
            {receipt.optimizer && (
              <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200/80 space-y-2">
                <div className="text-xs font-semibold text-slate-800 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                    Smart Routing Decision
                  </span>
                  {receipt.optimizer.fallback_applied ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Fallback Policy
                    </span>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Pareto Optimal
                    </span>
                  )}
                </div>
                <div className="text-xs space-y-1">
                  <div>
                    <span className="text-slate-500">Candidate Selected: </span>
                    <strong className="text-slate-900">{receipt.optimizer.selected_candidate}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Quality Standard (Q_req): </span>
                    <span className="text-slate-800 font-mono">{receipt.optimizer.quality_threshold_required}</span>
                    <span className="text-emerald-700 text-[11px] font-medium ml-1.5">
                      {receipt.optimizer.quality_threshold_met ? '(Standard Met)' : '(Not Met)'}
                    </span>
                  </div>
                </div>
                {receipt.optimizer.routing_rationale && (
                  <p className="text-xs text-slate-600 border-t border-slate-200/80 pt-1.5 leading-relaxed">
                    {receipt.optimizer.routing_rationale}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Caveats & Disclaimers */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/70 text-xs text-slate-500 space-y-1">
            <div className="flex items-center gap-1.5 text-slate-700 font-medium">
              <Info className="w-3.5 h-3.5 text-slate-400" /> Scientific Integrity Notice
            </div>
            <p className="text-[11px] leading-relaxed">
              {receipt.explainability.caveats_and_uncertainty}
            </p>
          </div>

          {/* Expandable Raw JSON Technical Section */}
          <div className="border border-slate-200 rounded-2xl overflow-hidden transition-all">
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 flex items-center justify-between text-xs font-semibold text-slate-700 transition-colors"
            >
              <span className="flex items-center gap-2">
                <Code className="w-4 h-4 text-slate-500" />
                Raw Machine-Readable Receipt (JSON)
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-slate-400 font-normal">
                  {showRawJson ? 'Hide technical data' : 'Inspect JSON'}
                </span>
                {showRawJson ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </div>
            </button>

            {showRawJson && (
              <div className="p-4 bg-slate-950 text-emerald-400 text-xs font-mono relative border-t border-slate-200 overflow-x-auto max-h-64">
                <div className="absolute top-3 right-3">
                  <button
                    onClick={handleCopyJson}
                    className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] flex items-center gap-1.5 transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <pre>{JSON.stringify(receipt, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between text-xs text-slate-500">
          <span className="text-[11px]">
            EcoMind Sustainability Assurance • Verifiable Receipt
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
