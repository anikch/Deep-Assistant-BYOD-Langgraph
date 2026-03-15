"use client";

import { useState, useRef } from "react";
import { Source } from "@/types";
import { sourcesApi } from "@/lib/api";

interface SourcesPanelProps {
  sessionId: string;
  sources: Source[];
  onSourcesChange: () => void;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "status-pending",
  processing: "status-processing",
  complete: "status-complete",
  failed: "status-failed",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  processing: "Processing",
  complete: "Ready",
  failed: "Failed",
};

const SOURCE_TYPE_ICONS: Record<string, string> = {
  pdf: "📄",
  pptx: "📊",
  image: "🖼️",
  txt: "📝",
  text: "📋",
  url: "🌐",
};

export default function SourcesPanel({ sessionId, sources, onSourcesChange }: SourcesPanelProps) {
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [showTextModal, setShowTextModal] = useState(false);
  const [url, setUrl] = useState("");
  const [pastedText, setPastedText] = useState("");
  const [pastedTextName, setPastedTextName] = useState("Pasted Text");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      await sourcesApi.uploadFile(sessionId, file);
      onSourcesChange();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleAddUrl = async () => {
    if (!url.trim()) return;
    setError("");
    setUploading(true);
    try {
      await sourcesApi.addUrl(sessionId, url.trim());
      setUrl("");
      setShowUrlInput(false);
      onSourcesChange();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Failed to add URL");
    } finally {
      setUploading(false);
    }
  };

  const handleAddText = async () => {
    if (!pastedText.trim()) return;
    setError("");
    setUploading(true);
    try {
      await sourcesApi.addText(sessionId, pastedText, pastedTextName);
      setPastedText("");
      setPastedTextName("Pasted Text");
      setShowTextModal(false);
      onSourcesChange();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Failed to add text");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (sourceId: string) => {
    if (!confirm("Delete this source?")) return;
    try {
      await sourcesApi.delete(sessionId, sourceId);
      onSourcesChange();
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-slate-200">
        <h2 className="font-semibold text-slate-900 text-sm mb-3">Sources</h2>
        <div className="flex flex-col gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.pptx,.jpg,.jpeg,.png,.txt"
            onChange={handleFileUpload}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg border border-dashed border-slate-300 text-slate-600 hover:border-indigo-400 hover:text-indigo-600 cursor-pointer transition-colors ${uploading ? "opacity-50 pointer-events-none" : ""}`}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Upload File (PDF, PPTX, IMG, TXT)
          </label>

          <button
            onClick={() => setShowUrlInput(!showUrlInput)}
            className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            Add URL
          </button>

          <button
            onClick={() => setShowTextModal(true)}
            className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Paste Text
          </button>
        </div>

        {showUrlInput && (
          <div className="mt-3 flex gap-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://..."
              className="input-field text-xs flex-1"
              onKeyDown={(e) => e.key === "Enter" && handleAddUrl()}
            />
            <button onClick={handleAddUrl} disabled={uploading} className="btn-primary text-xs py-1.5 px-3">
              Add
            </button>
          </div>
        )}

        {error && (
          <p className="text-xs text-red-600 mt-2">{error}</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {sources.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-slate-400">No sources yet. Add files, URLs, or paste text to get started.</p>
          </div>
        ) : (
          sources.map((source) => (
            <div key={source.id} className="flex items-start gap-2 p-2.5 bg-slate-50 rounded-lg group">
              <span className="text-base flex-shrink-0 mt-0.5">
                {SOURCE_TYPE_ICONS[source.source_type] || "📎"}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-800 truncate">{source.display_name}</p>
                <span className={STATUS_STYLES[source.ingest_status] || "status-badge bg-slate-100 text-slate-600"}>
                  {source.ingest_status === "processing" && (
                    <svg className="animate-spin -ml-0.5 mr-1 h-2.5 w-2.5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  )}
                  {STATUS_LABELS[source.ingest_status] || source.ingest_status}
                </span>
              </div>
              <button
                onClick={() => handleDelete(source.id)}
                className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-all flex-shrink-0"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))
        )}
      </div>

      {/* Paste Text Modal */}
      {showTextModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Paste Text</h2>
            <input
              type="text"
              value={pastedTextName}
              onChange={(e) => setPastedTextName(e.target.value)}
              placeholder="Source name"
              className="input-field mb-3"
            />
            <textarea
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste your text here..."
              className="input-field h-48 resize-none mb-1"
            />
            <p className="text-xs text-slate-400 mb-4">
              {pastedText.length.toLocaleString()} / 50,000 characters
            </p>
            <div className="flex gap-3">
              <button onClick={handleAddText} disabled={uploading || !pastedText.trim()} className="btn-primary flex-1">
                {uploading ? "Adding..." : "Add Source"}
              </button>
              <button onClick={() => setShowTextModal(false)} className="btn-secondary flex-1">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
