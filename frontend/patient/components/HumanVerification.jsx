import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Phone,
  Info,
  Lock,
  Loader2
} from 'lucide-react';

export default function HumanVerification({ 
  verificationStatus = 'unverified', // 'unverified' | 'loading' | 'verified' | 'failed' | 'expired'
  onStatusChange,
  errorMessage = null 
}) {
  const turnstileContainerRef = useRef(null);
  const widgetIdRef = useRef(null);

  // Cloudflare Turnstile Site Key from environment (public only - NEVER secret key)
  const turnstileSiteKey = import.meta.env?.VITE_TURNSTILE_SITE_KEY;
  const isProductionKeyConfigured = Boolean(turnstileSiteKey && turnstileSiteKey.trim() !== '');

  // Setup Turnstile if real site key is provided
  useEffect(() => {
    if (!isProductionKeyConfigured) return;

    let isMounted = true;

    const renderWidget = () => {
      if (window.turnstile && turnstileContainerRef.current && isMounted) {
        try {
          if (widgetIdRef.current) {
            window.turnstile.remove(widgetIdRef.current);
          }
          widgetIdRef.current = window.turnstile.render(turnstileContainerRef.current, {
            sitekey: turnstileSiteKey,
            theme: 'light',
            callback: (token) => {
              if (isMounted) {
                onStatusChange('verified', token);
              }
            },
            'error-callback': () => {
              if (isMounted) {
                onStatusChange('failed', null);
              }
            },
            'expired-callback': () => {
              if (isMounted) {
                onStatusChange('expired', null);
              }
            }
          });
        } catch (e) {
          console.warn('Turnstile render warning:', e);
        }
      }
    };

    if (window.turnstile) {
      renderWidget();
    } else {
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.onload = renderWidget;
      document.head.appendChild(script);
    }

    return () => {
      isMounted = false;
      if (window.turnstile && widgetIdRef.current) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch (e) {
          // ignore cleanup error
        }
      }
    };
  }, [isProductionKeyConfigured, turnstileSiteKey]);

  // Development simulation handlers (when real Cloudflare keys are not configured)
  const handleSimulateVerification = () => {
    onStatusChange('loading');
    setTimeout(() => {
      const mockToken = `dev-turnstile-token-${Date.now()}`;
      onStatusChange('verified', mockToken);
    }, 700);
  };

  const handleSimulateFailure = () => {
    onStatusChange('loading');
    setTimeout(() => {
      onStatusChange('failed', null);
    }, 500);
  };

  const handleSimulateExpired = () => {
    onStatusChange('expired', null);
  };

  const handleReset = () => {
    onStatusChange('unverified', null);
  };

  return (
    <div className="human-verification-card" aria-labelledby="verification-heading">
      {/* Title & Badge */}
      <div className="verification-header-row">
        <div className="verification-title-box">
          <Lock size={18} className="verification-lock-icon" aria-hidden="true" />
          <h4 id="verification-heading" className="verification-main-title">
            Human Verification
          </h4>
        </div>

        <span className={`verification-status-pill pill-${verificationStatus}`}>
          {verificationStatus === 'verified' && (
            <>
              <CheckCircle2 size={13} aria-hidden="true" />
              <span>Verified</span>
            </>
          )}
          {verificationStatus === 'loading' && (
            <>
              <Loader2 size={13} className="spinner-icon" aria-hidden="true" />
              <span>Verifying...</span>
            </>
          )}
          {verificationStatus === 'unverified' && (
            <>
              <Clock size={13} aria-hidden="true" />
              <span>Pending</span>
            </>
          )}
          {verificationStatus === 'failed' && (
            <>
              <ShieldAlert size={13} aria-hidden="true" />
              <span>Failed</span>
            </>
          )}
          {verificationStatus === 'expired' && (
            <>
              <AlertTriangle size={13} aria-hidden="true" />
              <span>Expired</span>
            </>
          )}
        </span>
      </div>

      {/* Production Turnstile Render Target */}
      {isProductionKeyConfigured ? (
        <div className="turnstile-live-container">
          <div ref={turnstileContainerRef} />
        </div>
      ) : (
        /* Development Simulation Sandbox */
        <div className="turnstile-dev-sandbox">
          <div className="sandbox-info-banner">
            <Info size={15} aria-hidden="true" />
            <div className="sandbox-banner-text">
              <strong>Development Environment:</strong> Cloudflare Turnstile site key not configured in <code>.env</code>. Using development bot-check simulator.
            </div>
          </div>

          {/* Interactive Simulation Area */}
          <div className="sandbox-interaction-box">
            {verificationStatus === 'unverified' && (
              <div className="sandbox-action-row">
                <button
                  type="button"
                  onClick={handleSimulateVerification}
                  className="btn-simulate-verify"
                  aria-label="Verify as human (Dev simulator)"
                >
                  <ShieldCheck size={18} aria-hidden="true" />
                  <span>Verify as Human (Dev Simulator)</span>
                </button>
              </div>
            )}

            {verificationStatus === 'loading' && (
              <div className="sandbox-loading-state">
                <Loader2 size={20} className="spinner-icon" color="#0284c7" aria-hidden="true" />
                <span>Simulating browser integrity verification...</span>
              </div>
            )}

            {verificationStatus === 'verified' && (
              <div className="sandbox-verified-state">
                <div className="verified-badge-row">
                  <CheckCircle2 size={18} color="#059669" aria-hidden="true" />
                  <strong>Development Check Passed</strong>
                  <span className="token-tag">Token Generated</span>
                </div>
                <button
                  type="button"
                  onClick={handleReset}
                  className="btn-sandbox-reset"
                  title="Reset verification state"
                >
                  <RefreshCw size={12} aria-hidden="true" />
                  <span>Reset</span>
                </button>
              </div>
            )}

            {verificationStatus === 'failed' && (
              <div className="sandbox-failed-state">
                <div className="failed-badge-row">
                  <ShieldAlert size={18} color="#dc2626" aria-hidden="true" />
                  <span>Verification rejected. Please retry check.</span>
                </div>
                <button
                  type="button"
                  onClick={handleSimulateVerification}
                  className="btn-simulate-retry"
                >
                  Retry Verification
                </button>
              </div>
            )}

            {verificationStatus === 'expired' && (
              <div className="sandbox-expired-state">
                <div className="expired-badge-row">
                  <AlertTriangle size={18} color="#d97706" aria-hidden="true" />
                  <span>Verification expired. Please re-verify.</span>
                </div>
                <button
                  type="button"
                  onClick={handleSimulateVerification}
                  className="btn-simulate-retry"
                >
                  Re-verify
                </button>
              </div>
            )}
          </div>

          {/* Development Testing State Switches */}
          <div className="sandbox-testing-switches">
            <span className="switches-label">Test Simulation States:</span>
            <div className="switches-buttons-group">
              <button 
                type="button" 
                onClick={handleSimulateVerification} 
                className="btn-mini-switch"
              >
                Pass
              </button>
              <button 
                type="button" 
                onClick={handleSimulateFailure} 
                className="btn-mini-switch"
              >
                Fail
              </button>
              <button 
                type="button" 
                onClick={handleSimulateExpired} 
                className="btn-mini-switch"
              >
                Expire
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Validation Error Banner (if user attempted submit before verifying) */}
      {errorMessage && (
        <div className="verification-error-alert" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Direct 112 Bypass Note (Ensures safety is NEVER blocked) */}
      <div className="verification-safety-bypass">
        <Phone size={14} color="#dc2626" aria-hidden="true" />
        <span>
          <strong>Emergency Bypass:</strong> For immediate assistance without verification, direct call 
          <a href="tel:112" className="inline-call-link"> 112</a> is always available.
        </span>
      </div>
    </div>
  );
}
