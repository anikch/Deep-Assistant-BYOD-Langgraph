export interface User {
  id: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface Session {
  id: string;
  user_id: string;
  title: string;
  status: "active" | "archived" | "deleted";
  llm_model: string;
  created_at: string;
  updated_at: string;
  archived_at?: string;
}

export interface LlmModel {
  id: string;
  name: string;
}

export interface EmbeddingModel {
  id: string;
  name: string;
  provider: string;
}

export interface PlatformSettings {
  active_embedding_model: string;
  available_embedding_models: EmbeddingModel[];
}

export interface Source {
  id: string;
  user_id: string;
  session_id: string;
  source_type: "pdf" | "pptx" | "image" | "txt" | "text" | "url";
  display_name: string;
  original_filename?: string;
  source_url?: string;
  ingest_status: "pending" | "processing" | "complete" | "failed";
  created_at: string;
  updated_at: string;
}

export interface Citation {
  source_id: string;
  source_name: string;
  chunk_index: number;
  excerpt: string;
}

export interface Message {
  id: string;
  session_id: string;
  user_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  structured_payload?: {
    plan?: string[];
    citations?: Citation[];
    agent_run_id?: string;
    clarification_needed?: boolean;
    clarification_question?: string;
  };
  created_at: string;
}

export interface ChatResponse {
  message_id: string;
  session_id: string;
  role: string;
  content: string;
  plan?: string[];
  citations?: Citation[];
  agent_run_id?: string;
  clarification_needed: boolean;
  clarification_question?: string;
  created_at: string;
}

export interface AgentRun {
  id: string;
  user_id: string;
  session_id: string;
  status: "pending" | "running" | "complete" | "failed";
  current_plan?: string[];
  final_summary?: string;
  started_at: string;
  completed_at?: string;
}

export interface Skill {
  id: string;
  user_id: string;
  name: string;
  version?: string;
  description?: string;
  skill_metadata_json?: Record<string, unknown>;
  install_status?: string;
  validation_status: "uploaded" | "validating" | "valid" | "invalid" | "failed";
  validation_errors?: string[];
  is_globally_enabled: boolean;
  uploaded_at: string;
  updated_at: string;
}

export interface SessionSkill {
  id: string;
  session_id: string;
  skill_id: string;
  is_enabled: boolean;
  created_at: string;
}

export interface Artifact {
  id: string;
  user_id: string;
  session_id: string;
  artifact_type: "pdf" | "csv" | "xlsx";
  display_name: string;
  artifact_metadata?: Record<string, unknown>;
  created_at: string;
}
