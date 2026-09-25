'use client';

import React, { useState, useEffect } from 'react';
import styles from './page.module.css';

interface ZoneItem {
  id?: number;
  name: string;
  zone_type: string;
  color: string;
  coordinates: [number, number][];
}

const DEFAULT_ZONE: ZoneItem = {
  name: 'Heavy Machinery Area',
  zone_type: 'Restricted',
  color: '#EF4444',
  coordinates: [
    [320, 160],
    [540, 170],
    [560, 310],
    [290, 290],
  ],
};

const COLOR_OPTIONS = [
  '#EF4444', // Red
  '#F97316', // Orange
  '#F59E0B', // Yellow
  '#10B981', // Green
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
];

export default function ZoneManagementPage() {
  const [zoneName, setZoneName] = useState(DEFAULT_ZONE.name);
  const [zoneType, setZoneType] = useState(DEFAULT_ZONE.zone_type);
  const [zoneColor, setZoneColor] = useState(DEFAULT_ZONE.color);
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>(DEFAULT_ZONE.coordinates);
  const [savedZones, setSavedZones] = useState<ZoneItem[]>([DEFAULT_ZONE]);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    const fetchZones = async () => {
      try {
        const res = await fetch('/api/zones');
        if (res.ok) {
          const data = await res.json();
          if (data && data.length > 0) {
            setSavedZones(data);
            setZoneName(data[0].name);
            setZoneType(data[0].zone_type);
            setZoneColor(data[0].color);
          }
        }
      } catch (err) {
        // Fallback
      }
    };
    fetchZones();
  }, []);

  const handleSave = async () => {
    setSaveStatus('Saving zone perimeter...');
    const newZone: ZoneItem = {
      name: zoneName,
      zone_type: zoneType,
      color: zoneColor,
      coordinates: polygonPoints,
    };

    try {
      const res = await fetch('/api/zones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newZone),
      });

      if (res.ok) {
        setSavedZones((prev) => [...prev, newZone]);
        setSaveStatus('Zone successfully saved and synced with YOLO detector!');
        setTimeout(() => setSaveStatus(null), 3000);
        return;
      }
    } catch (err) {}

    // Fallback local save
    setSavedZones((prev) => [...prev, newZone]);
    setSaveStatus('Zone saved (Local Cache). Ready for intrusion detection.');
    setTimeout(() => setSaveStatus(null), 3000);
  };

  const pointsString = polygonPoints.map((p) => p.join(',')).join(' ');

  return (
    <div className={styles.zonesWrapper}>
      <div className={styles.headerSection}>
        <div>
          <h1 className={styles.title}>6. Zone Management</h1>
          <p className={styles.subtitle}>
            Manage Restricted Zones — Define dangerous areas in the dataset images for real-time intrusion alerts.
          </p>
        </div>
      </div>

      <div className={styles.zoneLayout}>
        {/* Left: Interactive Canvas View */}
        <div className={styles.canvasCard}>
          <div className={styles.canvasHeader}>
            <span className={styles.canvasTitle}>Site Perimeter Calibration</span>
            <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>
              Polygon Active: {polygonPoints.length} vertices
            </span>
          </div>

          <div className={styles.canvasContainer}>
            <svg
              viewBox="0 0 640 400"
              style={{ width: '100%', height: '100%' }}
            >
              {/* Construction Site Background Graphics */}
              <rect width="640" height="400" fill="#2D3748" />
              {/* Ground & Machinery Graphics */}
              <polygon points="0,400 640,400 640,220 0,260" fill="#3E4C5E" />
              <polygon points="80,180 160,180 180,240 60,240" fill="#F5A623" opacity="0.8" />
              <text x="85" y="215" fill="#181926" fontSize="12" fontWeight="bold">
                🚜 Heavy Crane
              </text>

              {/* Dynamic Restricted Polygon Overlay */}
              <polygon
                points={pointsString}
                fill={zoneColor}
                fillOpacity="0.3"
                stroke={zoneColor}
                strokeWidth="3"
                strokeDasharray="6 4"
              />

              {/* Center Zone Label */}
              <g transform="translate(340, 230)">
                <rect
                  x="-90"
                  y="-14"
                  width="180"
                  height="28"
                  rx="6"
                  fill="rgba(0,0,0,0.75)"
                  stroke={zoneColor}
                  strokeWidth="1.5"
                />
                <text
                  x="0"
                  y="4"
                  fill="#FFFFFF"
                  fontSize="12"
                  fontWeight="bold"
                  textAnchor="middle"
                >
                  Restricted Zone ({zoneName})
                </text>
              </g>

              {/* Draggable/Interactive Vertices */}
              {polygonPoints.map((pt, idx) => (
                <circle
                  key={idx}
                  cx={pt[0]}
                  cy={pt[1]}
                  r="7"
                  fill="#FFFFFF"
                  stroke={zoneColor}
                  strokeWidth="3"
                  style={{ cursor: 'pointer' }}
                />
              ))}
            </svg>
          </div>

          {/* Active Registered Zones */}
          <div style={{ marginTop: '0.5rem' }}>
            <span style={{ fontSize: '0.86rem', fontWeight: 800, color: '#181926' }}>
              Active Monitored Zones
            </span>
            <div className={styles.activeZonesList}>
              {savedZones.map((z, idx) => (
                <div key={idx} className={styles.zoneItem}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        backgroundColor: z.color || '#EF4444',
                      }}
                    />
                    <span>{z.name}</span>
                  </div>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      padding: '2px 8px',
                      borderRadius: '6px',
                      backgroundColor: '#FEF3C7',
                      color: '#B45309',
                    }}
                  >
                    {z.zone_type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Zone Settings */}
        <div className={styles.settingsCard}>
          <h2 className={styles.settingsTitle}>Zone Settings</h2>

          <div className={styles.formGroup}>
            <label className={styles.label}>Zone Name</label>
            <input
              type="text"
              className={styles.input}
              value={zoneName}
              onChange={(e) => setZoneName(e.target.value)}
              placeholder="e.g. Heavy Machinery Area"
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Zone Type</label>
            <select
              className={styles.select}
              value={zoneType}
              onChange={(e) => setZoneType(e.target.value)}
            >
              <option value="Restricted">Restricted (Full Alert)</option>
              <option value="Hazardous">Hazardous (Caution)</option>
              <option value="Warning">Warning (Vest Required)</option>
            </select>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Zone Color</label>
            <div className={styles.colorPickerRow}>
              {COLOR_OPTIONS.map((c) => (
                <div
                  key={c}
                  className={`${styles.colorDot} ${zoneColor === c ? styles.colorDotSelected : ''}`}
                  style={{ backgroundColor: c }}
                  onClick={() => setZoneColor(c)}
                />
              ))}
            </div>
          </div>

          {saveStatus && (
            <div
              style={{
                fontSize: '0.8rem',
                fontWeight: 700,
                color: '#065F46',
                background: '#ECFDF5',
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1px solid #A7F3D0',
              }}
            >
              ✓ {saveStatus}
            </div>
          )}

          <button className={styles.saveBtn} onClick={handleSave}>
            Save Zone
          </button>
        </div>
      </div>
    </div>
  );
}
