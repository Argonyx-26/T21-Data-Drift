import React from 'react';

interface MascotProps {
  speechText?: string;
  variant?: 'tablet' | 'photo' | 'lightbulb' | 'dataset';
  height?: number;
}

export default function MascotIllustration({
  speechText,
  variant = 'tablet',
  height = 240,
}: MascotProps) {
  return (
    <div
      style={{
        position: 'relative',
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-end',
      }}
    >
      {/* Speech Bubble */}
      {speechText && (
        <div
          style={{
            position: 'absolute',
            top: '-15px',
            right: variant === 'tablet' ? '-20px' : '-35px',
            background: '#FFFFFF',
            padding: '7px 14px',
            borderRadius: '16px',
            boxShadow: '0 8px 24px -4px rgba(24, 25, 38, 0.14)',
            border: '2px solid #F5A623',
            fontSize: '0.82rem',
            fontWeight: 800,
            fontFamily: 'var(--font-heading)',
            color: '#181926',
            whiteSpace: 'nowrap',
            zIndex: 10,
            animation: 'fadeIn 0.5s ease',
          }}
        >
          {speechText}
          <div
            style={{
              position: 'absolute',
              bottom: '-7px',
              left: '20px',
              width: 0,
              height: 0,
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderTop: '7px solid #F5A623',
            }}
          />
        </div>
      )}

      {/* High-Fidelity SVG Mascot */}
      <svg
        width={height * 0.85}
        height={height}
        viewBox="0 0 200 240"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ filter: 'drop-shadow(0 12px 24px rgba(0,0,0,0.12))' }}
      >
        <defs>
          <linearGradient id="skin" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FDDFBA" />
            <stop offset="100%" stopColor="#F5B285" />
          </linearGradient>
          <linearGradient id="hardhat" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFDE59" />
            <stop offset="60%" stopColor="#F5A623" />
            <stop offset="100%" stopColor="#D98200" />
          </linearGradient>
          <linearGradient id="vest" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FF7A33" />
            <stop offset="100%" stopColor="#E24A00" />
          </linearGradient>
          <linearGradient id="vestStripe" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#E6FF55" />
            <stop offset="100%" stopColor="#9CDE00" />
          </linearGradient>
          <linearGradient id="suit" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2E334D" />
            <stop offset="100%" stopColor="#1B1E30" />
          </linearGradient>
          <linearGradient id="tabletGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#303545" />
            <stop offset="100%" stopColor="#12131A" />
          </linearGradient>
        </defs>

        {/* Mascot Body & Shoulders */}
        <path
          d="M40 180 C40 150, 60 142, 100 142 C140 142, 160 150, 160 180 L165 240 L35 240 Z"
          fill="url(#suit)"
        />

        {/* Safety Vest */}
        <path
          d="M55 146 L78 240 L122 240 L145 146 C132 142, 115 140, 100 140 C85 140, 68 142, 55 146 Z"
          fill="url(#vest)"
        />

        {/* Vest Reflective Stripes */}
        <line x1="68" y1="150" x2="84" y2="240" stroke="url(#vestStripe)" strokeWidth="8" strokeLinecap="round" />
        <line x1="132" y1="150" x2="116" y2="240" stroke="url(#vestStripe)" strokeWidth="8" strokeLinecap="round" />
        <line x1="60" y1="195" x2="140" y2="195" stroke="url(#vestStripe)" strokeWidth="7" />

        {/* Head / Neck */}
        <rect x="88" y="118" width="24" height="24" rx="6" fill="#F0A678" />
        <path
          d="M65 92 C65 60, 135 60, 135 92 C135 124, 65 124, 65 92 Z"
          fill="url(#skin)"
        />

        {/* Ears */}
        <circle cx="64" cy="94" r="7" fill="#F5B285" />
        <circle cx="136" cy="94" r="7" fill="#F5B285" />

        {/* Hair bangs */}
        <path d="M72 74 Q100 68 128 74 Q120 86 100 82 Q80 88 72 74 Z" fill="#2C1D11" />

        {/* Friendly Eyes */}
        <ellipse cx="84" cy="92" rx="4.5" ry="6" fill="#181926" />
        <circle cx="85.5" cy="90" r="1.8" fill="#FFFFFF" />
        <ellipse cx="116" cy="92" rx="4.5" ry="6" fill="#181926" />
        <circle cx="117.5" cy="90" r="1.8" fill="#FFFFFF" />

        {/* Eyebrows */}
        <path d="M78 82 Q84 79 91 82" stroke="#2C1D11" strokeWidth="2.5" strokeLinecap="round" fill="none" />
        <path d="M109 82 Q116 79 122 82" stroke="#2C1D11" strokeWidth="2.5" strokeLinecap="round" fill="none" />

        {/* Cheerful Smile */}
        <path d="M92 104 Q100 112 108 104" stroke="#8A3B14" strokeWidth="2.5" strokeLinecap="round" fill="none" />
        {/* Rosy cheeks */}
        <ellipse cx="76" cy="99" rx="5" ry="3" fill="#FF8D85" opacity="0.4" />
        <ellipse cx="124" cy="99" rx="5" ry="3" fill="#FF8D85" opacity="0.4" />

        {/* Yellow Hardhat */}
        <ellipse cx="100" cy="62" rx="46" ry="10" fill="url(#hardhat)" />
        <path
          d="M58 60 C58 24, 142 24, 142 60 C142 63, 58 63, 58 60 Z"
          fill="url(#hardhat)"
        />
        {/* Hardhat Ridge */}
        <path d="M96 24 C96 22, 104 22, 104 24 L104 60 L96 60 Z" fill="#FFEDB0" opacity="0.6" />
        {/* Hardhat front safety logo badge */}
        <circle cx="100" cy="46" r="6" fill="#FFFFFF" />
        <polygon points="100,42 103,48 97,48" fill="#F5A623" />

        {/* Item holding based on variant */}
        {variant === 'tablet' && (
          <g>
            <rect x="74" y="160" width="52" height="42" rx="5" fill="url(#tabletGrad)" stroke="#50566A" strokeWidth="2" />
            <rect x="79" y="165" width="42" height="30" rx="3" fill="#0EA5E9" opacity="0.8" />
            {/* Tablet graph screen */}
            <polyline points="83,188 90,178 98,183 108,172 116,184" fill="none" stroke="#FFFFFF" strokeWidth="2" />
            {/* Hands */}
            <circle cx="72" cy="180" r="7" fill="url(#skin)" />
            <circle cx="128" cy="180" r="7" fill="url(#skin)" />
          </g>
        )}

        {variant === 'photo' && (
          <g>
            {/* Photo frame */}
            <rect x="110" y="130" width="60" height="48" rx="8" fill="#FFFFFF" stroke="#3B82F6" strokeWidth="3" transform="rotate(10 110 130)" />
            <rect x="115" y="135" width="50" height="38" rx="5" fill="#38BDF8" transform="rotate(10 110 130)" />
            <circle cx="132" cy="148" r="5" fill="#FDE047" />
            <polygon points="122,172 138,155 156,172" fill="#2563EB" />
            {/* Hands holding photo */}
            <circle cx="106" cy="155" r="7" fill="url(#skin)" />
            <circle cx="168" cy="170" r="7" fill="url(#skin)" />
          </g>
        )}

        {variant === 'lightbulb' && (
          <g>
            {/* Lightbulb glowing above */}
            <circle cx="160" cy="80" r="14" fill="#FDE047" filter="drop-shadow(0 0 10px #FBBF24)" />
            <path d="M154 92 L166 92 L164 98 L156 98 Z" fill="#9CA3AF" />
            {/* Tablet in hand */}
            <rect x="74" y="160" width="52" height="42" rx="5" fill="url(#tabletGrad)" stroke="#50566A" strokeWidth="2" />
            <circle cx="72" cy="180" r="7" fill="url(#skin)" />
            <circle cx="128" cy="180" r="7" fill="url(#skin)" />
          </g>
        )}

        {variant === 'dataset' && (
          <g>
            {/* Stack of photo frames */}
            <rect x="120" y="145" width="54" height="42" rx="6" fill="#F3F4F6" stroke="#94A3B8" strokeWidth="2" transform="rotate(-8 120 145)" />
            <rect x="125" y="138" width="54" height="42" rx="6" fill="#FFFFFF" stroke="#3B82F6" strokeWidth="2.5" transform="rotate(6 125 138)" />
            <circle cx="140" cy="150" r="4" fill="#F59E0B" />
            {/* Hands */}
            <circle cx="120" cy="165" r="7" fill="url(#skin)" />
            <circle cx="178" cy="165" r="7" fill="url(#skin)" />
          </g>
        )}
      </svg>
    </div>
  );
}
