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
  AlertCircle 
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
      setError(err.response?.data?.detail || err.message || 'Failed to load receipts');
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

  return (
    <div className="space-y-5">
      {/* Search and Filters Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by ID, query, route, or provider..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          {/* Execution Path Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400">Path:</span>
            <select
              value={executionPath}
              onChange={(e) => {
                setExecutionPath(e.target.value);
                setPage(1);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">All Paths</option>
              <option value="deterministic_tool">Deterministic Tool</option>
              <option value="semantic_cache">Semantic Cache</option>
              <option value="model_inference">Model Inference</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400">Status:</span>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">All Statuses</option>
              <option value="SUCCESS">Success</option>
              <option value="FAILED">Failed</option>
              <option value="PARTIAL">Partial</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Receipts Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-2">
            <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-slate-400">Fetching Eco Receipts...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <FileText className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs text-slate-400">No receipts match your filter criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="p-3">Timestamp / IDs</th>
                  <th className="p-3">Query Preview</th>
                  <th className="p-3">Execution Path</th>
                  <th className="p-3">Route / Provider</th>
                  <th className="p-3">Latency</th>
                  <th className="p-3">Tokens</th>
                  <th className="p-3">API Cost</th>
                  <th className="p-3">Energy / Carbon</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {filteredItems.map((item) => (
                  <tr key={item.request_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="p-3 font-mono">
                      <div className="text-white text-[11px]">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </div>
                      <div className="text-[10px] text-slate-500 truncate max-w-[130px]">
                        {item.request_id}
                      </div>
                    </td>
                    <td className="p-3 max-w-[200px]">
                      <span className="text-slate-300 truncate block text-[11px]" title={item.query_preview || ''}>
                        {item.query_preview || '—'}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-medium ${
                        item.execution_path === 'deterministic_tool' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' :
                        item.execution_path === 'semantic_cache' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                      }`}>
                        {item.execution_path}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="text-slate-200 font-medium truncate max-w-[150px]">{item.route}</div>
                      <div className="text-[10px] text-slate-500">{item.provider} {item.model ? `• ${item.model}` : ''}</div>
                    </td>
                    <td className="p-3 font-mono text-cyan-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-cyan-500" />
                        {item.execution_time_ms.toFixed(1)} ms
                      </span>
                    </td>
                    <td className="p-3 font-mono">
                      {item.total_tokens !== null ? (
                        <span className="flex items-center gap-1 text-slate-300">
                          <Zap className="w-3 h-3 text-amber-400" />
                          {item.total_tokens}
                        </span>
                      ) : (
                        <span className="text-slate-500">Unmeasured</span>
                      )}
                    </td>
                    <td className="p-3 font-mono">
                      {item.is_zero_external_api_charge ? (
                        <span className="text-emerald-400 font-semibold">$0 API Charge</span>
                      ) : item.cost_usd !== null ? (
                        <span className="text-slate-300">${item.cost_usd.toFixed(6)}</span>
                      ) : (
                        <span className="text-slate-500">N/A</span>
                      )}
                    </td>
                    <td className="p-3 text-[11px]">
                      {item.is_energy_measured ? (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <Activity className="w-3 h-3" /> Measured ({item.energy_joules?.toFixed(1)} J)
                        </span>
                      ) : item.is_energy_estimated ? (
                        <span className="text-amber-400">Estimated ({item.energy_joules?.toFixed(1)} J)</span>
                      ) : (
                        <span className="text-slate-500">Unavailable</span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleInspect(item.request_id)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 text-xs font-medium inline-flex items-center gap-1 transition-colors"
                      >
                        <FileText className="w-3 h-3" />
                        <span>Inspect</span>
                        <ExternalLink className="w-2.5 h-2.5 text-slate-400" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {data && data.total_pages > 1 && (
          <div className="p-3.5 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs text-slate-400">
            <span>
              Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data.total_count)} of {data.total_count} records
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-slate-300 font-medium">
                Page {page} of {data.total_pages}
              </span>
              <button
                disabled={page >= data.total_pages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed"
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
