"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getStoredUser } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import { adminApi } from "@/lib/api";
import { PlatformSettings, EmbeddingModel } from "@/types";

export default function AdminPage() {
  const router = useRouter();
  const { logout } = useAuth();
  const user = getStoredUser();

  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [selectedEmbedding, setSelectedEmbedding] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!user.is_admin) {
      router.replace("/dashboard");
      return;
    }
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const res = await adminApi.getSettings();
      setSettings(res.data);
      setSelectedEmbedding(res.data.active_embedding_model);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosErr?.response?.status === 403) {
        setError("Admin access required");
      } else {
        setError("Failed to load settings");
      }
    } finally {
      setLoading(false);
    }
  };

  const saveEmbeddingModel = async () => {
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await adminApi.updateEmbeddingModel(selectedEmbedding);
      setMessage("Embedding model updated successfully. New documents will use the updated model.");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Failed to update embedding model");
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (error && !settings) {
    return (
      <div className="flex items-center justify-center min-h-screen flex-col gap-4">
        <p className="text-red-600">{error}</p>
        <Link href="/dashboard" className="btn-primary">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-slate-400 hover:text-slate-900 transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div className="w-8 h-8 bg-orange-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span className="font-bold text-slate-900 text-lg">Admin Configuration</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-500">
              <span className="font-medium text-slate-900">{user?.username}</span>
            </span>
            <button onClick={handleLogout} className="btn-secondary text-sm py-1.5 px-3">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Embedding Model Configuration */}
        <div className="card p-6">
          <h2 className="text-lg font-bold text-slate-900 mb-1">Embedding Model</h2>
          <p className="text-sm text-slate-500 mb-6">
            Select the embedding model used for document ingestion and semantic search across all platform users.
            Changing this model affects new document embeddings only. Previously embedded documents will retain their existing embeddings.
          </p>

          {message && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              {message}
            </div>
          )}

          {error && settings && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="space-y-3 mb-6">
            {settings?.available_embedding_models.map((model: EmbeddingModel) => (
              <label
                key={model.id}
                className={`flex items-start gap-3 p-4 border rounded-xl cursor-pointer transition-colors ${
                  selectedEmbedding === model.id
                    ? "border-indigo-500 bg-indigo-50/50"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <input
                  type="radio"
                  name="embedding_model"
                  value={model.id}
                  checked={selectedEmbedding === model.id}
                  onChange={(e) => setSelectedEmbedding(e.target.value)}
                  className="mt-1 accent-indigo-600"
                />
                <div>
                  <div className="font-medium text-slate-900">{model.name}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {model.provider === "sentence-transformers" && "Runs locally, no API cost. 384-dimensional embeddings."}
                    {model.id === "azure-text-embedding-3-small" && "Azure OpenAI hosted. 1536-dimensional embeddings. Requires Azure OpenAI API key."}
                    {model.id === "azure-text-embedding-3-large" && "Azure OpenAI hosted. 3072-dimensional embeddings. Higher quality, requires Azure OpenAI API key."}
                  </div>
                  {model.provider === "azure_openai" && (
                    <span className="inline-block mt-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">
                      Requires Azure OpenAI Key
                    </span>
                  )}
                </div>
              </label>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={saveEmbeddingModel}
              disabled={saving || selectedEmbedding === settings?.active_embedding_model}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            {selectedEmbedding !== settings?.active_embedding_model && (
              <span className="text-xs text-amber-600">
                Unsaved changes
              </span>
            )}
          </div>
        </div>

        {/* Info Card */}
        <div className="card p-6 mt-6 bg-amber-50 border-amber-200">
          <h3 className="text-sm font-semibold text-amber-900 mb-2">Important Notes</h3>
          <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
            <li>Changing the embedding model only affects newly ingested documents.</li>
            <li>Previously embedded documents will continue to use their original embeddings.</li>
            <li>For best results, re-ingest documents after changing the embedding model.</li>
            <li>Azure OpenAI embedding models require valid API credentials in the .env file.</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
