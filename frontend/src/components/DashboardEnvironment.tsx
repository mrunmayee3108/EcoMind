import React from 'react';
import { 
  Leaf, 
  ShieldCheck, 
  Info, 
  Layers, 
  Database, 
  Activity,
  Droplets,
  Zap
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
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-500 font-medium">Loading environmental metrics...</p>
      </div>
    );
  }

  if (!environment || environment.total_requests === 0) {
    return (
      <div className="py-20 text-center space-y-4 bg-white/70 backdrop-blur-md rounded-3xl border border-slate-200/80 p-8 shadow-sm">
        <div className="p-3.5 rounded-2xl bg-emerald-50 text-emerald-600 inline-block">
          <Leaf className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h4 className="text-base font-semibold text-slate-900">No Environmental Telemetry Recorded</h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Run queries in the Playground to record authentic physical energy measurements and validated emissions calculations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Integrity & Anti-Fabrication Banner */}
      <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200/80 flex items-start gap-3.5">
        <div className="p-2 rounded-xl bg-emerald-600 text-white shrink-0 shadow-sm shadow-emerald-600/20 mt-0.5">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h4 className="text-sm font-bold text-emerald-950">
            Scientific Integrity Guarantee: No Fabricated Constants
          </h4>
          <p className="text-xs text-emerald-800 leading-relaxed">
            EcoMind never invents or guesses environmental metrics. Direct hardware measurements from on-device sensors are strictly segregated from peer-reviewed cloud estimation models. Missing data is always explicitly marked as <strong className="font-semibold">Unavailable</strong> rather than assumed to be zero.
          </p>
        </div>
      </div>

      {/* Primary Energy & Carbon Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Measured Energy */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-3 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-emerald-600" />
              Direct Hardware Energy
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
              MEASURED
            </span>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 tracking-tight">
              {environment.measured_energy_joules.toFixed(3)} <span className="text-sm font-normal text-slate-500">Joules</span>
            </div>
            <div className="text-xs text-slate-500 mt-1 font-mono">
              {environment.measured_energy_kwh.toExponential(4)} kWh
            </div>
          </div>
          <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
            <span>Direct Sensor Records:</span>
            <strong className="text-slate-900 font-semibold">{environment.records_with_measured_energy}</strong>
          </div>
        </div>

        {/* Estimated Energy */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-3 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Database className="w-4 h-4 text-amber-600" />
              Model-Estimated Energy
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-semibold">
              ESTIMATED
            </span>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 tracking-tight">
              {environment.estimated_energy_joules.toFixed(3)} <span className="text-sm font-normal text-slate-500">Joules</span>
            </div>
            <div className="text-xs text-slate-500 mt-1 font-mono">
              {environment.estimated_energy_kwh.toExponential(4)} kWh
            </div>
          </div>
          <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
            <span>Model-Derived Records:</span>
            <strong className="text-slate-900 font-semibold">{environment.records_with_estimated_energy}</strong>
          </div>
        </div>

        {/* Operational Carbon */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-3 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Leaf className="w-4 h-4 text-cyan-600" />
              Operational Carbon
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 font-semibold">
              CALCULATED
            </span>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 tracking-tight">
              {environment.total_carbon_gco2e.toFixed(6)} <span className="text-sm font-normal text-slate-500">gCO₂e</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              From measured energy: {environment.carbon_from_measured_energy_gco2e.toFixed(6)} gCO₂e
            </div>
          </div>
          <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
            <span>Emissions Records:</span>
            <strong className="text-slate-900 font-semibold">{environment.records_with_carbon}</strong>
          </div>
        </div>
      </div>

      {/* Measurement Boundary & Water Disclosure Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Physical Boundaries */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-teal-600" />
            Physical Measurement Boundaries
          </h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            {environment.scope_boundary_notice}
          </p>
          <div className="pt-2 border-t border-slate-100 text-xs space-y-2">
            <span className="text-slate-500 font-semibold">Active Scopes Recorded:</span>
            <div className="flex flex-wrap gap-2">
              {Object.entries(environment.measurement_scopes_breakdown).map(([scope, count]) => (
                <span key={scope} className="px-2.5 py-1 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
                  {scope.replace(/_/g, ' ')}: <strong className="text-emerald-700 font-bold">{count}</strong>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Water Cooling & Grid Emissions */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            Water Cooling & Regional Electricity Grid
          </h4>
          
          <div className="p-3.5 rounded-xl bg-amber-50/60 border border-amber-200/70 space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-amber-900 font-semibold">
              <Droplets className="w-3.5 h-3.5 text-blue-500" /> Water Accounting Disclosure
            </div>
            <p className="text-xs text-amber-800 leading-relaxed">
              {environment.water_disclosure}
            </p>
          </div>

          <div className="text-xs space-y-1.5 pt-1">
            <span className="text-slate-500 font-semibold flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-600" /> Regional Grid Authorities Applied:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {Object.keys(environment.grid_sources_breakdown).length > 0 ? (
                Object.entries(environment.grid_sources_breakdown).map(([src, count]) => (
                  <span key={src} className="px-2 py-0.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
                    {src} ({count})
                  </span>
                ))
              ) : (
                <span className="text-slate-400 text-xs italic">Default or static regional grid factor</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
