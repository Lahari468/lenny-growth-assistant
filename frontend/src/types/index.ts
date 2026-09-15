export interface Citation {
  chunk_id: string;
  transcript_id: string;
  episode_title: string;
  guest: string;
  source_url: string;
  snippet: string;
  similarity_score: number;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  intent?: string;
  citations: Citation[];
  created_at: string;
  has_artifact?: boolean;
  artifact_id?: string;
}

export interface Session {
  id: string;
  title: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Artifact {
  id: string;
  session_id: string;
  message_id?: string;
  type: 'markdown' | 'html';
  title: string;
  content: string;
  raw_content?: string;
  created_at: string;
  is_sandboxed: boolean;
  sources?: Citation[];
}


export interface ModelInfo {
  id: string;
  name: string;
  provider: 'ollama' | 'anthropic';
  is_active: boolean;
  is_available: boolean;
  description?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  database: {
    status: string;
    type: string;
  };
  vector_store: {
    indexed_chunks: number;
    ready: boolean;
  };
  llm_providers: {
    active_provider: string;
    ollama_available: boolean;
    anthropic_available: boolean;
  };
  version: string;
}
