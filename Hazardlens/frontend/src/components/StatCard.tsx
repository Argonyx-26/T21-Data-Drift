import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  trends?: { text: string; positive: boolean }[];
  accentBorder?: string;
}

export default function StatCard({
  title,
  value,
  icon,
  iconBg,
  iconColor,
  trends = [],
}: StatCardProps) {
  return (
    <div
      style={{
        backgroundColor: '#FFFFFF',
        borderRadius: '18px',
        padding: '1.25rem 1.4rem',
        border: '1px solid #ECE7D9',
        boxShadow: '0 4px 16px -2px rgba(24, 25, 38, 0.04)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.8rem',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = '0 8px 24px -4px rgba(24, 25, 38, 0.08)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = '0 4px 16px -2px rgba(24, 25, 38, 0.04)';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            backgroundColor: iconBg,
            color: iconColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {icon}
        </div>
        <div>
          <div
            style={{
              fontSize: '1.65rem',
              fontWeight: 800,
              fontFamily: 'var(--font-heading)',
              color: '#181926',
              lineHeight: 1.1,
            }}
          >
            {value}
          </div>
          <div
            style={{
              fontSize: '0.82rem',
              fontWeight: 600,
              color: '#717182',
              marginTop: '2px',
            }}
          >
            {title}
          </div>
        </div>
      </div>

      {trends.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '4px' }}>
          {trends.map((t, idx) => (
            <span
              key={idx}
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                color: t.positive ? '#10B981' : '#EF4444',
                backgroundColor: t.positive ? '#ECFDF5' : '#FEF2F2',
                padding: '2px 7px',
                borderRadius: '6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
              }}
            >
              {t.positive ? '▲' : '▼'} {t.text}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
