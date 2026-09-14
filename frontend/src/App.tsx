import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  createSession,
  createShip30,
  getSession,
  sendSessionMessage,
} from "./services/api";

import type {
  ChatProvider,
  Session,
  SessionMessage,
  Source,
} from "./services/api";

import "./App.css";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  provider?: string;
  model?: string;
}

interface Artifact {
  title: string;
  content: string;
  sources: Source[];
  provider?: string;
  model?: string;
}

const SESSION_STORAGE_KEY =
  "lenny-growth-session-id";

const PROVIDER_INFO: Record<
  ChatProvider,
  {
    name: string;
    model: string;
    icon: string;
    description: string;
  }
> = {
  ollama: {
    name: "Ollama",
    model: "phi3:latest",
    icon: "◉",
    description: "Local · Private",
  },
  anthropic: {
    name: "Claude",
    model: "claude-sonnet-5",
    icon: "✦",
    description: "Anthropic · API",
  },
};

function App() {
  const [sessionId, setSessionId] =
    useState<string | null>(null);

  const [messages, setMessages] =
    useState<Message[]>([]);

  const [input, setInput] = useState("");

  const [loading, setLoading] =
    useState(false);

  const [loadingSession, setLoadingSession] =
    useState(true);

  const [provider, setProvider] =
    useState<ChatProvider>("ollama");

  const [providerMenuOpen, setProviderMenuOpen] =
    useState(false);

  const [artifact, setArtifact] =
    useState<Artifact>({
      title: "",
      content: "",
      sources: [],
    });

  const [error, setError] = useState("");

  useEffect(() => {
    async function restoreSession() {
      const storedSessionId =
        localStorage.getItem(
          SESSION_STORAGE_KEY,
        );

      if (!storedSessionId) {
        setLoadingSession(false);
        return;
      }

      try {
        const session: Session =
          await getSession(storedSessionId);

        setSessionId(session.id);

        if (
          session.provider === "ollama" ||
          session.provider === "anthropic"
        ) {
          setProvider(session.provider);
        }

        const restoredMessages: Message[] =
          session.messages.map(
            (message: SessionMessage) => ({
              role: message.role,
              content: message.content,
              provider:
                message.provider || undefined,
              model:
                message.model || undefined,
            }),
          );

        setMessages(restoredMessages);
      } catch (err) {
        console.error(
          "Session restore failed:",
          err,
        );

        localStorage.removeItem(
          SESSION_STORAGE_KEY,
        );

        setSessionId(null);
        setMessages([]);
      } finally {
        setLoadingSession(false);
      }
    }

    void restoreSession();
  }, []);

  async function ensureSession(
    firstQuestion: string,
  ): Promise<string> {
    if (sessionId) {
      return sessionId;
    }

    const session = await createSession(
      "Anonymous",
      firstQuestion.slice(0, 60),
      provider,
    );

    localStorage.setItem(
      SESSION_STORAGE_KEY,
      session.id,
    );

    setSessionId(session.id);

    return session.id;
  }

  async function askLenny() {
    const question = input.trim();

    if (
      !question ||
      loading ||
      loadingSession
    ) {
      return;
    }

    setError("");

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: question,
      },
    ]);

    setInput("");
    setLoading(true);

    try {
      const currentSessionId =
        await ensureSession(question);

      const result =
        await sendSessionMessage(
          currentSessionId,
          question,
          provider,
        );

      const answer =
        result.assistant_message?.content ||
        "I couldn't generate an answer.";

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: answer,
          sources: result.sources || [],
          provider: result.provider,
          model: result.model,
        },
      ]);
    } catch (err) {
      console.error("Chat error:", err);

      const message =
        err instanceof Error
          ? err.message
          : "Unable to generate a response.";

      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function generateArtifact() {
    const question = input.trim();

    if (
      !question ||
      loading ||
      loadingSession
    ) {
      return;
    }

    setError("");
    setLoading(true);

    try {
      const result =
        await createShip30(
          question,
          provider,
        );

      setArtifact({
        title: result.title,
        content: result.content,
        sources: result.sources || [],
        provider: result.provider,
        model: result.model,
      });

      setInput("");
    } catch (err) {
      console.error(
        "Artifact error:",
        err,
      );

      const message =
        err instanceof Error
          ? err.message
          : "Unable to generate the Ship 30 artifact.";

      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function newConversation() {
    setSessionId(null);

    localStorage.removeItem(
      SESSION_STORAGE_KEY,
    );

    setMessages([]);

    setArtifact({
      title: "",
      content: "",
      sources: [],
    });

    setInput("");
    setError("");
  }

  function selectProvider(
    nextProvider: ChatProvider,
  ) {
    if (loading) return;

    setProvider(nextProvider);
    setProviderMenuOpen(false);
    setError("");

    /*
     * A provider switch starts a fresh context.
     * This prevents one session from silently mixing
     * providers and keeps the session metadata truthful.
     */
    if (sessionId && messages.length > 0) {
      newConversation();
      setProvider(nextProvider);
    }
  }

  function useSuggestion(text: string) {
    setInput(text);
  }

  function exportArtifact() {
    if (!artifact.content) return;

    const blob = new Blob(
      [artifact.content],
      {
        type: "text/markdown;charset=utf-8",
      },
    );

    const url =
      URL.createObjectURL(blob);

    const link =
      document.createElement("a");

    link.href = url;

    link.download =
      `${artifact.title || "lenny-artifact"}`
        .replace(/[^a-z0-9]+/gi, "-")
        .replace(/^-|-$/g, "")
        .toLowerCase() + ".md";

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  }

  const activeProvider =
    PROVIDER_INFO[provider];

  if (loadingSession) {
    return (
      <div className="app">
        <div className="loading-screen">
          <div className="loading-spinner" />
          <p>Loading your workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">L</div>

          <div>
            <h1>Lenny</h1>
            <span>Growth Assistant</span>
          </div>
        </div>

        <button
          className="new-chat"
          onClick={newConversation}
          disabled={loading}
        >
          <span>＋</span>
          New conversation
        </button>

        <div className="sidebar-section">
          <div className="section-title">
            WORKSPACE
          </div>

          <div className="nav-item active">
            <span>◈</span>
            Chat
          </div>

          <div className="nav-item">
            <span>✦</span>
            Artifacts
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="local-ai">
            <span className="online-dot" />
            <span>
              {provider === "ollama"
                ? "Local AI ready"
                : "Cloud provider selected"}
            </span>
          </div>

          <small>
            {activeProvider.name} ·{" "}
            {activeProvider.model}
          </small>
        </div>
      </aside>

      <main className="main">
        <section className="chat">
          <header className="topbar">
            <div className="topbar-title">
              <strong>
                Growth workspace
              </strong>

              <span>
                Grounded answers from your
                knowledge base
              </span>
            </div>

            <div className="provider-wrapper">
              <button
                className={`provider ${
                  providerMenuOpen
                    ? "provider-open"
                    : ""
                }`}
                onClick={() =>
                  setProviderMenuOpen(
                    (value) => !value,
                  )
                }
                disabled={loading}
              >
                <span className="provider-dot" />

                <span>
                  {activeProvider.name}
                </span>

                <span className="provider-model">
                  {activeProvider.model}
                </span>

                <span className="chevron">
                  {providerMenuOpen
                    ? "⌃"
                    : "⌄"}
                </span>
              </button>

              {providerMenuOpen && (
                <div className="provider-menu">
                  {(
                    Object.keys(
                      PROVIDER_INFO,
                    ) as ChatProvider[]
                  ).map((item) => {
                    const info =
                      PROVIDER_INFO[item];

                    return (
                      <button
                        key={item}
                        className={`provider-option ${
                          provider === item
                            ? "selected"
                            : ""
                        }`}
                        onClick={() =>
                          selectProvider(item)
                        }
                      >
                        <span className="provider-option-icon">
                          {info.icon}
                        </span>

                        <span className="provider-option-text">
                          <strong>
                            {info.name}
                          </strong>

                          <small>
                            {info.model}
                          </small>

                          <em>
                            {info.description}
                          </em>
                        </span>

                        {provider === item && (
                          <span className="check">
                            ✓
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </header>

          <div className="messages">
            {messages.length === 0 ? (
              <div className="welcome">
                <div className="welcome-badge">
                  <span>✦</span>
                  GROUNDED GROWTH AI
                </div>

                <h2>
                  Turn growth questions
                  into better decisions.
                </h2>

                <p>
                  Ask about product-market fit,
                  retention, experimentation,
                  growth loops, or startup
                  strategy. Answers are grounded
                  in the connected knowledge base.
                </p>

                <div className="suggestions">
                  <button
                    onClick={() =>
                      useSuggestion(
                        "What are the earliest signals of product-market fit?",
                      )
                    }
                  >
                    <span>01</span>
                    Early product-market fit
                  </button>

                  <button
                    onClick={() =>
                      useSuggestion(
                        "What are the most important lessons about product growth?",
                      )
                    }
                  >
                    <span>02</span>
                    Product growth lessons
                  </button>

                  <button
                    onClick={() =>
                      useSuggestion(
                        "How should I think about retention?",
                      )
                    }
                  >
                    <span>03</span>
                    Retention strategy
                  </button>
                </div>
              </div>
            ) : (
              messages.map(
                (message, index) => (
                  <div
                    className={`message ${
                      message.role === "user"
                        ? "user"
                        : "assistant"
                    }`}
                    key={`${message.role}-${index}`}
                  >
                    <div className="message-avatar">
                      {message.role === "user"
                        ? "You"
                        : "L"}
                    </div>

                    <div className="message-body">
                      <div className="message-meta">
                        <div className="message-author">
                          {message.role === "user"
                            ? "You"
                            : "Lenny"}
                        </div>

                        {message.role ===
                          "assistant" &&
                          message.provider && (
                            <span>
                              {message.provider}
                              {" · "}
                              {message.model}
                            </span>
                          )}
                      </div>

                      <ReactMarkdown>
                        {message.content}
                      </ReactMarkdown>

                      {message.sources &&
                        message.sources.length >
                          0 && (
                          <div className="sources">
                            <span className="sources-label">
                              SOURCES
                            </span>

                            {message.sources.map(
                              (source) => (
                                <span
                                  className="source"
                                  key={
                                    source.source_id
                                  }
                                  title={
                                    source.title
                                  }
                                >
                                  {
                                    source.source_id
                                  }
                                </span>
                              ),
                            )}
                          </div>
                        )}
                    </div>
                  </div>
                ),
              )
            )}

            {loading && (
              <div className="message assistant">
                <div className="message-avatar">
                  L
                </div>

                <div className="message-body">
                  <div className="message-meta">
                    <div className="message-author">
                      Lenny
                    </div>

                    <span>
                      {activeProvider.name} ·
                      thinking
                    </span>
                  </div>

                  <div className="typing">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="error">
              <strong>Something went wrong</strong>
              <span>{error}</span>
            </div>
          )}

          <div className="composer">
            <textarea
              value={input}
              placeholder={`Ask Lenny about growth...`}
              rows={2}
              disabled={loading}
              onChange={(event) =>
                setInput(event.target.value)
              }
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey
                ) {
                  event.preventDefault();
                  void askLenny();
                }
              }}
            />

            <div className="composer-footer">
              <span>
                Enter to send · Shift + Enter
                for new line
              </span>

              <div className="composer-actions">
                <button
                  className="artifact-button"
                  disabled={
                    !input.trim() ||
                    loading
                  }
                  onClick={() =>
                    void generateArtifact()
                  }
                >
                  ✦ Create Ship 30
                </button>

                <button
                  className="send-button"
                  disabled={
                    !input.trim() ||
                    loading
                  }
                  onClick={() =>
                    void askLenny()
                  }
                >
                  {loading
                    ? "Thinking..."
                    : "Send →"}
                </button>
              </div>
            </div>
          </div>
        </section>

        <aside className="artifact">
          {!artifact.content ? (
            <div className="artifact-empty">
              <div className="artifact-empty-icon">
                ✦
              </div>

              <div className="artifact-kicker">
                SHIP 30 WORKSPACE
              </div>

              <h3>
                Turn insight into an
                publishable artifact.
              </h3>

              <p>
                Generate a grounded,
                approximately 1,250-word essay
                directly from the retrieved
                evidence.
              </p>

              <div className="artifact-tip">
                <span>HOW IT WORKS</span>

                <div>
                  <b>01</b> Ask a growth question
                </div>

                <div>
                  <b>02</b> Retrieve grounded evidence
                </div>

                <div>
                  <b>03</b> Create Ship 30
                </div>
              </div>
            </div>
          ) : (
            <>
              <header className="artifact-header">
                <div>
                  <span className="artifact-label">
                    GENERATED ARTIFACT
                  </span>

                  <h2>
                    {artifact.title}
                  </h2>

                  {artifact.provider && (
                    <small>
                      {artifact.provider} ·{" "}
                      {artifact.model}
                    </small>
                  )}
                </div>

                <button
                  className="export-button"
                  onClick={
                    exportArtifact
                  }
                >
                  Export .md
                </button>
              </header>

              <div className="artifact-content">
                <div className="artifact-document">
                  <ReactMarkdown>
                    {artifact.content}
                  </ReactMarkdown>
                </div>
              </div>

              {artifact.sources.length >
                0 && (
                <div className="artifact-sources">
                  <div className="artifact-source-heading">
                    Evidence used
                  </div>

                  {artifact.sources.map(
                    (source) => (
                      <div
                        className="artifact-source"
                        key={
                          source.source_id
                        }
                      >
                        <span className="source">
                          {
                            source.source_id
                          }
                        </span>

                        <div>
                          <strong>
                            {source.title}
                          </strong>

                          {source.source_url && (
                            <a
                              href={
                                source.source_url
                              }
                              target="_blank"
                              rel="noreferrer"
                            >
                              View source ↗
                            </a>
                          )}
                        </div>
                      </div>
                    ),
                  )}
                </div>
              )}
            </>
          )}
        </aside>
      </main>
    </div>
  );
}

export default App;