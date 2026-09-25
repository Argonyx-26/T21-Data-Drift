'use client';

import React, { useState, useEffect } from 'react';
import styles from './page.module.css';

export default function SettingsPage() {
  const [officerName, setOfficerName] = useState('Safety Officer');
  const [email, setEmail] = useState('officer@hazardlens.ai');
  const [siteLocation, setSiteLocation] = useState('Metro Construction Site - Sector 4');
  const [confThreshold, setConfThreshold] = useState(0.4);
  const [audioAlerts, setAudioAlerts] = useState(true);
  const [emailDigest, setEmailDigest] = useState(true);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    const userStr = localStorage.getItem('hazardlens_user');
    if (userStr) {
      try {
        const u = JSON.parse(userStr);
        if (u.name) setOfficerName(u.name);
        if (u.email) setEmail(u.email);
      } catch {}
    }
  }, []);

  const handleSave = () => {
    localStorage.setItem(
      'hazardlens_user',
      JSON.stringify({ name: officerName, email, role: 'admin' })
    );
    setSavedMsg('Settings updated successfully!');
    setTimeout(() => setSavedMsg(null), 3000);
  };

  return (
    <div className={styles.settingsWrapper}>
      <div className={styles.headerSection}>
        <div>
          <h1 className={styles.title}>9. Settings & Calibration</h1>
          <p className={styles.subtitle}>
            Configure YOLOv8 detection sensitivity, perimeter alerts, and officer profile.
          </p>
        </div>
      </div>

      {savedMsg && (
        <div
          style={{
            backgroundColor: '#ECFDF5',
            color: '#065F46',
            border: '1px solid #A7F3D0',
            padding: '10px 16px',
            borderRadius: '12px',
            fontSize: '0.85rem',
            fontWeight: 700,
          }}
        >
          ✓ {savedMsg}
        </div>
      )}

      {/* Model Parameters */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>YOLOv8 Detection Calibration</h2>

        <div className={styles.formGroup}>
          <label className={styles.label}>
            Confidence Threshold ({Math.round(confThreshold * 100)}%)
          </label>
          <div className={styles.sliderRow}>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              className={styles.rangeInput}
              value={confThreshold}
              onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
            />
            <span className={styles.sliderVal}>{confThreshold.toFixed(2)}</span>
          </div>
          <span style={{ fontSize: '0.74rem', color: '#6B7280' }}>
            Lower thresholds catch faint heads/vests but increase false positives; higher values ensure strict precision.
          </span>
        </div>

        <div className={styles.formGrid}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Model Weights</label>
            <input
              type="text"
              className={styles.input}
              value="best.pt (SafeZone YOLOv8n)"
              disabled
              style={{ opacity: 0.8 }}
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Bare-Head IOU Overlap</label>
            <input
              type="text"
              className={styles.input}
              value="0.20 (Standard)"
              disabled
              style={{ opacity: 0.8 }}
            />
          </div>
        </div>
      </div>

      {/* Alert Settings */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Alerts & Notifications</h2>

        <div className={styles.toggleRow}>
          <div className={styles.toggleText}>
            <span className={styles.toggleLabel}>Audible Zone Intrusion Warning</span>
            <span className={styles.toggleSub}>
              Trigger alarm when workers enter restricted equipment zones.
            </span>
          </div>
          <input
            type="checkbox"
            checked={audioAlerts}
            onChange={(e) => setAudioAlerts(e.target.checked)}
            style={{ width: '18px', height: '18px', accentColor: '#F5A623', cursor: 'pointer' }}
          />
        </div>

        <div className={styles.toggleRow}>
          <div className={styles.toggleText}>
            <span className={styles.toggleLabel}>Daily Safety Officer Email Digest</span>
            <span className={styles.toggleSub}>
              Send summary of violations and compliance metrics at 6:00 PM.
            </span>
          </div>
          <input
            type="checkbox"
            checked={emailDigest}
            onChange={(e) => setEmailDigest(e.target.checked)}
            style={{ width: '18px', height: '18px', accentColor: '#F5A623', cursor: 'pointer' }}
          />
        </div>
      </div>

      {/* Officer Profile */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Safety Officer Profile</h2>

        <div className={styles.formGrid}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Full Name</label>
            <input
              type="text"
              className={styles.input}
              value={officerName}
              onChange={(e) => setOfficerName(e.target.value)}
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Work Email</label>
            <input
              type="email"
              className={styles.input}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label}>Assigned Industrial Site</label>
          <input
            type="text"
            className={styles.input}
            value={siteLocation}
            onChange={(e) => setSiteLocation(e.target.value)}
          />
        </div>

        <button className={styles.saveBtn} onClick={handleSave}>
          Save Configuration
        </button>
      </div>
    </div>
  );
}
