import React from 'react';
import { ArrowLeft } from 'lucide-react';
import QuickEmergencyForm from '../components/QuickEmergencyForm';

export default function EmergencyRequest({ 
  patientProfile, 
  onSubmitEmergency, 
  onBack 
}) {
  return (
    <div className="main-content" style={{ maxWidth: '820px', margin: '0 auto', padding: '1rem 1rem 3rem' }}>
      {/* Minimal Back Button */}
      <div style={{ marginBottom: '1rem' }}>
        <button 
          onClick={onBack}
          className="btn btn-secondary"
          style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', gap: '6px' }}
          aria-label="Back to home"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          <span>Back to Home</span>
        </button>
      </div>

      {/* Streamlined Quick Emergency Form */}
      <QuickEmergencyForm
        patientProfile={patientProfile}
        onSubmitEmergency={onSubmitEmergency}
        onCancel={onBack}
      />
    </div>
  );
}
