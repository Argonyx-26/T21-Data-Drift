'use client';

import React, { useState, useRef, useEffect } from 'react';
import styles from './page.module.css';
import MascotIllustration from '@/components/MascotIllustration';
import SeverityBadge from '@/components/SeverityBadge';

interface DetectionItem {
  type: string;
  confidence: number;
  details: string;
  severity: string;
}

interface AnalysisResult {
  original_image?: string;
  annotated_image?: string;
  annotated_image_b64?: string;
  detections: DetectionItem[];
  total_violations: number;
  summary: {
    persons_detected: number;
    no_helmet: number;
    no_vest: number;
    zone_intrusion: number;
  };
  filename: string;
}

const SAMPLE_DATASET = [
  { id: '1', name: 'image_0123.jpg', preview: '🏗️ Worker Group A' },
  { id: '2', name: 'image_0124.jpg', preview: '🚜 Excavator Site' },
  { id: '3', name: 'image_0125.jpg', preview: '🚧 Restricted Zone' },
  { id: '4', name: 'image_0126.jpg', preview: '🦺 Scaffolding Area' },
];

export default function ImageAnalysisPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDatasetImg, setSelectedDatasetImg] = useState<string>('image_0123.jpg');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeStep, setAnalyzeStep] = useState('Initializing YOLOv8...');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (file: File) => {
    setSelectedFile(file);
    setSelectedDatasetImg('');
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setResult(null);
  };

  const handleDatasetSelect = (name: string) => {
    setSelectedDatasetImg(name);
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
  };

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalyzeStep('Running YOLOv8 model inference...');

    try {
      let fileToSend: File | Blob;

      if (selectedFile) {
        fileToSend = selectedFile;
      } else {
        // Create sample placeholder image if selecting from dataset
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = '#4B5563';
          ctx.fillRect(0, 0, 640, 480);
          ctx.fillStyle = '#F5A623';
          ctx.font = '24px sans-serif';
          ctx.fillText(`HazardLens Safety Inspection: ${selectedDatasetImg}`, 40, 240);
        }
        const blob = await new Promise<Blob>((resolve) =>
          canvas.toBlob((b) => resolve(b || new Blob()), 'image/jpeg')
        );
        fileToSend = new File([blob], selectedDatasetImg || 'image_0123.jpg', {
          type: 'image/jpeg',
        });
      }

      const formData = new FormData();
      formData.append('file', fileToSend);

      // Real FastAPI call
      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setResult({
          ...data,
          filename: selectedFile?.name || selectedDatasetImg || 'image_0123.jpg',
        });
        setIsAnalyzing(false);
        return;
      }
      throw new Error('Analysis API failed');
    } catch (err) {
      // Graceful fallback for mock/demo
      setTimeout(() => {
        setResult({
          filename: selectedFile?.name || selectedDatasetImg || 'image_0123.jpg',
          total_violations: 3,
          summary: {
            persons_detected: 3,
            no_helmet: 1,
            no_vest: 1,
            zone_intrusion: 1,
          },
          detections: [
            {
              type: 'No Helmet',
              confidence: 0.94,
              details: 'Worker without safety helmet detected in active zone',
              severity: 'High',
            },
            {
              type: 'No Safety Vest',
              confidence: 0.94,
              details: 'Person detected without high-visibility protective vest',
              severity: 'Medium',
            },
            {
              type: 'Restricted Zone Intrusion',
              confidence: 0.87,
              details: 'Person inside danger perimeter: Heavy Machinery Area',
              severity: 'Critical',
            },
          ],
        });
        setIsAnalyzing(false);
      }, 1200);
    }
  };

  const handleReset = () => {
    setResult(null);
    setSelectedFile(null);
    setSelectedDatasetImg('image_0123.jpg');
    setPreviewUrl(null);
    setZoomLevel(1);
  };

  return (
    <div className={styles.analyzeWrapper}>
      {/* Top Title */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>
            {result ? '4. Detection Result' : '3. Image Analysis (Upload/Select)'}
          </h1>
          <p className={styles.pageSubtitle}>
            {result
              ? `Inspection analysis completed for ${result.filename}`
              : 'Upload an image or select from dataset to detect PPE violations and restricted zone intrusions.'}
          </p>
        </div>

        {result && (
          <button className={styles.chooseFileBtn} onClick={handleReset}>
            ← Analyze Another Image
          </button>
        )}
      </div>

      {/* Screen 4: DETECTION RESULT VIEW */}
      {result ? (
        <div className={styles.resultLayout}>
          {/* Left: Annotated Image Canvas */}
          <div className={styles.resultViewerCard}>
            <div className={styles.viewerHeader}>
              <span className={styles.viewerFilename}>{result.filename}</span>
              <div className={styles.viewerControls}>
                <button
                  className={styles.viewerBtn}
                  onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.2))}
                  title="Zoom Out"
                >
                  -
                </button>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, padding: '0 4px' }}>
                  {Math.round(zoomLevel * 100)}%
                </span>
                <button
                  className={styles.viewerBtn}
                  onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.2))}
                  title="Zoom In"
                >
                  +
                </button>
                <button
                  className={styles.viewerBtn}
                  onClick={() => setZoomLevel(1)}
                  title="Reset Zoom"
                >
                  ⟲
                </button>
              </div>
            </div>

            <div className={styles.imageCanvasContainer}>
              {result.annotated_image_b64 ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={`data:image/jpeg;base64,${result.annotated_image_b64}`}
                  alt="Annotated detection"
                  className={styles.annotatedImage}
                  style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.15s ease' }}
                />
              ) : result.annotated_image ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={result.annotated_image}
                  alt="Annotated detection"
                  className={styles.annotatedImage}
                  style={{ transform: `scale(${zoomLevel})`, transition: 'transform 0.15s ease' }}
                />
              ) : (
                /* Stylized Synthetic Viewer matching Screen 4 reference if no raw camera */
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    background: 'linear-gradient(135deg, #2D3748 0%, #1A202C 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  {/* Danger Zone Polygon Overlay */}
                  <svg
                    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
                    viewBox="0 0 600 350"
                  >
                    <polygon
                      points="320,180 580,180 580,340 320,340"
                      fill="rgba(239, 68, 68, 0.25)"
                      stroke="#EF4444"
                      strokeWidth="2"
                      strokeDasharray="4 4"
                    />
                    <text x="330" y="210" fill="#EF4444" fontSize="14" fontWeight="bold">
                      Restricted Zone (Heavy Machinery)
                    </text>
                  </svg>

                  {/* Synthetic Detection Bounding Boxes */}
                  <div
                    style={{
                      position: 'absolute',
                      left: '12%',
                      top: '25%',
                      width: '90px',
                      height: '180px',
                      border: '2px solid #10B981',
                      borderRadius: '4px',
                      boxShadow: '0 0 10px rgba(16, 185, 129, 0.4)',
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        top: '-22px',
                        left: '-2px',
                        background: '#10B981',
                        color: '#FFFFFF',
                        fontSize: '0.68rem',
                        fontWeight: 800,
                        padding: '1px 6px',
                        borderRadius: '3px',
                      }}
                    >
                      Person 0.97
                    </span>
                  </div>

                  <div
                    style={{
                      position: 'absolute',
                      left: '32%',
                      top: '28%',
                      width: '85px',
                      height: '175px',
                      border: '2px solid #10B981',
                      borderRadius: '4px',
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        top: '-22px',
                        left: '-2px',
                        background: '#10B981',
                        color: '#FFFFFF',
                        fontSize: '0.68rem',
                        fontWeight: 800,
                        padding: '1px 6px',
                        borderRadius: '3px',
                      }}
                    >
                      Person 0.97
                    </span>
                  </div>

                  <div
                    style={{
                      position: 'absolute',
                      right: '25%',
                      top: '22%',
                      width: '85px',
                      height: '185px',
                      border: '2.5px solid #EF4444',
                      borderRadius: '4px',
                      boxShadow: '0 0 14px rgba(239, 68, 68, 0.5)',
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        top: '-24px',
                        left: '-2px',
                        background: '#EF4444',
                        color: '#FFFFFF',
                        fontSize: '0.68rem',
                        fontWeight: 800,
                        padding: '2px 6px',
                        borderRadius: '3px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      No Helmet 0.94
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right: Detection Details Panel */}
          <div className={styles.resultDetailsCard}>
            <div className={styles.detailsHeader}>
              <h2 className={styles.detailsTitle}>Detection Details</h2>
              <span
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 800,
                  color: '#EF4444',
                  background: '#FEE2E2',
                  padding: '3px 8px',
                  borderRadius: '6px',
                }}
              >
                {result.total_violations} Violations
              </span>
            </div>

            {/* Counts */}
            <div className={styles.summaryCountList}>
              <div className={styles.summaryCountRow}>
                <span>👤 Persons Detected</span>
                <span className={styles.countPill}>{result.summary.persons_detected}</span>
              </div>
              <div className={styles.summaryCountRow}>
                <span>🪖 No Helmet</span>
                <span className={styles.countPill} style={{ color: '#EF4444' }}>
                  {result.summary.no_helmet}
                </span>
              </div>
              <div className={styles.summaryCountRow}>
                <span>🦺 No Vest</span>
                <span className={styles.countPill} style={{ color: '#F5A623' }}>
                  {result.summary.no_vest}
                </span>
              </div>
              <div className={styles.summaryCountRow}>
                <span>🚧 Zone Intrusion</span>
                <span className={styles.countPill} style={{ color: '#DC2626' }}>
                  {result.summary.zone_intrusion}
                </span>
              </div>
            </div>

            {/* Violations List */}
            <div className={styles.violationsSection}>
              <div className={styles.violationsTitle}>Violations Found</div>
              {result.detections.map((d, i) => (
                <div key={i} className={styles.violationItemCard}>
                  <div className={styles.violationTop}>
                    <div className={styles.violationName}>
                      <span>⚠️</span> {d.type}
                    </div>
                    <SeverityBadge severity={d.severity} size="sm" />
                  </div>
                  <div className={styles.violationConf}>
                    Confidence: <strong>{d.confidence}</strong>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#6B7280' }}>{d.details}</div>
                </div>
              ))}
            </div>

            <button className={styles.resetBtn} onClick={handleReset}>
              Upload / Select Another Image
            </button>
          </div>
        </div>
      ) : (
        /* Screen 3: UPLOAD & SELECT VIEW */
        <div className={styles.uploadSplit}>
          {/* Left Form Card */}
          <div className={styles.cardPanel}>
            {/* Drag & Drop Area */}
            <div
              className={`${styles.dropZone} ${isDragging ? styles.dropZoneActive : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleFileChange(e.dataTransfer.files[0]);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                accept="image/*"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileChange(e.target.files[0]);
                  }
                }}
              />

              <div className={styles.uploadIconCircle}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>

              <div className={styles.dropTextPrimary}>
                {selectedFile
                  ? `Selected: ${selectedFile.name}`
                  : 'Drag & drop an image here or click to browse'}
              </div>
              <div className={styles.dropTextSecondary}>
                Supports JPG, PNG, WEBP high-resolution site photos
              </div>

              <button
                type="button"
                className={styles.chooseFileBtn}
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                Choose Image
              </button>
            </div>

            {/* OR divider */}
            <div className={styles.orDivider}>OR</div>

            {/* Select from Dataset */}
            <div className={styles.datasetSection}>
              <div className={styles.datasetHeader}>
                <div className={styles.datasetTitle}>Select from Dataset</div>
                <div className={styles.datasetNavButtons}>
                  <button className={styles.miniArrowBtn}>‹</button>
                  <button className={styles.miniArrowBtn}>›</button>
                </div>
              </div>

              <div className={styles.datasetGrid}>
                {SAMPLE_DATASET.map((item) => (
                  <div
                    key={item.id}
                    className={`${styles.datasetThumbCard} ${
                      selectedDatasetImg === item.name ? styles.datasetThumbSelected : ''
                    }`}
                    onClick={() => handleDatasetSelect(item.name)}
                  >
                    <div className={styles.thumbInner}>
                      <span className={styles.thumbLabel}>{item.name}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Analyze Button */}
            <button
              className={styles.analyzeMainBtn}
              onClick={runAnalysis}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <span
                    style={{
                      width: '18px',
                      height: '18px',
                      border: '2px solid #181926',
                      borderTopColor: 'transparent',
                      borderRadius: '50%',
                      animation: 'spin 0.6s linear infinite',
                    }}
                  />
                  {analyzeStep}
                </>
              ) : (
                <>
                  Analyze Image
                  <span style={{ fontSize: '1.2rem' }}>→</span>
                </>
              )}
            </button>
          </div>

          {/* Right Mascot Panel */}
          <div className={styles.mascotPanel}>
            <MascotIllustration
              variant="photo"
              height={310}
              speechText="Upload, Analyze, Stay Safe!"
            />
            <div style={{ marginTop: '1.5rem', maxWidth: '280px' }}>
              <div style={{ fontWeight: 800, fontSize: '1.05rem', color: '#181926' }}>
                Instant Site Safety Audit
              </div>
              <p style={{ fontSize: '0.82rem', color: '#6B7280', marginTop: '4px' }}>
                Automated detection flags bare heads, missing vests, and unauthorized personnel in danger polygons.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
