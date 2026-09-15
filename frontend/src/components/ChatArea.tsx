import React, { useState, useRef, useEffect } from 'react';
import { Send, Compass, Search, PenLine, LayoutDashboard } from 'lucide-react';
import { Message } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (content: string) => void;
  onViewArtifact?: (artifactId: string) => void;
}

const STARTER_PROMPTS = [
  {
    tag: 'Discovery',
    icon: Compass,
    text: 'How does Teresa Torres use continuous discovery to keep customer evidence close to product decisions?',
  },
  {
    tag: 'Positioning',
    icon: Search,
    text: 'Walk me through April Dunford’s positioning sequence, starting with competitive alternatives.',
  },
  {
    tag: 'PMF',
    icon: PenLine,
    text: 'Explain Rahul Vohra’s product-market-fit loop and why the somewhat-disappointed segment matters.',
  },
  {
    tag: 'Product Strategy',
    icon: LayoutDashboard,
    text: 'Compare feature teams and empowered product teams using Marty Cagan’s framework.',
  },
];

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onViewArtifact,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
  };

  return (
    <div className="chat-section">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"><Compass size={24} /></div>
            <h2 className="empty-title">The Lenny Growth Assistant</h2>
            <p className="empty-subtitle">
              Explore product discovery, positioning, product-market fit, and empowered-team thinking
              using grounded knowledge notes from Lenny’s Podcast.
            </p>

            <div className="starter-grid">
              {STARTER_PROMPTS.map((starter, idx) => {
                const Icon = starter.icon;
                return (
                  <button
                    key={idx}
                    className="starter-card"
                    onClick={() => onSendMessage(starter.text)}
                    type="button"
                  >
                    <div className="starter-tag"><Icon size={14} /> {starter.tag}</div>
                    <div className="starter-text">{starter.text}</div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <MessageBubble key={m.id} message={m} onViewArtifact={onViewArtifact} />
          ))
        )}

        {isLoading && (
          <div className="message-row assistant">
            <div className="message-meta">
              <Search size={13} />
              <span>Searching the knowledge base & synthesizing...</span>
            </div>
            <div className="message-bubble" style={{ width: 'auto' }}>
              <div className="shimmer">
                <span className="dot-flashing" />
                <span>Formulating grounded answer...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar">
        <form onSubmit={handleSubmit} className="input-container">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about discovery, positioning, PMF, strategy, or request an artifact..."
            className="chat-textarea"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={!input.trim() || isLoading}
            id="btn-send-message"
            aria-label="Send message"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
};
