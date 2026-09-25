'use client';

import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import styles from './page.module.css';
import StatCard from '@/components/StatCard';
import MascotIllustration from '@/components/MascotIllustration';

const TREND_DATA = [
  { date: 'Jan 1', noHelmet: 35, noVest: 15, zoneIntrusion: 10 },
  { date: 'Jan 7', noHelmet: 28, noVest: 12, zoneIntrusion: 8 },
  { date: 'Jan 14', noHelmet: 32, noVest: 14, zoneIntrusion: 6 },
  { date: 'Jan 21', noHelmet: 22, noVest: 9, zoneIntrusion: 5 },
  { date: 'Jan 28', noHelmet: 18, noVest: 7, zoneIntrusion: 4 },
];

const PIE_DATA = [
  { name: 'No Helmet', value: 141, color: '#EF4444' },
  { name: 'No Vest', value: 53, color: '#F5A623' },
  { name: 'Zone Intrusion', value: 34, color: '#3B82F6' },
];

export default function SafetyAnalyticsPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [totalImages, setTotalImages] = useState(1250);
  const [totalViolations, setTotalViolations] = useState(228);
  const [complianceRate, setComplianceRate] = useState(84);
  const [zoneCompliance, setZoneCompliance] = useState(91);

  useEffect(() => {
    setIsMounted(true);

    const fetchStats = async () => {
      try {
        const res = await fetch('/api/stats');
        if (res.ok) {
          const data = await res.json();
          setTotalImages(data.total_images || 1250);
          setTotalViolations(data.total_violations || 228);
          setComplianceRate(data.compliance_rate || 84);
          setZoneCompliance(91);
        }
      } catch (err) {}
    };

    fetchStats();
  }, []);

  return (
    <div className={styles.analyticsWrapper}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>7. Safety Analytics</h1>
          <p className={styles.subtitle}>
            Insights from dataset analysis results — monitoring trends and site compliance over time.
          </p>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#FFFFFF',
            border: '1px solid #ECE7D9',
            borderRadius: '12px',
            padding: '8px 14px',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: '#4B5563',
          }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          Jan 1, 2024 - Jan 31, 2024
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className={styles.statsGrid}>
        <StatCard
          title="Total Images"
          value={totalImages.toLocaleString()}
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
          }
          iconBg="#EFF6FF"
          iconColor="#2563EB"
        />

        <StatCard
          title="Total Violations"
          value={totalViolations.toLocaleString()}
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
            </svg>
          }
          iconBg="#FEF2F2"
          iconColor="#EF4444"
        />

        <StatCard
          title="Compliance Rate"
          value={`${complianceRate}%`}
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          }
          iconBg="#ECFDF5"
          iconColor="#10B981"
        />

        <StatCard
          title="Zone Compliance"
          value={`${zoneCompliance}%`}
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" />
            </svg>
          }
          iconBg="#ECFDF5"
          iconColor="#059669"
        />
      </div>

      {/* Charts Row */}
      <div className={styles.chartsRow}>
        {/* Trend Line Chart */}
        <div className={styles.whiteCard}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>Violations Trend</h2>
          </div>

          <div className={styles.chartContainer}>
            {isMounted && (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={TREND_DATA}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0ECE0" />
                  <XAxis dataKey="date" stroke="#9CA3AF" fontSize={11} />
                  <YAxis stroke="#9CA3AF" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '10px',
                      border: '1px solid #ECE7D9',
                      fontSize: '0.8rem',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="noHelmet"
                    name="No Helmet"
                    stroke="#EF4444"
                    strokeWidth={2.5}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="noVest"
                    name="No Vest"
                    stroke="#F5A623"
                    strokeWidth={2.5}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="zoneIntrusion"
                    name="Zone Intrusion"
                    stroke="#3B82F6"
                    strokeWidth={2.5}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Donut Distribution */}
        <div className={styles.whiteCard}>
          <div className={styles.cardHeader}>
            <h2 className={styles.cardTitle}>Violation Distribution</h2>
          </div>

          <div style={{ width: '100%', height: '170px', position: 'relative' }}>
            {isMounted && (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip />
                  <Pie
                    data={PIE_DATA}
                    innerRadius={50}
                    outerRadius={72}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {PIE_DATA.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            )}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
              }}
            >
              <span style={{ fontSize: '1.4rem', fontWeight: 900, color: '#181926' }}>
                {totalViolations}
              </span>
              <span style={{ fontSize: '0.68rem', fontWeight: 700, color: '#9CA3AF' }}>TOTAL</span>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '14px', marginTop: '10px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#EF4444' }}>● No Helmet 62%</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#F5A623' }}>● No Vest 23%</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#3B82F6' }}>● Zone 15%</span>
          </div>
        </div>

        {/* Mascot Lightbulb Card */}
        <div className={styles.mascotCard}>
          <MascotIllustration
            variant="lightbulb"
            height={220}
            speechText="Data Insights, Safer Sites!"
          />
          <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#181926', marginTop: '8px' }}>
            Predictive AI Safety
          </div>
          <p style={{ fontSize: '0.75rem', color: '#6B7280', marginTop: '3px' }}>
            Violation rates declined by 18% over the past 30 days.
          </p>
        </div>
      </div>
    </div>
  );
}
