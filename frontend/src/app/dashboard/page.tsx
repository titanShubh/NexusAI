"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { analytics, getToken } from "@/services/api";
import {
  Loader2,
  Clock,
  Cpu,
  ShieldAlert,
  Coins,
  Activity,
  Award,
  TrendingUp
} from "lucide-react";

export default function Dashboard() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Auth guard
    if (!getToken()) {
      router.push("/login");
      return;
    }

    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await analytics.getDashboard();
      setMetrics(data);
    } catch (e) {
      console.error("Failed to load dashboard metrics:", e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            <p className="text-slate-400 text-sm">Querying trace database...</p>
          </div>
        </main>
      </div>
    );
  }

  // Calculate percentages for route distribution
  const total = metrics?.total_queries || 0;
  const dist = metrics?.agent_distribution || {};
  const getPct = (val: number) => (total > 0 ? Math.round((val / total) * 100) : 0);

  const routeColors: any = {
    rag: "bg-blue-500",
    sql: "bg-emerald-500",
    hybrid: "bg-purple-500",
    direct: "bg-slate-500"
  };

  const routeLabels: any = {
    rag: "RAG Engine",
    sql: "Text-to-SQL",
    hybrid: "Hybrid (Parallel)",
    direct: "Direct LLM"
  };

  // Find max confidence bucket for SVG scale
  const histogram = metrics?.confidence_histogram || {};
  const histogramValues: number[] = Object.values(histogram);
  const maxHistVal = Math.max(...histogramValues, 1);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col overflow-y-auto p-8">
        <div className="max-w-6xl w-full mx-auto space-y-8 animate-fade-in">
          
          {/* Header */}
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-3xl font-bold text-white tracking-tight">Observability Dashboard</h2>
              <p className="text-slate-400 mt-1">Real-time system telemetry and agent diagnostic reports.</p>
            </div>
            <button
              onClick={loadDashboard}
              className="flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-semibold px-4 py-2 rounded-xl transition-all text-xs"
            >
              <Activity className="w-3.5 h-3.5 text-blue-500" />
              <span>Refresh Telemetry</span>
            </button>
          </div>

          {/* Metric cards grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            
            {/* Metric 1 */}
            <div className="glass-panel p-6 rounded-2xl flex items-center space-x-4">
              <div className="bg-blue-500/10 text-blue-400 p-3 rounded-xl">
                <Cpu className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Total Queries</span>
                <span className="text-2xl font-bold text-white block mt-0.5">{metrics?.total_queries || 0}</span>
              </div>
            </div>

            {/* Metric 2 */}
            <div className="glass-panel p-6 rounded-2xl flex items-center space-x-4">
              <div className="bg-emerald-500/10 text-emerald-400 p-3 rounded-xl">
                <Clock className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Avg Latency</span>
                <span className="text-2xl font-bold text-white block mt-0.5">
                  {metrics?.avg_latency_ms ? `${metrics.avg_latency_ms} ms` : "N/A"}
                </span>
              </div>
            </div>

            {/* Metric 3 */}
            <div className="glass-panel p-6 rounded-2xl flex items-center space-x-4">
              <div className="bg-purple-500/10 text-purple-400 p-3 rounded-xl">
                <Coins className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Token Cost</span>
                <span className="text-2xl font-bold text-white block mt-0.5">
                  {metrics?.total_tokens_used ? metrics.total_tokens_used.toLocaleString() : 0}
                </span>
              </div>
            </div>

            {/* Metric 4 */}
            <div className="glass-panel p-6 rounded-2xl flex items-center space-x-4">
              <div className="bg-amber-500/10 text-amber-400 p-3 rounded-xl">
                <Award className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Confidence Rating</span>
                <span className="text-2xl font-bold text-white block mt-0.5">
                  {total > 0 ? "Production" : "Pending"}
                </span>
              </div>
            </div>

          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            
            {/* Left Box: Route Distribution */}
            <div className="lg:col-span-6 glass-panel p-6 rounded-2xl">
              <h3 className="font-bold text-white mb-6 flex items-center space-x-2">
                <TrendingUp className="w-4.5 h-4.5 text-blue-500" />
                <span>Agent Execution Distribution</span>
              </h3>

              {total === 0 ? (
                <div className="text-center py-12 text-slate-500 text-sm">
                  Send chat queries to accumulate routing distribution statistics.
                </div>
              ) : (
                <div className="space-y-5">
                  {Object.keys(dist).map((route) => {
                    const count = dist[route];
                    const pct = getPct(count);
                    const color = routeColors[route] || "bg-slate-500";
                    const label = routeLabels[route] || route;
                    return (
                      <div key={route} className="space-y-1.5">
                        <div className="flex justify-between text-xs font-semibold">
                          <span className="text-slate-300">{label}</span>
                          <span className="text-slate-500">
                            {count} queries ({pct}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden">
                          <div
                            className={`${color} h-full rounded-full transition-all duration-500`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Box: Confidence Histogram SVG */}
            <div className="lg:col-span-6 glass-panel p-6 rounded-2xl">
              <h3 className="font-bold text-white mb-6 flex items-center space-x-2">
                <ShieldAlert className="w-4.5 h-4.5 text-emerald-500" />
                <span>Validation Confidence Distribution</span>
              </h3>

              {total === 0 ? (
                <div className="text-center py-12 text-slate-500 text-sm">
                  Confidence statistics will compile as evaluators score queries.
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  {/* Clean responsive SVG bar chart */}
                  <svg className="w-full h-48 bg-slate-900/10 rounded-xl" viewBox="0 0 400 160">
                    {/* Draw Gridlines */}
                    <line x1="40" y1="20" x2="380" y2="20" stroke="#1e293b" strokeWidth="1" strokeDasharray="4" />
                    <line x1="40" y1="70" x2="380" y2="70" stroke="#1e293b" strokeWidth="1" strokeDasharray="4" />
                    <line x1="40" y1="120" x2="380" y2="120" stroke="#1e293b" strokeWidth="1" strokeDasharray="4" />
                    
                    {/* X axis */}
                    <line x1="40" y1="130" x2="380" y2="130" stroke="#334155" strokeWidth="1" />
                    
                    {/* Render bars dynamically */}
                    {Object.keys(histogram).map((bucket, bIdx) => {
                      const count = histogram[bucket];
                      // Calculate height of bar relative to maximum count
                      const maxBarHeight = 100;
                      const height = (count / maxHistVal) * maxBarHeight;
                      const x = 60 + bIdx * 65;
                      const y = 130 - height;
                      
                      return (
                        <g key={bucket} className="group">
                          {/* Hover Tooltip/Value */}
                          <text
                            x={x + 18}
                            y={y - 6}
                            fill="#f8fafc"
                            fontSize="9"
                            fontWeight="bold"
                            textAnchor="middle"
                            className="opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                          >
                            {count}
                          </text>

                          {/* Bar */}
                          <rect
                            x={x}
                            y={y}
                            width="36"
                            height={height}
                            fill="url(#emerald-grad)"
                            rx="4"
                            className="transition-all duration-300 hover:opacity-85 cursor-pointer"
                          />

                          {/* X labels */}
                          <text
                            x={x + 18}
                            y="145"
                            fill="#94a3b8"
                            fontSize="9"
                            textAnchor="middle"
                          >
                            {bucket}
                          </text>
                        </g>
                      );
                    })}
                    
                    <defs>
                      <linearGradient id="emerald-grad" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#10b981" />
                        <stop offset="100%" stopColor="#047857" />
                      </linearGradient>
                    </defs>
                  </svg>
                  
                  <span className="text-[10px] text-slate-500 mt-3 uppercase tracking-wider font-semibold">
                    Confidence Range (0.0 ➔ 1.0)
                  </span>
                </div>
              )}
            </div>

          </div>

        </div>
      </main>
    </div>
  );
}
