import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Sparkles, ShieldCheck, FileText, BarChart3, Lightbulb } from 'lucide-react';
import { Message } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (content: string) => void;
  onViewArtifact?: (artifactId: string) => void;
}

const STARTER_PROMPTS = [
  { tag: 'Grounded QA', icon: Lightbulb, text: 'How did Shreyas Doshi define High Agency for product managers?' },
  { tag: 'B2B Growth', icon: BarChart3, text: 'What is Elena Verna’s thesis on Reverse Trials vs Freemium?' },
  { tag: 'Ship 30 Essay', icon: FileText, text: 'Write a Ship 30 style essay on Brian Chesky’s Founder Mode and product craft.' },
  { tag: 'HTML Artifact', icon: BarChart3, text: 'Generate an HTML growth metric scorecard dashboard based on Gustaf Alströmer.' },
];

const QUICK_ACTIONS = ['Product growth lessons', 'Find a framework', 'Generate an artifact'];

export const ChatArea: React.FC<ChatAreaProps> = ({ messages, isLoading, onSendMessage, onViewArtifact }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
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
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  return (
    <main className="chat-section">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="hero-mark"><Sparkles size={23} /></div>
            <div className="eyebrow"><span /> PRODUCT INTELLIGENCE / 01</div>
            <h1 className="empty-title">Turn insight<br /><span>into action.</span></h1>
            <p className="empty-subtitle">
              Search the conversation archive, pressure-test product thinking, and turn proven ideas into something you can ship.
            </p>

            <div className="capability-row">
              <span><ShieldCheck size={14} /> Grounded answers</span>
              <span><FileText size={14} /> Ship 30</span>
              <span><BarChart3 size={14} /> Build artifacts</span>
            </div>

            <div className="starter-heading"><span>Pick a starting point</span><small>Four focused workflows</small></div>
            <div className="starter-grid">
              {STARTER_PROMPTS.map((starter) => {
                const Icon = starter.icon;
                return (
                  <button key={starter.text} className="starter-card" onClick={() => onSendMessage(starter.text)}>
                    <div className="starter-card-top">
                      <span className="starter-icon"><Icon size={15} /></span>
                      <span className="starter-tag">{starter.tag}</span>
                    </div>
                    <div className="starter-text">{starter.text}</div>
                    <span className="starter-arrow">+</span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} onViewArtifact={onViewArtifact} />)
        )}

        {isLoading && (
          <div className="message-row assistant">
            <div className="message-meta"><Sparkles size={13} /><span>Searching transcripts & synthesizing</span></div>
            <div className="message-bubble loading-bubble">
              <div className="shimmer"><span className="dot-flashing" /><span>Formulating a grounded answer…</span></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="composer-wrap">
        <div className="quick-actions"><span className="composer-label">QUICK START</span>
          {QUICK_ACTIONS.map((action) => (
            <button key={action} onClick={() => setInput(action === 'Find a framework' ? 'What are the best product growth frameworks in the transcripts?' : action === 'Generate an artifact' ? 'Generate an HTML growth scorecard dashboard.' : 'What are the most important lessons about product growth?')}>
              {action}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="input-container">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask a product question or build something from the archive…"
            className="chat-textarea"
            disabled={isLoading}
            aria-label="Message"
          />
          <button type="submit" className="send-btn" disabled={!input.trim() || isLoading} id="btn-send-message" aria-label="Send message">
            <ArrowUp size={17} />
          </button>
        </form>
      </div>
    </main>
  );
};
