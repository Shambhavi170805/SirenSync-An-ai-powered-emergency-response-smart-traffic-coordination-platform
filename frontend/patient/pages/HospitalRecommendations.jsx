import React, { useState, useEffect } from 'react';
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
  Navigation,
  Loader2,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import HospitalCard from '../components/HospitalCard';
import MockMap from '../components/MockMap';
import { mockHospitals } from '../data/mockData';
import emergencyService from '../services/emergencyService';

export default function HospitalRecommendations({
  activeEmergency,
  onSelectHospital,
  onBackToRequest,
  onNavigate
}) {
  const [hospitals, setHospitals] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [rankingError, setRankingError] = useState(null);
  const [reservingHospitalId, setReservingHospitalId] = useState(null);
  const [reservationError, setReservationError] = useState(null);
  const [sortBy, setSortBy] = useState('score'); // 'score', 'eta', 'beds', 'distance'

  // Fetch live hospital rankings from backend
  const fetchRankings = async () => {
    setIsLoading(true);
    setRankingError(null);

    try {
      const emergencyId = activeEmergency?.emergencyId || activeEmergency?.requestId || 'EMG-PREVIEW';
      const patientLocation = {
        latitude: activeEmergency?.coordinates?.latitude || activeEmergency?.patientLocation?.latitude || 30.3255,
        longitude: activeEmergency?.coordinates?.longitude || activeEmergency?.patientLocation?.longitude || 78.0437,
        address: activeEmergency?.currentLocation || activeEmergency?.patientLocation?.address || 'Rajpur Road, Clock Tower, Dehradun'
      };

      const response = await emergencyService.rankHospitals({
        emergencyId,
        region: activeEmergency?.region || 'Dehradun',
        patientLocation,
        emergencyType: activeEmergency?.emergencyType || 'CARDIAC_ARREST',
        priority: activeEmergency?.triagePriority || activeEmergency?.priority || 'P1_CRITICAL',
        requiredBedType: activeEmergency?.requiredBedType || 'ICU',
        requiredCapabilities: activeEmergency?.requiredCapabilities || [],
        symptoms: activeEmergency?.symptoms || activeEmergency?.patientCondition || ''
      });

      if (response && response.rankedHospitals && response.rankedHospitals.length > 0) {
        setHospitals(response.rankedHospitals);
      } else {
        // Empty response from backend ranking
        setHospitals([]);
      }
    } catch (err) {
      console.error('Backend hospital ranking request failed:', err);
      setRankingError(err.message || 'Unable to connect to live hospital intelligence service.');
      setHospitals([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRankings();
  }, [activeEmergency?.emergencyId, activeEmergency?.requestId]);

  // Handle hospital selection and atomic bed reservation
  const handleSelectHospital = async (hospital) => {
    const emergencyId = activeEmergency?.emergencyId || activeEmergency?.requestId;
    const hospitalId = hospital.hospitalId || hospital.id;
    const requiredBedType = activeEmergency?.requiredBedType || 'ICU';

    if (!emergencyId) {
      setReservationError('No active emergency ID found. Please create an emergency request first.');
      return;
    }

    setReservingHospitalId(hospitalId);
    setReservationError(null);

    try {
      // Real CAS lock atomic reservation via backend
      const res = await emergencyService.selectHospital({
        emergencyId,
        hospitalId,
        requiredBedType
      });

      onSelectHospital({
        ...hospital,
        hospitalId,
        reservation: res.reservation,
        coordinatingHospital: res.hospital || hospital,
        updatedEmergency: res.emergency
      });
    } catch (err) {
      console.error('Failed to reserve bed at selected hospital:', err);
      setReservationError(err.message || 'Hospital bed reservation conflict. Please select another recommended facility.');
    } finally {
      setReservingHospitalId(null);
    }
  };

  // Sort ranked hospitals
  let sortedHospitals = [...hospitals];
  if (sortBy === 'score') {
    sortedHospitals.sort((a, b) => (b.compositeScore ?? b.recommendationScore ?? 0) - (a.compositeScore ?? a.recommendationScore ?? 0));
  } else if (sortBy === 'eta') {
    sortedHospitals.sort((a, b) => {
      const distA = a.breakdown?.distanceKm ?? a.distanceKm ?? 99;
      const distB = b.breakdown?.distanceKm ?? b.distanceKm ?? 99;
      return distA - distB;
    });
  } else if (sortBy === 'beds') {
    sortedHospitals.sort((a, b) => {
      const bedsA = a.breakdown?.availableBedsCount ?? a.availableBeds?.icu ?? 0;
      const bedsB = b.breakdown?.availableBedsCount ?? b.availableBeds?.icu ?? 0;
      return bedsB - bedsA;
    });
  } else if (sortBy === 'distance') {
    sortedHospitals.sort((a, b) => {
      const distA = a.breakdown?.distanceKm ?? a.distanceKm ?? 99;
      const distB = b.breakdown?.distanceKm ?? b.distanceKm ?? 99;
      return distA - distB;
    });
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '1.1rem', fontWeight: 900, color: '#0f172a' }}>
              Emergency ID: {activeEmergency?.emergencyId || activeEmergency?.requestId || 'EMG-ACTIVE'}
            </span>
            <span className={`badge ${activeEmergency?.severity === 'Critical' ? 'badge-critical' : 'badge-high'}`}>
              {activeEmergency?.severity || activeEmergency?.triagePriority || 'P1_CRITICAL'}
            </span>
            <span className="badge badge-info">
              {activeEmergency?.emergencyType || 'CARDIAC_ARREST'}
            </span>
            {activeEmergency?.attachmentsCount > 0 && (
              <span className="badge badge-success" style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                📎 {activeEmergency.attachmentsCount} {activeEmergency.attachmentsCount === 1 ? 'Report' : 'Reports'} Attached
              </span>
            )}
          </div>

          <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
            Patient: <strong>{activeEmergency?.patientName || 'Emergency Patient'}</strong> {activeEmergency?.patientCondition && <span>({activeEmergency.patientCondition})</span>} • Location: <strong>{activeEmergency?.currentLocation || activeEmergency?.patientLocation?.address || 'Dehradun'}</strong>
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

      {/* Reservation Error Banner (e.g., CAS concurrency conflict) */}
      {reservationError && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #ef4444',
          borderRadius: '12px',
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          color: '#991b1b'
        }} role="alert">
          <AlertTriangle size={24} style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>Bed Reservation Conflict</div>
            <div style={{ fontSize: '0.85rem', marginTop: '2px' }}>{reservationError}</div>
          </div>
        </div>
      )}

      {/* Ranking Error Banner */}
      {rankingError && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #ef4444',
          borderRadius: '12px',
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          color: '#991b1b'
        }} role="alert">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertTriangle size={24} style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>Hospital Intelligence Service Unavailable</div>
              <div style={{ fontSize: '0.85rem', marginTop: '2px' }}>{rankingError}</div>
            </div>
          </div>
          <button
            onClick={fetchRankings}
            className="btn btn-secondary"
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.85rem', gap: '6px' }}
          >
            <RefreshCw size={14} /> Retry Ranking
          </button>
        </div>
      )}

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
            4-Factor Hospital Rankings ({sortedHospitals.length} Evaluated)
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
              { id: 'score', label: 'Composite Score' },
              { id: 'eta', label: 'Distance / ETA' },
              { id: 'beds', label: 'Available Beds' }
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

      {/* Loading Spinner */}
      {isLoading ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem 1.5rem',
          background: '#ffffff',
          borderRadius: '16px',
          border: '1px solid #e2e8f0',
          marginBottom: '2rem'
        }}>
          <Loader2 size={36} className="spinner-icon" style={{ color: '#0284c7', margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>
            Evaluating Regional Hospital Capacities...
          </h3>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.35rem' }}>
            Applying 4-factor scoring: Distance (30%) + Bed Availability (30%) + Capability Match (25%) + Corridor Traffic (15%)
          </p>
        </div>
      ) : sortedHospitals.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem 1.5rem',
          background: '#ffffff',
          borderRadius: '16px',
          border: '1px solid #e2e8f0',
          marginBottom: '2rem'
        }}>
          <AlertTriangle size={36} style={{ color: '#f59e0b', margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a' }}>
            No Matching Hospitals in Radius
          </h3>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.35rem' }}>
            No hospitals found within the 30 km emergency radius matching required capabilities.
          </p>
          <button
            onClick={fetchRankings}
            className="btn btn-primary"
            style={{ marginTop: '1rem', padding: '0.5rem 1.25rem' }}
          >
            Retry Regional Scan
          </button>
        </div>
      ) : (
        /* Hospital Cards Grid */
        <div className="grid-2" style={{ marginBottom: '2rem' }}>
          {sortedHospitals.map((hospital) => {
            const hId = hospital.hospitalId || hospital.id;
            return (
              <HospitalCard
                key={hId}
                hospital={hospital}
                isSelected={activeEmergency?.selectedHospital?.hospitalId === hId || activeEmergency?.selectedHospital?.id === hId}
                onSelectHospital={handleSelectHospital}
                isSelecting={reservingHospitalId === hId}
              />
            );
          })}
        </div>
      )}

      {/* Map visualization of recommended facilities */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Navigation size={18} color="#0284c7" />
              Regional Corridor Map & Route Conditions
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
              Traffic conditions and emergency transit vectors across {activeEmergency?.region || 'Dehradun'} corridor
            </p>
          </div>
        </div>

        <MockMap
          selectedHospitalId={activeEmergency?.selectedHospital?.hospitalId || activeEmergency?.selectedHospital?.id || "hosp-max-ddn"}
          patientLocation={{ address: activeEmergency?.currentLocation || "Rajpur Road, Clock Tower, Dehradun" }}
        />
      </div>
    </div>
  );
}
