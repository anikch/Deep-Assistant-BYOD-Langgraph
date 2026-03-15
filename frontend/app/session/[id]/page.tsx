"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getStoredUser } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import { sessionsApi, sourcesApi, chatApi, skillsApi, artifactsApi } from "@/lib/api";
import { Session, Source, Message, Skill, SessionSkill, Artifact } from "@/types";
import SourcesPanel from "@/components/session/SourcesPanel";
import ChatPanel from "@/components/session/ChatPanel";
import RightPanel from "@/components/session/RightPanel";

export default function SessionPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const router = useRouter();
  const { logout } = useAuth();
  const user = getStoredUser();

  const [session, setSession] = useState<Session | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [sessionSkills, setSessionSkills] = useState<SessionSkill[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    loadAll();
  }, [sessionId]);

  // Poll for source status updates
  useEffect(() => {
    const hasProcessing = sources.some((s) => s.ingest_status === "pending" || s.ingest_status === "processing");
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      loadSources();
    }, 3000);

    return () => clearInterval(interval);
  }, [sources]);

  const loadAll = async () => {
    try {
      const [sessionRes, sourcesRes, messagesRes, skillsRes, artifactsRes] = await Promise.all([
        sessionsApi.get(sessionId),
        sourcesApi.list(sessionId),
        chatApi.getMessages(sessionId),
        skillsApi.list(),
        artifactsApi.list(sessionId),
      ]);

      setSession(sessionRes.data);
      setSources(sourcesRes.data);
      setMessages(messagesRes.data);
      setSkills(skillsRes.data);
      setArtifacts(artifactsRes.data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr?.response?.status === 404) {
        setError("Session not found");
      } else {
        setError("Failed to load session");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadSources = useCallback(async () => {
    const res = await sourcesApi.list(sessionId);
    setSources(res.data);
  }, [sessionId]);

  const handleMessageSent = useCallback((userMsg: Message, assistantMsg: Message) => {
    setMessages((prev) => {
      // Remove the temp message if it exists
      const filtered = prev.filter((m) => !m.id.startsWith("temp-"));
      return [...filtered, userMsg, assistantMsg];
    });
  }, []);

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

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen flex-col gap-4">
        <p className="text-slate-600">{error}</p>
        <Link href="/dashboard" className="btn-primary">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-100">
      {/* Header */}
      <header className="bg-[#1a1a2e] text-white px-4 py-3 flex items-center gap-4 flex-shrink-0">
        <Link href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold truncate">{session?.title || "Session"}</h1>
          <div className="flex items-center gap-2">
            <p className="text-xs text-slate-400">{sources.length} source{sources.length !== 1 ? "s" : ""}</p>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
              session?.llm_model === "azure_openai"
                ? "bg-blue-900/30 text-blue-300"
                : "bg-emerald-900/30 text-emerald-300"
            }`}>
              {session?.llm_model === "azure_openai" ? "Azure OpenAI" : "Gemini"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/skills" className="text-xs text-slate-400 hover:text-white transition-colors">
            Skills
          </Link>
          <span className="text-xs text-slate-400">{user?.username}</span>
          <button onClick={handleLogout} className="text-xs text-slate-400 hover:text-white transition-colors">
            Sign out
          </button>
        </div>
      </header>

      {/* 3-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel - Sources */}
        <div className="w-64 flex-shrink-0 bg-white border-r border-slate-200 overflow-hidden flex flex-col">
          <SourcesPanel
            sessionId={sessionId}
            sources={sources}
            onSourcesChange={loadSources}
          />
        </div>

        {/* Center panel - Chat */}
        <div className="flex-1 overflow-hidden flex flex-col bg-slate-50">
          <ChatPanel
            sessionId={sessionId}
            messages={messages}
            onMessageSent={handleMessageSent}
            loading={loading}
          />
        </div>

        {/* Right panel - Plan/Artifacts/Skills */}
        <div className="w-72 flex-shrink-0 bg-white border-l border-slate-200 overflow-hidden flex flex-col">
          <RightPanel
            sessionId={sessionId}
            messages={messages}
            artifacts={artifacts}
            skills={skills}
            sessionSkills={sessionSkills}
            onArtifactsChange={async () => {
              const res = await artifactsApi.list(sessionId);
              setArtifacts(res.data);
            }}
            onSkillsChange={async () => {
              const res = await skillsApi.list();
              setSkills(res.data);
            }}
          />
        </div>
      </div>
    </div>
  );
}
