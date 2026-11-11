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
  Phone,
  CheckCircle,
  AlertTriangle
} from 'lucide-react';

export default function HospitalCard({ 
  hospital, 
  isSelected, 
  onSelectHospital 
}) {
  const getTrafficBadge = (level) => {
    switch (level) {
      case 'low':
        return {
          bg: '#ecfdf5',
          border: '#a7f3d0',
          text: '#065f46',
          label: 'Low Traffic (Fastest Flow)'
        };
      case 'moderate':
        return {
          bg: '#fefce8',
          border: '#fef08a',
          text: '#854d0e',
          label: 'Moderate Traffic'
        };
      case 'high':
        return {
          bg: '#fef2f2',
          border: '#fecaca',
          text: '#991b1b',
          label: 'Heavy Traffic Congestion'
        };
      default:
        return {
          bg: '#f1f5f9',
          border: '#e2e8f0',
          text: '#475569',
          label: hospital.trafficCondition
        };
    }
  };

  const trafficInfo = getTrafficBadge(hospital.trafficLevel);

  return (
    <div className={`hospital-card ${hospital.isRecommended ? 'recommended-card' : ''}`} style={{
      borderColor: isSelected ? '#0284c7' : undefined,
      boxShadow: isSelected ? '0 0 0 2px #0284c7, 0 10px 15px -3px rgba(0,0,0,0.1)' : undefined
    }}>
      {hospital.isRecommended && (
        <div className="recommended-ribbon">
          <Sparkles size={13} />
          Recommended
        </div>
      )}

      {/* Top Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a', lineHeight: 1.3 }}>
              {hospital.name}
            </h3>
            <p style={{ fontSize: '0.825rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '3px' }}>
              <MapPin size={14} color="#94a3b8" />
              {hospital.address}
            </p>
          </div>

          {/* AI Score Badge */}
          <div style={{
            background: hospital.isRecommended ? '#fef3c7' : '#f1f5f9',
            border: `1px solid ${hospital.isRecommended ? '#fde68a' : '#e2e8f0'}`,
            borderRadius: '12px',
            padding: '6px 12px',
            textAlign: 'center',
            flexShrink: 0
          }}>
            <div style={{ fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', color: hospital.isRecommended ? '#b45309' : '#64748b', letterSpacing: '0.04em' }}>
              Match Score
            </div>
            <div style={{ fontSize: '1.35rem', fontWeight: 900, color: hospital.isRecommended ? '#92400e' : '#0f172a' }}>
              {hospital.recommendationScore}
              <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#94a3b8' }}>/100</span>
            </div>
          </div>
        </div>

        {/* Emergency Specialization */}
        <div style={{
          background: '#f8fafc',
          padding: '8px 12px',
          borderRadius: '8px',
          margin: '0.75rem 0',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.03em' }}>
            Emergency Specialization
          </div>
          <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0284c7', marginTop: '2px' }}>
            {hospital.specialization}
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
              {hospital.distanceKm} km
            </div>
          </div>

          {/* ETA */}
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '8px 10px' }}>
            <div style={{ fontSize: '0.7rem', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
              <Clock size={12} /> ETA
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#dc2626', marginTop: '2px' }}>
              {hospital.etaMinutes} min
            </div>
          </div>

          {/* Beds */}
          <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '8px', padding: '8px 10px' }}>
            <div style={{ fontSize: '0.7rem', color: '#065f46', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
              <Bed size={12} /> Beds
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#059669', marginTop: '2px' }}>
              {hospital.availableBeds.icu} ICU <span style={{ fontSize: '0.7rem', fontWeight: 500, color: '#64748b' }}>({hospital.availableBeds.emergency} ER)</span>
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
            <span>Traffic Condition: <strong>{hospital.trafficCondition}</strong></span>
            <div style={{ fontSize: '0.725rem', fontWeight: 400, opacity: 0.9 }}>
              {hospital.trafficRouteDetail}
            </div>
          </div>
        </div>

        {/* Recommendation explanation */}
        {hospital.recommendationReason && (
          <p style={{ fontSize: '0.775rem', color: '#475569', marginTop: '0.65rem', fontStyle: 'italic', display: 'flex', alignItems: 'flex-start', gap: '4px' }}>
            <span style={{ color: '#0284c7', fontWeight: 700 }}>•</span>
            {hospital.recommendationReason}
          </p>
        )}
      </div>

      {/* Select Hospital Action */}
      <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '1rem', marginTop: '0.5rem' }}>
        <button
          onClick={() => onSelectHospital(hospital)}
          className={`btn ${isSelected ? 'btn-medical' : hospital.isRecommended ? 'btn-primary' : 'btn-secondary'}`}
          style={{ width: '100%', padding: '0.75rem', fontWeight: 700, fontSize: '0.95rem' }}
        >
          {isSelected ? (
            <>
              <CheckCircle size={18} />
              Hospital Selected
            </>
          ) : (
            <>
              <span>Select Hospital</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
