'use client';

import React, { useEffect, useState } from 'react';

export default function ApiStatusBadge() {
  const [status, setStatus] = useState<'checking' | 'connected' | 'fallback'>('checking');
  const [modelReady, setModelReady] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setStatus('connected');
            setModelReady(!!data.model_loaded);
          }
          return;
        }
      } catch (err) {
        // Fallback
      }
      if (isMounted) {
        setStatus('fallback');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  if (status === 'checking') return null;

  const isConnected = status === 'connected';

  return (
    <div
      title={
        isConnected
          ? `Connected to FastAPI Backend. YOLOv8 Model: ${modelReady ? 'Loaded' : 'Ready'}`
          : 'Backend unreachable. Running with demo/fallback data.'
      }
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '0.72rem',
        fontWeight: 700,
        padding: '3px 10px',
        borderRadius: '9999px',
        backgroundColor: isConnected ? '#ECFDF5' : '#FFFBEB',
        color: isConnected ? '#065F46' : '#B45309',
        border: `1px solid ${isConnected ? '#A7F3D0' : '#FCD34D'}`,
      }}
    >
      <span
        style={{
          width: '7px',
          height: '7px',
          borderRadius: '50%',
          backgroundColor: isConnected ? '#10B981' : '#F59E0B',
          boxShadow: isConnected ? '0 0 6px #10B981' : 'none',
        }}
      />
      {isConnected ? 'API Connected (YOLOv8 Active)' : 'Demo Fallback Data'}
    </div>
  );
}
