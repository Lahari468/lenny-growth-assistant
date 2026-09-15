import { Session, Message, Artifact, ModelInfo, HealthStatus } from '../types';

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) {
        errorMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data.error && data.error.message) {
        errorMsg = data.error.message;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<HealthStatus>(res);
  },

  async listSessions(): Promise<{ sessions: Session[]; total: number }> {
    const res = await fetch(`${API_BASE}/sessions`);
    return handleResponse<{ sessions: Session[]; total: number }>(res);
  },

  async createSession(title?: string): Promise<Session> {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    return handleResponse<Session>(res);
  },

  async deleteSession(sessionId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to delete session ${sessionId}`);
    }
  },

  async listMessages(sessionId: string): Promise<{ messages: Message[]; total: number }> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
    return handleResponse<{ messages: Message[]; total: number }>(res);
  },

  async sendMessage(
    sessionId: string,
    content: string,
    provider?: string,
    model?: string
  ): Promise<Message> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, provider, model }),
    });
    return handleResponse<Message>(res);
  },

  async listArtifacts(sessionId: string): Promise<{ artifacts: Artifact[]; total: number }> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/artifacts`);
    return handleResponse<{ artifacts: Artifact[]; total: number }>(res);
  },

  async getArtifact(sessionId: string, artifactId: string): Promise<Artifact> {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/artifacts/${artifactId}`);
    return handleResponse<Artifact>(res);
  },

  async listModels(): Promise<ModelInfo[]> {
    const res = await fetch(`${API_BASE}/models`);
    return handleResponse<ModelInfo[]>(res);
  },

  async setActiveProvider(provider: string): Promise<{ status: string; active_provider: string }> {
    const res = await fetch(`${API_BASE}/models/active`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
    });
    return handleResponse<{ status: string; active_provider: string }>(res);
  },
};
