"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getStoredUser } from "@/lib/auth";
import { useAuth } from "@/hooks/useAuth";
import { skillsApi } from "@/lib/api";
import { Skill } from "@/types";
import { formatDistanceToNow } from "date-fns";

const VALIDATION_STATUS_STYLES: Record<string, string> = {
  valid: "status-complete",
  invalid: "status-failed",
  failed: "status-failed",
  validating: "status-processing",
  uploaded: "status-pending",
};

const VALIDATION_STATUS_LABELS: Record<string, string> = {
  valid: "Valid",
  invalid: "Invalid",
  failed: "Failed",
  validating: "Validating",
  uploaded: "Uploaded",
};

export default function SkillsPage() {
  const router = useRouter();
  const { logout } = useAuth();
  const user = getStoredUser();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }
    loadSkills();
  }, []);

  const loadSkills = async () => {
    try {
      const res = await skillsApi.list();
      setSkills(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      await skillsApi.upload(file);
      await loadSkills();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleToggleGlobal = async (skill: Skill) => {
    try {
      if (skill.is_globally_enabled) {
        await skillsApi.disable(skill.id);
      } else {
        await skillsApi.enable(skill.id);
      }
      await loadSkills();
    } catch {
      // ignore
    }
  };

  const handleDelete = async (skillId: string) => {
    if (!confirm("Are you sure you want to delete this skill?")) return;
    try {
      await skillsApi.delete(skillId);
      setSkills((prev) => prev.filter((s) => s.id !== skillId));
      if (selectedSkill?.id === skillId) setSelectedSkill(null);
    } catch {
      // ignore
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-slate-400 hover:text-slate-700 transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              </div>
              <span className="font-bold text-slate-900">Skills Manager</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-500">{user?.username}</span>
            <button onClick={handleLogout} className="btn-secondary text-sm py-1.5 px-3">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Skills</h1>
            <p className="text-slate-500 mt-1">Upload and manage custom skills for your research sessions</p>
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={handleUpload}
              className="hidden"
              id="skill-upload"
            />
            <label
              htmlFor="skill-upload"
              className={`btn-primary cursor-pointer flex items-center gap-2 ${uploading ? "opacity-50 pointer-events-none" : ""}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {uploading ? "Uploading..." : "Upload Skill ZIP"}
            </label>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-6">
            {error}
          </div>
        )}

        {/* Skill format info */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-indigo-900 mb-2">Skill ZIP Format</h3>
          <p className="text-xs text-indigo-700 mb-2">
            Upload a ZIP file containing a <code className="bg-indigo-100 px-1 rounded">SKILL.md</code> file at the top level with the following frontmatter:
          </p>
          <pre className="text-xs bg-indigo-100 rounded-lg p-3 text-indigo-800 overflow-x-auto">
{`---
name: My Skill Name
description: What this skill does
version: "1.0"
---

# My Skill

Documentation and usage instructions here...`}
          </pre>
          <p className="text-xs text-indigo-600 mt-2">
            Allowed file types: .md, .txt, .py, .json, .yaml, .yml, .js
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
          </div>
        ) : skills.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No skills yet</h3>
            <p className="text-slate-500 text-sm">Upload a skill ZIP to get started</p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-6 py-3">Skill</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Version</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Status</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Uploaded</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Global</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {skills.map((skill) => (
                  <tr
                    key={skill.id}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => setSelectedSkill(skill)}
                  >
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-900 text-sm">{skill.name}</div>
                      {skill.description && (
                        <div className="text-xs text-slate-500 mt-0.5 line-clamp-1">{skill.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-500">{skill.version || "—"}</td>
                    <td className="px-4 py-4">
                      <span className={VALIDATION_STATUS_STYLES[skill.validation_status] || "status-badge bg-slate-100 text-slate-600"}>
                        {VALIDATION_STATUS_LABELS[skill.validation_status] || skill.validation_status}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-xs text-slate-400">
                      {formatDistanceToNow(new Date(skill.uploaded_at), { addSuffix: true })}
                    </td>
                    <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleToggleGlobal(skill)}
                        disabled={skill.validation_status !== "valid"}
                        className={`w-9 h-5 rounded-full transition-colors ${
                          skill.is_globally_enabled ? "bg-indigo-600" : "bg-slate-300"
                        } ${skill.validation_status !== "valid" ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
                      >
                        <div className={`w-3.5 h-3.5 bg-white rounded-full shadow transition-transform mx-0.5 ${skill.is_globally_enabled ? "translate-x-4" : "translate-x-0"}`} />
                      </button>
                    </td>
                    <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleDelete(skill.id)}
                        className="text-slate-400 hover:text-red-500 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Skill detail modal */}
      {selectedSkill && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-slate-200">
              <div>
                <h2 className="text-lg font-bold text-slate-900">{selectedSkill.name}</h2>
                <div className="flex items-center gap-3 mt-1">
                  {selectedSkill.version && (
                    <span className="text-xs text-slate-400">v{selectedSkill.version}</span>
                  )}
                  <span className={VALIDATION_STATUS_STYLES[selectedSkill.validation_status] || ""}>
                    {VALIDATION_STATUS_LABELS[selectedSkill.validation_status]}
                  </span>
                </div>
              </div>
              <button onClick={() => setSelectedSkill(null)} className="text-slate-400 hover:text-slate-700">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {selectedSkill.description && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-slate-700 mb-1">Description</h3>
                  <p className="text-sm text-slate-600">{selectedSkill.description}</p>
                </div>
              )}

              {selectedSkill.validation_errors && selectedSkill.validation_errors.length > 0 && (
                <div className="mb-4 bg-red-50 border border-red-200 rounded-xl p-4">
                  <h3 className="text-sm font-semibold text-red-800 mb-2">Validation Errors</h3>
                  <ul className="space-y-1">
                    {selectedSkill.validation_errors.map((err, i) => (
                      <li key={i} className="text-xs text-red-700 flex items-start gap-2">
                        <span className="text-red-500 mt-0.5">•</span>
                        {err}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedSkill.skill_metadata_json && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">Metadata</h3>
                  <pre className="text-xs bg-slate-100 rounded-xl p-4 overflow-x-auto text-slate-700">
                    {JSON.stringify(selectedSkill.skill_metadata_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
