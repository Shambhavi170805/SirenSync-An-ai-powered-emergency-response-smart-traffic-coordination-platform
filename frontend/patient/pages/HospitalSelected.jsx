import React from 'react';
import { 
  CheckCircle2, 
  Building2, 
  Clock, 
  MapPin, 
  Phone, 
  ShieldCheck, 
  ArrowRight, 
  RotateCcw,
  Activity,
  Bed,
  Car
} from 'lucide-react';

export default function HospitalSelected({ 
  activeEmergency, 
  onViewStatus, 
  onChangeHospital 
}) {
  const hospital = activeEmergency?.selectedHospital;

  if (!hospital) {
    return (
      <div className="main-content" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
        <p>No hospital selected yet. Please return to the recommendations list.</p>
        <button onClick={onChangeHospital} className="btn btn-primary" style={{ marginTop: '1rem' }}>
          Back to Recommendations
        </button>
      </div>
    );
  }

  return (
    <div className="main-content">
      {/* Container */}
      <div style={{ maxWidth: '720px', margin: '0 auto' }}>
        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          {/* Success Check Icon */}
          <div style={{
            width: '76px',
            height: '76px',
            borderRadius: '50%',
            background: '#ecfdf5',
            color: '#059669',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.5rem',
            boxShadow: '0 8px 20px -4px rgba(5, 150, 105, 0.25)',
            border: '2px solid #a7f3d0'
          }}>
            <CheckCircle2 size={44} strokeWidth={2.5} />
          </div>

          <h2 style={{ fontSize: '1.85rem', fontWeight: 900, color: '#0f172a', marginBottom: '0.45rem', letterSpacing: '-0.02em' }}>
            Hospital Selected Successfully
          </h2>

          <p style={{ fontSize: '0.925rem', color: '#64748b', marginBottom: '2rem', maxWidth: '520px', margin: '0 auto 2rem' }}>
            Your choice has been recorded. Emergency medical triage has locked your receiving center and transmitted initial vitals to the incoming intake team.
          </p>

          {/* Primary Confirmation Details Card */}
          <div style={{
            background: '#f8fafc',
            border: '2px solid #e2e8f0',
            borderRadius: '16px',
            padding: '1.75rem',
            textAlign: 'left',
            marginBottom: '2rem'
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem' }}>
              {/* Selected Hospital Name */}
              <div style={{ gridColumn: 'span 2', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem' }}>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.04em' }}>
                  Selected Hospital
                </div>
                <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#0f172a', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Building2 size={24} color="#0284c7" />
                  <span>{hospital.name}</span>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <MapPin size={14} />
                  {hospital.address}
                </div>
              </div>

              {/* Request ID */}
              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.04em' }}>
                  Request ID
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#dc2626', marginTop: '2px' }}>
                  {activeEmergency?.requestId || 'EMG-2026-001'}
                </div>
              </div>

              {/* Status */}
              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.04em' }}>
                  Status
                </div>
                <div style={{ marginTop: '4px' }}>
                  <span className="badge badge-success" style={{ fontSize: '0.85rem', padding: '4px 10px' }}>
                    ● Hospital Selected
                  </span>
                </div>
              </div>

              {/* Estimated Arrival Time */}
              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.04em' }}>
                  Estimated Arrival
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0284c7', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Clock size={18} />
                  <span>{hospital.etaMinutes} minutes</span>
                </div>
              </div>

              {/* Distance & Bed Reservation */}
              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.04em' }}>
                  Distance & Bed Status
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#334155', marginTop: '4px' }}>
                  {hospital.distanceKm} km • {hospital.availableBeds.icu} ICU Beds Held
                </div>
              </div>
            </div>

            {/* Verification banner of patient autonomy */}
            <div style={{
              marginTop: '1.25rem',
              paddingTop: '1rem',
              borderTop: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.8rem',
              color: '#059669',
              fontWeight: 600
            }}>
              <ShieldCheck size={18} />
              <span>Confirmed: "The final hospital choice is made by the patient."</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <button
              onClick={onChangeHospital}
              className="btn btn-secondary"
              style={{ padding: '0.8rem 1.5rem', fontWeight: 600 }}
            >
              <RotateCcw size={16} />
              Change Hospital Choice
            </button>

            <button
              onClick={onViewStatus}
              className="btn btn-primary"
              style={{ padding: '0.8rem 2rem', fontWeight: 800, fontSize: '1rem', boxShadow: '0 4px 12px rgba(220, 38, 38, 0.3)' }}
            >
              <span>View Emergency Status</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
