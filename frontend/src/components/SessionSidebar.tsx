import React from 'react';
import { MessageSquare, Trash2, Plus } from 'lucide-react';
import { Session } from '../types';

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string, e: React.MouseEvent) => void;
  onNewChat?: () => void;
}

export const SessionSidebar: React.FC<SessionSidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewChat,
}) => {
  return (
    <aside className="sessions-sidebar">
      <div className="sidebar-top">
        <div>
          <div className="sidebar-kicker">WORKBENCH / 01</div>
          <div className="sidebar-heading">Conversation log <span>{sessions.length}</span></div>
        </div>
        {onNewChat && (
          <button className="sidebar-add" onClick={onNewChat} aria-label="Start new chat" title="Start new chat">
            <Plus size={15} />
          </button>
        )}
      </div>

      <div className="sessions-list">
        {sessions.length === 0 ? (
          <div className="sidebar-empty">
            <MessageSquare size={18} />
            <p>Your conversations will appear here.</p>
          </div>
        ) : sessions.map((s) => {
          const isActive = s.id === activeSessionId;
          return (
            <button
              key={s.id}
              className={`session-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectSession(s.id)}
            >
              <MessageSquare size={15} />
              <span className="session-title-text" title={s.title}>{s.title}</span>
              <span
                className="session-delete-btn"
                title="Delete session"
                onClick={(e) => onDeleteSession(s.id, e)}
              >
                <Trash2 size={13} />
              </span>
            </button>
          );
        })}
      </div>

    </aside>
  );
};
