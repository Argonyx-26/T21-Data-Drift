'use client';

import React, { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff } from 'lucide-react';
import styles from './page.module.css';
import HazardLensLogo from '@/components/HazardLensLogo';
import MascotIllustration from '@/components/MascotIllustration';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('officer@hazardlens.ai');
  const [password, setPassword] = useState('safetyfirst123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Forgot Password Modal State
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);

  // Sign Up Modal State
  const [showSignUpModal, setShowSignUpModal] = useState(false);
  const [signUpName, setSignUpName] = useState('');
  const [signUpEmail, setSignUpEmail] = useState('');
  const [signUpPassword, setSignUpPassword] = useState('');
  const [signUpConfirm, setSignUpConfirm] = useState('');
  const [signUpError, setSignUpError] = useState('');
  const [signUpSuccess, setSignUpSuccess] = useState(false);
  const [signUpLoading, setSignUpLoading] = useState(false);

  const submitLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('hazardlens_token', data.token);
        localStorage.setItem('hazardlens_user', JSON.stringify(data.user));
        router.push('/dashboard');
        return;
      }

      const errData = await res.json().catch(() => null);
      throw new Error(errData?.detail || 'Invalid email or password.');
    } catch (err: any) {
      if (err.message && !err.message.includes('fetch')) {
        setError(err.message);
      } else {
        // Fallback for demo when backend is offline
        localStorage.setItem('hazardlens_token', 'demo-token-fallback');
        localStorage.setItem(
          'hazardlens_user',
          JSON.stringify({
            name: 'Safety Officer',
            email,
            role: 'admin',
          })
        );
        router.push('/dashboard');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleForgotSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!forgotEmail) return;
    setForgotLoading(true);
    setTimeout(() => {
      setForgotLoading(false);
      setForgotSent(true);
    }, 600);
  };

  const handleSignUpSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSignUpError('');

    if (!signUpName || !signUpEmail || !signUpPassword) {
      setSignUpError('Please complete all required fields.');
      return;
    }

    if (signUpPassword.length < 6) {
      setSignUpError('Password must be at least 6 characters long.');
      return;
    }

    if (signUpPassword !== signUpConfirm) {
      setSignUpError('Passwords do not match. Please verify.');
      return;
    }

    setSignUpLoading(true);
    setTimeout(() => {
      setSignUpLoading(false);
      setSignUpSuccess(true);
    }, 700);
  };

  return (
    <div className={styles.loginWrapper}>
      <div className={styles.bgCranes} />

      <div className={styles.loginCard}>
        {/* Left Section: Form & Branding */}
        <div className={styles.leftSection}>
          <div className={styles.logoRow}>
            <HazardLensLogo size="md" theme="light" />
          </div>

          <h1 className={styles.heroTitle}>
            Safer Workplaces
            <span className={styles.yellowHighlight}>Brighter Tomorrows</span>
          </h1>

          <p className={styles.heroSubtitle}>
            AI-powered safety monitoring for construction and industrial sites.
          </p>

          {error && <div className={styles.errorBanner}>{error}</div>}

          <form className={styles.formBox} onSubmit={submitLogin}>
            <div className={styles.inputGroup}>
              <span className={styles.inputIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </span>
              <input
                type="email"
                className={styles.inputField}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className={styles.inputGroup}>
              <span className={styles.inputIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </span>
              <input
                type={showPassword ? 'text' : 'password'}
                className={styles.inputField}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className={styles.eyeToggleBtn}
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            <div className={styles.rowBetween}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  style={{ accentColor: '#F5A623', width: '15px', height: '15px' }}
                />
                Remember me
              </label>
              <button
                type="button"
                className={styles.forgotLink}
                onClick={() => {
                  setForgotEmail(email);
                  setForgotSent(false);
                  setShowForgotModal(true);
                }}
              >
                Forgot password?
              </button>
            </div>

            <button type="submit" className={styles.loginBtn} disabled={loading}>
              {loading ? 'Logging in...' : 'Login →'}
            </button>
          </form>

          <div className={styles.signupText}>
            Don&apos;t have an account?
            <button
              type="button"
              className={styles.signupLink}
              onClick={() => {
                setSignUpError('');
                setSignUpSuccess(false);
                setShowSignUpModal(true);
              }}
            >
              Sign up
            </button>
          </div>
        </div>

        {/* Right Section: Mascot & Improved AI Value Card */}
        <div className={styles.rightSection}>
          <div className={styles.mascotGlow} />

          <MascotIllustration
            variant="tablet"
            height={260}
            speechText="Site safety inspection active!"
          />

          {/* Improved Product Value Card */}
          <div className={styles.aiFeatureCard}>
            <div className={styles.aiCardHeader}>
              <div>
                <div className={styles.aiCardTitle}>HazardLens</div>
                <div style={{ fontSize: '0.72rem', color: '#6B7280' }}>
                  AI-Powered Workplace Safety Monitoring
                </div>
              </div>
              <span className={styles.aiPill}>Real-Time</span>
            </div>

            <div className={styles.aiFeatureList}>
              <div className={styles.aiFeatureItem}>
                <span className={styles.aiBulletIcon}>🪖</span>
                <span>Automated PPE Detection (Head, Helmet, Vest)</span>
              </div>
              <div className={styles.aiFeatureItem}>
                <span className={styles.aiBulletIcon}>🚧</span>
                <span>Restricted-Zone Perimeter Intrusion Alerts</span>
              </div>
              <div className={styles.aiFeatureItem}>
                <span className={styles.aiBulletIcon}>⚡</span>
                <span>Real-Time Safety Analysis & Event Logging</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div
          className={styles.modalBackdrop}
          onClick={() => setShowForgotModal(false)}
        >
          <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div>
                <h3 className={styles.modalTitle}>Reset Password</h3>
                <p className={styles.modalSubtitle}>
                  Enter your email address to receive password recovery instructions.
                </p>
              </div>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowForgotModal(false)}
              >
                ✕
              </button>
            </div>

            {forgotSent ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className={styles.successBox}>
                  If an account exists for <strong>{forgotEmail}</strong>, a password reset link has been sent.
                </div>
                <button
                  type="button"
                  className={styles.loginBtn}
                  onClick={() => setShowForgotModal(false)}
                >
                  Back to Login
                </button>
              </div>
            ) : (
              <form onSubmit={handleForgotSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className={styles.inputGroup}>
                  <span className={styles.inputIcon}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                  </span>
                  <input
                    type="email"
                    className={styles.inputField}
                    placeholder="you@example.com"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className={styles.loginBtn}
                  disabled={forgotLoading}
                >
                  {forgotLoading ? 'Sending...' : 'Send Reset Link'}
                </button>

                <button
                  type="button"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#6B7280',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    marginTop: '4px',
                  }}
                  onClick={() => setShowForgotModal(false)}
                >
                  Back to Login
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Sign Up Modal */}
      {showSignUpModal && (
        <div
          className={styles.modalBackdrop}
          onClick={() => setShowSignUpModal(false)}
        >
          <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div>
                <h3 className={styles.modalTitle}>Create Account</h3>
                <p className={styles.modalSubtitle}>
                  Register as an authorized Safety Officer or Site Manager.
                </p>
              </div>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={() => setShowSignUpModal(false)}
              >
                ✕
              </button>
            </div>

            {signUpSuccess ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className={styles.successBox}>
                  Account created successfully! You can now log in with your credentials.
                </div>
                <button
                  type="button"
                  className={styles.loginBtn}
                  onClick={() => {
                    setShowSignUpModal(false);
                    setEmail(signUpEmail);
                  }}
                >
                  Proceed to Login
                </button>
              </div>
            ) : (
              <form onSubmit={handleSignUpSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                {signUpError && <div className={styles.errorBanner}>{signUpError}</div>}

                <div className={styles.inputGroup}>
                  <input
                    type="text"
                    className={styles.inputField}
                    style={{ paddingLeft: '14px' }}
                    placeholder="Full Name (e.g. Safety Officer)"
                    value={signUpName}
                    onChange={(e) => setSignUpName(e.target.value)}
                    required
                  />
                </div>

                <div className={styles.inputGroup}>
                  <input
                    type="email"
                    className={styles.inputField}
                    style={{ paddingLeft: '14px' }}
                    placeholder="Work Email"
                    value={signUpEmail}
                    onChange={(e) => setSignUpEmail(e.target.value)}
                    required
                  />
                </div>

                <div className={styles.inputGroup}>
                  <input
                    type="password"
                    className={styles.inputField}
                    style={{ paddingLeft: '14px' }}
                    placeholder="Password (min 6 characters)"
                    value={signUpPassword}
                    onChange={(e) => setSignUpPassword(e.target.value)}
                    required
                  />
                </div>

                <div className={styles.inputGroup}>
                  <input
                    type="password"
                    className={styles.inputField}
                    style={{ paddingLeft: '14px' }}
                    placeholder="Confirm Password"
                    value={signUpConfirm}
                    onChange={(e) => setSignUpConfirm(e.target.value)}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className={styles.loginBtn}
                  disabled={signUpLoading}
                >
                  {signUpLoading ? 'Registering...' : 'Register Account'}
                </button>

                <button
                  type="button"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#6B7280',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    marginTop: '4px',
                  }}
                  onClick={() => setShowSignUpModal(false)}
                >
                  Already have an account? Sign In
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
