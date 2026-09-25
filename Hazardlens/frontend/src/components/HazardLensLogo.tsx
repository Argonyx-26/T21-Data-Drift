import React from 'react';

interface HazardLensLogoProps {
  size?: 'sm' | 'md' | 'lg';
  theme?: 'dark' | 'light';
  showWordmark?: boolean;
}

export default function HazardLensLogo({
  size = 'md',
  theme = 'light',
  showWordmark = true,
}: HazardLensLogoProps) {
  const iconDimensions = {
    sm: 32,
    md: 40,
    lg: 48,
  }[size];

  const fontSize = {
    sm: '1.15rem',
    md: '1.4rem',
    lg: '1.75rem',
  }[size];

  const isDark = theme === 'dark';

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
      {/* Safety Shield + Hard-Hat Emblem */}
      <svg
        width={iconDimensions}
        height={iconDimensions}
        viewBox="0 0 44 44"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0, filter: 'drop-shadow(0 4px 10px rgba(245, 166, 35, 0.35))' }}
      >
        <defs>
          <linearGradient id="shieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#F5A623" />
            <stop offset="100%" stopColor="#E28807" />
          </linearGradient>
          <linearGradient id="crestGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="100%" stopColor="#FFF2D6" />
          </linearGradient>
        </defs>

        {/* Outer Hexagonal Safety Shield */}
        <path
          d="M22 2 L39 8 V21 C39 31.5 22 41 22 41 C22 41 5 31.5 5 21 V8 L22 2 Z"
          fill="url(#shieldGrad)"
        />

        {/* Shield Inner Inset */}
        <path
          d="M22 5.5 L36 10.5 V20.5 C36 29 22 37.5 22 37.5 C22 37.5 8 29 8 20.5 V10.5 L22 5.5 Z"
          fill="#181926"
        />

        {/* Stylized Hard-Hat Contour */}
        {/* Brim */}
        <ellipse cx="22" cy="24" rx="10.5" ry="3.2" fill="url(#shieldGrad)" />
        {/* Dome */}
        <path
          d="M13.5 23.5 C13.5 15.5 30.5 15.5 30.5 23.5 Z"
          fill="url(#shieldGrad)"
        />
        {/* Central Ridge */}
        <path
          d="M21 16 L23 16 L23.5 23.5 L20.5 23.5 Z"
          fill="url(#crestGrad)"
          opacity="0.9"
        />
        {/* AI Lens Center Dot */}
        <circle cx="22" cy="20" r="1.8" fill="#181926" />
      </svg>

      {/* Brand Wordmark */}
      {showWordmark && (
        <span
          style={{
            fontFamily: 'var(--font-heading)',
            fontSize,
            fontWeight: 800,
            letterSpacing: '-0.02em',
            display: 'inline-flex',
            alignItems: 'baseline',
            lineHeight: 1,
          }}
        >
          <span style={{ color: isDark ? '#FFFFFF' : '#181926' }}>Hazard</span>
          <span style={{ color: '#F5A623' }}>Lens</span>
          <span
            style={{
              width: '5px',
              height: '5px',
              borderRadius: '50%',
              backgroundColor: '#F5A623',
              marginLeft: '2px',
              display: 'inline-block',
            }}
          />
        </span>
      )}
    </div>
  );
}
