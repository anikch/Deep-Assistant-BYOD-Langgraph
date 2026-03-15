"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getStoredUser } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import { sessionsApi } from "@/lib/api";
import { Session, LlmModel } from "@/types";
import { formatDistanceToNow } from "date-fns";

export default function DashboardPage() {
  const router = useRouter();
  const { logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [llmModels, setLlmModels] = useState<LlmModel[]>([]);
  const [selectedModel, setSelectedModel] = useState("gemini");
  const user = getStoredUser();

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    loadSessions();
    loadLlmModels();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await sessionsApi.list(true);
      setSessions(res.data);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const loadLlmModels = async () => {
    try {
      const res = await sessionsApi.listLlmModels();
      setLlmModels(res.data);
    } catch {
      // fallback defaults
      setLlmModels([
        { id: "gemini", name: "Google Gemini" },
        { id: "azure_openai", name: "Azure OpenAI GPT" },
      ]);
    }
  };

  const createSession = async () => {
    setCreating(true);
    try {
      const res = await sessionsApi.create(newTitle || "New Session", selectedModel);
      router.push(`/session/${res.data.id}`);
    } catch {
      setCreating(false);
    }
  };

  const deleteSession = async (id: string) => {
    if (!confirm("Are you sure you want to delete this session?")) return;
    await sessionsApi.delete(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
  };

  const archiveSession = async (id: string, currentStatus: string) => {
    const newStatus = currentStatus === "archived" ? "active" : "archived";
    const res = await sessionsApi.update(id, { status: newStatus });
    setSessions((prev) => prev.map((s) => (s.id === id ? res.data : s)));
  };

  const renameSession = async (id: string) => {
    if (!editTitle.trim()) return;
    const res = await sessionsApi.update(id, { title: editTitle });
    setSessions((prev) => prev.map((s) => (s.id === id ? res.data : s)));
    setEditingId(null);
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const activeSessions = sessions.filter((s) => s.status === "active");
  const archivedSessions = sessions.filter((s) => s.status === "archived");

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <span className="font-bold text-slate-900 text-lg">Deep Research Agent</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/skills" className="text-sm text-slate-600 hover:text-slate-900 font-medium">
              Skills
            </Link>
            {user?.is_admin && (
              <Link href="/admin" className="text-sm text-slate-600 hover:text-slate-900 font-medium">
                Admin
              </Link>
            )}
            <span className="text-sm text-slate-500">
              Hello, <span className="font-medium text-slate-900">{user?.username}</span>
            </span>
            <button onClick={handleLogout} className="btn-secondary text-sm py-1.5 px-3">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Research Sessions</h1>
            <p className="text-slate-500 mt-1">Create and manage your research workspaces</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Session
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
          </div>
        ) : (
          <>
            {activeSessions.length === 0 && archivedSessions.length === 0 ? (
              <div className="text-center py-20">
                <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-slate-900 mb-2">No sessions yet</h2>
                <p className="text-slate-500 mb-6">Create your first research session to get started</p>
                <button onClick={() => setShowCreateModal(true)} className="btn-primary">
                  Create Session
                </button>
              </div>
            ) : (
              <>
                {activeSessions.length > 0 && (
                  <div className="mb-8">
                    <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">
                      Active Sessions ({activeSessions.length})
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {activeSessions.map((session) => (
                        <SessionCard
                          key={session.id}
                          session={session}
                          editingId={editingId}
                          editTitle={editTitle}
                          setEditingId={setEditingId}
                          setEditTitle={setEditTitle}
                          onRename={renameSession}
                          onArchive={archiveSession}
                          onDelete={deleteSession}
                          router={router}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {archivedSessions.length > 0 && (
                  <div>
                    <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">
                      Archived ({archivedSessions.length})
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 opacity-70">
                      {archivedSessions.map((session) => (
                        <SessionCard
                          key={session.id}
                          session={session}
                          editingId={editingId}
                          editTitle={editTitle}
                          setEditingId={setEditingId}
                          setEditTitle={setEditTitle}
                          onRename={renameSession}
                          onArchive={archiveSession}
                          onDelete={deleteSession}
                          router={router}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>

      {/* Create modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4">New Research Session</h2>
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Session title (optional)"
              className="input-field mb-4"
              onKeyDown={(e) => e.key === "Enter" && createSession()}
              autoFocus
            />
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-1">
                AI Model
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="input-field"
              >
                {llmModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-400 mt-1">
                Model cannot be changed after session is created
              </p>
            </div>
            <div className="flex gap-3">
              <button onClick={createSession} disabled={creating} className="btn-primary flex-1">
                {creating ? "Creating..." : "Create Session"}
              </button>
              <button onClick={() => setShowCreateModal(false)} className="btn-secondary flex-1">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SessionCard({
  session,
  editingId,
  editTitle,
  setEditingId,
  setEditTitle,
  onRename,
  onArchive,
  onDelete,
  router,
}: {
  session: Session;
  editingId: string | null;
  editTitle: string;
  setEditingId: (id: string | null) => void;
  setEditTitle: (title: string) => void;
  onRename: (id: string) => void;
  onArchive: (id: string, status: string) => void;
  onDelete: (id: string) => void;
  router: ReturnType<typeof useRouter>;
}) {
  return (
    <div className="card p-5 hover:shadow-md transition-shadow cursor-pointer group">
      <div onClick={() => router.push(`/session/${session.id}`)}>
        {editingId === session.id ? (
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className="input-field mb-2 text-sm"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Enter") onRename(session.id);
              if (e.key === "Escape") setEditingId(null);
            }}
            autoFocus
          />
        ) : (
          <h3 className="font-semibold text-slate-900 mb-2 line-clamp-2 group-hover:text-indigo-600 transition-colors">
            {session.title}
          </h3>
        )}
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
            session.llm_model === "azure_openai"
              ? "bg-blue-100 text-blue-700"
              : "bg-emerald-100 text-emerald-700"
          }`}>
            {session.llm_model === "azure_openai" ? "Azure OpenAI" : "Gemini"}
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Updated {formatDistanceToNow(new Date(session.updated_at), { addSuffix: true })}
        </p>
      </div>

      <div className="flex items-center gap-1 mt-4 pt-3 border-t border-slate-100">
        {editingId === session.id ? (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); onRename(session.id); }}
              className="text-xs text-indigo-600 hover:text-indigo-700 font-medium px-2 py-1"
            >
              Save
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setEditingId(null); }}
              className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1"
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); setEditingId(session.id); setEditTitle(session.title); }}
              className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded"
              title="Rename"
            >
              Rename
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onArchive(session.id, session.status); }}
              className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded"
              title={session.status === "archived" ? "Unarchive" : "Archive"}
            >
              {session.status === "archived" ? "Unarchive" : "Archive"}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
              className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded ml-auto"
              title="Delete"
            >
              Delete
            </button>
          </>
        )}
      </div>
    </div>
  );
}
