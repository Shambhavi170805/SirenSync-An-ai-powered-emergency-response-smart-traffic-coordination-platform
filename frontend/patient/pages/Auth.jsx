import React, { useState, useId } from 'react';
import { 
  Eye, 
  EyeOff, 
  ShieldCheck, 
  User, 
  Mail, 
  Lock, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  ArrowRight,
  Phone,
  HeartPulse,
  Siren,
  ArrowLeft
} from 'lucide-react';
import authService from '../services/authService';
import TurnstileWidget from '../components/TurnstileWidget';

export default function Auth({ onAuthSuccess, onBackToEmergency, initialMode = 'signin' }) {
  const [mode, setMode] = useState(initialMode); // 'signin' | 'signup'

  // Form Fields
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [captchaToken, setCaptchaToken] = useState('XXXX.DUMMY.TOKEN.XXXX');

  // UI & Feedback States
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  const formId = useId();

  // Calculate password strength
  const calculatePasswordStrength = (pass) => {
    if (!pass) return { score: 0, label: 'None', color: '#64748b' };
    let score = 0;
    if (pass.length >= 8) score += 1;
    if (pass.length >= 12) score += 1;
    if (/[a-z]/.test(pass) && /[A-Z]/.test(pass)) score += 1;
    if (/[0-9]/.test(pass)) score += 1;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(pass)) score += 1;

    switch (score) {
      case 0:
      case 1:
        return { score: 1, label: 'Weak', color: '#ef4444' };
      case 2:
        return { score: 2, label: 'Fair', color: '#f59e0b' };
      case 3:
        return { score: 3, label: 'Good', color: '#3b82f6' };
      case 4:
      case 5:
        return { score: 4, label: 'Strong', color: '#10b981' };
      default:
        return { score: 0, label: 'None', color: '#64748b' };
    }
  };

  const strength = calculatePasswordStrength(password);

  // Client-side validations
  const validateForm = () => {
    const errors = {};
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!email.trim()) {
      errors.email = 'Email address is required';
    } else if (!emailRegex.test(email.trim())) {
      errors.email = 'Please enter a valid email address';
    }

    if (!password) {
      errors.password = 'Password is required';
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    } else if (mode === 'signup' && !/[0-9!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.password = 'Include at least one number or special character';
    }

    if (mode === 'signup') {
      if (!fullName.trim()) {
        errors.fullName = 'Full name is required';
      } else if (fullName.trim().length < 2) {
        errors.fullName = 'Name must be at least 2 characters';
      }

      if (password !== confirmPassword) {
        errors.confirmPassword = 'Passwords do not match';
      }
    }

    if (!captchaToken) {
      errors.captcha = 'Please complete the security verification challenge';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      if (mode === 'signup') {
        const res = await authService.register({
          fullName: fullName.trim(),
          email: email.trim().toLowerCase(),
          password,
          confirmPassword,
          captchaToken
        });
        setSuccessMessage('Account created successfully! Welcome to SirenSync.');
        setTimeout(() => {
          if (onAuthSuccess) onAuthSuccess(res.patient);
        }, 700);
      } else {
        const res = await authService.login({
          email: email.trim().toLowerCase(),
          password,
          captchaToken
        });
        setSuccessMessage('Welcome back! Signed in successfully.');
        setTimeout(() => {
          if (onAuthSuccess) onAuthSuccess(res.patient);
        }, 600);
      }
    } catch (err) {
      console.error('Authentication submission failed:', err);
      // User-safe generic message for login failure to prevent user enumeration
      if (err.status === 401) {
        setErrorMessage('Invalid email or password. Please verify your credentials and try again.');
      } else {
        setErrorMessage(err.message || 'Authentication failed. Please check your connection and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    setErrorMessage('');
    setSuccessMessage('');
    setValidationErrors({});
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="auth-page-container">
      {/* Emergency Priority Alert Strip */}
      <div className="emergency-priority-strip" role="region" aria-label="Emergency warning">
        <div className="strip-inner">
          <div className="strip-left">
            <HeartPulse size={18} className="pulse-slow" />
            <span>In an active medical emergency? Don't wait for login.</span>
          </div>
          <div className="strip-right">
            <button 
              type="button" 
              onClick={onBackToEmergency}
              className="btn btn-sm btn-outline-emergency"
            >
              <Siren size={14} />
              <span>Instant Emergency Assistance</span>
            </button>
            <a href="tel:112" className="btn btn-sm btn-call-112">
              <Phone size={14} />
              <span>Direct 112 Call</span>
            </a>
          </div>
        </div>
      </div>

      <div className="auth-card-wrapper">
        <div className="auth-card">
          {/* Card Header */}
          <div className="auth-card-header">
            <div className="brand-logo-badge">
              <Siren size={28} className="text-emergency" />
            </div>
            <h1 className="auth-title">
              {mode === 'signup' ? 'Create Patient Account' : 'Patient Sign In'}
            </h1>
            <p className="auth-subtitle">
              {mode === 'signup' 
                ? 'Register your emergency medical profile for prioritized EMS triage & hospital dispatch' 
                : 'Sign in to access your saved medical history, emergency contacts, and active tracking'}
            </p>
          </div>

          {/* Mode Switch Tabs */}
          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signin'}
              className={`auth-tab ${mode === 'signin' ? 'active' : ''}`}
              onClick={() => switchMode('signin')}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signup'}
              className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => switchMode('signup')}
            >
              Create Account
            </button>
          </div>

          {/* Global Alert Messages */}
          {errorMessage && (
            <div className="auth-alert auth-alert-error" role="alert">
              <AlertCircle size={18} />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="auth-alert auth-alert-success" role="status">
              <CheckCircle2 size={18} />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate className="auth-form">
            {/* Full Name (Sign Up only) */}
            {mode === 'signup' && (
              <div className="form-group">
                <label htmlFor={`${formId}-fullName`} className="form-label">
                  Full Name <span className="text-danger">*</span>
                </label>
                <div className="input-with-icon">
                  <User size={18} className="input-icon" />
                  <input
                    id={`${formId}-fullName`}
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Aarav Sharma"
                    className={`form-input ${validationErrors.fullName ? 'input-error' : ''}`}
                    disabled={isLoading}
                    autoComplete="name"
                    required
                  />
                </div>
                {validationErrors.fullName && (
                  <span className="field-error-text" role="alert">{validationErrors.fullName}</span>
                )}
              </div>
            )}

            {/* Email Address */}
            <div className="form-group">
              <label htmlFor={`${formId}-email`} className="form-label">
                Email Address <span className="text-danger">*</span>
              </label>
              <div className="input-with-icon">
                <Mail size={18} className="input-icon" />
                <input
                  id={`${formId}-email`}
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="patient@example.com"
                  className={`form-input ${validationErrors.email ? 'input-error' : ''}`}
                  disabled={isLoading}
                  autoComplete="email"
                  required
                />
              </div>
              {validationErrors.email && (
                <span className="field-error-text" role="alert">{validationErrors.email}</span>
              )}
            </div>

            {/* Password */}
            <div className="form-group">
              <div className="label-row">
                <label htmlFor={`${formId}-password`} className="form-label">
                  Password <span className="text-danger">*</span>
                </label>
                {mode === 'signin' && (
                  <span className="form-hint-text">Minimum 8 characters</span>
                )}
              </div>
              <div className="input-with-icon">
                <Lock size={18} className="input-icon" />
                <input
                  id={`${formId}-password`}
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className={`form-input ${validationErrors.password ? 'input-error' : ''}`}
                  disabled={isLoading}
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="password-toggle-btn"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {validationErrors.password && (
                <span className="field-error-text" role="alert">{validationErrors.password}</span>
              )}

              {/* Password Strength Meter (Sign Up Only) */}
              {mode === 'signup' && password.length > 0 && (
                <div className="strength-meter-box">
                  <div className="strength-header">
                    <span className="strength-label">Password Strength:</span>
                    <strong style={{ color: strength.color }}>{strength.label}</strong>
                  </div>
                  <div className="strength-bars" aria-hidden="true">
                    {[1, 2, 3, 4].map((index) => (
                      <div
                        key={index}
                        className="strength-bar-segment"
                        style={{
                          backgroundColor: index <= strength.score ? strength.color : 'rgba(255,255,255,0.1)'
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password (Sign Up only) */}
            {mode === 'signup' && (
              <div className="form-group">
                <label htmlFor={`${formId}-confirmPassword`} className="form-label">
                  Confirm Password <span className="text-danger">*</span>
                </label>
                <div className="input-with-icon">
                  <Lock size={18} className="input-icon" />
                  <input
                    id={`${formId}-confirmPassword`}
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat your password"
                    className={`form-input ${validationErrors.confirmPassword ? 'input-error' : ''}`}
                    disabled={isLoading}
                    autoComplete="new-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="password-toggle-btn"
                    aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {validationErrors.confirmPassword && (
                  <span className="field-error-text" role="alert">{validationErrors.confirmPassword}</span>
                )}
              </div>
            )}

            {/* CAPTCHA Turnstile Security Widget */}
            <div className="form-group">
              <TurnstileWidget 
                onVerify={(tok) => {
                  setCaptchaToken(tok);
                  setValidationErrors(prev => ({ ...prev, captcha: null }));
                }}
                error={validationErrors.captcha}
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary btn-auth-submit"
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="spin-animation" />
                  <span>{mode === 'signup' ? 'Creating Account...' : 'Signing In...'}</span>
                </>
              ) : (
                <>
                  <span>{mode === 'signup' ? 'Create Patient Account' : 'Sign In to SirenSync'}</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>

            {/* Switch Mode Prompt */}
            <div className="auth-footer-prompt">
              {mode === 'signin' ? (
                <p>
                  Don't have an account yet?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode('signup')}
                    className="auth-link-btn"
                  >
                    Create Account
                  </button>
                </p>
              ) : (
                <p>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode('signin')}
                    className="auth-link-btn"
                  >
                    Sign In
                  </button>
                </p>
              )}
            </div>

            {/* Back to Guest Emergency */}
            <div className="auth-back-row">
              <button
                type="button"
                onClick={onBackToEmergency}
                className="btn-back-link"
              >
                <ArrowLeft size={16} />
                <span>Return to Emergency Dashboard (Guest Mode)</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
