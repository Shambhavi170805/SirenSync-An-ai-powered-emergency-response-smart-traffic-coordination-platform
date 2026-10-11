import React from 'react';
import { 
  AlertOctagon, 
  User, 
  MapPin, 
  PhoneCall, 
  HeartPulse, 
  ShieldCheck, 
  ArrowRight, 
  Building2, 
  Clock, 
  Activity, 
  CheckCircle2, 
  AlertCircle,
  Sparkles,
  Zap
} from 'lucide-react';
import MockMap from '../components/MockMap';
import { quickScenarios } from '../data/mockData';

export default function Dashboard({ 
  patientProfile, 
  activeEmergency, 
  onStartRequest, 
  onQuickScenario,
  onNavigate 
}) {
  return (
    <div className="main-content">
      {/* Hero / Emergency Dispatch Action Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        borderRadius: '20px',
        padding: '2rem 2.25rem',
        color: '#ffffff',
        marginBottom: '2rem',
        boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.3)',
        border: '1px solid #334155',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Decorative radar background */}
        <div style={{
          position: 'absolute',
          right: '-40px',
          top: '-40px',
          width: '280px',
          height: '280px',
          borderRadius: '50%',
          border: '1px solid rgba(255, 255, 255, 0.06)',
          pointerEvents: 'none'
        }} />
        <div style={{
          position: 'absolute',
          right: '20px',
          top: '20px',
          width: '160px',
          height: '160px',
          borderRadius: '50%',
          border: '1px dashed rgba(239, 68, 68, 0.2)',
          pointerEvents: 'none'
        }} />

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.5rem', position: 'relative', zIndex: 1 }}>
          <div style={{ maxWidth: '640px' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', padding: '4px 12px', borderRadius: '999px', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.85rem', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              <span className="pulsing-dot" />
              <span>LIVE TRIAGE & COORDINATION GRID ACTIVE</span>
            </div>

            <h1 style={{ fontSize: '2.1rem', fontWeight: 900, letterSpacing: '-0.025em', lineHeight: 1.15, marginBottom: '0.65rem' }}>
              Instant Emergency Medical Assistance
            </h1>

            <p style={{ color: '#cbd5e1', fontSize: '0.975rem', lineHeight: 1.5, marginBottom: '1.25rem' }}>
              SirenSync dynamically connects you with optimal regional emergency centers, secures real-time bed reservations, and primes green-corridor ambulance routing across Dehradun.
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <button 
                onClick={onStartRequest}
                className="btn-large-sos"
              >
                <AlertOctagon size={24} />
                <span>Request Emergency Assistance</span>
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '0.85rem' }}>
                <Clock size={16} color="#38bdf8" />
                <span>Avg. Ambulance Response: <strong>&lt; 9 Mins</strong></span>
              </div>
            </div>
          </div>

          {/* Quick Hotlines Card */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(10px)',
            borderRadius: '16px',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            padding: '1.25rem 1.5rem',
            minWidth: '240px'
          }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 700, letterSpacing: '0.04em', marginBottom: '0.75rem' }}>
              Emergency Helplines
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>National Ambulance</span>
                <span style={{ fontWeight: 800, color: '#f87171', fontSize: '0.95rem' }}>📞 108</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>Police Control Room</span>
                <span style={{ fontWeight: 800, color: '#60a5fa', fontSize: '0.95rem' }}>📞 112</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}>
                <span style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>Disaster Management</span>
                <span style={{ fontWeight: 800, color: '#34d399', fontSize: '0.95rem' }}>📞 1070</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Emergency Status Banner (if active) */}
      {activeEmergency && (
        <div style={{
          background: '#fff1f2',
          border: '2px solid #fecdd3',
          borderRadius: '16px',
          padding: '1.25rem 1.5rem',
          marginBottom: '2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          boxShadow: '0 4px 12px rgba(225, 29, 72, 0.08)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              background: '#e11d48',
              color: '#ffffff',
              padding: '12px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <AlertCircle size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 800, fontSize: '1.05rem', color: '#9f1239' }}>
                  ACTIVE EMERGENCY IN PROGRESS: {activeEmergency.requestId}
                </span>
                <span className="badge badge-critical">
                  {activeEmergency.severity}
                </span>
              </div>
              <div style={{ fontSize: '0.875rem', color: '#475569', marginTop: '3px' }}>
                Type: <strong>{activeEmergency.emergencyType}</strong> • Status: <strong>{activeEmergency.status}</strong>
                {activeEmergency.selectedHospital && (
                  <span> • Selected Facility: <strong>{activeEmergency.selectedHospital.name}</strong></span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              onClick={() => onNavigate(activeEmergency.selectedHospital ? 'status' : 'recommendations')}
              className="btn btn-primary"
              style={{ fontWeight: 700 }}
            >
              <span>{activeEmergency.selectedHospital ? 'View Live Status Tracker' : 'View Hospital Recommendations'}</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Quick Demonstration Scenarios for Mentor Meeting */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '16px',
        padding: '1.25rem 1.5rem',
        marginBottom: '2rem',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={18} color="#d97706" />
            <span style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a' }}>
              Mentor Demonstration Fast-Track Scenarios
            </span>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Click any scenario to auto-populate emergency triage in 1 step:
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {quickScenarios.map((sc, idx) => (
            <div 
              key={idx}
              onClick={() => onQuickScenario(sc)}
              style={{
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                padding: '0.85rem 1rem',
                cursor: 'pointer',
                background: '#f8fafc',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#0284c7';
                e.currentTarget.style.background = '#f0f9ff';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e2e8f0';
                e.currentTarget.style.background = '#f8fafc';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#0f172a' }}>
                  {sc.name}
                </span>
                <span className={`badge ${sc.severity === 'Critical' ? 'badge-critical' : 'badge-high'}`} style={{ fontSize: '0.65rem' }}>
                  {sc.severity}
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#64748b', lineClamp: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {sc.symptoms}
              </p>
              <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#0284c7', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span>Launch Scenario</span>
                <ArrowRight size={12} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Grid: Patient Profile (Left) & Current Location (Right) */}
      <div className="grid-2">
        {/* Section 1: Patient Profile */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', paddingBottom: '0.75rem', borderBottom: '1px solid #f1f5f9' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div style={{
                background: '#e0f2fe',
                color: '#0284c7',
                padding: '8px',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <User size={20} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>
                  Registered Patient Profile
                </h2>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Patient ID: {patientProfile.id}
                </span>
              </div>
            </div>

            <span className="badge badge-success">
              <ShieldCheck size={12} />
              Verified Health Record
            </span>
          </div>

          {/* Profile details */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Full Name</span>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0f172a' }}>{patientProfile.name}</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Age & Gender</span>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>{patientProfile.age} yrs • {patientProfile.gender}</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Blood Group</span>
              <div style={{ fontSize: '1.05rem', fontWeight: 900, color: '#dc2626' }}>{patientProfile.bloodGroup}</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Emergency Contact</span>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>{patientProfile.emergencyContact.phone}</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{patientProfile.emergencyContact.name}</div>
            </div>
          </div>

          {/* Allergies & Conditions */}
          <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '10px', border: '1px solid #e2e8f0', marginBottom: '1.25rem' }}>
            <div style={{ marginBottom: '8px' }}>
              <span style={{ fontSize: '0.725rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>Known Drug Allergies:</span>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
                {patientProfile.knownAllergies.map((alg, i) => (
                  <span key={i} style={{ background: '#fee2e2', color: '#991b1b', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, border: '1px solid #fecaca' }}>
                    ⚠️ {alg}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <span style={{ fontSize: '0.725rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>Pre-existing Medical History:</span>
              <div style={{ fontSize: '0.825rem', color: '#334155', marginTop: '2px', fontWeight: 600 }}>
                {patientProfile.medicalConditions.join(' • ')}
              </div>
            </div>
          </div>

          {/* Insurance */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: '#64748b', borderTop: '1px solid #f1f5f9', paddingTop: '0.75rem' }}>
            <span>Insurance Coverage:</span>
            <span style={{ fontWeight: 700, color: '#059669' }}>{patientProfile.insuranceProvider} (Active)</span>
          </div>
        </div>

        {/* Section 2: Current Location */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', paddingBottom: '0.75rem', borderBottom: '1px solid #f1f5f9' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div style={{
                background: '#ecfdf5',
                color: '#059669',
                padding: '8px',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <MapPin size={20} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>
                  Current Telemetry & Location
                </h2>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Dehradun Emergency Response Sector
                </span>
              </div>
            </div>

            <span className="badge badge-info">
              {patientProfile.currentLocation.accuracy}
            </span>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <div style={{ fontSize: '0.8rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>
              Pinned Location
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>
              {patientProfile.currentLocation.address}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '2px' }}>
              Lat: {patientProfile.currentLocation.coordinates.lat}° N • Lng: {patientProfile.currentLocation.coordinates.lng}° E
            </div>
          </div>

          {/* Embedded Mock GIS Map */}
          <MockMap patientLocation={patientProfile.currentLocation} />
        </div>
      </div>
    </div>
  );
}
