import React, { useState, useRef } from 'react';
import { 
  Siren, 
  Phone, 
  ShieldAlert, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle,
  Clock,
  MapPin,
  Building2,
  Activity
} from 'lucide-react';
import QuickEmergencyForm from '../components/QuickEmergencyForm';

export default function Dashboard({ 
  currentUser,
  patientProfile, 
  activeEmergency, 
  onSubmitEmergency, 
  onNavigate 
}) {
  // Whether the quick emergency request form is revealed
  const [isFormOpen, setIsFormOpen] = useState(false);
  const formRef = useRef(null);

  const handleOpenForm = () => {
    setIsFormOpen(true);
    // Smooth scroll down to form
    setTimeout(() => {
      if (formRef.current) {
        formRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  };

  return (
    <div className="landing-emergency-container">
      {/* Active Emergency Alert Banner (if user already submitted an emergency) */}
      {activeEmergency && (
        <div className="active-emergency-banner" role="region" aria-label="Active emergency alert">
          <div className="active-banner-left">
            <div className="active-banner-icon-box" aria-hidden="true">
              <ShieldAlert size={22} />
            </div>
            <div>
              <div className="active-banner-title">
                Active Emergency: {activeEmergency.requestId}
              </div>
              <div className="active-banner-sub">
                Type: <strong>{activeEmergency.emergencyType}</strong> • Status: <strong>{activeEmergency.status}</strong>
                {activeEmergency.selectedHospital && (
                  <span> • Facility: <strong>{activeEmergency.selectedHospital.name}</strong></span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={() => onNavigate(activeEmergency.selectedHospital ? 'status' : 'recommendations')}
            className="btn btn-primary btn-resume-emergency"
          >
            <span>{activeEmergency.selectedHospital ? 'View Status Timeline' : 'View Hospital Options'}</span>
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
      )}

      {/* Patient Account Status / Guest Banner */}
      {currentUser ? (
        <div className="patient-status-pill-banner" role="status">
          <div className="status-pill-left">
            <CheckCircle2 size={16} className="text-success" />
            <span>
              Signed in as <strong>{currentUser.full_name}</strong> ({currentUser.email})
            </span>
          </div>
          <span className="profile-sync-badge">Emergency Profile Linked</span>
        </div>
      ) : (
        <div className="patient-guest-notice-banner">
          <span>Emergency assistance is open to all patients without logging in.</span>
          <button 
            type="button" 
            onClick={() => onNavigate('auth')} 
            className="btn-guest-signin"
          >
            Sign In / Register Profile →
          </button>
        </div>
      )}

      {/* ========================================================
          B. PROMINENT EMERGENCY ACTION HERO
      ======================================================== */}
      <section className="emergency-hero-section" aria-label="Emergency assistance trigger">
        <div className="hero-content-wrapper">
          {/* Main Headline */}
          <h1 className="hero-main-title">
            Need Emergency Medical Help?
          </h1>

          <p className="hero-main-subtitle">
            Get connected to nearby ambulances and hospitals in Dehradun.
          </p>

          {/* Primary Action Button */}
          <div className="hero-action-box">
            <button
              onClick={handleOpenForm}
              className="btn-emergency-hero-cta"
              aria-expanded={isFormOpen}
              aria-controls="quick-emergency-form-panel"
            >
              <Siren size={32} className="hero-cta-icon" aria-hidden="true" />
              <div className="hero-cta-text-group">
                <span className="hero-cta-primary-text">REQUEST EMERGENCY HELP</span>
                <span className="hero-cta-subtext">Get connected to nearby emergency assistance.</span>
              </div>
            </button>
          </div>

          {/* Secondary Helpline Direct Call (Accessible & Prominent for safety) */}
          <div className="hero-secondary-safety-bar">
            <div className="safety-bar-text">
              <span className="critical-warning-dot" aria-hidden="true" />
              <span>Immediate life threat? Direct call to police, fire, & medical emergency:</span>
            </div>
            <a 
              href="tel:112" 
              className="btn-call-112-prominent"
              aria-label="Direct call to National Emergency Services 112"
            >
              <Phone size={18} aria-hidden="true" />
              <span>Call 112 (National Helpline)</span>
            </a>
          </div>
        </div>
      </section>

      {/* ========================================================
          C. QUICK EMERGENCY REQUEST FORM (REVEALED ON ACTION)
      ======================================================== */}
      {isFormOpen ? (
        <section 
          ref={formRef} 
          id="quick-emergency-form-panel" 
          className="form-reveal-section"
          aria-label="Emergency assistance request form"
        >
          <QuickEmergencyForm
            patientProfile={patientProfile}
            onSubmitEmergency={onSubmitEmergency}
            onCancel={() => setIsFormOpen(false)}
          />
        </section>
      ) : (
        /* Preview prompt if form not yet open */
        <section className="emergency-preview-hints">
          <div className="hints-card">
            <h2 className="hints-title">How SirenSync Assists You</h2>
            <div className="hints-grid">
              <div className="hint-item">
                <div className="hint-num">1</div>
                <div>
                  <strong>Tap the Request Button</strong>
                  <p>State what happened and where help is needed in 30 seconds.</p>
                </div>
              </div>
              <div className="hint-item">
                <div className="hint-num">2</div>
                <div>
                  <strong>Compare Nearby Hospitals</strong>
                  <p>View facilities ranked by distance, emergency beds, and travel time.</p>
                </div>
              </div>
              <div className="hint-item">
                <div className="hint-num">3</div>
                <div>
                  <strong>Select Hospital & Track</strong>
                  <p>Confirm the hospital of your choice and monitor status updates.</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
