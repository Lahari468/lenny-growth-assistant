import React from 'react';
import { Plus, Server, Wifi } from 'lucide-react';
import { ModelInfo, HealthStatus } from '../types';

interface HeaderProps {
  models: ModelInfo[];
  activeProvider: string;
  onProviderChange: (provider: string) => void;
  health: HealthStatus | null;
  onNewChat: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  models,
  activeProvider,
  onProviderChange,
  health,
  onNewChat,
}) => {
  const isHealthy = health?.status === 'healthy';
  const isDegraded = health?.status === 'degraded';
  const providerModels = models.filter((m) => m.provider === activeProvider);
  const activeModel = providerModels.find((m) => m.is_active) || providerModels[0];

  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon" aria-hidden="true">
          <span className="logo-orbit"><span>L</span></span>
        </div>
        <div className="brand-copy">
          <div className="brand-title">LENNY / GROWTH</div>
          <div className="brand-subtitle">Product intelligence workspace</div>
        </div>
      </div>

      <div className="header-actions">
        <div className="model-selector" title={activeModel?.description || 'Switch active model provider'}>
          <Server size={14} />
          <select value={activeProvider} onChange={(e) => onProviderChange(e.target.value)} aria-label="AI provider">
            {models.length > 0 ? (
              Array.from(new Set(models.map((m) => m.provider))).map((prov) => (
                <option key={prov} value={prov}>
                  {prov === 'ollama' ? 'Ollama · Local' : 'Claude · Cloud'}
                </option>
              ))
            ) : (
              <>
                <option value="ollama">Ollama · Local</option>
                <option value="anthropic">Claude · Cloud</option>
              </>
            )}
          </select>
        </div>

        <div
          className={`status-pill ${isHealthy ? 'healthy' : isDegraded ? 'degraded' : 'offline'}`}
          title={
            health
              ? `Database: ${health.database.status} · ${health.vector_store.indexed_chunks} indexed chunks · ${health.llm_providers.active_provider}`
              : 'Checking backend health...'
          }
        >
          <Wifi size={12} />
          <span>{isHealthy ? 'SYSTEM ONLINE' : isDegraded ? 'DEGRADED' : health ? 'OFFLINE' : 'CONNECTING'}</span>
        </div>

        <button className="btn-primary" onClick={onNewChat} id="btn-new-chat">
          <Plus size={15} />
          <span>New chat</span>
        </button>
      </div>
    </header>
  );
};
