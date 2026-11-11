import React, { useState } from 'react';
import { 
  Activity, 
  Building2, 
  Clock, 
  ShieldCheck, 
  Phone, 
  AlertCircle, 
  Truck, 
  CheckCircle2, 
  MapPin, 
  ArrowLeft,
  Navigation,
  Radio,
  FileCheck2,
  Sparkles
} from 'lucide-react';
import Timeline from '../components/Timeline';
import MockMap from '../components/MockMap';
import { defaultTimelineSteps, mockAssignedAmbulance } from '../data/mockData';

export default function EmergencyStatus({ 
  activeEmergency, 
  onBackToDashboard, 
  onBackToHospitals 
}) {
  const hospital = activeEmergency?.selectedHospital;
  const requestId = activeEmergency?.requestId || 'EMG-2026-001';

  // State to simulate advancing timeline steps for mentor demonstration
  // Default step 3 is "Ambulance Coordination" (index 3)
  const [currentStepIndex, setCurrentStepIndex] = useState(3);
  const [timelineSteps, setTimelineSteps] = useState(defaultTimelineSteps);

  const handleAdvanceStep = () => {
    if (currentStepIndex < timelineSteps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    }
  };

  const handleResetTimeline = () => {
    setCurrentStepIndex(3);
  };

  const currentStepTitle = timelineSteps[currentStepIndex]?.title || "Hospital Selected";

  return (
    <div className="main-content">
      {/* Header breadcrumb & controls */}
      <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
        <button 
          onClick={onBackToDashboard}
          className="btn btn-secondary"
          style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', gap: '6px' }}
        >
          <ArrowLeft size={16} />
          <span>Back to Dashboard</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Step 4 of 4:</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#059669' }}>Live Telemetry & Status</span>
        </div>
      </div>

      {/* Primary Emergency Status Card */}
      <div style={{
        background: '#ffffff',
        border: '2px solid #e2e8f0',
        borderRadius: '20px',
        padding: '2rem',
        marginBottom: '2rem',
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.06)'
      }}>
        {/* Top Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '1.25rem', marginBottom: '1.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="pulsing-dot" />
              <span style={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', color: '#dc2626', letterSpacing: '0.05em' }}>
                Active Emergency Telemetry Tracker
              </span>
            </div>
            <h1 style={{ fontSize: '1.85rem', fontWeight: 900, color: '#0f172a', marginTop: '4px' }}>
              Emergency ID: {requestId}
            </h1>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="badge badge-critical" style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
              {activeEmergency?.severity || 'Critical'}
            </span>
            <span className="badge badge-info" style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
              {activeEmergency?.emergencyType || 'Cardiac Emergency'}
            </span>
          </div>
        </div>

        {/* 3 Key Status Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
          {/* Selected Hospital */}
          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.03em' }}>
              Selected Hospital
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Building2 size={20} color="#0284c7" />
              <span>{hospital?.name || "Max Super Speciality Hospital"}</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>
              {hospital?.address || "Mussoorie Diversion Road, Dehradun"}
            </div>
          </div>

          {/* Current Status */}
          <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#065f46', fontWeight: 700, letterSpacing: '0.03em' }}>
              Current Status
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#065f46', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={20} color="#059669" />
              <span>"{currentStepTitle}"</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#047857', marginTop: '4px' }}>
              State synced via SirenSync Local Bus
            </div>
          </div>

          {/* Estimated Arrival Time */}
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#991b1b', fontWeight: 700, letterSpacing: '0.03em' }}>
              Estimated Transit ETA
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#dc2626', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={20} color="#dc2626" />
              <span>{hospital?.etaMinutes || 11} Minutes</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#b91c1c', marginTop: '4px' }}>
              Green Corridor Traffic wave allocated
            </div>
          </div>
        </div>

        {/* Real-time Triage Dispatch Notice */}
        <div style={{
          background: '#f0fdf4',
          border: '1px solid #bbf7d0',
          borderRadius: '12px',
          padding: '0.85rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          fontSize: '0.85rem',
          color: '#166534'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Radio size={18} color="#16a34a" />
            <span>
              <strong>Receiving Emergency Department Prepped:</strong> Trauma Bay and Cardiac Cath Lab reserved. Patient vitals stream queued.
            </span>
          </div>
          <button 
            onClick={onBackToHospitals}
            className="btn btn-secondary"
            style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem' }}
          >
            Re-examine Hospitals
          </button>
        </div>
      </div>

      {/* Grid: Timeline (Left) & Dispatch + Route Map (Right) */}
      <div className="grid-2">
        {/* Left Column: Progress Timeline */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', paddingBottom: '0.75rem', borderBottom: '1px solid #f1f5f9' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={20} color="#dc2626" />
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a' }}>
                Emergency Lifecycle Timeline
              </h2>
            </div>
            <span className="badge badge-info" style={{ fontSize: '0.75rem' }}>
              Frontend Mock States
            </span>
          </div>

          {/* Timeline Component */}
          <Timeline 
            steps={timelineSteps}
            currentStepIndex={currentStepIndex}
            onAdvanceStep={handleAdvanceStep}
            onResetTimeline={handleResetTimeline}
          />
        </div>

        {/* Right Column: Ambulance Unit & Live Corridor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Ambulance Telemetry Card */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Truck size={20} color="#0284c7" />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a' }}>
                  Assigned Ambulance Unit
                </h3>
              </div>
              <span className="badge badge-success">
                ● Radio Connected
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Unit Identifier</span>
                <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0f172a' }}>{mockAssignedAmbulance.unitId}</div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{mockAssignedAmbulance.type}</div>
              </div>

              <div>
                <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Paramedic In-Charge</span>
                <div style={{ fontSize: '1rem', fontWeight: 800, color: '#0f172a' }}>{mockAssignedAmbulance.paramedic}</div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Driver: {mockAssignedAmbulance.driverName}</div>
              </div>
            </div>

            {/* Equipment onboard */}
            <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>
                Equipment & Life Support Onboard:
              </div>
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '4px' }}>
                {mockAssignedAmbulance.equipment.map((eq, i) => (
                  <span key={i} style={{ background: '#ffffff', border: '1px solid #cbd5e1', fontSize: '0.725rem', padding: '2px 6px', borderRadius: '4px', color: '#334155' }}>
                    ✓ {eq}
                  </span>
                ))}
              </div>
            </div>

            {/* Call button */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span style={{ color: '#64748b' }}>Emergency Comms Hotline:</span>
              <a 
                href={`tel:${mockAssignedAmbulance.phone}`}
                style={{ 
                  color: '#dc2626', 
                  fontWeight: 800, 
                  textDecoration: 'none', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '4px',
                  background: '#fef2f2',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: '1px solid #fecaca'
                }}
              >
                <Phone size={14} />
                {mockAssignedAmbulance.phone}
              </a>
            </div>
          </div>

          {/* Route Map Card */}
          <div className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Navigation size={16} color="#0284c7" />
                Live Corridor Vector
              </h4>
              <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: 600 }}>
                Signal Synchronized
              </span>
            </div>

            <MockMap 
              selectedHospitalId={hospital?.id || "hosp-max-ddn"}
              patientLocation={{ address: activeEmergency?.currentLocation || "Rajpur Road, Dehradun" }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
