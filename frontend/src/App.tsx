import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Calculator, 
  Cpu, 
  Zap, 
  Leaf, 
  Send, 
  Clock, 
  Layers, 
  CheckCircle2, 
  ShieldCheck, 
  Info,
  Server,
  ArrowRight,
  Database,
  Sparkles
} from 'lucide-react';

interface TokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  is_estimated: boolean;
}

interface ChatResponse {
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
}

interface ToolInfo {
  name: string;
  description: string;
  type: string;
  calls_llm: boolean;
}

interface ModelProfile {
  model_id: string;
  provider: string;
  tier: string;
  context_window: number;
  description: string;
  is_local: boolean;
}

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [query, setQuery] = useState("");
  const [preferredRoute, setPreferredRoute] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse | null>(null);

  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [models, setModels] = useState<ModelProfile[]>([]);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    // Fetch system tools and models on load
    const checkSystem = async () => {
      try {
        const [toolsRes, modelsRes] = await Promise.all([
          axios.get<ToolInfo[]>(`${API_BASE}/tools`),
          axios.get<ModelProfile[]>(`${API_BASE}/models`)
        ]);
        setTools(toolsRes.data);
        setModels(modelsRes.data);
        setBackendHealthy(true);
      } catch (err) {
        setBackendHealthy(false);
      }
    };
    checkSystem();
  }, []);

  const handleExecute = async (overrideQuery?: string) => {
    const q = (overrideQuery || query).trim();
    if (!q) return;
    if (overrideQuery) setQuery(overrideQuery);

    setLoading(true);
    setError(null);

    try {
      const res = await axios.post<ChatResponse>(`${API_BASE}/chat`, {
        query: q,
        preferred_route: preferredRoute
      });
      setResponse(res.data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to execute request";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const sampleQueries = [
    { label: "Deterministic Tool (0 Tokens)", q: "calculate 25 times 100", route: "auto" },
    { label: "Cache Seed Query", q: "Explain the difference between TCP and UDP.", route: "auto" },
    { label: "Cache Hit Variant", q: "What is the difference between UDP and TCP?", route: "auto" },
    { label: "Scoped Query (Cache Miss)", q: "Compare TCP and UDP specifically for high-latency networks.", route: "auto" },
    { label: "Temporal Query (Cache Miss)", q: "What was the capital of France in 1800?", route: "auto" }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Leaf className="w-5 h-5 text-slate-950 font-bold" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white">EcoMind</span>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Phase 4 Control Plane
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Accuracy-First Semantic Cache & Sustainable Inference Control Plane
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
              <span className={`h-2 w-2 rounded-full ${backendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
              <span className="text-slate-300 font-medium">
                {backendHealthy ? 'Backend Connected' : 'Offline / Standby'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-8">
        
        {/* Research Banner */}
        <div className="rounded-xl p-4 bg-gradient-to-r from-emerald-950/40 via-slate-900/60 to-slate-900/40 border border-emerald-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 mt-0.5">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-emerald-300">Empirical Integrity Protocol</h2>
              <p className="text-xs text-slate-400 leading-relaxed max-w-3xl">
                EcoMind measures authentic metrics (real execution latency, actual API token usage) and never fabricates fake environmental constants. Deterministic queries bypass neural network inference entirely, achieving 0 token consumption.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 whitespace-nowrap bg-slate-800/60 px-3 py-1.5 rounded-lg border border-slate-700">
            <Server className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tools: {tools.length}</span>
            <span className="text-slate-600">•</span>
            <Layers className="w-3.5 h-3.5 text-teal-400" />
            <span>Profiles: {models.length}</span>
          </div>
        </div>

        {/* Playground Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left / Input Section */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Send className="w-4 h-4 text-emerald-400" />
                  Inference Query
                </label>
                <span className="text-xs text-slate-400">Deterministic Tool or LLM</span>
              </div>

              {/* Text Input */}
              <div className="relative">
                <textarea
                  rows={4}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter a calculation (e.g. 15 * 8 + 30) or any natural language prompt..."
                  className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl p-3.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-sm transition-all resize-none"
                />
              </div>

              {/* Sample Queries */}
              <div>
                <div className="text-xs font-medium text-slate-400 mb-2 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  Try Sample Benchmarks:
                </div>
                <div className="flex flex-wrap gap-2">
                  {sampleQueries.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleExecute(item.q)}
                      className="px-2.5 py-1 rounded-lg text-xs bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 hover:text-white transition-all flex items-center gap-1"
                    >
                      <span>{item.label}</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                    </button>
                  ))}
                </div>
              </div>

              {/* Routing Preferences */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <label className="text-xs font-semibold text-slate-300">
                  Execution Path Directive
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                  {[
                    { id: "auto", label: "Auto (Control Plane)" },
                    { id: "deterministic_tool", label: "Deterministic Only" },
                    { id: "semantic_cache", label: "Semantic Cache" },
                    { id: "small_model", label: "Small Model (Local)" },
                    { id: "medium_model", label: "Medium (Cloud)" },
                    { id: "large_model", label: "Large (Cloud)" }
                  ].map((route) => (
                    <button
                      key={route.id}
                      type="button"
                      onClick={() => setPreferredRoute(route.id)}
                      className={`p-2 rounded-lg border text-left transition-all ${
                        preferredRoute === route.id
                          ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-300 font-medium'
                          : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:bg-slate-800/40'
                      }`}
                    >
                      {route.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <button
                onClick={() => handleExecute()}
                disabled={loading || !query.trim()}
                className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium text-sm transition-all shadow-lg shadow-emerald-900/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Routing Query...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    <span>Execute Inference Path</span>
                  </>
                )}
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-xs">
                <span className="font-semibold">Routing Error:</span> {error}
              </div>
            )}
          </div>

          {/* Right / Telemetry & Response Section */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5 flex flex-col h-full min-h-[420px]">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-teal-400" />
                  Execution Telemetry
                </h3>
                {response && (
                  response.cache_status === 'hit' ? (
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-emerald-400" /> Semantic Cache (HIT)
                    </span>
                  ) : response.cache_status === 'miss' ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-medium">
                      Cache MISS → {response.route}
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                      {response.route}
                    </span>
                  )
                )}
              </div>

              {response ? (
                <div className="space-y-5 flex-1 flex flex-col justify-between">
                  {/* Telemetry Metrics Grid */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-cyan-400" />
                        Execution Latency
                      </div>
                      <div className="text-lg font-bold text-white mt-1">
                        {response.execution_time_ms.toFixed(2)} <span className="text-xs text-slate-400 font-normal">ms</span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                        Cache Status
                      </div>
                      {response.cache_status === 'hit' ? (
                        <div className="text-base font-bold text-emerald-400 mt-1 flex items-center gap-1">
                          HIT <span className="text-xs text-slate-400 font-normal">({(response.cache_similarity ?? 1.0).toFixed(4)})</span>
                        </div>
                      ) : response.cache_status === 'miss' ? (
                        <div className="text-base font-semibold text-amber-400 mt-1">
                          MISS <span className="text-xs text-slate-400 font-normal">{response.cache_similarity ? `(${response.cache_similarity.toFixed(4)})` : '(No Match)'}</span>
                        </div>
                      ) : (
                        <div className="text-base font-semibold text-slate-400 mt-1">
                          BYPASSED <span className="text-xs text-slate-500 font-normal">(Tool)</span>
                        </div>
                      )}
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Server className="w-3.5 h-3.5 text-purple-400" />
                        Model Inference
                      </div>
                      <div className="text-sm font-semibold text-slate-200 mt-1 truncate">
                        {response.cache_status === 'hit' ? (
                          <span className="text-emerald-400 font-bold">Avoided (0 LLM Calls)</span>
                        ) : response.provider === 'deterministic' ? (
                          <span className="text-emerald-400">Avoided (Deterministic Tool)</span>
                        ) : (
                          response.model || response.provider
                        )}
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Zap className="w-3.5 h-3.5 text-amber-400" />
                        Token Usage
                      </div>
                      <div className="text-lg font-bold text-white mt-1">
                        {response.cache_status === 'hit' ? (
                          <span className="text-emerald-400">0 <span className="text-xs text-slate-400 font-normal">tokens (Cached)</span></span>
                        ) : (
                          <span>{response.token_usage?.total_tokens ?? 0} <span className="text-xs text-slate-400 font-normal">tokens</span></span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Output Answer */}
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-slate-400 flex items-center justify-between">
                      <span>Result</span>
                      <span className="text-[10px] text-slate-500 font-mono">Provider: {response.provider}</span>
                    </div>
                    <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 font-mono text-sm text-emerald-300 leading-relaxed whitespace-pre-wrap max-h-56 overflow-y-auto">
                      {response.answer}
                    </div>
                  </div>

                  {/* Metadata pill */}
                  {response.metadata && (
                    <div className="text-[11px] text-slate-400 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="font-semibold text-slate-300">Routing Metadata: </span>
                      {response.metadata.reasoning || JSON.stringify(response.metadata.complexity || {})}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500 space-y-3">
                  <div className="p-3 rounded-full bg-slate-800/50">
                    <Info className="w-6 h-6 text-slate-400" />
                  </div>
                  <p className="text-sm">Run an inference query to view real-time routing telemetry, model assignment, and token efficiency.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* System Registry Inspection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
          
          {/* Tools Registry */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 space-y-3">
            <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Calculator className="w-4 h-4 text-emerald-400" />
              Registered Deterministic Tools
            </h4>
            <div className="space-y-2">
              {tools.map((t, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-white capitalize">{t.name}</span>
                    <p className="text-[11px] text-slate-400">{t.description}</p>
                  </div>
                  <span className="px-2 py-0.5 text-[10px] rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    0 LLM Calls
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Model Profiles Catalog */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 space-y-3">
            <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Database className="w-4 h-4 text-teal-400" />
              Configured Model Profiles
            </h4>
            <div className="space-y-2">
              {models.map((m, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-white">{m.model_id}</span>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                        m.tier === 'small' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' :
                        m.tier === 'medium' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                      }`}>
                        {m.tier.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">{m.description}</p>
                  </div>
                  <span className="text-[10px] text-slate-500">
                    {m.is_local ? 'Local' : 'Cloud'}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </main>
    </div>
  );
}
