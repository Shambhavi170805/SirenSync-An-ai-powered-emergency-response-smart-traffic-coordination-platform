import React, { useState } from 'react';
import { 
  Car, 
  HeartPulse, 
  Wind, 
  AlertCircle, 
  PlusCircle, 
  MapPin, 
  Navigation, 
  Phone, 
  User, 
  Users, 
  CheckCircle2, 
  XCircle, 
  HelpCircle, 
  ChevronDown, 
  ChevronUp, 
  ArrowRight,
  ShieldAlert,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { emergencyTypes, whoNeedsHelpOptions, patientConditionOptions } from '../data/mockData';

export default function QuickEmergencyForm({ 
  patientProfile, 
  onSubmitEmergency, 
  onCancel = null 
}) {
  // Form State
  const [location, setLocation] = useState(
    patientProfile?.currentLocation?.address || 'Rajpur Road, Dehradun, Uttarakhand'
  );
  const [locationStatus, setLocationStatus] = useState('idle'); // 'idle' | 'locating' | 'success' | 'error'
  const [locationError, setLocationError] = useState(null);

  const [category, setCategory] = useState('accident'); // default to 'accident' for emergency-first focus
  const [whoNeedsHelp, setWhoNeedsHelp] = useState('me'); // 'me' | 'someone_else'
  const [patientCondition, setPatientCondition] = useState('conscious'); // 'conscious' | 'unconscious' | 'not_sure'
  
  const [contactNumber, setContactNumber] = useState(
    patientProfile?.phone || '+91 98765 43210'
  );
  const [contactError, setContactError] = useState(null);

  const [showAdditionalInfo, setShowAdditionalInfo] = useState(false);
  const [additionalNotes, setAdditionalNotes] = useState('');
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdRequest, setCreatedRequest] = useState(null);

  // Common quick landmark suggestions for 1-tap entry in Dehradun
  const quickLandmarks = [
    "Rajpur Road, Dehradun",
    "Clock Tower Chowk",
    "Ballupur Chowk",
    "ISBT Dehradun"
  ];

  // Optional symptom chips
  const symptomChips = [
    "Active Bleeding",
    "Head Injury",
    "Fracture / Trauma",
    "Chest Pain",
    "Difficulty Breathing",
    "Vehicle Collision"
  ];

  // Browser Geolocation handler with graceful error handling
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus('error');
      setLocationError('Geolocation is not supported by your browser. Please type your location manually below.');
      return;
    }

    setLocationStatus('locating');
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude.toFixed(4);
        const lng = position.coords.longitude.toFixed(4);
        const detectedText = `GPS: Lat ${lat}° N, Lng ${lng}° E (Near Rajpur Road, Dehradun)`;
        setLocation(detectedText);
        setLocationStatus('success');
        setLocationError(null);
      },
      (error) => {
        setLocationStatus('error');
        if (error.code === 1) { // PERMISSION_DENIED
          setLocationError('Location permission was denied. Please enter your address or landmark manually below.');
        } else if (error.code === 2) { // POSITION_UNAVAILABLE
          setLocationError('GPS signal unavailable. Please type your address manually below.');
        } else if (error.code === 3) { // TIMEOUT
          setLocationError('Location request timed out. Please enter your location manually below.');
        } else {
          setLocationError('Could not detect location. Please type your address manually below.');
        }
      },
      {
        timeout: 10000,
        enableHighAccuracy: true
      }
    );
  };

  const toggleSymptom = (chip) => {
    if (selectedSymptoms.includes(chip)) {
      setSelectedSymptoms(selectedSymptoms.filter(s => s !== chip));
    } else {
      setSelectedSymptoms([...selectedSymptoms, chip]);
    }
  };

  const getCategoryIcon = (id) => {
    switch (id) {
      case 'accident': return <Car size={26} />;
      case 'medical': return <HeartPulse size={26} />;
      case 'breathing': return <Wind size={26} />;
      case 'unconscious': return <AlertCircle size={26} />;
      default: return <PlusCircle size={26} />;
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Validation 1: Location required
    if (!location || location.trim() === '') {
      setLocationError('Emergency location is required. Please enter an address or tap a landmark.');
      return;
    }

    // Validation 2: Phone format (minimum 10 digits)
    const digitsOnly = contactNumber.replace(/\D/g, '');
    if (digitsOnly.length < 10) {
      setContactError('Please enter a valid phone number (at least 10 digits).');
      return;
    }
    setContactError(null);

    setIsSubmitting(true);

    // Selected category object
    const selectedCatObj = emergencyTypes.find(t => t.id === category) || emergencyTypes[0];

    // Determine triage severity based on inputs
    let derivedSeverity = 'High';
    if (category === 'accident' || category === 'unconscious' || patientCondition === 'unconscious') {
      derivedSeverity = 'Critical';
    } else if (category === 'breathing') {
      derivedSeverity = 'Critical';
    } else if (category === 'other' && patientCondition === 'conscious') {
      derivedSeverity = 'Moderate';
    }

    // Compile symptoms string
    const combinedSymptoms = [
      ...selectedSymptoms,
      additionalNotes.trim()
    ].filter(Boolean).join(', ') || `${selectedCatObj.label} emergency reported.`;

    const mockId = `EMG-2026-001`;

    const requestPayload = {
      requestId: mockId,
      patientName: whoNeedsHelp === 'me' ? (patientProfile?.name || 'Aarav Sharma') : 'Injured Patient (Reported by Bystander)',
      age: patientProfile?.age || 29,
      contactNumber: contactNumber,
      currentLocation: location,
      emergencyType: selectedCatObj.label,
      emergencyCategoryId: category,
      whoNeedsHelp: whoNeedsHelp === 'me' ? 'Me' : 'Someone else',
      patientCondition: patientCondition === 'conscious' ? 'Conscious' : (patientCondition === 'unconscious' ? 'Unconscious' : 'Not sure'),
      symptoms: combinedSymptoms,
      severity: derivedSeverity,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      status: "Emergency Request Created"
    };

    // Realistic brief local transition simulation
    setTimeout(() => {
      setIsSubmitting(false);
      setCreatedRequest(requestPayload);

      // Brief confirmation view before advancing to hospital recommendations
      setTimeout(() => {
        onSubmitEmergency(requestPayload);
      }, 1400);
    }, 600);
  };

  return (
    <div className="quick-emergency-form-wrapper" id="emergency-form-section">
      {/* Success Confirmation Modal */}
      {createdRequest && (
        <div className="confirmation-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className="confirmation-modal-card">
            <div className="confirmation-icon-circle" aria-hidden="true">
              <CheckCircle2 size={40} strokeWidth={2.5} />
            </div>

            <h3 id="modal-title" className="confirmation-modal-title">
              Emergency Request Created
            </h3>

            <p className="confirmation-modal-subtitle">
              Your request has been logged. Preparing hospital recommendations matching your emergency.
            </p>

            <div className="confirmation-details-summary">
              <div className="summary-row">
                <span className="summary-label">Emergency ID:</span>
                <strong className="summary-id-badge">{createdRequest.requestId}</strong>
              </div>
              <div className="summary-row">
                <span className="summary-label">Emergency Type:</span>
                <strong className="summary-val">{createdRequest.emergencyType}</strong>
              </div>
              <div className="summary-row">
                <span className="summary-label">Location:</span>
                <span className="summary-val">{createdRequest.currentLocation}</span>
              </div>
              <div className="summary-row">
                <span className="summary-label">Patient Condition:</span>
                <span className="summary-val">{createdRequest.patientCondition}</span>
              </div>
            </div>

            <div className="confirmation-footer-note">
              <span className="pulsing-dot" aria-hidden="true" />
              <span>Redirecting to hospital options...</span>
            </div>

            <button
              type="button"
              className="btn btn-primary btn-modal-proceed"
              onClick={() => onSubmitEmergency(createdRequest)}
            >
              <span>View Recommended Hospitals</span>
              <ArrowRight size={18} aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {/* Main Streamlined Form */}
      <form onSubmit={handleSubmit} className="emergency-form-card" noValidate>
        {/* Form Title & Instruction */}
        <div className="form-header-bar">
          <div className="form-header-title-box">
            <ShieldAlert size={24} className="header-alert-icon" aria-hidden="true" />
            <div>
              <h2 className="form-main-heading">Emergency Assistance Request</h2>
              <p className="form-main-subheading">
                Complete these quick details to locate nearest trauma centers and emergency services.
              </p>
            </div>
          </div>
          {onCancel && (
            <button 
              type="button" 
              onClick={onCancel}
              className="btn btn-secondary btn-cancel-form"
            >
              Cancel
            </button>
          )}
        </div>

        {/* ========================================================
            1. EMERGENCY LOCATION
        ======================================================== */}
        <div className="form-field-group">
          <label htmlFor="emergency-location-input" className="field-label">
            1. Emergency Location <span className="required-star">*</span>
          </label>

          {/* Location Action & Detection Button */}
          <div className="location-action-row">
            <button
              type="button"
              onClick={handleDetectLocation}
              disabled={locationStatus === 'locating'}
              className={`btn-use-location ${locationStatus === 'success' ? 'location-btn-success' : ''}`}
              aria-label="Use device GPS location"
            >
              {locationStatus === 'locating' ? (
                <>
                  <Loader2 size={18} className="spinner-icon" aria-hidden="true" />
                  <span>Detecting GPS Location...</span>
                </>
              ) : (
                <>
                  <Navigation size={18} aria-hidden="true" />
                  <span>Use My Current Location</span>
                </>
              )}
            </button>

            {locationStatus === 'success' && (
              <span className="location-success-badge" role="status">
                <CheckCircle2 size={14} aria-hidden="true" />
                <span>GPS Location Detected</span>
              </span>
            )}
          </div>

          {/* Location Error Warning if Geolocation Fails */}
          {locationError && (
            <div className="location-error-alert" role="alert">
              <AlertTriangle size={16} aria-hidden="true" />
              <span>{locationError}</span>
            </div>
          )}

          {/* Manual Input Fallback */}
          <div className="location-input-wrapper">
            <MapPin size={18} className="input-pin-icon" aria-hidden="true" />
            <input
              id="emergency-location-input"
              type="text"
              required
              value={location}
              onChange={(e) => {
                setLocation(e.target.value);
                if (locationError) setLocationError(null);
              }}
              placeholder="Enter current road, landmark, or street in Dehradun..."
              className="location-text-input"
              aria-required="true"
            />
          </div>

          {/* Quick Landmark Chips for 1-Tap Mobile Selection */}
          <div className="quick-landmarks-row">
            <span className="landmarks-prompt">Quick tap nearby:</span>
            {quickLandmarks.map((lm, idx) => (
              <button
                key={idx}
                type="button"
                className={`landmark-chip ${location === lm ? 'active-landmark-chip' : ''}`}
                onClick={() => {
                  setLocation(lm);
                  setLocationError(null);
                }}
              >
                + {lm.split(',')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* ========================================================
            2. WHAT HAPPENED? (LARGE SELECTABLE CARDS)
        ======================================================== */}
        <div className="form-field-group">
          <label className="field-label">
            2. What Happened? <span className="required-star">*</span>
          </label>
          <p className="field-helper-text">Tap the card that best matches the situation:</p>

          <div className="category-cards-grid" role="radiogroup" aria-label="Emergency category">
            {emergencyTypes.map((type) => {
              const isSelected = category === type.id;
              return (
                <div
                  key={type.id}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                  onClick={() => setCategory(type.id)}
                  onKeyDown={(e) => (e.key === ' ' || e.key === 'Enter') && setCategory(type.id)}
                  className={`emergency-category-card ${isSelected ? 'category-card-selected' : ''}`}
                >
                  <div className="category-card-icon" aria-hidden="true">
                    {getCategoryIcon(type.id)}
                  </div>
                  <div className="category-card-content">
                    <div className="category-card-title">{type.label}</div>
                    <div className="category-card-desc">{type.desc}</div>
                  </div>
                  <div className="category-radio-indicator" aria-hidden="true">
                    {isSelected && <span className="radio-inner-dot" />}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ========================================================
            3. WHO NEEDS HELP? (LARGE SEGMENTED CARDS)
        ======================================================== */}
        <div className="form-field-group">
          <label className="field-label">
            3. Who Needs Help? <span className="required-star">*</span>
          </label>

          <div className="segmented-grid segmented-2" role="radiogroup" aria-label="Who needs help">
            {whoNeedsHelpOptions.map((opt) => {
              const isSelected = whoNeedsHelp === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => setWhoNeedsHelp(opt.id)}
                  className={`segmented-choice-btn ${isSelected ? 'segmented-selected' : ''}`}
                >
                  {opt.id === 'me' ? <User size={20} aria-hidden="true" /> : <Users size={20} aria-hidden="true" />}
                  <div>
                    <div className="segmented-title">{opt.label}</div>
                    <div className="segmented-subtext">{opt.sublabel}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* ========================================================
            4. PATIENT CONDITION
        ======================================================== */}
        <div className="form-field-group">
          <label className="field-label">
            4. Patient Condition <span className="required-star">*</span>
          </label>

          <div className="segmented-grid segmented-3" role="radiogroup" aria-label="Patient condition">
            {patientConditionOptions.map((opt) => {
              const isSelected = patientCondition === opt.id;
              let icon = <CheckCircle2 size={18} />;
              if (opt.id === 'unconscious') icon = <XCircle size={18} />;
              if (opt.id === 'not_sure') icon = <HelpCircle size={18} />;

              return (
                <button
                  key={opt.id}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => setPatientCondition(opt.id)}
                  className={`segmented-choice-btn condition-btn ${isSelected ? `condition-selected-${opt.id}` : ''}`}
                >
                  <div className="condition-icon-box" aria-hidden="true">
                    {icon}
                  </div>
                  <div>
                    <div className="segmented-title">{opt.label}</div>
                    <div className="segmented-subtext">{opt.desc}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* ========================================================
            5. CONTACT NUMBER
        ======================================================== */}
        <div className="form-field-group">
          <label htmlFor="emergency-phone-input" className="field-label">
            5. Contact Phone Number <span className="required-star">*</span>
          </label>
          <p className="field-helper-text">
            For ambulance paramedics and receiving emergency unit to coordinate transit.
          </p>

          <div className="contact-input-wrapper">
            <Phone size={18} className="input-phone-icon" aria-hidden="true" />
            <input
              id="emergency-phone-input"
              type="tel"
              required
              value={contactNumber}
              onChange={(e) => {
                setContactNumber(e.target.value);
                if (contactError) setContactError(null);
              }}
              placeholder="e.g. 98765 43210"
              className="contact-text-input"
              aria-required="true"
            />
          </div>

          {contactError && (
            <div className="field-error-message" role="alert">
              {contactError}
            </div>
          )}
        </div>

        {/* ========================================================
            6. ADDITIONAL INFORMATION (OPTIONAL & COLLAPSED BY DEFAULT)
        ======================================================== */}
        <div className="form-field-group optional-details-group">
          <button
            type="button"
            onClick={() => setShowAdditionalInfo(!showAdditionalInfo)}
            className="btn-toggle-optional"
            aria-expanded={showAdditionalInfo}
          >
            <span>
              {showAdditionalInfo ? '− Hide additional details' : '+ Add details (landmarks, vehicle type, symptoms) — Optional'}
            </span>
            {showAdditionalInfo ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
          </button>

          {showAdditionalInfo && (
            <div className="optional-details-panel">
              <label htmlFor="additional-notes-input" className="optional-notes-label">
                Tap symptom tags to add:
              </label>
              
              <div className="symptom-chips-row">
                {symptomChips.map((chip, idx) => {
                  const isChipActive = selectedSymptoms.includes(chip);
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleSymptom(chip)}
                      className={`symptom-chip ${isChipActive ? 'symptom-chip-active' : ''}`}
                    >
                      {isChipActive ? '✓ ' : '+ '} {chip}
                    </button>
                  );
                })}
              </div>

              <textarea
                id="additional-notes-input"
                rows={2}
                value={additionalNotes}
                onChange={(e) => setAdditionalNotes(e.target.value)}
                placeholder="Optional notes (e.g., Near petrol pump, 2 vehicles involved, bleeding from leg)..."
                className="optional-notes-textarea"
              />
            </div>
          )}
        </div>

        {/* Secondary Disclaimer & Safety Call */}
        <div className="emergency-disclaimer-card">
          <div className="disclaimer-text">
            <strong>Emergency Advisory:</strong> If you are unable to submit this form or network drops, call 
            <a href="tel:112" className="inline-call-link"> 112 directly</a>.
          </div>
        </div>

        {/* ========================================================
            D. STICKY SUBMIT BUTTON
        ======================================================== */}
        <div className="sticky-submit-container">
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-sticky-emergency-submit"
            aria-label="Send emergency request"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={24} className="spinner-icon" aria-hidden="true" />
                <span>Processing Emergency Request...</span>
              </>
            ) : (
              <>
                <ShieldAlert size={24} aria-hidden="true" />
                <span>SEND EMERGENCY REQUEST</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
