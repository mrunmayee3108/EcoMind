import React from 'react';
import { 
  Cpu, 
  ShieldCheck, 
  AlertTriangle, 
  Clock, 
  DollarSign, 
  Activity, 
  CheckCircle2, 
  Sparkles
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
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-500 font-medium">Analyzing routing efficiency...</p>
      </div>
    );
  }

  if (!routesData || routesData.total_evaluated_requests === 0) {
    return (
      <div className="py-20 text-center space-y-4 bg-white/70 backdrop-blur-md rounded-3xl border border-slate-200/80 p-8 shadow-sm">
        <div className="p-3.5 rounded-2xl bg-indigo-50 text-indigo-600 inline-block">
          <Cpu className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h4 className="text-base font-semibold text-slate-900">No Routing Decisions Recorded</h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Multi-objective routing evaluations will be recorded here as queries are routed through the control plane.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Educational Header */}
      <div className="p-5 rounded-2xl bg-indigo-50/60 border border-indigo-200/80 flex items-start gap-3.5">
        <div className="p-2 rounded-xl bg-indigo-600 text-white shrink-0 shadow-sm shadow-indigo-600/20 mt-0.5">
          <Sparkles className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h4 className="text-sm font-bold text-indigo-950">
            Smart Routing: Balancing Quality, Speed, Cost, and Footprint
          </h4>
          <p className="text-xs text-indigo-900 leading-relaxed">
            Every query evaluated by EcoMind is checked against a strict quality threshold first. Answer quality is never compromised to save resources. When multiple execution paths meet your quality requirements, EcoMind selects the route that minimizes computational footprint and response latency.
          </p>
        </div>
      </div>

      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Pareto Optimal Balance */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">Optimal Balance Rate</span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2 tracking-tight">
            {routesData.pareto_optimal_selection_rate_percent.toFixed(1)}%
          </div>
          <p className="text-xs text-slate-500 mt-1.5">
            Non-dominated across Quality, Speed, Cost, & Energy
          </p>
        </div>

        {/* Quality Standard Compliance */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">Quality Compliance</span>
            <div className="p-2 rounded-xl bg-teal-50 text-teal-600">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600 mt-2 tracking-tight">
            {routesData.quality_threshold_compliance_percent.toFixed(1)}%
          </div>
          <p className="text-xs text-slate-500 mt-1.5">
            100% satisfied required task quality standards
          </p>
        </div>

        {/* Fallback Engagement Rate */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">Safe Fallback Engaged</span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2 tracking-tight">
            {routesData.fallback_engagement_rate_percent.toFixed(1)}%
          </div>
          <p className="text-xs text-slate-500 mt-1.5">
            Safe default routing on unmetered or offline models
          </p>
        </div>
      </div>

      {/* Route Performance Table */}
      <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h4 className="text-sm font-bold text-slate-900">Execution Route Performance Breakdown</h4>
            <p className="text-xs text-slate-500 mt-0.5">Comparative performance and resource metrics across all routes</p>
          </div>
          <span className="text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full self-start sm:self-auto">
            {routesData.total_evaluated_requests} queries evaluated
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-200">
              <tr>
                <th className="p-3.5 font-semibold">Route</th>
                <th className="p-3.5 font-semibold">Queries</th>
                <th className="p-3.5 font-semibold">Avg Response Time</th>
                <th className="p-3.5 font-semibold">Optimal Rate</th>
                <th className="p-3.5 font-semibold">Model Calls Saved</th>
                <th className="p-3.5 font-semibold">API Charges</th>
                <th className="p-3.5 font-semibold">Energy</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {routesData.route_statistics.map((stat, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="p-3.5 font-semibold text-slate-900">{stat.route}</td>
                  <td className="p-3.5">{stat.request_count}</td>
                  <td className="p-3.5 font-mono text-cyan-700 font-medium">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-cyan-600" />
                      {stat.avg_latency_ms.toFixed(1)} ms
                    </span>
                  </td>
                  <td className="p-3.5">
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                      {stat.pareto_count} optimal
                    </span>
                  </td>
                  <td className="p-3.5 font-medium text-emerald-700">
                    {stat.avoided_calls}
                  </td>
                  <td className="p-3.5 font-mono text-slate-700">
                    <span className="flex items-center gap-0.5">
                      <DollarSign className="w-3 h-3 text-amber-600" />
                      {stat.total_cost_usd.toFixed(6)}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono text-slate-600">
                    {stat.total_energy_joules !== null ? (
                      <span className="flex items-center gap-1 text-emerald-700">
                        <Activity className="w-3 h-3 text-emerald-600" />
                        {stat.total_energy_joules.toFixed(2)} J
                      </span>
                    ) : (
                      <span className="text-slate-400">N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fallback Reasons (if any) */}
      {Object.keys(routesData.fallback_reasons_breakdown).length > 0 && (
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" /> Fallback Policy Engagements
          </h4>
          <div className="space-y-2">
            {Object.entries(routesData.fallback_reasons_breakdown).map(([reason, count]) => (
              <div key={reason} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs flex items-center justify-between">
                <span className="text-slate-700 font-medium">{reason}</span>
                <span className="px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
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
