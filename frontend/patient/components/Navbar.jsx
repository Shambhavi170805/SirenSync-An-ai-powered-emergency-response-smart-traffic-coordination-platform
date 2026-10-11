import React from 'react';
import { 
  Siren, 
  Activity, 
  MapPin, 
  FileText, 
  Building2, 
  CheckCircle2, 
  RotateCcw,
  ShieldAlert
} from 'lucide-react';

export default function Navbar({ 
  currentPage, 
  setCurrentPage, 
  activeEmergency, 
  onResetDemo 
}) {
  return (
    <header className="top-navbar">
      <div className="nav-inner">
        {/* Brand */}
        <div className="brand-wrapper" onClick={() => setCurrentPage('dashboard')}>
          <div className="brand-icon-box">
            <Siren size={24} />
          </div>
          <div className="brand-text">
            <h1>
              SirenSync
              <span style={{ fontSize: '0.65rem', background: '#e0f2fe', color: '#0369a1', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                PHASE 2 PROTOTYPE
              </span>
            </h1>
            <div className="brand-tagline">
              AI-Powered Emergency Response & Smart Traffic Platform
            </div>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="nav-links">
          <button 
            className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentPage('dashboard')}
          >
            <Activity size={16} />
            <span>Dashboard</span>
          </button>

          <button 
            className={`nav-btn emergency-nav-btn ${currentPage === 'request' ? 'active' : ''}`}
            onClick={() => setCurrentPage('request')}
          >
            <ShieldAlert size={16} />
            <span>Request Assistance</span>
          </button>

          {activeEmergency && (
            <>
              <button 
                className={`nav-btn ${currentPage === 'recommendations' ? 'active' : ''}`}
                onClick={() => setCurrentPage('recommendations')}
              >
                <Building2 size={16} />
                <span>Hospitals</span>
              </button>

              {activeEmergency.selectedHospital && (
                <>
                  <button 
                    className={`nav-btn ${currentPage === 'selected' ? 'active' : ''}`}
                    onClick={() => setCurrentPage('selected')}
                  >
                    <CheckCircle2 size={16} />
                    <span>Selection</span>
                  </button>

                  <button 
                    className={`nav-btn ${currentPage === 'status' ? 'active' : ''}`}
                    onClick={() => setCurrentPage('status')}
                  >
                    <div className="pulsing-dot" />
                    <span>Status Tracker</span>
                  </button>
                </>
              )}
            </>
          )}

          {/* Active emergency badge or ready status */}
          {activeEmergency ? (
            <div className="emergency-chip" title="Active emergency session">
              <span className="pulsing-dot" />
              <span>{activeEmergency.requestId}</span>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#059669', background: '#ecfdf5', padding: '4px 8px', borderRadius: '999px', border: '1px solid #a7f3d0', fontWeight: 600 }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
              Dehradun EMS Ready
            </div>
          )}

          {/* Demo reset button */}
          <button 
            className="btn btn-secondary" 
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', gap: '4px' }}
            onClick={onResetDemo}
            title="Reset demonstration state"
          >
            <RotateCcw size={13} />
            Reset Demo
          </button>
        </nav>
      </div>
    </header>
  );
}
