import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  FileText, 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  Clock, 
  Zap, 
  Activity, 
  ExternalLink, 
  AlertCircle,
  Filter
} from 'lucide-react';
import type { 
  PaginatedReceiptsResponse, 
  ReceiptSummaryItem, 
  EcoReceipt 
} from '../types.ts';

interface ReceiptsExplorerProps {
  apiBase: string;
  onSelectReceipt: (receipt: EcoReceipt) => void;
}

export const ReceiptsExplorer: React.FC<ReceiptsExplorerProps> = ({
  apiBase,
  onSelectReceipt
}) => {
  const [data, setData] = useState<PaginatedReceiptsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [executionPath, setExecutionPath] = useState<string>('all');
  const [status, setStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const fetchReceipts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = {
        page,
        page_size: pageSize
      };
      if (executionPath !== 'all') params.execution_path = executionPath;
      if (status !== 'all') params.status = status;

      const res = await axios.get<PaginatedReceiptsResponse>(`${apiBase}/dashboard/receipts`, { params });
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load activity records');
    } finally {
      setLoading(false);
    }
  }, [apiBase, page, pageSize, executionPath, status]);

  useEffect(() => {
    fetchReceipts();
  }, [fetchReceipts]);

  const handleInspect = async (requestId: string) => {
    try {
      const res = await axios.get<EcoReceipt>(`${apiBase}/dashboard/receipts/${requestId}`);
      onSelectReceipt(res.data);
    } catch (err: any) {
      alert(`Could not load full receipt: ${err.message}`);
    }
  };

  const filteredItems = (data?.items || []).filter((item: ReceiptSummaryItem) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.request_id.toLowerCase().includes(term) ||
      item.receipt_id.toLowerCase().includes(term) ||
      (item.query_preview && item.query_preview.toLowerCase().includes(term)) ||
      item.route.toLowerCase().includes(term) ||
      item.provider.toLowerCase().includes(term)
    );
  });

  const getMethodBadge = (path: string) => {
    switch (path) {
      case 'deterministic_tool':
        return { text: 'Built-in Tool', badge: 'bg-cyan-50 text-cyan-800 border-cyan-200' };
      case 'semantic_cache':
        return { text: 'Saved Response', badge: 'bg-emerald-50 text-emerald-800 border-emerald-200' };
      default:
        return { text: 'AI Model', badge: 'bg-indigo-50 text-indigo-800 border-indigo-200' };
    }
  };

  return (
    <div className="space-y-5">
      {/* Search and Filters Bar */}
      <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3.5">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search queries, models, or IDs..."
            className="w-full pl-9 pr-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition-all"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          {/* Method Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
            <span className="text-slate-500">Method:</span>
            <select
              value={executionPath}
              onChange={(e) => {
                setExecutionPath(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-emerald-600"
            >
              <option value="all">All Methods</option>
              <option value="deterministic_tool">Built-in Tools</option>
              <option value="semantic_cache">Saved Responses</option>
              <option value="model_inference">AI Models</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500">Status:</span>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-emerald-600"
            >
              <option value="all">All Statuses</option>
              <option value="SUCCESS">Success</option>
              <option value="PARTIAL">Partial</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* History Table Container */}
      <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-24 flex flex-col items-center justify-center space-y-2">
            <div className="w-6 h-6 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-slate-500">Fetching activity records...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <FileText className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-xs text-slate-500">No activity records match your filter criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="p-3.5 font-semibold">Time</th>
                  <th className="p-3.5 font-semibold">User Prompt</th>
                  <th className="p-3.5 font-semibold">Method</th>
                  <th className="p-3.5 font-semibold">Route & Model</th>
                  <th className="p-3.5 font-semibold">Response Time</th>
                  <th className="p-3.5 font-semibold">AI Tokens</th>
                  <th className="p-3.5 font-semibold">API Fee</th>
                  <th className="p-3.5 font-semibold">Energy & Carbon</th>
                  <th className="p-3.5 font-semibold text-right">Receipt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredItems.map((item) => {
                  const badgeInfo = getMethodBadge(item.execution_path);
                  return (
                    <tr key={item.request_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="p-3.5 font-mono text-slate-500 whitespace-nowrap">
                        <div className="text-slate-900 font-medium text-[11px]">
                          {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {new Date(item.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                        </div>
                      </td>
                      <td className="p-3.5 max-w-[200px]">
                        <span className="text-slate-800 font-medium truncate block text-[11px]" title={item.query_preview || ''}>
                          {item.query_preview ? `"${item.query_preview}"` : '—'}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-medium border ${badgeInfo.badge}`}>
                          {badgeInfo.text}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <div className="text-slate-900 font-medium truncate max-w-[140px]" title={item.route}>
                          {item.route}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {item.provider} {item.model ? `• ${item.model}` : ''}
                        </div>
                      </td>
                      <td className="p-3.5 font-mono text-cyan-700">
                        <span className="flex items-center gap-1 font-medium">
                          <Clock className="w-3 h-3 text-cyan-600" />
                          {item.execution_time_ms.toFixed(1)} ms
                        </span>
                      </td>
                      <td className="p-3.5 font-mono">
                        {item.total_tokens !== null ? (
                          <span className="flex items-center gap-1 text-slate-700">
                            <Zap className="w-3 h-3 text-amber-500" />
                            {item.total_tokens}
                          </span>
                        ) : (
                          <span className="text-slate-400">0 (Tool)</span>
                        )}
                      </td>
                      <td className="p-3.5 font-mono">
                        {item.is_zero_external_api_charge ? (
                          <span className="text-emerald-700 font-semibold">$0.00</span>
                        ) : item.cost_usd !== null ? (
                          <span className="text-slate-700">${item.cost_usd.toFixed(6)}</span>
                        ) : (
                          <span className="text-slate-400">N/A</span>
                        )}
                      </td>
                      <td className="p-3.5 text-[11px]">
                        {item.is_energy_measured ? (
                          <span className="text-emerald-700 flex items-center gap-1 font-medium">
                            <Activity className="w-3 h-3" /> Measured ({item.energy_joules?.toFixed(1)} J)
                          </span>
                        ) : item.is_energy_estimated ? (
                          <span className="text-amber-700">Estimated ({item.energy_joules?.toFixed(1)} J)</span>
                        ) : (
                          <span className="text-slate-400">Unavailable</span>
                        )}
                      </td>
                      <td className="p-3.5 text-right whitespace-nowrap">
                        <button
                          onClick={() => handleInspect(item.request_id)}
                          className="px-3 py-1 rounded-xl bg-slate-50 hover:bg-emerald-50 text-slate-700 hover:text-emerald-700 border border-slate-200 hover:border-emerald-300 text-xs font-medium inline-flex items-center gap-1.5 transition-all shadow-2xs"
                        >
                          <FileText className="w-3 h-3 text-emerald-600" />
                          <span>Receipt</span>
                          <ExternalLink className="w-2.5 h-2.5 text-slate-400" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {data && data.total_pages > 1 && (
          <div className="px-5 py-3.5 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data.total_count)} of {data.total_count} records
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded-lg border border-slate-200 hover:bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-slate-700 font-medium">
                Page {page} of {data.total_pages}
              </span>
              <button
                disabled={page >= data.total_pages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded-lg border border-slate-200 hover:bg-white text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
