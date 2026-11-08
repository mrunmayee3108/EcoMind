import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  Leaf, 
  Send, 
  Clock, 
  Cpu, 
  Zap, 
  DollarSign, 
  Sparkles, 
  BarChart3, 
  FileText, 
  RefreshCw, 
  Eye, 
  Copy, 
  Check, 
  SlidersHorizontal, 
  ChevronDown, 
  ChevronUp, 
  ShieldCheck, 
  ArrowRight,
  Calculator,
  Compass
} from 'lucide-react';

import type { 
  ChatResponse, 
  EcoReceipt, 
  DashboardSummaryResponse, 
  DashboardEnvironmentResponse, 
  DashboardRoutesResponse, 
  TimeseriesPoint 
} from './types.ts';

import { ReceiptModal } from './components/ReceiptModal.tsx';
import { DashboardOverview } from './components/DashboardOverview.tsx';
import { DashboardEnvironment } from './components/DashboardEnvironment.tsx';
import { DashboardRoutes } from './components/DashboardRoutes.tsx';
import { ReceiptsExplorer } from './components/ReceiptsExplorer.tsx';

const API_BASE = "http://127.0.0.1:8000";

type ActiveView = 'playground' | 'dashboard';
type DashboardTab = 'overview' | 'environment' | 'routes' | 'receipts';

export default function App() {
  const [activeView, setActiveView] = useState<ActiveView>('playground');
  const [dashboardTab, setDashboardTab] = useState<DashboardTab>('overview');

  // Playground state
  const [query, setQuery] = useState("");
  const [preferredRoute, setPreferredRoute] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [copiedAnswer, setCopiedAnswer] = useState(false);

  // Modal inspection state
  const [inspectReceipt, setInspectReceipt] = useState<EcoReceipt | null>(null);

  // Dashboard analytics state
  const [timeRange, setTimeRange] = useState<string>('all');
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [summaryData, setSummaryData] = useState<DashboardSummaryResponse | null>(null);
  const [envData, setEnvData] = useState<DashboardEnvironmentResponse | null>(null);
  const [routesData, setRoutesData] = useState<DashboardRoutesResponse | null>(null);
  const [timeseriesData, setTimeseriesData] = useState<TimeseriesPoint[]>([]);

  // System check on initial load
  useEffect(() => {
    const checkSystem = async () => {
      try {
        await axios.get(`${API_BASE}/tools`);
        setBackendHealthy(true);
      } catch {
        setBackendHealthy(false);
      }
    };
    checkSystem();
  }, []);

  // Fetch dashboard metrics
  const fetchDashboardMetrics = useCallback(async () => {
    setDashboardLoading(true);
    try {
      let startDate: string | undefined = undefined;
      const now = new Date();
      if (timeRange === '24h') {
        startDate = new Date(now.getTime() - 24 * 3600 * 1000).toISOString();
      } else if (timeRange === '7d') {
        startDate = new Date(now.getTime() - 7 * 24 * 3600 * 1000).toISOString();
      } else if (timeRange === '30d') {
        startDate = new Date(now.getTime() - 30 * 24 * 3600 * 1000).toISOString();
      }

      const params = startDate ? { start_date: startDate } : {};

      const [sumRes, envRes, routesRes, tsRes] = await Promise.all([
        axios.get<DashboardSummaryResponse>(`${API_BASE}/dashboard/summary`, { params }),
        axios.get<DashboardEnvironmentResponse>(`${API_BASE}/dashboard/environment`, { params }),
        axios.get<DashboardRoutesResponse>(`${API_BASE}/dashboard/routes`, { params }),
        axios.get<TimeseriesPoint[]>(`${API_BASE}/dashboard/timeseries`, { params: { ...params, interval: 'hour' } })
      ]);

      setSummaryData(sumRes.data);
      setEnvData(envRes.data);
      setRoutesData(routesRes.data);
      setTimeseriesData(tsRes.data);
    } catch (err: unknown) {
      console.error("Failed to fetch dashboard metrics:", err);
    } finally {
      setDashboardLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    if (activeView === 'dashboard') {
      fetchDashboardMetrics();
    }
  }, [activeView, fetchDashboardMetrics]);

  const handleExecute = async (overrideQuery?: string) => {
    const q = (overrideQuery || query).trim();
    if (!q) return;
    if (overrideQuery) setQuery(overrideQuery);

    setLoading(true);
    setError(null);
    setCopiedAnswer(false);

    try {
      const res = await axios.post<ChatResponse>(`${API_BASE}/chat`, {
        query: q,
        preferred_route: preferredRoute
      });
      setResponse(res.data);
    } catch (err: unknown) {
      let msg = "Failed to execute request";
      if (axios.isAxiosError(err)) {
        msg = err.response?.data?.detail || err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading && query.trim()) {
        handleExecute();
      }
    }
  };

  const handleCopyAnswer = () => {
    if (!response?.answer) return;
    navigator.clipboard.writeText(response.answer);
    setCopiedAnswer(true);
    setTimeout(() => setCopiedAnswer(false), 2000);
  };

  const promptSuggestions = [
    { title: "Calculate 125 × 48", prompt: "Calculate 125 * 48" },
    { title: "Explain how solar panels work", prompt: "Explain how solar panels work in simple terms." },
    { title: "Python sort function", prompt: "Write a clean Python function to sort a list of numbers with comments." },
    { title: "Concept of neural networks", prompt: "Summarise the core concept of artificial neural networks." }
  ];

  const processingOptions = [
    {
      id: "auto",
      title: "Automatic (Recommended)",
      desc: "EcoMind selects the most energy-efficient, accurate route available."
    },
    {
      id: "deterministic_tool",
      title: "Built-in Tool Only",
      desc: "Direct algorithmic execution (math/time) with zero AI token consumption."
    },
    {
      id: "semantic_cache",
      title: "Saved Response Only",
      desc: "Retrieve verified answers to previously asked questions instantly."
    },
    {
      id: "small_model",
      title: "Small Model",
      desc: "Lightweight, low-energy AI model ideal for concise questions."
    },
    {
      id: "medium_model",
      title: "Medium Model",
      desc: "Balanced AI model suitable for general queries and code."
    },
    {
      id: "large_model",
      title: "Large Model",
      desc: "High-capacity reasoning model for intricate analysis."
    }
  ];

  const getFriendlyRouteLabel = (resp: ChatResponse) => {
    if (resp.cache_status === 'hit') {
      return {
        label: "Saved Response (Semantic Cache)",
        sub: `Reused verified response (${((resp.cache_similarity ?? 1.0) * 100).toFixed(0)}% match) — 0 AI tokens needed`,
        color: "text-emerald-700 bg-emerald-50 border-emerald-200"
      };
    }
    if (resp.provider === 'deterministic') {
      return {
        label: "Built-in Tool (Algorithmic)",
        sub: "Executed locally without calling an AI model — 0 tokens consumed",
        color: "text-blue-700 bg-blue-50 border-blue-200"
      };
    }
    if (resp.provider === 'mock_llm' || resp.provider === 'cloud_llm' || resp.provider === 'local_gpu') {
      return {
        label: `AI Model (${resp.model || resp.provider})`,
        sub: "Generated using sustainability-optimized multi-objective routing",
        color: "text-slate-700 bg-slate-100 border-slate-200"
      };
    }
    return {
      label: resp.route || "Processed",
      sub: "Request completed successfully",
      color: "text-slate-700 bg-slate-100 border-slate-200"
    };
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans selection:bg-emerald-100 selection:text-emerald-900">
      {/* Top Header */}
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur-md sticky top-0 z-40 shadow-xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo & Tagline */}
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-sm shadow-emerald-600/20">
              <Leaf className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight text-slate-900">EcoMind</span>
              </div>
              <p className="text-xs text-slate-500 font-medium hidden sm:block">
                Smarter AI. Lighter Footprint.
              </p>
            </div>
          </div>

          {/* Primary View Switcher */}
          <div className="flex items-center gap-1.5 bg-slate-100/90 p-1 rounded-xl border border-slate-200/80">
            <button
              onClick={() => setActiveView('playground')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeView === 'playground'
                  ? 'bg-white text-emerald-700 border border-slate-200/60 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>AI Assistant</span>
            </button>
            <button
              onClick={() => setActiveView('dashboard')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeView === 'dashboard'
                  ? 'bg-white text-emerald-700 border border-slate-200/60 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5 text-teal-600" />
              <span>Sustainability Dashboard</span>
            </button>
          </div>

          {/* System Status Pill */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-xs font-medium text-slate-600">
              <span className={`h-2 w-2 rounded-full ${backendHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'}`}></span>
              <span className="hidden md:inline">{backendHealthy ? 'System Ready' : 'Connecting...'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-8 w-full space-y-8">
        
        {/* ========================================================= */}
        {/* VIEW 1: AI ASSISTANT / PLAYGROUND                         */}
        {/* ========================================================= */}
        {activeView === 'playground' && (
          <div className="space-y-8 max-w-4xl mx-auto">
            {/* Friendly Hero Banner */}
            <div className="text-center space-y-2 pt-2 pb-1">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                How can I help you today?
              </h1>
              <p className="text-sm text-slate-500 max-w-xl mx-auto">
                Ask a question, request an explanation, or solve a math problem. EcoMind automatically routes your request for high accuracy and minimal carbon footprint.
              </p>
            </div>

            {/* Main Input Box Card */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 shadow-sm space-y-4 transition-all">
              {/* Textarea */}
              <div className="relative">
                <textarea
                  rows={4}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything (e.g. Calculate 125 * 48, explain how photosynthesis works, or draft an email)..."
                  className="w-full bg-slate-50/60 border border-slate-200 rounded-xl p-4 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 focus:bg-white text-sm transition-all resize-none leading-relaxed"
                />
              </div>

              {/* Action Bar (Suggestions, Advanced Toggle, Send) */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
                {/* Advanced Settings Toggle */}
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 py-1.5 px-2.5 rounded-lg hover:bg-slate-100 transition-colors self-start sm:self-auto"
                >
                  <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
                  <span>Processing Preferences</span>
                  {showAdvanced ? (
                    <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  )}
                  {preferredRoute !== 'auto' && (
                    <span className="ml-1 px-1.5 py-0.2 rounded text-[10px] bg-emerald-100 text-emerald-800 font-bold">
                      Manual
                    </span>
                  )}
                </button>

                {/* Send Button */}
                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <span className="text-[11px] text-slate-400 hidden sm:inline">
                    Press <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 font-mono text-[10px]">Enter ↵</kbd> to send
                  </span>
                  <button
                    onClick={() => handleExecute()}
                    disabled={loading || !query.trim()}
                    className="py-2.5 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm transition-all shadow-sm hover:shadow disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Finding answer...</span>
                      </>
                    ) : (
                      <>
                        <span>Ask EcoMind</span>
                        <Send className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Collapsible Advanced Preferences */}
              {showAdvanced && (
                <div className="pt-4 border-t border-slate-100 space-y-3 animate-in fade-in duration-150">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Execution Route Directive
                    </span>
                    <span className="text-xs text-slate-500">
                      Controls which engine evaluates your request
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                    {processingOptions.map((opt) => (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => setPreferredRoute(opt.id)}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          preferredRoute === opt.id
                            ? 'bg-emerald-50/80 border-emerald-500 text-slate-900 shadow-xs'
                            : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-xs font-bold ${preferredRoute === opt.id ? 'text-emerald-800' : 'text-slate-800'}`}>
                            {opt.title}
                          </span>
                          {preferredRoute === opt.id && (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 leading-snug">
                          {opt.desc}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Natural Prompt Suggestions */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-500 flex items-center gap-1.5 px-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                Or try one of these suggestions:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {promptSuggestions.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExecute(item.prompt)}
                    className="p-3 rounded-xl bg-white hover:bg-emerald-50/60 border border-slate-200/80 hover:border-emerald-300 text-left transition-all flex items-center justify-between group shadow-2xs"
                  >
                    <span className="text-xs font-medium text-slate-700 group-hover:text-emerald-900">
                      {item.title}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-600 transition-transform group-hover:translate-x-0.5" />
                  </button>
                ))}
              </div>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
                <span className="font-bold">Error:</span>
                <span>{error}</span>
              </div>
            )}

            {/* Response Presentation Card */}
            {response && (
              <div className="space-y-4 animate-in fade-in duration-200">
                {/* Answer Card */}
                <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-md bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs">
                        A
                      </div>
                      <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        Response
                      </span>
                    </div>
                    <button
                      onClick={handleCopyAnswer}
                      className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 px-2.5 py-1 rounded-md hover:bg-slate-200/60 transition-colors"
                      title="Copy response"
                    >
                      {copiedAnswer ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-700 font-medium">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 text-slate-500" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="p-6 text-sm text-slate-900 leading-relaxed whitespace-pre-wrap font-sans">
                    {response.answer}
                  </div>
                </div>

                {/* Compact "Response Insights" Card */}
                {(() => {
                  const routeInfo = getFriendlyRouteLabel(response);
                  return (
                    <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-4">
                      {/* Insights Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                        <div className="flex items-center gap-2">
                          <Compass className="w-4 h-4 text-emerald-600" />
                          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                            Response Insights
                          </span>
                        </div>
                        {response.eco_receipt && (
                          <button
                            onClick={() => setInspectReceipt(response.eco_receipt!)}
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-1.5 rounded-lg transition-colors self-start sm:self-auto cursor-pointer"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            <span>View Eco Receipt</span>
                            <Eye className="w-3 h-3 text-emerald-600" />
                          </button>
                        )}
                      </div>

                      {/* Route Banner */}
                      <div className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${routeInfo.color}`}>
                        <div>
                          <div className="text-xs font-bold">{routeInfo.label}</div>
                          <p className="text-[11px] opacity-80 mt-0.5">{routeInfo.sub}</p>
                        </div>
                        <span className="text-xs font-mono font-bold self-start sm:self-auto">
                          {response.execution_time_ms.toFixed(1)} ms
                        </span>
                      </div>

                      {/* Key Indicators Grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                          <div className="text-[11px] text-slate-500 flex items-center gap-1">
                            <Clock className="w-3 h-3 text-slate-400" /> Latency
                          </div>
                          <div className="text-sm font-bold text-slate-900 mt-1">
                            {response.execution_time_ms.toFixed(1)} <span className="text-[11px] font-normal text-slate-500">ms</span>
                          </div>
                        </div>

                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                          <div className="text-[11px] text-slate-500 flex items-center gap-1">
                            <Zap className="w-3 h-3 text-amber-500" /> Token Usage
                          </div>
                          <div className="text-sm font-bold text-slate-900 mt-1">
                            {response.cache_status === 'hit' || response.provider === 'deterministic' ? (
                              <span className="text-emerald-700 font-semibold">0 tokens (Avoided)</span>
                            ) : (
                              <span>{response.token_usage?.total_tokens ?? 0} <span className="text-[11px] font-normal text-slate-500">tokens</span></span>
                            )}
                          </div>
                        </div>

                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                          <div className="text-[11px] text-slate-500 flex items-center gap-1">
                            <Cpu className="w-3 h-3 text-teal-600" /> Energy Status
                          </div>
                          <div className="text-sm font-bold text-slate-900 mt-1">
                            {response.eco_receipt?.environment.energy.is_measured ? (
                              <span className="text-emerald-700 font-semibold">GPU Measured</span>
                            ) : response.eco_receipt?.environment.energy.is_estimated ? (
                              <span className="text-slate-700 font-medium">Estimated</span>
                            ) : (
                              <span className="text-slate-600 font-medium">Local Process</span>
                            )}
                          </div>
                        </div>

                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                          <div className="text-[11px] text-slate-500 flex items-center gap-1">
                            <DollarSign className="w-3 h-3 text-slate-400" /> API Cost
                          </div>
                          <div className="text-sm font-bold text-slate-900 mt-1">
                            {response.eco_receipt?.cost.value_usd !== undefined && response.eco_receipt?.cost.value_usd !== null ? (
                              `$${response.eco_receipt.cost.value_usd.toFixed(6)}`
                            ) : (
                              "$0.000000"
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* How EcoMind Saves Energy (Friendly Explainer) */}
            <div className="pt-4 border-t border-slate-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs space-y-1.5">
                  <div className="flex items-center gap-2 text-emerald-700 font-semibold text-xs">
                    <Calculator className="w-4 h-4" />
                    <span>Instant Built-in Tools</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Math, equations, and temporal questions run instantly through local algorithmic tools without consuming any AI model energy.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs space-y-1.5">
                  <div className="flex items-center gap-2 text-teal-700 font-semibold text-xs">
                    <Sparkles className="w-4 h-4" />
                    <span>Accuracy-First Saved Answers</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Similar queries reuse verified answers safely using strict semantic similarity thresholds, cutting unnecessary model calls.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs space-y-1.5">
                  <div className="flex items-center gap-2 text-blue-700 font-semibold text-xs">
                    <ShieldCheck className="w-4 h-4" />
                    <span>Certified Eco Receipts</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Every request generates a verifiable receipt with authentic latency, measured energy, grid carbon, and water disclosures.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* VIEW 2: SUSTAINABILITY DASHBOARD                          */}
        {/* ========================================================= */}
        {activeView === 'dashboard' && (
          <div className="space-y-6">
            {/* Dashboard Subheader & Controls */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
              {/* Dashboard Subtabs */}
              <div className="flex flex-wrap items-center gap-1.5 bg-slate-100/90 p-1 rounded-xl border border-slate-200/80">
                {[
                  { id: 'overview', label: 'Overview' },
                  { id: 'environment', label: 'Environmental Impact' },
                  { id: 'routes', label: 'How EcoMind Works' },
                  { id: 'receipts', label: 'Activity History' }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setDashboardTab(tab.id as DashboardTab)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      dashboardTab === tab.id
                        ? 'bg-white text-emerald-800 border border-slate-200/70 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Time Range Filter & Refresh */}
              <div className="flex items-center gap-2 self-end sm:self-auto">
                <div className="flex items-center gap-1 bg-slate-100/90 p-1 rounded-xl border border-slate-200/80 text-xs">
                  {[
                    { id: '24h', label: '24h' },
                    { id: '7d', label: '7d' },
                    { id: '30d', label: '30d' },
                    { id: 'all', label: 'All Time' }
                  ].map((range) => (
                    <button
                      key={range.id}
                      onClick={() => setTimeRange(range.id)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                        timeRange === range.id
                          ? 'bg-white text-slate-900 font-bold shadow-2xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {range.label}
                    </button>
                  ))}
                </div>
                <button
                  onClick={fetchDashboardMetrics}
                  disabled={dashboardLoading}
                  className="p-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50 shadow-2xs"
                  title="Refresh metrics"
                >
                  <RefreshCw className={`w-4 h-4 ${dashboardLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {/* Subtab 1: Overview */}
            {dashboardTab === 'overview' && (
              <DashboardOverview
                summary={summaryData}
                timeseries={timeseriesData}
                loading={dashboardLoading}
              />
            )}

            {/* Subtab 2: Environmental Impact */}
            {dashboardTab === 'environment' && (
              <DashboardEnvironment
                environment={envData}
                loading={dashboardLoading}
              />
            )}

            {/* Subtab 3: How EcoMind Works (Routing Analytics) */}
            {dashboardTab === 'routes' && (
              <DashboardRoutes
                routesData={routesData}
                loading={dashboardLoading}
              />
            )}

            {/* Subtab 4: Activity History (Receipts Explorer) */}
            {dashboardTab === 'receipts' && (
              <ReceiptsExplorer
                apiBase={API_BASE}
                onSelectReceipt={(rcpt) => setInspectReceipt(rcpt)}
              />
            )}
          </div>
        )}

      </main>

      {/* Eco Receipt Inspection Modal */}
      {inspectReceipt && (
        <ReceiptModal
          receipt={inspectReceipt}
          onClose={() => setInspectReceipt(null)}
        />
      )}
    </div>
  );
}
