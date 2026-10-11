import React, { useState } from 'react';
import { 
  AlertTriangle, 
  User, 
  MapPin, 
  Phone, 
  Activity, 
  FileText, 
  ArrowRight, 
  ArrowLeft,
  CheckCircle2, 
  Sparkles,
  ShieldAlert,
  Heart,
  Wind,
  Flame,
  Zap
} from 'lucide-react';
import { emergencyTypes, severityLevels, quickScenarios } from '../data/mockData';

export default function EmergencyRequest({ 
  patientProfile, 
  onSubmitEmergency, 
  onBack,
  presetScenario = null 
}) {
  const [formData, setFormData] = useState({
    patientName: presetScenario?.patientName || patientProfile.name || '',
    age: presetScenario?.age || patientProfile.age || '',
    contactNumber: presetScenario?.contactNumber || patientProfile.phone || '',
    currentLocation: presetScenario?.location || patientProfile.currentLocation.address || 'Rajpur Road, Dehradun, Uttarakhand',
    emergencyType: presetScenario?.emergencyType || 'Cardiac Emergency',
    symptoms: presetScenario?.symptoms || 'Severe retrosternal chest pain radiating to left shoulder, breathlessness, profuse sweating.',
    severity: presetScenario?.severity || 'Critical'
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedSuccess, setSubmittedSuccess] = useState(false);
  const [createdRequestId, setCreatedRequestId] = useState('');

  const commonSymptomChips = [
    "Severe Chest Pain",
    "Shortness of Breath",
    "Active Bleeding",
    "Unconscious / Fainting",
    "Head Injury / Trauma",
    "Severe Allergic Reaction",
    "Inability to Speak / Facial Droop",
    "Severe Burns"
  ];

  const handleChipClick = (chip) => {
    if (!formData.symptoms.includes(chip)) {
      setFormData(prev => ({
        ...prev,
        symptoms: prev.symptoms ? `${prev.symptoms}, ${chip}` : chip
      }));
    }
  };

  const handleApplyScenario = (scenario) => {
    setFormData({
      patientName: scenario.patientName,
      age: scenario.age,
      contactNumber: scenario.contactNumber,
      currentLocation: scenario.location,
      emergencyType: scenario.emergencyType,
      symptoms: scenario.symptoms,
      severity: scenario.severity
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Mock request ID generation
    const mockId = `EMG-2026-001`;
    setCreatedRequestId(mockId);

    // Short realistic simulation delay for UX
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmittedSuccess(true);

      setTimeout(() => {
        onSubmitEmergency({
          ...formData,
          requestId: mockId,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          status: "Emergency Request Created"
        });
      }, 1200);
    }, 700);
  };

  return (
    <div className="main-content">
      {/* Header breadcrumb */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button 
          onClick={onBack}
          className="btn btn-secondary"
          style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', gap: '6px' }}
        >
          <ArrowLeft size={16} />
          <span>Back to Dashboard</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Step 1 of 4:</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#dc2626' }}>Triage Dispatch Form</span>
        </div>
      </div>

      {/* Submission Success Modal Overlay */}
      {submittedSuccess && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.75)',
          backdropFilter: 'blur(5px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '20px',
            padding: '2.5rem 2rem',
            maxWidth: '480px',
            width: '100%',
            textAlign: 'center',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            border: '2px solid #a7f3d0'
          }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: '#ecfdf5',
              color: '#059669',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.25rem',
              boxShadow: '0 4px 12px rgba(5, 150, 105, 0.2)'
            }}>
              <CheckCircle2 size={36} strokeWidth={2.5} />
            </div>

            <h3 style={{ fontSize: '1.45rem', fontWeight: 900, color: '#0f172a', marginBottom: '0.5rem' }}>
              Emergency Request Created
            </h3>

            <p style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '1.25rem' }}>
              Your emergency signal has been received. Nearest hospitals are being ranked dynamically for immediate intake.
            </p>

            <div style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              padding: '0.85rem',
              marginBottom: '1.5rem',
              display: 'inline-block',
              minWidth: '220px'
            }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700 }}>
                Assigned Emergency ID
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#dc2626', letterSpacing: '0.05em', marginTop: '2px' }}>
                {createdRequestId}
              </div>
            </div>

            <div style={{ fontSize: '0.85rem', color: '#0284c7', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
              <span className="pulsing-dot" />
              <span>Redirecting to Hospital Recommendations...</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Request Form Container */}
      <div style={{ maxWidth: '820px', margin: '0 auto' }}>
        <div className="card" style={{ padding: '2rem' }}>
          {/* Form Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid #f1f5f9' }}>
            <div style={{
              background: 'linear-gradient(135deg, #dc2626, #b91c1c)',
              color: '#ffffff',
              padding: '12px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(220, 38, 38, 0.3)'
            }}>
              <ShieldAlert size={28} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 900, color: '#0f172a' }}>
                Request Emergency Assistance
              </h2>
              <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '2px' }}>
                Enter patient symptoms and triage metrics to automatically match specialized facilities and reserve emergency beds.
              </p>
            </div>
          </div>

          {/* Quick-Fill Scenarios Bar */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '10px',
            padding: '0.75rem 1rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px'
          }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Zap size={14} color="#d97706" /> Quick Autofill Preset:
            </span>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {quickScenarios.map((sc, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleApplyScenario(sc)}
                  className="btn btn-secondary"
                  style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', borderRadius: '6px' }}
                >
                  {sc.name}
                </button>
              ))}
            </div>
          </div>

          {/* Emergency Form */}
          <form onSubmit={handleSubmit}>
            {/* Row 1: Name & Age */}
            <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">
                  Patient Full Name <span style={{ color: '#dc2626' }}>*</span>
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    required
                    className="form-input"
                    value={formData.patientName}
                    onChange={(e) => setFormData({ ...formData, patientName: e.target.value })}
                    placeholder="e.g. Aarav Sharma"
                  />
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">
                  Age (Years) <span style={{ color: '#dc2626' }}>*</span>
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  max="125"
                  className="form-input"
                  value={formData.age}
                  onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                  placeholder="e.g. 29"
                />
              </div>
            </div>

            {/* Row 2: Contact & Location */}
            <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">
                  Contact Phone Number <span style={{ color: '#dc2626' }}>*</span>
                </label>
                <input
                  type="tel"
                  required
                  className="form-input"
                  value={formData.contactNumber}
                  onChange={(e) => setFormData({ ...formData, contactNumber: e.target.value })}
                  placeholder="+91 98765 43210"
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">
                  Current Location <span style={{ color: '#dc2626' }}>*</span>
                </label>
                <input
                  type="text"
                  required
                  className="form-input"
                  value={formData.currentLocation}
                  onChange={(e) => setFormData({ ...formData, currentLocation: e.target.value })}
                  placeholder="e.g. Rajpur Road, Dehradun, Uttarakhand"
                />
              </div>
            </div>

            {/* Row 3: Emergency Type */}
            <div className="form-group">
              <label className="form-label">
                Emergency Category <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '10px' }}>
                {[
                  "Accident",
                  "Cardiac Emergency",
                  "Breathing Problem",
                  "Injury",
                  "Other"
                ].map((type) => {
                  const isSelected = formData.emergencyType === type;
                  return (
                    <div
                      key={type}
                      onClick={() => setFormData({ ...formData, emergencyType: type })}
                      style={{
                        padding: '0.75rem 1rem',
                        borderRadius: '10px',
                        border: `2px solid ${isSelected ? '#dc2626' : '#e2e8f0'}`,
                        background: isSelected ? '#fef2f2' : '#ffffff',
                        cursor: 'pointer',
                        textAlign: 'center',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: '0.85rem', color: isSelected ? '#b91c1c' : '#334155' }}>
                        {type}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Row 4: Severity Selection */}
            <div className="form-group">
              <label className="form-label">
                Clinical Severity Level <span style={{ color: '#dc2626' }}>*</span>
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                {severityLevels.map((sev) => {
                  const isSelected = formData.severity === sev.level;
                  return (
                    <div
                      key={sev.level}
                      onClick={() => setFormData({ ...formData, severity: sev.level })}
                      style={{
                        border: `2px solid ${isSelected ? sev.color : '#e2e8f0'}`,
                        background: isSelected ? (sev.level === 'Critical' ? '#fee2e2' : sev.level === 'High' ? '#ffedd5' : '#fef9c3') : '#ffffff',
                        padding: '1rem',
                        borderRadius: '12px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 800, fontSize: '1rem', color: sev.color }}>
                          {sev.level}
                        </span>
                        {isSelected && <span style={{ fontSize: '1.1rem' }}>✓</span>}
                      </div>
                      <p style={{ fontSize: '0.725rem', color: '#64748b', lineHeight: 1.35 }}>
                        {sev.description}
                      </p>
                      <div style={{ marginTop: '6px', fontSize: '0.7rem', fontWeight: 700, color: '#334155' }}>
                        Dispatch Goal: {sev.etaTolerance}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Row 5: Symptoms & Description */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.45rem' }}>
                <label className="form-label" style={{ marginBottom: 0 }}>
                  Observed Symptoms & Medical Details <span style={{ color: '#dc2626' }}>*</span>
                </label>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Click chips to append:
                </span>
              </div>

              {/* Quick symptom tags */}
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
                {commonSymptomChips.map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleChipClick(chip)}
                    style={{
                      background: '#f1f5f9',
                      border: '1px solid #cbd5e1',
                      borderRadius: '999px',
                      padding: '3px 8px',
                      fontSize: '0.725rem',
                      color: '#334155',
                      cursor: 'pointer'
                    }}
                  >
                    + {chip}
                  </button>
                ))}
              </div>

              <textarea
                required
                className="form-textarea"
                rows={3}
                value={formData.symptoms}
                onChange={(e) => setFormData({ ...formData, symptoms: e.target.value })}
                placeholder="Describe current symptoms, consciousness, bleeding, pulse sensation..."
              />
            </div>

            {/* Notice */}
            <div style={{
              background: '#eff6ff',
              border: '1px solid #bfdbfe',
              borderRadius: '10px',
              padding: '0.85rem 1rem',
              marginBottom: '1.75rem',
              fontSize: '0.825rem',
              color: '#1e40af',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <Sparkles size={18} color="#2563eb" flexShrink={0} />
              <span>
                <strong>SirenSync Phase 2 Notice:</strong> Form submission will store local mock telemetry and immediately score regional hospitals without external API dependencies.
              </span>
            </div>

            {/* Submit Action */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '1rem' }}>
              <button
                type="button"
                onClick={onBack}
                className="btn btn-secondary"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn btn-primary"
                style={{ padding: '0.85rem 2rem', fontSize: '1rem', fontWeight: 800 }}
              >
                {isSubmitting ? (
                  <>
                    <span className="pulsing-dot" />
                    <span>Processing Triage...</span>
                  </>
                ) : (
                  <>
                    <span>Submit & Find Hospitals</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
