import React from 'react';
import {
  Building2,
  MapPin,
  Clock,
  Bed,
  Car,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Activity
} from 'lucide-react';

export default function HospitalCard({
  hospital,
  isSelected,
  onSelectHospital,
  isSelecting = false
}) {
  const hospitalId = hospital.hospitalId || hospital.id;
  const hospitalName = hospital.name;
  const hospitalAddress = hospital.location?.address || hospital.address || 'Emergency Medical Corridor';

  // Real composite score is 0.0 - 1.0; legacy mock was 0 - 100
  const matchScore = hospital.compositeScore !== undefined
    ? Math.round(hospital.compositeScore * 100)
    : (hospital.recommendationScore || 85);

  const isRecommended = hospital.rank === 1 || hospital.isRecommended;
  const isEligible = hospital.isEligible !== false;

  const distanceKm = hospital.breakdown?.distanceKm !== undefined
    ? Number(hospital.breakdown.distanceKm).toFixed(1)
    : (hospital.distanceKm || '3.5');

  // Traffic & ETA calculation
  const trafficFactor = hospital.breakdown?.trafficCongestionFactor || 1.1;
  const etaMinutes = hospital.etaMinutes || Math.max(3, Math.round(Number(distanceKm) * 2.5 * trafficFactor));

  const getTrafficInfo = () => {
    if (hospital.breakdown) {
      const factor = hospital.breakdown.trafficCongestionFactor;
      if (factor > 1.35) {
        return {
          bg: '#fef2f2',
          border: '#fecaca',
          text: '#991b1b',
          label: `Congested (${factor.toFixed(2)}x factor)`
        };
      }
      if (factor > 1.1) {
        return {
          bg: '#fefce8',
          border: '#fef08a',
          text: '#854d0e',
          label: `Moderate Traffic (${factor.toFixed(2)}x factor)`
        };
      }
      return {
        bg: '#ecfdf5',
        border: '#a7f3d0',
        text: '#065f46',
        label: `Clear Corridor (${factor.toFixed(2)}x factor)`
      };
    }

    // Fallback legacy
    switch (hospital.trafficLevel) {
      case 'low':
        return { bg: '#ecfdf5', border: '#a7f3d0', text: '#065f46', label: 'Low Traffic' };
      case 'high':
        return { bg: '#fef2f2', border: '#fecaca', text: '#991b1b', label: 'Heavy Traffic Congestion' };
      default:
        return { bg: '#fefce8', border: '#fef08a', text: '#854d0e', label: hospital.trafficCondition || 'Moderate Traffic' };
    }
  };

  const trafficInfo = getTrafficInfo();

  // Bed counts
  const availableBedsCount = hospital.breakdown?.availableBedsCount !== undefined
    ? hospital.breakdown.availableBedsCount
    : (hospital.availableBeds?.icu ? hospital.availableBeds.icu + hospital.availableBeds.emergency : 4);

  const icuAvailable = hospital.bedSummary?.ICU?.available ?? hospital.availableBeds?.icu ?? 2;
  const erAvailable = hospital.bedSummary?.EMERGENCY?.available ?? hospital.availableBeds?.emergency ?? 2;

  // Capabilities
  const matchedCaps = hospital.breakdown?.matchedCapabilities || hospital.specializationsList || [];
  const explanation = hospital.breakdown?.explanation || hospital.recommendationReason;

  return (
    <div className={`hospital-card ${isRecommended ? 'recommended-card' : ''}`} style={{
      borderColor: isSelected ? '#0284c7' : undefined,
      boxShadow: isSelected ? '0 0 0 2px #0284c7, 0 10px 15px -3px rgba(0,0,0,0.1)' : undefined,
      opacity: !isEligible ? 0.75 : 1
    }}>
      {isRecommended && (
        <div className="recommended-ribbon">
          <Sparkles size={13} />
          AI Recommended
        </div>
      )}

      {/* Top Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a', lineHeight: 1.3 }}>
              {hospitalName}
            </h3>
            <p style={{ fontSize: '0.825rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '3px' }}>
              <MapPin size={14} color="#94a3b8" />
              {hospitalAddress}
            </p>
          </div>

          {/* AI Score Badge */}
          <div style={{
            background: isRecommended ? '#fef3c7' : '#f1f5f9',
            border: `1px solid ${isRecommended ? '#fde68a' : '#e2e8f0'}`,
            borderRadius: '12px',
            padding: '6px 12px',
            textAlign: 'center',
            flexShrink: 0
          }}>
            <div style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', color: isRecommended ? '#b45309' : '#64748b', letterSpacing: '0.04em' }}>
              Match Score
            </div>
            <div style={{ fontSize: '1.35rem', fontWeight: 900, color: isRecommended ? '#92400e' : '#0f172a' }}>
              {matchScore}
              <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#94a3b8' }}>/100</span>
            </div>
          </div>
        </div>

        {/* Matched Capabilities / Specialization */}
        <div style={{
          background: '#f8fafc',
          padding: '8px 12px',
          borderRadius: '8px',
          margin: '0.75rem 0',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.03em' }}>
            Verified Capabilities & Specialization
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '4px' }}>
            {matchedCaps.length > 0 ? (
              matchedCaps.map((cap, i) => (
                <span key={i} style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: '#e0f2fe',
                  color: '#0369a1',
                  padding: '2px 8px',
                  borderRadius: '4px'
                }}>
                  {cap}
                </span>
              ))
            ) : (
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0284c7' }}>
                {hospital.specialization || 'Comprehensive Emergency Care'}
              </span>
            )}
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          margin: '0.75rem 0'
        }}>
          {/* Distance */}
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '8px 10px' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '3px' }}>
              <MapPin size={12} /> Distance
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0f172a', marginTop: '2px' }}>
              {distanceKm} km
            </div>
          </div>

          {/* ETA */}
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '8px 10px' }}>
            <div style={{ fontSize: '0.7rem', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
              <Clock size={12} /> ETA
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#dc2626', marginTop: '2px' }}>
              {etaMinutes} min
            </div>
          </div>

          {/* Beds */}
          <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '8px', padding: '8px 10px' }}>
            <div style={{ fontSize: '0.7rem', color: '#065f46', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
              <Bed size={12} /> Avail. Beds
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#059669', marginTop: '2px' }}>
              {availableBedsCount} <span style={{ fontSize: '0.7rem', fontWeight: 500, color: '#64748b' }}>({icuAvailable} ICU / {erAvailable} ER)</span>
            </div>
          </div>
        </div>

        {/* Traffic Condition Banner */}
        <div style={{
          background: trafficInfo.bg,
          border: `1px solid ${trafficInfo.border}`,
          borderRadius: '8px',
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.8rem',
          color: trafficInfo.text,
          fontWeight: 600
        }}>
          <Car size={15} />
          <div>
            <span>Traffic Condition: <strong>{trafficInfo.label}</strong></span>
          </div>
        </div>

        {/* Recommendation explanation */}
        {explanation && (
          <p style={{ fontSize: '0.775rem', color: '#475569', marginTop: '0.65rem', fontStyle: 'italic', display: 'flex', alignItems: 'flex-start', gap: '4px' }}>
            <span style={{ color: '#0284c7', fontWeight: 700 }}>•</span>
            {explanation}
          </p>
        )}
      </div>

      {/* Select Hospital Action */}
      <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '1rem', marginTop: '0.5rem' }}>
        <button
          onClick={() => onSelectHospital(hospital)}
          disabled={!isEligible || isSelecting}
          className={`btn ${isSelected ? 'btn-medical' : isRecommended ? 'btn-primary' : 'btn-secondary'}`}
          style={{ width: '100%', padding: '0.75rem', fontWeight: 700, fontSize: '0.95rem' }}
        >
          {isSelecting ? (
            <>
              <Loader2 size={18} className="spinner-icon" />
              <span>Reserving Bed & Coordinating...</span>
            </>
          ) : isSelected ? (
            <>
              <CheckCircle size={18} />
              <span>Hospital Selected</span>
            </>
          ) : !isEligible ? (
            <span>No Compatible Beds</span>
          ) : (
            <>
              <span>Select Hospital & Reserve Bed</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
