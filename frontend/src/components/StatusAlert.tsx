import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface StatusAlertProps {
  message: string | null;
  onDismiss: () => void;
}

export const StatusAlert: React.FC<StatusAlertProps> = ({ message, onDismiss }) => {
  if (!message) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        background: '#1F2937',
        border: '1px solid #EF4444',
        borderRadius: 8,
        padding: '12px 16px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        maxWidth: 450,
        zIndex: 100,
      }}
    >
      <AlertTriangle size={18} color="#EF4444" style={{ flexShrink: 0 }} />
      <span style={{ fontSize: 13, color: '#F9FAFB', flex: 1 }}>{message}</span>
      <button
        onClick={onDismiss}
        style={{ background: 'transparent', color: '#9CA3AF', padding: 4 }}
      >
        <X size={14} />
      </button>
    </div>
  );
};
