'use client';
import { useEffect } from 'react';

export default function SideSheet({ isOpen, onClose, title, subtitle, tag, children, maxWidth = '640px' }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="sidesheet-overlay" onClick={onClose}>
      <div 
        className="sidesheet-panel" 
        style={{ maxWidth }} 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="sidesheet-header">
          <div className="sidesheet-title-block">
            <div className="sidesheet-title-row">
              <h3 className="sidesheet-title">{title}</h3>
              {tag && <span className="sidesheet-tag font-mono">{tag}</span>}
            </div>
            {subtitle && <p className="sidesheet-subtitle font-mono">{subtitle}</p>}
          </div>
          <button 
            className="sidesheet-close-btn" 
            onClick={onClose}
            aria-label="Close panel"
          >
            ✕
          </button>
        </div>
        <div className="sidesheet-body">
          {children}
        </div>
      </div>
    </div>
  );
}
