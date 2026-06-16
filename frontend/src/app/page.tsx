"use client";

import Link from "next/link";
import { Cpu, ShieldCheck, Database, Layers, ArrowRight } from "lucide-react";

export default function Home() {
  return (
    <main className="flex-1 min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/30 via-slate-950 to-slate-950 flex flex-col justify-center items-center px-4 relative overflow-hidden">
      {/* Background patterns */}
      <div className="absolute top-0 left-0 right-0 h-[500px] bg-[radial-gradient(circle_at_50%_-120%,rgba(59,130,246,0.15),transparent)] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-35" />

      <div className="max-w-4xl text-center space-y-8 relative z-10 animate-fade-in">
        {/* Badge */}
        <div className="inline-flex items-center space-x-2 bg-blue-500/10 border border-blue-500/20 px-3 py-1 rounded-full text-xs font-semibold text-blue-400">
          <Cpu className="w-3.5 h-3.5 animate-spin [animation-duration:8s]" />
          <span>LangGraph Multi-Agent Orchestrator</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Enterprise Intelligence with <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-emerald-400">
            Hybrid RAG & SQL
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Ask questions naturally. NexusAI decomposes, secures, and routes queries dynamically between unstructured corporate documents and SQL databases, displaying real-time agent traces.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link
            href="/chat"
            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-3.5 rounded-xl transition-all duration-200 shadow-lg shadow-blue-600/30 w-full sm:w-auto justify-center"
          >
            <span>Enter Chat Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/login?guest=true"
            className="flex items-center justify-center bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 font-semibold px-8 py-3.5 rounded-xl transition-colors duration-200 w-full sm:w-auto"
          >
            Try Guest Demo
          </Link>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-16">
          {/* Feature 1 */}
          <div className="glass-panel p-6 rounded-2xl text-left space-y-3 relative group hover:border-blue-500/50 transition-all duration-300">
            <div className="bg-blue-500/10 text-blue-400 p-2.5 rounded-xl w-fit">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-white text-lg">Input Guardrails</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Detects SQL injections, prompt manipulation, and PII leaks before sending requests to the core LLM pipelines.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="glass-panel p-6 rounded-2xl text-left space-y-3 relative group hover:border-emerald-500/50 transition-all duration-300">
            <div className="bg-emerald-500/10 text-emerald-400 p-2.5 rounded-xl w-fit">
              <Database className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-white text-lg">Structured Text-to-SQL</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Introspects tables, compiles clean SQL statements, executes, and automatically renders interactive Plotly visualizations.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="glass-panel p-6 rounded-2xl text-left space-y-3 relative group hover:border-purple-500/50 transition-all duration-300">
            <div className="bg-purple-500/10 text-purple-400 p-2.5 rounded-xl w-fit">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-white text-lg">Real-Time Traces</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Complete observability timeline tracing node executions, latency splits, token consumption, and evaluation checks.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
