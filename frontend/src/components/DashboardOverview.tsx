import React from 'react';
import { 
  Zap, 
  Clock, 
  Layers, 
  Cpu, 
  CheckCircle2, 
  DollarSign, 
  Server, 
  Sparkles,
  ArrowUpRight
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
  onNavigateToHistory?: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  summary,
  timeseries,
  loading,
  onNavigateToHistory
}) => {
  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-500 font-medium">Gathering real-time usage metrics...</p>
      </div>
    );
  }

  if (!summary || summary.total_requests === 0) {
    return (
      <div className="py-20 text-center space-y-4 bg-white/70 backdrop-blur-md rounded-3xl border border-slate-200/80 p-8 shadow-sm">
        <div className="p-3.5 rounded-2xl bg-emerald-50 text-emerald-600 inline-block">
          <Sparkles className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h4 className="text-base font-semibold text-slate-900">No Activity Recorded Yet</h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try asking a question or running a calculation in the Playground. Your activity, savings, and Eco Receipts will appear here immediately.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 4 Primary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Total Queries */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">Total Queries</span>
            <div className="p-2 rounded-xl bg-slate-50 text-slate-600">
              <Server className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2 tracking-tight">
            {summary.total_requests.toLocaleString()}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-medium mt-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{summary.success_rate_percent.toFixed(1)}% Success Rate</span>
          </div>
        </div>

        {/* KPI 2: Zero-Inference Answers */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">Model Calls Avoided</span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600 mt-2 tracking-tight">
            {summary.total_model_calls_avoided.toLocaleString()}
          </div>
          <p className="text-xs text-slate-500 mt-1.5">
            Answered via built-in tools & cache
          </p>
        </div>

        {/* KPI 3: Avg Response Time */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">Average Response Time</span>
            <div className="p-2 rounded-xl bg-cyan-50 text-cyan-600">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2 tracking-tight">
            {summary.avg_latency_ms.toFixed(1)} <span className="text-xs font-normal text-slate-500">ms</span>
          </div>
          <p className="text-xs text-slate-500 mt-1.5">
            {(summary.total_execution_time_ms / 1000).toFixed(2)}s total compute
          </p>
        </div>

        {/* KPI 4: External API Cost */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-medium">External API Charges</span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2 tracking-tight">
            ${summary.total_external_api_cost_usd.toFixed(6)}
          </div>
          <p className="text-xs text-slate-500 mt-1.5">
            <strong className="text-emerald-700 font-semibold">{summary.zero_external_api_cost_count}</strong> queries with $0 API fees
          </p>
        </div>
      </div>

      {/* Activity Timeline Chart */}
      {timeseries.length > 0 && (
        <div className="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold text-slate-900">Query Activity & Response Time Over Time</h4>
              <p className="text-xs text-slate-500 mt-0.5">Chronological request volume and latency distribution</p>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium">
              <span className="flex items-center gap-1.5 text-emerald-700">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" /> Requests
              </span>
              <span className="flex items-center gap-1.5 text-cyan-700">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" /> Response Time (ms)
              </span>
            </div>
          </div>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeseries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="reqGradLight" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#059669" stopOpacity={0.0}/>
                  </linearGradient>
                  <linearGradient id="latGradLight" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="time_bucket" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis yAxisId="left" stroke="#059669" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" stroke="#06b6d4" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ 
                    backgroundColor: '#ffffff', 
                    borderColor: '#e2e8f0', 
                    borderRadius: '1rem', 
                    fontSize: '12px',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)'
                  }}
                />
                <Area yAxisId="left" type="monotone" dataKey="request_count" stroke="#059669" strokeWidth={2} fillOpacity={1} fill="url(#reqGradLight)" name="Queries" />
                <Area yAxisId="right" type="monotone" dataKey="avg_latency_ms" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#latGradLight)" name="Avg Latency (ms)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Breakdown Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Processing Methods */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-teal-600" /> Processing Method
            </h4>
          </div>
          <div className="space-y-3">
            {Object.entries(summary.execution_paths_breakdown).map(([path, count]) => {
              const pct = (count / summary.total_requests) * 100;
              const formattedName = path === 'deterministic_tool' ? 'Built-in Tools' :
                                    path === 'semantic_cache' ? 'Saved Responses' : 'AI Model Inference';
              return (
                <div key={path} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-700 font-medium">{formattedName}</span>
                    <span className="text-slate-500">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${
                        path === 'deterministic_tool' ? 'bg-cyan-500' :
                        path === 'semantic_cache' ? 'bg-emerald-500' :
                        'bg-indigo-500'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Routes */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-indigo-600" /> Route Distribution
          </h4>
          <div className="space-y-3">
            {Object.entries(summary.routes_breakdown).slice(0, 5).map(([route, count]) => {
              const pct = (count / summary.total_requests) * 100;
              return (
                <div key={route} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-700 font-medium truncate max-w-[170px]" title={route}>{route}</span>
                    <span className="text-slate-500">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-emerald-600 rounded-full transition-all duration-500" 
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Providers */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-amber-600" /> Provider Distribution
          </h4>
          <div className="space-y-3">
            {Object.entries(summary.providers_breakdown).map(([provider, count]) => {
              const pct = (count / summary.total_requests) * 100;
              const displayProvider = provider === 'deterministic' ? 'Built-in Tool' :
                                      provider === 'cache' ? 'Saved Response' : provider;
              return (
                <div key={provider} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-700 font-medium capitalize">{displayProvider}</span>
                    <span className="text-slate-500">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-teal-500 rounded-full transition-all duration-500" 
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {onNavigateToHistory && (
        <div className="flex justify-end pt-2">
          <button
            onClick={onNavigateToHistory}
            className="text-xs text-emerald-700 hover:text-emerald-800 font-medium flex items-center gap-1 transition-colors"
          >
            <span>View detailed activity history</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
