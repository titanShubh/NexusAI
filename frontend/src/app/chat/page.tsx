"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { chat, getToken } from "@/services/api";
import {
  MessageSquare,
  Plus,
  Send,
  Loader2,
  AlertCircle,
  Database,
  Cpu,
  CheckCircle,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Shield,
  HelpCircle,
  ArrowRight,
  TrendingUp,
  FileText
} from "lucide-react";

interface Message {
  id: string;
  role: string;
  content: string;
  agent_name?: string;
  sources_json?: any[];
  sql_query?: string;
  chart_url?: string;
  confidence_score?: number;
  latency_ms?: number;
  tokens_used?: number;
  created_at: string;
  // UI states
  showTrace?: boolean;
  agent_trace?: any[];
}

export default function Chat() {
  const router = useRouter();
  const [conversations, setConversations] = useState<any[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Real-time SSE node state tracking
  const [activeSteps, setActiveSteps] = useState<any[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auth guard
    if (!getToken()) {
      router.push("/login");
      return;
    }

    loadSessions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeSteps]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadSessions = async (selectFirst = true) => {
    try {
      const list = await chat.listConversations();
      setConversations(list);
      
      if (selectFirst && list.length > 0) {
        handleSelectConversation(list[0].id);
      } else if (list.length === 0) {
        // Create initial session
        handleNewSession();
      }
    } catch (e) {
      console.error("Failed to load conversations:", e);
    }
  };

  const handleSelectConversation = async (id: string) => {
    setActiveId(id);
    setMessages([]);
    setError("");
    setActiveSteps([]);
    
    try {
      const data = await chat.getConversation(id);
      setMessages(data.messages || []);
    } catch (e) {
      console.error("Failed to load message history:", e);
    }
  };

  const handleNewSession = async () => {
    try {
      const newSession = await chat.createConversation();
      setConversations((prev) => [newSession, ...prev]);
      handleSelectConversation(newSession.id);
    } catch (e) {
      setError("Failed to create new chat session.");
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || loading || !activeId) return;

    const queryText = inputText;
    setInputText("");
    setLoading(true);
    setError("");
    setActiveSteps([]);

    // 1. Add user message locally
    const userMessage: Message = {
      id: Math.random().toString(),
      role: "user",
      content: queryText,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);

    // Initialize streaming steps list
    const initialSteps = [
      { name: "Guardrails", status: "running" },
      { name: "Supervisor", status: "pending" },
      { name: "Execution", status: "pending" },
      { name: "Eval Engine", status: "pending" },
      { name: "Response Gen", status: "pending" }
    ];
    setActiveSteps(initialSteps);

    // 2. Open SSE Stream
    chat.streamChat(
      queryText,
      activeId,
      (stepData) => {
        // Step trace callback
        setActiveSteps((prev) =>
          prev.map((step) => {
            if (step.name === stepData.node_name) {
              return { ...step, status: stepData.status, latency: stepData.latency_ms };
            }
            // Transition next steps
            if (stepData.node_name === "Guardrails" && step.name === "Supervisor") {
              return { ...step, status: stepData.status === "failed" ? "skipped" : "running" };
            }
            if (stepData.node_name === "Supervisor" && step.name === "Execution") {
              return { ...step, status: "running" };
            }
            if (
              (stepData.node_name === "RAGAgent" || stepData.node_name === "SQLAgent" || stepData.node_name === "AnalyticsAgent") &&
              step.name === "Execution"
            ) {
              return { ...step, status: "completed" };
            }
            if (stepData.node_name === "Execution" && step.name === "Eval Engine") {
              return { ...step, status: "running" };
            }
            if (stepData.node_name === "EvalAgent" && step.name === "Eval Engine") {
              return { ...step, status: "completed" };
            }
            if (stepData.node_name === "EvalAgent" && step.name === "Response Gen") {
              return { ...step, status: "running" };
            }
            return step;
          })
        );
      },
      (finalData) => {
        // Final consolidated response callback
        const assistantMessage: Message = {
          id: Math.random().toString(),
          role: "assistant",
          content: finalData.content,
          agent_name: "NexusOrchestrator",
          sources_json: finalData.sources,
          sql_query: finalData.sql_query,
          chart_url: finalData.chart_url,
          confidence_score: finalData.confidence_score,
          agent_trace: finalData.agent_trace,
          created_at: new Date().toISOString()
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setLoading(false);
        setActiveSteps([]);
        loadSessions(false); // Refresh conversation titles
      },
      (err) => {
        setError(err || "Failed to process query.");
        setLoading(false);
        setActiveSteps([]);
      }
    );
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    if (score >= 0.5) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    return "bg-red-500/10 text-red-400 border-red-500/20";
  };

  const toggleTrace = (messageId: string) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, showTrace: !msg.showTrace } : msg))
    );
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Sidebar />

      {/* Chat Sessions List (Sub-sidebar) */}
      <div className="w-64 bg-slate-900/50 border-r border-slate-800 flex flex-col h-screen shrink-0">
        <div className="p-4 border-b border-slate-800">
          <button
            onClick={handleNewSession}
            className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 px-4 rounded-xl transition-all duration-200 shadow-md shadow-blue-600/15"
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm">New Session</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {conversations.map((conv) => {
            const isActive = activeId === conv.id;
            return (
              <button
                key={conv.id}
                onClick={() => handleSelectConversation(conv.id)}
                className={`w-full flex items-center space-x-3 px-3 py-3 rounded-xl text-left transition-colors ${
                  isActive
                    ? "bg-slate-800 text-white font-medium border border-slate-700/50"
                    : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                }`}
              >
                <MessageSquare className="w-4 h-4 text-blue-500 shrink-0" />
                <span className="text-xs truncate w-full">{conv.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Chat Workspace */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden bg-slate-950/20">
        
        {/* Error notification */}
        {error && (
          <div className="bg-red-500/10 border-b border-red-500/20 text-red-400 text-xs px-6 py-3 flex items-center space-x-2 shrink-0">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}

        {/* Message Log */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4">
              <div className="bg-blue-600/10 p-4 rounded-2xl text-blue-400">
                <Sparkles className="w-8 h-8" />
              </div>
              <h3 className="font-bold text-white text-lg">Hybrid Agent Assistant</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Provide business questions like:
              </p>
              <div className="w-full space-y-2 text-xs">
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-left text-slate-300">
                  "Who is the customer segment with the highest lifetime value?"
                </div>
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-left text-slate-300">
                  "Show me a line chart of sales amounts over time."
                </div>
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-left text-slate-300">
                  "Compare monthly database sales with the revenue targets in the PDF doc."
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={msg.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-in`}
                >
                  <div
                    className={`max-w-3xl w-full rounded-2xl p-6 ${
                      isUser
                        ? "bg-blue-600 text-white max-w-xl"
                        : "glass-panel text-slate-100"
                    }`}
                  >
                    {/* Role Header */}
                    {!isUser && (
                      <div className="flex items-center justify-between mb-4 border-b border-slate-800/50 pb-2">
                        <div className="flex items-center space-x-2 text-xs text-blue-400 font-semibold uppercase tracking-wider">
                          <Cpu className="w-3.5 h-3.5" />
                          <span>{msg.agent_name || "NexusOrchestrator"}</span>
                        </div>
                        {msg.confidence_score !== undefined && (
                          <div
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getConfidenceColor(
                              msg.confidence_score
                            )}`}
                          >
                            Confidence: {Math.round(msg.confidence_score * 100)}%
                          </div>
                        )}
                      </div>
                    )}

                    {/* Content */}
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </div>

                    {/* Cited RAG Sources */}
                    {!isUser && msg.sources_json && msg.sources_json.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-slate-800/40">
                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                          Cited Sources
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {msg.sources_json.map((src, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center px-2 py-1 rounded bg-slate-900 text-slate-400 text-xs border border-slate-800"
                            >
                              <FileText className="w-3 h-3 mr-1 text-blue-400" />
                              <span className="truncate max-w-[150px]">{src.filename} (Page {src.page_number})</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* SQL query visualizer */}
                    {!isUser && msg.sql_query && (
                      <div className="mt-4 bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-x-auto">
                        <div className="flex items-center space-x-2 text-[10px] text-emerald-400 font-bold uppercase tracking-wider mb-2">
                          <Database className="w-3 h-3" />
                          <span>Executed SQL Query</span>
                        </div>
                        <code className="text-xs font-mono text-slate-300">{msg.sql_query}</code>
                      </div>
                    )}

                    {/* Plotly base64 image visualization */}
                    {!isUser && msg.chart_url && (
                      <div className="mt-4 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/60 p-2">
                        <img
                          src={msg.chart_url}
                          alt="Aggregated SQL Chart Visualization"
                          className="w-full h-auto rounded-lg"
                        />
                      </div>
                    )}

                    {/* Observability trace dropdown trigger */}
                    {!isUser && msg.agent_trace && msg.agent_trace.length > 0 && (
                      <div className="mt-4 pt-2 border-t border-slate-800/40">
                        <button
                          onClick={() => toggleTrace(msg.id)}
                          className="flex items-center space-x-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                        >
                          {msg.showTrace ? (
                            <>
                              <ChevronUp className="w-3.5 h-3.5" />
                              <span>Hide Agent Traces</span>
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-3.5 h-3.5" />
                              <span>Inspect Execution Traces</span>
                            </>
                          )}
                        </button>

                        {/* Observability trace panel */}
                        {msg.showTrace && (
                          <div className="mt-4 space-y-4 animate-fade-in text-xs bg-slate-950/80 border border-slate-850 p-4 rounded-xl">
                            <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
                              <h4 className="font-bold text-slate-300 uppercase tracking-wider">
                                Trace Diagnostics
                              </h4>
                              <span className="text-slate-500 text-[10px]">Explainable AI Pipeline</span>
                            </div>

                            {/* Node Execution Steps timeline */}
                            <div className="space-y-3 relative before:absolute before:inset-y-1 before:left-2.5 before:w-0.5 before:bg-slate-800">
                              {msg.agent_trace.map((traceNode, tIdx) => (
                                <div key={tIdx} className="flex items-start space-x-3 relative">
                                  <div
                                    className={`w-5.5 h-5.5 rounded-full flex items-center justify-center shrink-0 border z-10 ${
                                      traceNode.status === "success"
                                        ? "bg-slate-900 border-blue-500/40 text-blue-400"
                                        : traceNode.status === "skipped"
                                        ? "bg-slate-950 border-slate-800 text-slate-600"
                                        : "bg-slate-900 border-red-500/40 text-red-400"
                                    }`}
                                  >
                                    <Clock className="w-3 h-3" />
                                  </div>
                                  <div className="flex-1 flex items-center justify-between min-w-0">
                                    <div>
                                      <span className="font-semibold text-slate-200">{traceNode.node_name}</span>
                                      {traceNode.metadata?.route_decision && (
                                        <span className="ml-2 px-1.5 py-0.2 bg-blue-600/10 text-blue-400 rounded-md text-[9px] uppercase font-bold">
                                          {traceNode.metadata.route_decision}
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center space-x-2 text-[10px] text-slate-500">
                                      {traceNode.status !== "skipped" && (
                                        <span>{traceNode.latency_ms} ms</span>
                                      )}
                                      <span className="capitalize font-semibold">{traceNode.status}</span>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* SSE Node status steps tracker */}
          {loading && activeSteps.length > 0 && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-md w-full glass-panel rounded-2xl p-5 border-blue-500/20 bg-blue-950/5">
                <div className="flex items-center space-x-2 mb-3">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
                    Orchestrator Executing
                  </span>
                </div>
                <div className="space-y-2 text-xs">
                  {activeSteps.map((step, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-slate-400">
                        <div
                          className={`w-1.5 h-1.5 rounded-full ${
                            step.status === "running"
                              ? "bg-blue-400 animate-pulse"
                              : step.status === "completed" || step.status === "success"
                              ? "bg-emerald-400"
                              : step.status === "skipped"
                              ? "bg-slate-700"
                              : step.status === "failed"
                              ? "bg-red-400"
                              : "bg-slate-800"
                          }`}
                        />
                        <span>{step.name}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 uppercase font-semibold">
                        {step.status === "running" ? (
                          <span className="text-blue-400 animate-pulse">Running...</span>
                        ) : (
                          step.status
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Query Input Box */}
        <div className="p-6 border-t border-slate-900 bg-slate-950 shrink-0">
          <form onSubmit={handleSend} className="max-w-4xl w-full mx-auto relative">
            <input
              type="text"
              required
              className="w-full px-5 py-4.5 rounded-2xl glass-input text-sm pr-14"
              placeholder="Ask a question about sales metrics, HR details, or policy PDFs..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !inputText.trim()}
              className="absolute right-3.5 top-3.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white p-2.5 rounded-xl transition-all duration-200 flex items-center justify-center"
            >
              {loading ? (
                <Loader2 className="w-4.5 h-4.5 animate-spin" />
              ) : (
                <Send className="w-4.5 h-4.5" />
              )}
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}
