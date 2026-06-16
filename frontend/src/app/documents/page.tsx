"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { documents, schema, getToken } from "@/services/api";
import {
  Upload,
  FileText,
  Trash2,
  Database,
  Loader2,
  CheckCircle,
  AlertCircle,
  Eye,
  Columns
} from "lucide-react";

export default function Documents() {
  const router = useRouter();
  const [docsList, setDocsList] = useState<any[]>([]);
  const [dbTables, setDbTables] = useState<any>({});
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingSchema, setLoadingSchema] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [expandedTable, setExpandedTable] = useState<string | null>("sales");

  useEffect(() => {
    // Auth guard
    if (!getToken()) {
      router.push("/login");
      return;
    }

    fetchDocuments();
    fetchSchema();

    // Poll document list to show status changes (processing -> completed)
    const interval = setInterval(fetchDocuments, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDocuments = async () => {
    try {
      const list = await documents.list();
      setDocsList(list);
    } catch (e) {
      console.error("Failed to load documents:", e);
    } finally {
      setLoadingDocs(false);
    }
  };

  const fetchSchema = async () => {
    try {
      const tables = await schema.getTables();
      setDbTables(tables);
    } catch (e) {
      console.error("Failed to load schema:", e);
    } finally {
      setLoadingSchema(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = file.name.toLowerCase();
    if (!ext.endsWith(".pdf") && !ext.endsWith(".csv")) {
      setUploadError("Only PDF and CSV files are supported.");
      return;
    }

    setUploading(true);
    setUploadError("");

    try {
      await documents.upload(file);
      await fetchDocuments();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload file.");
    } finally {
      setUploading(false);
      // Reset input value
      e.target.value = "";
    }
  };

  const handleDeleteDoc = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document and all associated vectors?")) return;
    
    try {
      await documents.delete(id);
      setDocsList(docsList.filter((d) => d.id !== id));
    } catch (e) {
      alert("Failed to delete document.");
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col overflow-y-auto p-8">
        <div className="max-w-6xl w-full mx-auto space-y-8 animate-fade-in">
          
          {/* Header */}
          <div>
            <h2 className="text-3xl font-bold text-white tracking-tight">Data Catalog</h2>
            <p className="text-slate-400 mt-1">Manage unstructured PDFs and explore the structured relational schemas.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            
            {/* Left Column: Documents & Upload */}
            <div className="lg:col-span-7 space-y-6">
              
              {/* Dropzone Uploader */}
              <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
                <h3 className="font-bold text-white mb-4 flex items-center space-x-2">
                  <Upload className="w-4.5 h-4.5 text-blue-500" />
                  <span>Upload Unstructured Context</span>
                </h3>
                
                <label className="border-2 border-dashed border-slate-700 hover:border-blue-500/50 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors duration-200 bg-slate-900/30">
                  <input
                    type="file"
                    accept=".pdf,.csv"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={uploading}
                  />
                  {uploading ? (
                    <div className="flex flex-col items-center space-y-2">
                      <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                      <span className="text-sm font-semibold text-slate-300">Uploading & Scheduling Indexer...</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center space-y-2 text-center">
                      <FileText className="w-8 h-8 text-slate-500 mb-1" />
                      <span className="text-sm font-semibold text-slate-300">Click to upload a PDF</span>
                      <span className="text-xs text-slate-500">Max size 20MB. Fully indexed in vector space.</span>
                    </div>
                  )}
                </label>
                
                {uploadError && (
                  <div className="mt-3 text-xs text-red-400 bg-red-950/20 border border-red-900/30 px-3 py-2 rounded-lg flex items-center space-x-2">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{uploadError}</span>
                  </div>
                )}
              </div>

              {/* Uploaded Documents List */}
              <div className="glass-panel p-6 rounded-2xl">
                <h3 className="font-bold text-white mb-4">Indexed Context Documents</h3>
                
                {loadingDocs ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                  </div>
                ) : docsList.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 text-sm">
                    No documents uploaded yet. Upload a PDF to start hybrid RAG queries.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {docsList.map((doc) => (
                      <div key={doc.id} className="py-4 flex items-center justify-between first:pt-0 last:pb-0">
                        <div className="flex items-start space-x-3 pr-4 min-w-0">
                          <FileText className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-white truncate">{doc.filename}</p>
                            <div className="flex items-center space-x-2 text-xs text-slate-500 mt-1">
                              <span>{formatBytes(doc.file_size)}</span>
                              <span>•</span>
                              <span>{doc.chunk_count} Chunks</span>
                              <span>•</span>
                              <span className="capitalize">{new Date(doc.created_at).toLocaleDateString()}</span>
                            </div>
                          </div>
                        </div>

                        {/* Status / Actions */}
                        <div className="flex items-center space-x-4">
                          {doc.upload_status === "completed" && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Active
                            </span>
                          )}
                          {doc.upload_status === "processing" && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                              Parsing
                            </span>
                          )}
                          {doc.upload_status === "pending" && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              Queued
                            </span>
                          )}
                          {doc.upload_status === "failed" && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                              <AlertCircle className="w-3 h-3 mr-1" />
                              Failed
                            </span>
                          )}

                          <button
                            onClick={() => handleDeleteDoc(doc.id)}
                            className="p-1.5 text-slate-500 hover:text-red-400 rounded-lg hover:bg-slate-800 transition-colors"
                            title="Delete document"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Database Schema Explorer */}
            <div className="lg:col-span-5">
              <div className="glass-panel p-6 rounded-2xl h-fit">
                <div className="flex items-center space-x-2 text-white font-bold mb-4">
                  <Database className="w-5 h-5 text-emerald-500" />
                  <h3>PostgreSQL Schema Explorer</h3>
                </div>
                <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                  These tables contain transactional data available to the Text-to-SQL agent engine. You can query these tables in the Chat workspace.
                </p>

                {loadingSchema ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.keys(dbTables).map((tableName) => {
                      const isExpanded = expandedTable === tableName;
                      const columns = dbTables[tableName];
                      return (
                        <div
                          key={tableName}
                          className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/20"
                        >
                          <button
                            onClick={() => setExpandedTable(isExpanded ? null : tableName)}
                            className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-800/40 transition-colors"
                          >
                            <div className="flex items-center space-x-2">
                              <Columns className="w-4 h-4 text-emerald-400" />
                              <span className="font-semibold text-sm text-slate-200 uppercase tracking-wider">{tableName}</span>
                            </div>
                            <span className="text-xs text-slate-500">{columns.length} columns</span>
                          </button>

                          {isExpanded && (
                            <div className="px-4 py-3 bg-slate-950/40 border-t border-slate-800 text-xs">
                              <table className="w-full text-left">
                                <thead>
                                  <tr className="text-slate-500 border-b border-slate-800/50">
                                    <th className="pb-1 font-semibold">Column</th>
                                    <th className="pb-1 font-semibold">Type</th>
                                    <th className="pb-1 font-semibold text-right">Nullable</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/30">
                                  {columns.map((col: any) => (
                                    <tr key={col.name} className="text-slate-300">
                                      <td className="py-2 font-mono text-emerald-300">{col.name}</td>
                                      <td className="py-2 font-mono text-slate-400">{col.type}</td>
                                      <td className="py-2 text-right text-slate-500">
                                        {col.nullable ? "Yes" : "No"}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

          </div>

        </div>
      </main>
    </div>
  );
}
