import React from 'react';
import { 
  Siren, 
  Phone, 
  RotateCcw,
  User,
  LogOut,
  LogIn,
  ShieldCheck
} from 'lucide-react';

export default function Navbar({ 
  currentPage, 
  setCurrentPage, 
  activeEmergency, 
  onResetDemo,
  currentUser,
  onLogout
}) {
  return (
    <header className="top-navbar" role="banner">
      <div className="nav-inner">
        {/* Brand & Connection Status */}
        <div 
          className="brand-wrapper" 
          onClick={() => setCurrentPage('dashboard')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && setCurrentPage('dashboard')}
          aria-label="SirenSync Home"
        >
          <div className="brand-icon-box" aria-hidden="true">
            <Siren size={22} />
          </div>
          <div className="brand-text">
            <div className="brand-title-row">
              <span className="brand-name">SirenSync</span>
              <span className="status-indicator-badge" title="Connection status">
                <span className="status-dot-green" aria-hidden="true" />
                <span>Online • Dehradun Node</span>
              </span>
            </div>
            <div className="brand-tagline">
              Emergency Response Network
            </div>
          </div>
        </div>

        {/* Essential Actions */}
        <div className="nav-actions">
          {/* Active Emergency Status Jump-chip */}
          {activeEmergency && (
            <button 
              className="active-emergency-pill"
              onClick={() => setCurrentPage(activeEmergency.selectedHospital ? 'status' : 'recommendations')}
              title="Return to active emergency workflow"
              aria-label={`View active emergency ${activeEmergency.requestId}`}
            >
              <span className="pulsing-dot" aria-hidden="true" />
              <span className="pill-text">{activeEmergency.requestId}</span>
            </button>
          )}

          {/* User Account / Sign In Badge */}
          {currentUser ? (
            <div className="user-profile-nav-group" title={`Signed in as ${currentUser.email}`}>
              <div className="user-profile-badge">
                <div className="user-avatar-circle" aria-hidden="true">
                  <User size={14} />
                </div>
                <div className="user-badge-info">
                  <span className="user-badge-name">{currentUser.full_name}</span>
                  <span className="user-badge-status">
                    <ShieldCheck size={11} className="text-success inline-icon" />
                    <span>Verified Patient</span>
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={onLogout}
                className="btn-nav-logout"
                title="Sign out of patient account"
                aria-label="Sign out"
              >
                <LogOut size={14} />
                <span className="logout-text">Sign Out</span>
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setCurrentPage('auth')}
              className={`btn-nav-signin ${currentPage === 'auth' ? 'active' : ''}`}
              title="Sign in or create a patient account"
              aria-label="Sign in or register"
            >
              <LogIn size={15} />
              <span>Sign In / Register</span>
            </button>
          )}

          {/* National Emergency Hotline: 112 */}
          <a 
            href="tel:112" 
            className="btn-emergency-call"
            aria-label="Direct call to National Emergency Services 112"
            title="Immediate direct phone line to emergency services"
          >
            <Phone size={16} aria-hidden="true" />
            <span className="call-text">
              <span className="call-label">Direct Call</span>
              <strong className="call-number">112</strong>
            </span>
          </a>

          {/* Prototype Reset Button */}
          <button 
            className="btn-reset-demo" 
            onClick={onResetDemo}
            title="Reset demonstration state"
            aria-label="Reset prototype to initial state"
          >
            <RotateCcw size={14} aria-hidden="true" />
            <span className="reset-label">Reset</span>
          </button>
        </div>
      </div>
    </header>
  );
}
