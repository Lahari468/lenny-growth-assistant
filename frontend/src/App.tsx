import React, { useState, useEffect, useCallback } from 'react';
import { api } from './api/client';
import { Session, Message, Artifact, ModelInfo, HealthStatus } from './types';
import { Header } from './components/Header';
import { SessionSidebar } from './components/SessionSidebar';
import { ChatArea } from './components/ChatArea';
import { ArtifactViewer } from './components/ArtifactViewer';
import { StatusAlert } from './components/StatusAlert';

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [activeProvider, setActiveProvider] = useState<string>('ollama');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isArtifactLoading, setIsArtifactLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);


  // Initial load: fetch health, models, and sessions
  const loadInitialData = useCallback(async () => {
    try {
      const [h, mList, sList] = await Promise.allSettled([
        api.getHealth(),
        api.listModels(),
        api.listSessions(),
      ]);

      if (h.status === 'fulfilled') {
        setHealth(h.value);
        setActiveProvider(h.value.llm_providers.active_provider || 'ollama');
      }
      if (mList.status === 'fulfilled') {
        setModels(mList.value);
      }
      if (sList.status === 'fulfilled') {
        setSessions(sList.value.sessions);
        if (sList.value.sessions.length > 0 && !activeSessionId) {
          setActiveSessionId(sList.value.sessions[0].id);
        }
      }
    } catch (err) {
      console.error('Error during initial app boot:', err);
    }
  }, [activeSessionId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load messages whenever active session changes
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      setActiveArtifact(null);
      return;
    }

    const loadSessionContent = async () => {
      try {
        const [msgsRes, artsRes] = await Promise.all([
          api.listMessages(activeSessionId),
          api.listArtifacts(activeSessionId),
        ]);
        setMessages(msgsRes.messages);
        if (artsRes.artifacts.length > 0) {
          setActiveArtifact(artsRes.artifacts[0]);
        } else {
          setActiveArtifact(null);
        }
      } catch (err: any) {
        setErrorMessage(err.message || 'Failed to load session messages');
      }
    };

    loadSessionContent();
  }, [activeSessionId]);

  const handleCreateNewChat = async () => {
    try {
      const newSession = await api.createSession();
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setMessages([]);
      setActiveArtifact(null);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to create new session');
    }
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteSession(id);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSessionId === id) {
        if (remaining.length > 0) {
          setActiveSessionId(remaining[0].id);
        } else {
          handleCreateNewChat();
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete session');
    }
  };

  const handleSendMessage = async (content: string) => {
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      try {
        const newSession = await api.createSession();
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        currentSessionId = newSession.id;
      } catch (err: any) {
        setErrorMessage(err.message || 'Failed to initialize session');
        return;
      }
    }

    // Optimistic user message append
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: currentSessionId,
      role: 'user',
      content,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    const isArtifactQuery = /\b(generate|create|build|render|make|draft)\b.*?\b(markdown|html|landing\s+page|artifact|dashboard|component|document)\b/i.test(content);
    setIsLoading(true);
    if (isArtifactQuery) {
      setIsArtifactLoading(true);
    }

    try {
      const assistantMsg = await api.sendMessage(currentSessionId, content, activeProvider);
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), tempUserMsg, assistantMsg]);

      // If an artifact was generated in this response, fetch and display it
      if (assistantMsg.has_artifact && assistantMsg.artifact_id) {
        const art = await api.getArtifact(currentSessionId, assistantMsg.artifact_id);
        setActiveArtifact(art);
      }

      // Update session title in sidebar
      const updatedSessions = await api.listSessions();
      setSessions(updatedSessions.sessions);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to receive assistant response');
    } finally {
      setIsLoading(false);
      setIsArtifactLoading(false);
    }
  };

  const handleProviderChange = async (provider: string) => {
    try {
      await api.setActiveProvider(provider);
      setActiveProvider(provider);
    } catch (err: any) {
      setErrorMessage(err.message || `Failed to switch to provider: ${provider}`);
    }
  };

  const handleViewArtifact = async (artifactId: string) => {
    if (!activeSessionId) return;
    try {
      const art = await api.getArtifact(activeSessionId, artifactId);
      setActiveArtifact(art);
    } catch (err: any) {
      setErrorMessage(err.message || 'Could not load requested artifact');
    }
  };

  return (
    <div className="app-container">
      <Header
        models={models}
        activeProvider={activeProvider}
        onProviderChange={handleProviderChange}
        health={health}
        onNewChat={handleCreateNewChat}
      />

      <div className="main-workspace">
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={(id) => setActiveSessionId(id)}
          onDeleteSession={handleDeleteSession}
          onNewChat={handleCreateNewChat}
        />

        <ChatArea
          messages={messages}
          isLoading={isLoading}
          onSendMessage={handleSendMessage}
          onViewArtifact={handleViewArtifact}
        />

        {(activeArtifact || isArtifactLoading) && (
          <ArtifactViewer
            artifact={activeArtifact}
            isLoading={isArtifactLoading}
            onClose={() => setActiveArtifact(null)}
          />
        )}
      </div>


      <StatusAlert message={errorMessage} onDismiss={() => setErrorMessage(null)} />
    </div>
  );
};
export default App;
