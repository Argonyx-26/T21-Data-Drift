import React from 'react';

interface SeverityBadgeProps {
  severity: string;
  size?: 'sm' | 'md';
}

export default function SeverityBadge({ severity, size = 'md' }: SeverityBadgeProps) {
  const norm = (severity || 'Medium').toLowerCase();
  
  let bg = '#FEF3C7';
  let text = '#B45309';
  let border = '#FDE68A';

  if (norm === 'critical') {
    bg = '#FEE2E2';
    text = '#DC2626';
    border = '#FCA5A5';
  } else if (norm === 'high') {
    bg = '#FFEDD5';
    text = '#EA580C';
    border = '#FDBA74';
  } else if (norm === 'medium') {
    bg = '#FEF3C7';
    text = '#D97706';
    border = '#FCD34D';
  } else if (norm === 'low') {
    bg = '#D1FAE5';
    text = '#059669';
    border = '#6EE7B7';
  }

  const isSmall = size === 'sm';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: isSmall ? '3px 8px' : '4px 14px',
        borderRadius: '9999px',
        fontSize: isSmall ? '0.72rem' : '0.8rem',
        fontWeight: 700,
        backgroundColor: bg,
        color: text,
        border: `1px solid ${border}`,
        letterSpacing: '0.02em',
        textTransform: 'capitalize',
        whiteSpace: 'nowrap',
      }}
    >
      {severity}
    </span>
  );
}
