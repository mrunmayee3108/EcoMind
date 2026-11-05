import React from 'react';
import { 
  Zap, 
  Clock, 
  Layers, 
  Cpu, 
  CheckCircle2, 
  DollarSign, 
  Server, 
  AlertCircle 
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import type { DashboardSummaryResponse, TimeseriesPoint } from '../types.ts';

interface DashboardOverviewProps {
  summary: DashboardSummaryResponse | null;
  timeseries: TimeseriesPoint[];
  loading: boolean;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  summary,
  timeseries,
  loading
}) => {
  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Loading historical telemetry metrics...</p>
      </div>
    );
  }

  if (!summary || summary.total_requests === 0) {
    return (
      <div className="py-20 text-center space-y-3 bg-slate-900/40 rounded-2xl border border-slate-800 p-8">
        <div className="p-3 rounded-full bg-slate-800 inline-block text-slate-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-slate-200">No Historical Records Found</h4>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Execute inference queries in the Playground to generate persistent execution telemetry and Eco Receipts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Card 1: Total Requests */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total Requests</span>
            <Server className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {summary.total_requests.toLocaleString()}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 mt-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>{summary.success_rate_percent.toFixed(1)}% Success Rate</span>
          </div>
        </div>

        {/* Card 2: Model Calls Avoided */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Model Calls Avoided</span>
            <Layers className="w-4 h-4 text-teal-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            {summary.total_model_calls_avoided.toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Directly satisfied via cache/tools
          </p>
        </div>

        {/* Card 3: Avg Execution Latency */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Mean Latency</span>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {summary.avg_latency_ms.toFixed(1)} <span className="text-xs font-normal text-slate-400">ms</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Total {(summary.total_execution_time_ms / 1000).toFixed(2)}s compute
          </p>
        </div>

        {/* Card 4: External API Cost */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>External API Cost</span>
            <DollarSign className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            ${summary.total_external_api_cost_usd.toFixed(6)}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {summary.zero_external_api_cost_count} requests with $0 charges
          </p>
        </div>
      </div>

      {/* Timeseries Graph: Volume & Latency */}
      {timeseries.length > 0 && (
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-white">Execution Activity & Latency Timeline</h4>
              <p className="text-xs text-slate-400">Historical request volume and average execution time</p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Requests
              </span>
              <span className="flex items-center gap-1.5 text-cyan-400">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Latency (ms)
              </span>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeseries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="reqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                  </linearGradient>
                  <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                <XAxis dataKey="time_bucket" stroke="#64748b" fontSize={11} />
                <YAxis yAxisId="left" stroke="#10b981" fontSize={11} />
                <YAxis yAxisId="right" orientation="right" stroke="#22d3ee" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                />
                <Area yAxisId="left" type="monotone" dataKey="request_count" stroke="#10b981" fillOpacity={1} fill="url(#reqGrad)" name="Requests" />
                <Area yAxisId="right" type="monotone" dataKey="avg_latency_ms" stroke="#22d3ee" fillOpacity={1} fill="url(#latGrad)" name="Avg Latency (ms)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Breakdowns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Execution Paths Breakdown */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-teal-400" /> Execution Paths
          </h4>
          <div className="space-y-2">
            {Object.entries(summary.execution_paths_breakdown).map(([path, count]) => {
              const pct = (count / summary.total_requests) * 100;
              return (
                <div key={path} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-mono capitalize">{path.replace('_', ' ')}</span>
                    <span className="text-slate-400">{count} ({pct.toFixed(1)}%)</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${
                        path === 'deterministic_tool' ? 'bg-cyan-400' :
                        path === 'semantic_cache' ? 'bg-emerald-400' :
                        'bg-purple-400'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Route Distribution */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-purple-400" /> Route Distribution
          </h4>
          <div className="space-y-2">
            {Object.entries(summary.routes_breakdown).map(([route, count]) => {
              const pct = (count / summary.total_requests) * 100;
              return (
                <div key={route} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 truncate max-w-[180px]">{route}</span>
                    <span className="text-slate-400">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-emerald-500 rounded-full" 
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Providers Breakdown */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-amber-400" /> Provider Breakdown
          </h4>
          <div className="space-y-2">
            {Object.entries(summary.providers_breakdown).map(([provider, count]) => {
              const pct = (count / summary.total_requests) * 100;
              return (
                <div key={provider} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 capitalize">{provider}</span>
                    <span className="text-slate-400">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-teal-400 rounded-full" 
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
