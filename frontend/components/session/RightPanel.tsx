"use client";

import { useState } from "react";
import { Artifact, Message, Skill, SessionSkill } from "@/types";
import { artifactsApi, skillsApi } from "@/lib/api";

interface RightPanelProps {
  sessionId: string;
  messages: Message[];
  artifacts: Artifact[];
  skills: Skill[];
  sessionSkills: SessionSkill[];
  onArtifactsChange: () => void;
  onSkillsChange: () => void;
}

type Tab = "plan" | "artifacts" | "skills";

export default function RightPanel({
  sessionId,
  messages,
  artifacts,
  skills,
  sessionSkills,
  onArtifactsChange,
  onSkillsChange,
}: RightPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("plan");

  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
  const currentPlan = lastAssistantMsg?.structured_payload?.plan || [];

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white">
        {(["plan", "artifacts", "skills"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-3 text-xs font-medium capitalize transition-colors border-b-2 ${
              activeTab === tab
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "plan" && (
          <PlanTab plan={currentPlan} />
        )}
        {activeTab === "artifacts" && (
          <ArtifactsTab
            sessionId={sessionId}
            artifacts={artifacts}
            onArtifactsChange={onArtifactsChange}
          />
        )}
        {activeTab === "skills" && (
          <SkillsTab
            sessionId={sessionId}
            skills={skills}
            sessionSkills={sessionSkills}
            onSkillsChange={onSkillsChange}
          />
        )}
      </div>
    </div>
  );
}

function PlanTab({ plan }: { plan: string[] }) {
  if (plan.length === 0) {
    return (
      <div className="p-4 text-center text-slate-400 text-sm py-12">
        <svg className="w-8 h-8 mx-auto mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p>Send a message to see the agent&apos;s research plan</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Latest Research Plan</h3>
      <ol className="space-y-2">
        {plan.map((step, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 text-xs rounded-full flex items-center justify-center font-semibold mt-0.5">
              {i + 1}
            </span>
            <span className="text-sm text-slate-700 leading-relaxed">
              {step.replace(/^Step \d+:\s*/i, "")}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function ArtifactsTab({
  sessionId,
  artifacts,
  onArtifactsChange,
}: {
  sessionId: string;
  artifacts: Artifact[];
  onArtifactsChange: () => void;
}) {
  const [showGenerate, setShowGenerate] = useState(false);
  const [genType, setGenType] = useState<"pdf" | "csv" | "xlsx">("pdf");
  const [genName, setGenName] = useState("");
  const [genContent, setGenContent] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!genContent.trim() || !genName.trim()) return;
    setGenerating(true);
    setError("");
    try {
      await artifactsApi.generate(sessionId, {
        artifact_type: genType,
        display_name: genName,
        content: genContent,
      });
      setShowGenerate(false);
      setGenContent("");
      setGenName("");
      onArtifactsChange();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Artifacts</h3>
        <button
          onClick={() => setShowGenerate(!showGenerate)}
          className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
        >
          + Generate
        </button>
      </div>

      {showGenerate && (
        <div className="mb-4 p-3 bg-slate-50 rounded-xl border border-slate-200">
          <div className="flex gap-2 mb-3">
            {(["pdf", "csv", "xlsx"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setGenType(type)}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg uppercase ${
                  genType === type ? "bg-indigo-600 text-white" : "bg-white border border-slate-200 text-slate-600"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={genName}
            onChange={(e) => setGenName(e.target.value)}
            placeholder="File name"
            className="input-field text-xs mb-2"
          />
          <textarea
            value={genContent}
            onChange={(e) => setGenContent(e.target.value)}
            placeholder="Content to include..."
            className="input-field text-xs h-24 resize-none mb-2"
          />
          {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
          <button onClick={handleGenerate} disabled={generating || !genContent.trim() || !genName.trim()} className="btn-primary text-xs py-1.5 w-full">
            {generating ? "Generating..." : "Generate"}
          </button>
        </div>
      )}

      {artifacts.length === 0 ? (
        <div className="text-center text-slate-400 text-xs py-8">No artifacts yet</div>
      ) : (
        <div className="space-y-2">
          {artifacts.map((artifact) => (
            <a
              key={artifact.id}
              href={artifactsApi.downloadUrl(artifact.id)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors group"
            >
              <span className="text-xl">
                {artifact.artifact_type === "pdf" ? "📄" : artifact.artifact_type === "csv" ? "📊" : "📈"}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-slate-800 truncate">{artifact.display_name}</p>
                <p className="text-xs text-slate-400 uppercase">{artifact.artifact_type}</p>
              </div>
              <svg className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function SkillsTab({
  sessionId,
  skills,
  sessionSkills,
  onSkillsChange,
}: {
  sessionId: string;
  skills: Skill[];
  sessionSkills: SessionSkill[];
  onSkillsChange: () => void;
}) {
  const sessionSkillMap = new Map(sessionSkills.map((ss) => [ss.skill_id, ss.is_enabled]));

  const handleToggle = async (skillId: string, currentlyEnabled: boolean) => {
    try {
      if (currentlyEnabled) {
        await skillsApi.disableForSession(sessionId, skillId);
      } else {
        await skillsApi.enableForSession(sessionId, skillId);
      }
      onSkillsChange();
    } catch {
      // ignore
    }
  };

  const validSkills = skills.filter((s) => s.validation_status === "valid");

  if (validSkills.length === 0) {
    return (
      <div className="p-4 text-center text-slate-400 text-xs py-8">
        <p className="mb-2">No valid skills available</p>
        <a href="/skills" className="text-indigo-600 hover:underline">
          Upload skills
        </a>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
        Skills for this session
      </h3>
      <div className="space-y-2">
        {validSkills.map((skill) => {
          const isEnabled = sessionSkillMap.get(skill.id) !== false && skill.is_globally_enabled;
          return (
            <div key={skill.id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-medium text-slate-800">{skill.name}</p>
                  {skill.version && (
                    <span className="text-xs text-slate-400">v{skill.version}</span>
                  )}
                </div>
                {skill.description && (
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{skill.description}</p>
                )}
              </div>
              <button
                onClick={() => handleToggle(skill.id, isEnabled)}
                disabled={!skill.is_globally_enabled}
                className={`flex-shrink-0 w-9 h-5 rounded-full transition-colors ${
                  isEnabled ? "bg-indigo-600" : "bg-slate-300"
                } ${!skill.is_globally_enabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
              >
                <div className={`w-3.5 h-3.5 bg-white rounded-full shadow transition-transform mx-0.5 ${isEnabled ? "translate-x-4" : "translate-x-0"}`} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
