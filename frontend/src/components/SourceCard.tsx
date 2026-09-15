import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { Citation } from '../types';

interface SourceCardProps {
  citation: Citation;
  index: number;
}

export const SourceCard: React.FC<SourceCardProps> = ({ citation, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="citation-card">
      <div className="citation-top" onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="citation-title">
            Source {index}: {citation.guest} — {citation.episode_title}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="citation-match">{(citation.similarity_score * 100).toFixed(0)}% match</span>
          {expanded ? <ChevronUp size={14} color="#9CA3AF" /> : <ChevronDown size={14} color="#9CA3AF" />}
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 8, borderTop: '1px solid #1F2937', paddingTop: 8 }}>
          <p className="citation-snippet">"{citation.snippet}"</p>
          <a
            href={citation.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="citation-link"
          >
            <span>Open Transcript / Episode Clip</span>
            <ExternalLink size={12} />
          </a>
        </div>
      )}
    </div>
  );
};
