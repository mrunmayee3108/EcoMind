import React from 'react';
import { 
  Leaf, 
  ShieldCheck, 
  AlertTriangle, 
  Info, 
  Layers, 
  Database, 
  Activity 
} from 'lucide-react';
import type { DashboardEnvironmentResponse } from '../types.ts';

interface DashboardEnvironmentProps {
  environment: DashboardEnvironmentResponse | null;
  loading: boolean;
}

export const DashboardEnvironment: React.FC<DashboardEnvironmentProps> = ({
  environment,
  loading
}) => {
  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">Loading environmental accounting metrics...</p>
      </div>
    );
  }

  if (!environment || environment.total_requests === 0) {
    return (
      <div className="py-20 text-center space-y-3 bg-slate-900/40 rounded-2xl border border-slate-800 p-8">
        <div className="p-3 rounded-full bg-slate-800 inline-block text-slate-400">
          <Leaf className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-slate-200">No Environmental Telemetry Captured</h4>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Execute queries in the Playground to record authentic energy measurements and validated emissions estimates.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Empirical Protocol Banner */}
      <div className="p-4 rounded-2xl bg-emerald-950/30 border border-emerald-500/20 flex items-start gap-3">
        <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 mt-0.5">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h4 className="text-xs font-bold text-emerald-300 uppercase tracking-wider">
            Strict Environmental Accounting & Anti-Fabrication Safeguards
          </h4>
          <p className="text-xs text-slate-300 leading-relaxed">
            EcoMind never invents or fabricates environmental data. Missing values remain explicitly unmeasured (null), physical on-device hardware telemetry is segregated from cloud model estimates, and operational carbon requires authentic energy and valid grid emissions factors.
          </p>
        </div>
      </div>

      {/* Energy Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Measured Energy */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-emerald-400" />
              Hardware Measured Energy
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              MEASURED
            </span>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">
              {environment.measured_energy_joules.toFixed(3)} <span className="text-sm font-normal text-slate-400">J</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              ({environment.measured_energy_kwh.toExponential(4)} kWh)
            </div>
          </div>
          <div className="pt-2 border-t border-slate-800/80 text-xs text-slate-400 flex items-center justify-between">
            <span>Direct Sensor Records:</span>
            <strong className="text-white">{environment.records_with_measured_energy}</strong>
          </div>
        </div>

        {/* Estimated Energy */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Database className="w-4 h-4 text-amber-400" />
              Model-Estimated Energy
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
              ESTIMATED
            </span>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">
              {environment.estimated_energy_joules.toFixed(3)} <span className="text-sm font-normal text-slate-400">J</span>
            </div>
            <div className="text-xs text-slate-400 mt-1">
              ({environment.estimated_energy_kwh.toExponential(4)} kWh)
            </div>
          </div>
          <div className="pt-2 border-t border-slate-800/80 text-xs text-slate-400 flex items-center justify-between">
            <span>Estimation Model Records:</span>
            <strong className="text-white">{environment.records_with_estimated_energy}</strong>
          </div>
        </div>

        {/* Operational Carbon */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Leaf className="w-4 h-4 text-cyan-400" />
              Operational Carbon
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold">
              CALCULATED
            </span>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">
              {environment.total_carbon_gco2e.toFixed(6)} <span className="text-sm font-normal text-slate-400">gCO2e</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              From measured energy: {environment.carbon_from_measured_energy_gco2e.toFixed(6)} gCO2e
            </div>
          </div>
          <div className="pt-2 border-t border-slate-800/80 text-xs text-slate-400 flex items-center justify-between">
            <span>Calculated Carbon Records:</span>
            <strong className="text-white">{environment.records_with_carbon}</strong>
          </div>
        </div>
      </div>

      {/* Disclosures & Scope Boundary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Measurement Boundaries */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-teal-400" />
            Active Physical Measurement Boundaries
          </h4>
          <p className="text-xs text-slate-300 leading-relaxed">
            {environment.scope_boundary_notice}
          </p>
          <div className="pt-2 border-t border-slate-800 text-xs space-y-1.5">
            <span className="text-slate-400 font-semibold">Scope Distribution:</span>
            <div className="flex flex-wrap gap-2">
              {Object.entries(environment.measurement_scopes_breakdown).map(([scope, count]) => (
                <span key={scope} className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300">
                  {scope}: <strong className="text-emerald-400">{count}</strong>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Water Disclosure & Grid Sources */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            Water Disclosure & Grid Intensity Sources
          </h4>
          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-amber-400 font-semibold">
              <AlertTriangle className="w-3.5 h-3.5" /> Water Accounting Status
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              {environment.water_disclosure}
            </p>
          </div>
          <div className="text-xs space-y-1.5 pt-1">
            <span className="text-slate-400 font-semibold">Grid Intensity Authorities:</span>
            <div className="flex flex-wrap gap-2">
              {Object.keys(environment.grid_sources_breakdown).length > 0 ? (
                Object.entries(environment.grid_sources_breakdown).map(([src, count]) => (
                  <span key={src} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-cyan-400">
                    {src} ({count})
                  </span>
                ))
              ) : (
                <span className="text-slate-500 text-xs italic">No regional grid factor active</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
