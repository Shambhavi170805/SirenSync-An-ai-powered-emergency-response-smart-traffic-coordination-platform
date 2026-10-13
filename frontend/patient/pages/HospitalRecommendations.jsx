import React, { useState } from 'react';
import { 
  Building2, 
  MapPin, 
  Clock, 
  ArrowLeft, 
  Sparkles, 
  Filter, 
  ShieldCheck, 
  SlidersHorizontal,
  Info,
  CheckCircle2,
  Navigation
} from 'lucide-react';
import HospitalCard from '../components/HospitalCard';
import MockMap from '../components/MockMap';
import { mockHospitals } from '../data/mockData';

export default function HospitalRecommendations({ 
  activeEmergency, 
  onSelectHospital, 
  onBackToRequest, 
  onNavigate 
}) {
  const [sortBy, setSortBy] = useState('score'); // 'score', 'eta', 'beds', 'distance'
  const [filterSpec, setFilterSpec] = useState('all');

  // Clone and sort mock hospitals
  let hospitals = [...mockHospitals];

  if (filterSpec !== 'all') {
    hospitals = hospitals.filter(h => 
      h.specialization.toLowerCase().includes(filterSpec.toLowerCase()) ||
      h.specializationsList.some(s => s.toLowerCase().includes(filterSpec.toLowerCase()))
    );
  }

  if (sortBy === 'score') {
    hospitals.sort((a, b) => b.recommendationScore - a.recommendationScore);
  } else if (sortBy === 'eta') {
    hospitals.sort((a, b) => a.etaMinutes - b.etaMinutes);
  } else if (sortBy === 'beds') {
    hospitals.sort((a, b) => b.availableBeds.icu - a.availableBeds.icu);
  } else if (sortBy === 'distance') {
    hospitals.sort((a, b) => a.distanceKm - b.distanceKm);
  }

  return (
    <div className="main-content">
      {/* Top Bar with back link and Emergency ID */}
      <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
        <button 
          onClick={onBackToRequest}
          className="btn btn-secondary"
          style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', gap: '6px' }}
        >
          <ArrowLeft size={16} />
          <span>Edit Emergency Details</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Step 2 of 4:</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0284c7' }}>Hospital Evaluation</span>
        </div>
      </div>

      {/* Emergency Context Banner */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '16px',
        padding: '1.25rem 1.5rem',
        marginBottom: '1.75rem',
        boxShadow: '0 2px 4px rgba(0,0,0,0.04)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '1.1rem', fontWeight: 900, color: '#0f172a' }}>
              Emergency ID: {activeEmergency?.requestId || 'EMG-2026-001'}
            </span>
            <span className={`badge ${activeEmergency?.severity === 'Critical' ? 'badge-critical' : 'badge-high'}`}>
              {activeEmergency?.severity || 'Critical'}
            </span>
            <span className="badge badge-info">
              {activeEmergency?.emergencyType || 'Cardiac Emergency'}
            </span>
            {activeEmergency?.attachmentsCount > 0 && (
              <span className="badge badge-success" style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                📎 {activeEmergency.attachmentsCount} {activeEmergency.attachmentsCount === 1 ? 'Report' : 'Reports'} Attached
              </span>
            )}
          </div>

          <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
            Patient: <strong>{activeEmergency?.patientName || 'Aarav Sharma'}</strong> {activeEmergency?.patientCondition && <span>({activeEmergency.patientCondition})</span>} • Location: <strong>{activeEmergency?.currentLocation || 'Rajpur Road, Dehradun'}</strong>
          </div>
        </div>

        {/* Vital Rule Callout: Patient Decision */}
        <div style={{
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: '10px',
          padding: '0.65rem 1rem',
          maxWidth: '360px',
          fontSize: '0.8rem',
          color: '#1e40af'
        }}>
          <div style={{ fontWeight: 800, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={14} color="#2563eb" />
            Patient Autonomy Principle:
          </div>
          <div style={{ marginTop: '2px', fontWeight: 500 }}>
            "The final hospital choice is made by the patient."
          </div>
        </div>
      </div>

      {/* Filter and Sort Toolbar */}
      <div style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '0.85rem 1.25rem',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        {/* Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={18} color="#f59e0b" />
          <span style={{ fontWeight: 800, fontSize: '1rem', color: '#0f172a' }}>
            Ranked Hospital Recommendations ({hospitals.length})
          </span>
        </div>

        {/* Sort Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#64748b' }}>
            <SlidersHorizontal size={14} />
            <span>Sort by:</span>
          </div>

          <div style={{ display: 'flex', gap: '4px' }}>
            {[
              { id: 'score', label: 'AI Score' },
              { id: 'eta', label: 'Fastest ETA' },
              { id: 'beds', label: 'ICU Beds' },
              { id: 'distance', label: 'Distance' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSortBy(tab.id)}
                className={`btn ${sortBy === tab.id ? 'btn-medical' : 'btn-secondary'}`}
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.775rem', borderRadius: '6px' }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Hospital Cards Grid */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        {hospitals.map((hospital) => (
          <HospitalCard
            key={hospital.id}
            hospital={hospital}
            isSelected={activeEmergency?.selectedHospital?.id === hospital.id}
            onSelectHospital={onSelectHospital}
          />
        ))}
      </div>

      {/* Map visualization of recommended facilities */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Navigation size={18} color="#0284c7" />
              Regional Corridor Map & Route Conditions
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
              Traffic conditions and emergency transit vectors across Dehradun hospital nodes
            </p>
          </div>
        </div>

        <MockMap 
          selectedHospitalId={activeEmergency?.selectedHospital?.id || "hosp-max-ddn"}
          patientLocation={{ address: activeEmergency?.currentLocation || "Rajpur Road, Dehradun" }}
        />
      </div>
    </div>
  );
}
