import React, { useState } from 'react';
import { ShieldCheck, Download, Code, Eye, FileText, Copy, Check, X, AlertCircle, Loader2, BookOpen } from 'lucide-react';
import { Artifact } from '../types';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  isLoading?: boolean;
  error?: string | null;
  onClose?: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({
  artifact,
  isLoading = false,
  error = null,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'preview' | 'source'>('preview');
  const [copied, setCopied] = useState(false);

  // Loading state
  if (isLoading) {
    return (
      <aside className="artifact-panel" aria-label="Artifact viewer loading">
        <div className="artifact-header">
          <span style={{ fontSize: 13, fontWeight: 600, color: '#9CA3AF' }}>Generating Artifact...</span>
          {onClose && (
            <button onClick={onClose} className="artifact-close-btn" aria-label="Close artifact viewer">
              <X size={15} />
            </button>
          )}
        </div>
        <div className="artifact-empty">
          <Loader2 size={36} className="spinning-loader" style={{ color: '#6366F1', marginBottom: 14 }} />
          <h4 style={{ fontSize: 15, fontWeight: 600, color: '#D1D5DB', marginBottom: 6 }}>
            Crafting Standalone Artifact
          </h4>
          <p style={{ fontSize: 13, color: '#6B7280', maxWidth: 280 }}>
            Synthesizing conversation context and applying security isolation sandbox...
          </p>
        </div>
      </aside>
    );
  }

  // Error state
  if (error) {
    return (
      <aside className="artifact-panel" aria-label="Artifact viewer error">
        <div className="artifact-header">
          <span style={{ fontSize: 13, fontWeight: 600, color: '#EF4444' }}>Artifact Error</span>
          {onClose && (
            <button onClick={onClose} className="artifact-close-btn" aria-label="Close artifact viewer">
              <X size={15} />
            </button>
          )}
        </div>
        <div className="artifact-empty">
          <AlertCircle size={38} style={{ color: '#EF4444', marginBottom: 12 }} />
          <h4 style={{ fontSize: 15, fontWeight: 600, color: '#FCA5A5', marginBottom: 6 }}>
            Failed to Load Artifact
          </h4>
          <p style={{ fontSize: 13, color: '#9CA3AF', maxWidth: 280 }}>{error}</p>
        </div>
      </aside>
    );
  }

  // Empty state
  if (!artifact) {
    return (
      <aside className="artifact-panel" aria-label="Artifact viewer empty">
        <div className="artifact-header">
          <span style={{ fontSize: 13, fontWeight: 600, color: '#9CA3AF' }}>Artifact Viewer</span>
        </div>
        <div className="artifact-empty">
          <FileText size={42} style={{ opacity: 0.3, marginBottom: 12 }} />
          <h4 style={{ fontSize: 15, fontWeight: 600, color: '#D1D5DB', marginBottom: 6 }}>
            No Artifact Selected
          </h4>
          <p style={{ fontSize: 13, color: '#6B7280', maxWidth: 280 }}>
            Ask the assistant to generate a Markdown strategy document or HTML/CSS landing page to view it live here.
          </p>
        </div>
      </aside>
    );
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy artifact content:', err);
    }
  };

  const handleDownload = () => {
    const ext = artifact.type === 'html' ? 'html' : 'md';
    const mime = artifact.type === 'html' ? 'text/html' : 'text/markdown';
    const blob = new Blob([artifact.content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Safe inline markdown token parser
  const renderInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return <strong key={index} style={{ color: '#F3F4F6' }}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
        return <em key={index}>{part.slice(1, -1)}</em>;
      }
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code
            key={index}
            style={{
              background: 'rgba(255,255,255,0.08)',
              padding: '2px 5px',
              borderRadius: 4,
              fontFamily: 'var(--font-mono, monospace)',
              fontSize: '0.9em',
              color: '#C7D2FE',
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  // Native Markdown Document Renderer without dangerouslySetInnerHTML
  const renderMarkdownDocument = (content: string) => {
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let inTable = false;
    let tableRows: string[][] = [];

    const flushTable = (keyIndex: number) => {
      if (tableRows.length === 0) return;
      const headers = tableRows[0];
      const dataRows = tableRows.slice(1).filter((r) => !r.every((c) => c.match(/^[:\-\s]+$/)));
      elements.push(
        <div key={`table-${keyIndex}`} style={{ overflowX: 'auto', margin: '16px 0' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, border: '1px solid #1F2937' }}>
            <thead>
              <tr style={{ background: '#111827', borderBottom: '2px solid #374151' }}>
                {headers.map((h, hi) => (
                  <th key={hi} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#E5E7EB' }}>
                    {renderInline(h.trim())}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataRows.map((row, ri) => (
                <tr key={ri} style={{ borderBottom: '1px solid #1F2937', background: ri % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{ padding: '8px 12px', color: '#9CA3AF' }}>
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
      inTable = false;
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Check table row
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        inTable = true;
        const cols = trimmed.slice(1, -1).split('|');
        tableRows.push(cols);
        return;
      } else if (inTable) {
        flushTable(idx);
      }

      // Headers
      if (line.startsWith('# ')) {
        elements.push(
          <h1 key={idx} style={{ fontSize: 22, fontWeight: 700, color: '#FFFFFF', marginTop: 16, marginBottom: 8, borderBottom: '1px solid #1F2937', paddingBottom: 6 }}>
            {renderInline(line.replace('# ', ''))}
          </h1>
        );
      } else if (line.startsWith('## ')) {
        elements.push(
          <h2 key={idx} style={{ fontSize: 17, fontWeight: 600, color: '#F3F4F6', marginTop: 18, marginBottom: 8 }}>
            {renderInline(line.replace('## ', ''))}
          </h2>
        );
      } else if (line.startsWith('### ')) {
        elements.push(
          <h3 key={idx} style={{ fontSize: 14.5, fontWeight: 600, color: '#E5E7EB', marginTop: 14, marginBottom: 6 }}>
            {renderInline(line.replace('### ', ''))}
          </h3>
        );
      } else if (line.startsWith('> ')) {
        elements.push(
          <blockquote key={idx} style={{ borderLeft: '3px solid #6366F1', padding: '6px 14px', margin: '10px 0', background: 'rgba(99, 102, 241, 0.05)', color: '#D1D5DB', fontStyle: 'italic', borderRadius: '0 4px 4px 0' }}>
            {renderInline(line.replace('> ', ''))}
          </blockquote>
        );
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        elements.push(
          <li key={idx} style={{ marginLeft: 20, marginBottom: 4, color: '#D1D5DB', fontSize: 13.5, lineHeight: 1.6 }}>
            {renderInline(line.substring(2))}
          </li>
        );
      } else if (/^\d+\.\s/.test(line)) {
        const text = line.replace(/^\d+\.\s/, '');
        elements.push(
          <li key={idx} style={{ marginLeft: 20, marginBottom: 4, color: '#D1D5DB', fontSize: 13.5, lineHeight: 1.6 }}>
            {renderInline(text)}
          </li>
        );
      } else if (trimmed === '') {
        elements.push(<div key={idx} style={{ height: 8 }} />);
      } else {
        elements.push(
          <p key={idx} style={{ color: '#D1D5DB', fontSize: 13.5, lineHeight: 1.65, marginBottom: 6 }}>
            {renderInline(line)}
          </p>
        );
      }
    });

    if (inTable) {
      flushTable(lines.length);
    }

    return <div className="native-markdown-document">{elements}</div>;
  };

  return (
    <aside className="artifact-panel" aria-label="Artifact viewer panel">
      <div className="artifact-header">
        <div className="artifact-title-group">
          <span className="artifact-title" title={artifact.title}>
            {artifact.title}
          </span>
          <span className="artifact-type-badge">{artifact.type.toUpperCase()}</span>
          <span className="security-badge" title="Rendered in isolated sandboxed iframe without script execution">
            <ShieldCheck size={12} />
            <span>Sandboxed</span>
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {/* Tabs */}
          <div className="artifact-tabs">
            <button
              className={`artifact-tab ${activeTab === 'preview' ? 'active' : ''}`}
              onClick={() => setActiveTab('preview')}
              aria-label="Preview artifact"
            >
              <Eye size={12} style={{ marginRight: 4 }} />
              <span>Preview</span>
            </button>
            <button
              className={`artifact-tab ${activeTab === 'source' ? 'active' : ''}`}
              onClick={() => setActiveTab('source')}
              aria-label="View source code"
            >
              <Code size={12} style={{ marginRight: 4 }} />
              <span>Source</span>
            </button>
          </div>

          {/* Copy */}
          <button
            onClick={handleCopy}
            className="artifact-action-btn"
            title="Copy artifact content"
            aria-label="Copy artifact content"
          >
            {copied ? <Check size={14} color="#10B981" /> : <Copy size={14} />}
          </button>

          {/* Download */}
          <button
            onClick={handleDownload}
            className="artifact-action-btn"
            title="Download artifact file"
            aria-label="Download artifact file"
          >
            <Download size={14} />
          </button>

          {/* Close button */}
          {onClose && (
            <button
              onClick={onClose}
              className="artifact-action-btn close-btn"
              title="Close artifact viewer"
              aria-label="Close artifact viewer"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      <div className={`artifact-body ${artifact.type === 'markdown' && activeTab === 'preview' ? 'markdown-mode' : ''}`}>
        {activeTab === 'preview' ? (
          artifact.type === 'html' ? (
            /* Sandboxed iframe with strictly empty sandbox attribute:
               - No allow-same-origin (cannot access localStorage, cookies, parent DOM)
               - No allow-scripts (scripts will not execute)
               - No allow-top-navigation (cannot escape frame context) */
            <iframe
              sandbox=""
              srcDoc={artifact.content}
              title={artifact.title}
              className="sandboxed-frame"
            />
          ) : (
            <div style={{ padding: 20, overflowY: 'auto', height: '100%' }}>
              {renderMarkdownDocument(artifact.content)}
            </div>
          )
        ) : (
          <div className="source-viewer-container">
            <pre className="source-code-pre">
              <code>{artifact.content}</code>
            </pre>
          </div>
        )}
      </div>

      {/* Citations Footer if sources exist */}
      {artifact.sources && artifact.sources.length > 0 && (
        <div className="artifact-sources-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#9CA3AF' }}>
            <BookOpen size={13} color="#6366F1" />
            <span>Grounded in {artifact.sources.length} Lenny's Podcast transcript source(s)</span>
          </div>
        </div>
      )}
    </aside>
  );
};

