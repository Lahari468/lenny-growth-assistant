import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api";

export type ChatProvider = "ollama" | "anthropic";

export interface Source {
  source_id: string;
  title: string;
  source_url?: string | null;
  score?: number;
  document_id?: string;
  chunk_id?: string;
  chunk_index?: number;
  source_file?: string | null;
  speakers?: string[];
  paragraph_start?: number | null;
  paragraph_end?: number | null;
}

export interface GroundedResponse {
  answer?: string;
  assistant_message?: {
    content: string;
    provider?: string;
    model?: string;
  };
  content?: string;
  provider?: string;
  model?: string;
  retrieval_count?: number;
  sources: Source[];
}

export interface SessionMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  provider?: string | null;
  model?: string | null;
}

export interface Session {
  id: string;
  user_id: string;
  user_name: string;
  title?: string | null;
  provider: string;
  created_at: string;
  updated_at: string;
  messages: SessionMessage[];
}

export interface SessionMessageResponse {
  user_message: SessionMessage;
  assistant_message: SessionMessage;
  sources: Source[];
  provider: string;
  model: string;
  retrieval_count: number;
}

export interface ArtifactResponse {
  artifact_type: string;
  title: string;
  content: string;
  provider: string;
  model: string;
  retrieval_count: number;
  sources: Source[];
}

function getErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (error.code === "ERR_NETWORK") {
      return (
        "Unable to connect to the backend. " +
        "Make sure FastAPI is running on port 8000."
      );
    }
  }

  return fallback;
}

export async function groundedChat(
  query: string,
  provider?: ChatProvider,
): Promise<GroundedResponse> {
  try {
    const { data } =
      await axios.post<GroundedResponse>(
        `${API_BASE}/chat/grounded`,
        {
          query,
          top_k: 5,
          provider,
        },
      );

    return data;
  } catch (error) {
    throw new Error(
      getErrorMessage(
        error,
        "Unable to generate grounded answer.",
      ),
    );
  }
}

export async function createSession(
  userName = "Anonymous",
  title?: string,
  provider?: ChatProvider,
): Promise<Session> {
  try {
    const { data } =
      await axios.post<Session>(
        `${API_BASE}/sessions`,
        {
          user_name: userName,
          title: title || null,
          provider,
        },
      );

    return data;
  } catch (error) {
    throw new Error(
      getErrorMessage(
        error,
        "Unable to create a new conversation.",
      ),
    );
  }
}

export async function getSession(
  sessionId: string,
): Promise<Session> {
  try {
    const { data } =
      await axios.get<Session>(
        `${API_BASE}/sessions/${sessionId}`,
      );

    return data;
  } catch (error) {
    throw new Error(
      getErrorMessage(
        error,
        "Unable to load the conversation.",
      ),
    );
  }
}

export async function getSessions(): Promise<Session[]> {
  try {
    const { data } =
      await axios.get<Session[]>(
        `${API_BASE}/sessions`,
      );

    return data;
  } catch (error) {
    throw new Error(
      getErrorMessage(
        error,
        "Unable to load conversations.",
      ),
    );
  }
}

export async function sendSessionMessage(
  sessionId: string,
  content: string,
  provider?: ChatProvider,
): Promise<SessionMessageResponse> {
  try {
    const { data } =
      await axios.post<SessionMessageResponse>(
        `${API_BASE}/sessions/${sessionId}/messages`,
        {
          content,
          top_k: 5,
          provider,
        },
      );

    return data;
  } catch (error) {
    throw new Error(
      getErrorMessage(
        error,
        "Unable to generate grounded answer. " +
          "Please try again.",
      ),
    );
  }
}

export async function createShip30(
  query: string,
  provider?: ChatProvider,
): Promise<ArtifactResponse> {
  try {
    const { data } =
      await axios.post<ArtifactResponse>(
        `${API_BASE}/chat/ship30`,
        {
          query,
          top_k: 5,
          provider,
        },
      );

    return data;
  } catch (error) {
    throw new Error(
      getErrorMessage(
        error,
        "Unable to generate the Ship 30 artifact.",
      ),
    );
  }
}