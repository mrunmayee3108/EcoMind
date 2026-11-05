import React from 'react';
import { 
  Cpu, 
  ShieldCheck, 
  AlertTriangle, 
  Clock, 
  Layers, 
  DollarSign, 
  Activity 
} from 'lucide-react';
import type { DashboardRoutesResponse } from '../types.ts';

interface DashboardRoutesProps {
  routesData: DashboardRoutesResponse | null;
  loading: boolean;
}

export const DashboardRoutes: React.FC<DashboardRoutesProps> = ({
  routesData,
  loading
}) => {
  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Loading routing optimization metrics...</p>
      </div>
    );
  }

  if (!routesData || routesData.total_evaluated_requests === 0) {
    return (
      <div className="py-20 text-center space-y-3 bg-slate-900/40 rounded-2xl border border-slate-800 p-8">
        <div className="p-3 rounded-full bg-slate-800 inline-block text-slate-400">
          <Cpu className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-slate-200">No Routing Decisions Evaluated</h4>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Multi-objective routing evaluations will be recorded as queries are routed through the control plane.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Optimizer Overview KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Pareto Frontier Rate */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Pareto Selection Rate</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {routesData.pareto_optimal_selection_rate_percent.toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Non-dominated on Quality, Latency, Cost, & Energy
          </p>
        </div>

        {/* Quality Threshold Compliance */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Quality Compliance (Q_req)</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            {routesData.quality_threshold_compliance_percent.toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Satisfied hard task complexity constraints
          </p>
        </div>

        {/* Fallback Engagement Rate */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Fallback Engagement Rate</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {routesData.fallback_engagement_rate_percent.toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Engaged default policy on missing metrics/errors
          </p>
        </div>
      </div>

      {/* Route Statistics Table */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-white">Route Performance & Candidate Breakdown</h4>
            <p className="text-xs text-slate-400">Comparative metrics across all chosen execution routes</p>
          </div>
          <span className="text-xs text-slate-400 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700">
            Total Evaluated: {routesData.total_evaluated_requests}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="p-3">Route Label</th>
                <th className="p-3">Requests</th>
                <th className="p-3">Mean Latency</th>
                <th className="p-3">Pareto Count</th>
                <th className="p-3">Avoided Calls</th>
                <th className="p-3">Total Cost</th>
                <th className="p-3">Energy (J)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {routesData.route_statistics.map((stat, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="p-3 font-semibold text-white">{stat.route}</td>
                  <td className="p-3">{stat.request_count}</td>
                  <td className="p-3 text-cyan-400 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-cyan-500" />
                      {stat.avg_latency_ms.toFixed(1)} ms
                    </span>
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                      {stat.pareto_count}
                    </span>
                  </td>
                  <td className="p-3 text-emerald-400 font-medium">
                    {stat.avoided_calls}
                  </td>
                  <td className="p-3 font-mono text-slate-300">
                    <span className="flex items-center gap-0.5">
                      <DollarSign className="w-3 h-3 text-amber-400" />
                      {stat.total_cost_usd.toFixed(6)}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-slate-400">
                    {stat.total_energy_joules !== null ? (
                      <span className="flex items-center gap-1 text-emerald-400">
                        <Activity className="w-3 h-3 text-emerald-500" />
                        {stat.total_energy_joules.toFixed(2)} J
                      </span>
                    ) : (
                      <span className="text-slate-500">N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fallback Reasons Breakdown */}
      {Object.keys(routesData.fallback_reasons_breakdown).length > 0 && (
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4" /> Fallback Policy Justifications
          </h4>
          <div className="space-y-2">
            {Object.entries(routesData.fallback_reasons_breakdown).map(([reason, count]) => (
              <div key={reason} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs flex items-center justify-between">
                <span className="text-slate-300">{reason}</span>
                <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
                  {count} occurrences
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
