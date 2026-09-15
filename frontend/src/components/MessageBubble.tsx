import React, { useState } from 'react';
import { BookOpen, Sparkles, Layout, ChevronDown, ChevronUp } from 'lucide-react';
import { Message } from '../types';
import { SourceCard } from './SourceCard';

interface MessageBubbleProps {
  message: Message;
  onViewArtifact?: (artifactId: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onViewArtifact }) => {
  const isUser = message.role === 'user';
  const [showCitations, setShowCitations] = useState(false);

  const renderInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
        return <em key={index}>{part.slice(1, -1)}</em>;
      }
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code
            key={index}
            style={{
              background: 'rgba(255,255,255,0.1)',
              padding: '2px 4px',
              borderRadius: 4,
              fontFamily: 'monospace',
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  // Format basic markdown text into pure React elements without any dangerouslySetInnerHTML
  const renderFormattedContent = (content: string) => {
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];

    lines.forEach((line, i) => {
      if (line.startsWith('### ')) {
        elements.push(<h3 key={i}>{renderInline(line.replace('### ', ''))}</h3>);
      } else if (line.startsWith('## ')) {
        elements.push(<h2 key={i}>{renderInline(line.replace('## ', ''))}</h2>);
      } else if (line.startsWith('# ')) {
        elements.push(<h1 key={i}>{renderInline(line.replace('# ', ''))}</h1>);
      } else if (line.startsWith('> ')) {
        elements.push(
          <blockquote key={i} style={{ borderLeft: '3px solid #6366F1', paddingLeft: 12, margin: '8px 0', color: '#9CA3AF', fontStyle: 'italic' }}>
            {renderInline(line.substring(2))}
          </blockquote>
        );
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        elements.push(<li key={i}>{renderInline(line.substring(2))}</li>);
      } else if (line.trim() === '') {
        elements.push(<div key={i} style={{ height: 6 }} />);
      } else {
        elements.push(<p key={i}>{renderInline(line)}</p>);
      }
    });

    return <div className="formatted-content">{elements}</div>;
  };


  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="message-meta" aria-label="The Lenny Growth Assistant response">
          <span className="meta-icon" aria-hidden="true" style={{ display: 'inline-flex', alignItems: 'center' }}>
            <Sparkles size={13} color="#6366F1" />
          </span>
          <span className="assistant-title" style={{ fontWeight: 600 }}>The Lenny Growth Assistant</span>
          {message.intent && (
            <span className="intent-badge">
              {message.intent === 'ship30' ? 'Ship 30 Essay' : message.intent === 'artifact_generation' ? 'Artifact' : 'Grounded QA'}
            </span>
          )}
        </div>
      )}

      <div className="message-bubble">
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <div>
            {renderFormattedContent(message.content)}

            {/* View Artifact Banner if generated */}
            {message.has_artifact && message.artifact_id && (
              <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Layout size={16} color="#818CF8" />
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#C7D2FE' }}>
                    Interactive Artifact Generated
                  </span>
                </div>
                {onViewArtifact && (
                  <button
                    onClick={() => onViewArtifact(message.artifact_id!)}
                    style={{ background: '#6366F1', color: '#fff', padding: '4px 10px', borderRadius: 4, fontSize: 12, fontWeight: 600 }}
                  >
                    Open in Viewer
                  </button>
                )}
              </div>
            )}

            {/* Citations Accordion - strictly separated from answer */}
            {message.citations && message.citations.length > 0 && (
              <div className="citations-wrapper">
                <button
                  className="citations-header"
                  onClick={() => setShowCitations(!showCitations)}
                >
                  <BookOpen size={13} />
                  <span>
                    Verified Transcript Citations ({message.citations.length} sources)
                  </span>
                  {showCitations ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>

                {showCitations && (
                  <div className="citations-list">
                    {message.citations.map((cit, idx) => (
                      <SourceCard key={cit.chunk_id || idx} citation={cit} index={idx + 1} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
