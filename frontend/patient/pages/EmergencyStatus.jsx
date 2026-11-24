import React, { useState, useEffect } from 'react';
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
  Sparkles,
  Lock,
  RefreshCw
} from 'lucide-react';
import Timeline from '../components/Timeline';
import MockMap from '../components/MockMap';
import emergencyService from '../services/emergencyService';

export default function EmergencyStatus({
  activeEmergency,
  onBackToDashboard,
  onBackToHospitals
}) {
  const hospital = activeEmergency?.selectedHospital;
  const emergencyId = activeEmergency?.emergencyId || activeEmergency?.requestId || activeEmergency?.emergency_id || 'EMG-ACTIVE';
  const reservation = hospital?.reservation || activeEmergency?.reservation;

  const [liveEmergency, setLiveEmergency] = useState(null);
  const [trackingSnapshot, setTrackingSnapshot] = useState(null);
  const [trackingPending, setTrackingPending] = useState(true);
  const [trafficRoute, setTrafficRoute] = useState(null);

  // Keep patient status synchronized with the same emergency ID used by
  // reservation, ambulance dispatch, hospital queue and driver telemetry.
  useEffect(() => {
    if (!emergencyId || emergencyId === 'EMG-ACTIVE') return undefined;
    let isMounted = true;
    let pollTimer = null;
    let socket = null;

    const refresh = async () => {
      try {
        const snapshot = await emergencyService.getTrackingSnapshot(emergencyId);
        if (isMounted && snapshot?.emergencyId === emergencyId) {
          setTrackingSnapshot(snapshot);
          setTrackingPending(false);
        }
      } catch (err) {
        // A 404 means dispatch is still pending. Keep retrying without
        // clearing a previously received snapshot during transient failures.
        if (isMounted) setTrackingPending(false);
      }
      try {
        const data = await emergencyService.getEmergency(emergencyId);
        if (isMounted && data) setLiveEmergency(data);
      } catch (err) {
        if (isMounted) console.warn('Emergency status refresh:', err);
      }
    };

    refresh();
    pollTimer = window.setInterval(refresh, 2500);

    // WebSocket gives immediate updates; polling remains as reconnect fallback.
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/tracking/ws`);
      socket.onopen = () => socket?.send(JSON.stringify({ action: 'subscribe', emergency_id: emergencyId }));
      socket.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const message = JSON.parse(event.data);
          const payload = message?.payload;
          if (message.type === 'SNAPSHOT' && payload?.emergencyId === emergencyId) {
            setTrackingSnapshot(payload);
            setTrackingPending(false);
          } else if (payload?.emergencyId === emergencyId || payload?.emergencyId === undefined) {
            setTrackingSnapshot((previous) => {
              if (!previous) return previous;
              if (message.type === 'LOCATION_UPDATE') {
                return { ...previous, currentLocation: { latitude: payload.latitude, longitude: payload.longitude, address: payload.address }, routeProgress: Number.isFinite(payload.routeProgress) ? payload.routeProgress : previous.routeProgress, status: payload.status || previous.status, isSimulated: payload.isSimulated, timestamp: payload.timestamp };
              }
              if (message.type === 'ROUTE_PROGRESS_UPDATE') return { ...previous, routeProgress: payload.routeProgress, isSimulated: payload.isSimulated, timestamp: payload.timestamp };
              if (message.type === 'STATUS_CHANGE') return { ...previous, status: payload.status, timestamp: payload.timestamp };
              if (message.type === 'AMBULANCE_DISPATCHED') return { ...previous, ...payload };
              return previous;
            });
          }
        } catch (err) {
          console.warn('Unable to parse tracking event:', err);
        }
      };
    } catch (err) {
      console.warn('Tracking WebSocket unavailable; polling remains active.', err);
    }

    return () => {
      isMounted = false;
      if (pollTimer) window.clearInterval(pollTimer);
      if (socket) socket.close();
    };
  }, [emergencyId]);

  useEffect(() => {
    const ambulanceId = trackingSnapshot?.ambulanceId;
    if (!ambulanceId) { setTrafficRoute(null); return undefined; }
    let active = true;
    const refreshRoute = async () => {
      try {
        const route = await emergencyService.getAmbulanceRoute(ambulanceId);
        if (active) setTrafficRoute(route);
      } catch (err) {
        if (active) setTrafficRoute(null);
      }
    };
    refreshRoute();
    const timer = window.setInterval(refreshRoute, 60000);
    return () => { active = false; window.clearInterval(timer); };
  }, [trackingSnapshot?.ambulanceId, trackingSnapshot?.destinationHospitalId]);

  const ambulanceStatus = trackingSnapshot?.status || null;
  const timelineSteps = [
    { id: 1, title: 'Emergency Request Created', status: 'completed', description: 'Patient emergency intake was saved to the shared operational database.' },
    { id: 2, title: 'Hospitals Ranked', status: 'completed', description: 'Hospitals were evaluated against distance, capabilities, traffic and bed availability.' },
    { id: 3, title: 'Hospital Selected & Bed Reserved', status: 'completed', description: 'The selected hospital and bed reservation are recorded for this emergency.' },
    { id: 4, title: 'Ambulance Assigned', status: !trackingSnapshot ? 'active' : (ambulanceStatus === 'ASSIGNED' ? 'active' : 'completed'), description: trackingSnapshot ? `${trackingSnapshot.vehicleNumber} assigned to this emergency.` : 'The dispatch coordinator is matching an eligible available ambulance.' },
    { id: 5, title: 'Ambulance En Route to Pickup', status: ['EN_ROUTE_PICKUP', 'PATIENT_ONBOARD', 'EN_ROUTE_HOSPITAL', 'ARRIVED'].includes(ambulanceStatus) ? (ambulanceStatus === 'EN_ROUTE_PICKUP' ? 'active' : 'completed') : 'pending', description: 'Device GPS updates are synchronized with the hospital queue and patient tracker.' },
    { id: 6, title: 'Patient Onboard / En Route to Hospital', status: ['PATIENT_ONBOARD', 'EN_ROUTE_HOSPITAL'].includes(ambulanceStatus) ? 'active' : (ambulanceStatus === 'ARRIVED' ? 'completed' : 'pending'), description: 'Ambulance journey progress is derived from GPS telemetry, not manual progress entry.' },
    { id: 7, title: 'Arrived at Hospital', status: ambulanceStatus === 'ARRIVED' ? 'completed' : 'pending', description: 'Arrival is reflected when the ambulance lifecycle reaches the destination.' },
  ];

  const hospitalName = hospital?.name || hospital?.coordinatingHospital?.name || "Selected Hospital";
  const hospitalAddress = hospital?.location?.address || hospital?.address || "Emergency Medical Corridor";
  const contactNumber = hospital?.contactNumber || hospital?.coordinatingHospital?.contactNumber || "+91 80 2502 4444";
  const distanceKm = hospital?.breakdown?.distanceKm !== undefined ? Number(hospital.breakdown.distanceKm).toFixed(1) : (hospital?.distanceKm || '3.5');
  const etaMinutes = hospital?.etaMinutes || Math.max(3, Math.round(Number(distanceKm) * 2.5));

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
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Emergency progress:</span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#059669' }}>Automatically synchronized</span>
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
              Emergency ID: {emergencyId}
            </h1>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="badge badge-critical" style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
              {activeEmergency?.severity || activeEmergency?.triagePriority || 'P1_CRITICAL'}
            </span>
            <span className="badge badge-info" style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
              {activeEmergency?.emergencyType || 'CARDIAC_ARREST'}
            </span>
          </div>
        </div>

        {/* 3 Key Status Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
          {/* Selected Hospital */}
          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, letterSpacing: '0.03em' }}>
              Receiving Emergency Facility
            </div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Building2 size={20} color="#0284c7" />
              <span>{hospitalName}</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px' }}>
              {hospitalAddress}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#0284c7', marginTop: '6px', fontWeight: 600 }}>
              Hotline: {contactNumber}
            </div>
          </div>

          {/* Current Status */}
          <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#065f46', fontWeight: 700, letterSpacing: '0.03em' }}>
              Bed & Dispatch Status
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#065f46', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lock size={18} color="#059669" />
              <span>Bed Reserved (CAS Lock)</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#047857', marginTop: '4px' }}>
              Token: <strong>{reservation?.reservationId || reservation?.reservation_id || 'CONFIRMED'}</strong>
            </div>
          </div>

          {/* Estimated Arrival Time */}
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#991b1b', fontWeight: 700, letterSpacing: '0.03em' }}>
              Estimated Transit ETA
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#dc2626', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={20} color="#dc2626" />
              <span>{trafficRoute?.trafficAware ? `${Math.max(1, Math.round(trafficRoute.durationSeconds / 60))} Minutes` : `${etaMinutes} Minutes`}</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#b91c1c', marginTop: '4px' }}>
              {trafficRoute?.trafficAware ? `Live traffic route • ${(Number(trafficRoute.distanceMeters || 0) / 1000).toFixed(1)} km` : `Initial estimate: ${distanceKm} km • live traffic API not configured`}
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
              <strong>Receiving Hospital Emergency Desk:</strong> Emergency bed atomically locked. Triage queue updated in real-time.
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
              Emergency timeline
            </span>
          </div>

          {/* Timeline Component */}
          <Timeline steps={timelineSteps} />
        </div>

        {/* Right Column: Ambulance Unit & Live Corridor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Ambulance Telemetry Card */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Truck size={20} color="#0284c7" />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0f172a' }}>Assigned Ambulance Unit</h3>
              </div>
              <span className={`badge ${trackingSnapshot ? 'badge-success' : 'badge-info'}`}>
                {trackingSnapshot ? (trackingSnapshot.isSimulated ? 'Simulation Telemetry' : 'Live Telemetry') : 'Awaiting Dispatch'}
              </span>
            </div>

            {trackingSnapshot ? (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Vehicle Number</span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#0f172a' }}>{trackingSnapshot.vehicleNumber}</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{trackingSnapshot.ambulanceType}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Assigned Driver</span>
                    <div style={{ fontSize: '1rem', fontWeight: 800, color: '#0f172a' }}>{trackingSnapshot.driverName}</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{trackingSnapshot.status.replaceAll('_', ' ')}</div>
                  </div>
                </div>
                <div style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>Ambulance Location</div>
                  <div style={{ fontSize: '0.85rem', color: '#334155', marginTop: '4px' }}>
                    {trackingSnapshot.currentLocation?.address || `${Number(trackingSnapshot.currentLocation?.latitude).toFixed(5)}, ${Number(trackingSnapshot.currentLocation?.longitude).toFixed(5)}`}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#0369a1', fontWeight: 700, marginTop: '6px' }}>
                    GPS route progress: {Number(trackingSnapshot.routeProgress).toFixed(1)}%
                  </div>
                  <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '999px', overflow: 'hidden', marginTop: '8px' }}>
                    <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, Number(trackingSnapshot.routeProgress) || 0))}%`, background: '#0284c7', transition: 'width 500ms ease' }} />
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '5px' }}>
                    Last update: {trackingSnapshot.timestamp ? new Date(trackingSnapshot.timestamp).toLocaleTimeString() : 'Receiving telemetry'}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                  <span style={{ color: '#64748b' }}>Driver contact:</span>
                  <a href={`tel:${trackingSnapshot.driverContact}`} style={{ color: '#dc2626', fontWeight: 800, textDecoration: 'none' }}>
                    <Phone size={14} style={{ display: 'inline', marginRight: 4 }} />{trackingSnapshot.driverContact}
                  </a>
                </div>
              </>
            ) : (
              <div style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: 1.6 }}>
                {trackingPending ? 'Checking ambulance dispatch status…' : (liveEmergency?.dispatchStatus === 'AMBULANCE_PENDING' ? 'Bed reservation confirmed. Dispatch coordination is retrying. This panel updates automatically when an eligible ambulance is assigned.' : 'The bed reservation is confirmed. Waiting for the ambulance assignment update. This panel refreshes automatically.')}
              </div>
            )}
          </div>

          {/* Route Map Card */}
          <div className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Navigation size={16} color="#0284c7" />
                Live Corridor Vector
              </h4>
              <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: 600 }}>
                {trackingSnapshot?.isSimulated ? 'Simulated Telemetry' : (trafficRoute?.trafficAware ? 'Live GPS + Traffic' : 'Live GPS • Traffic API needed')}
              </span>
            </div>

            <MockMap
              selectedHospitalId={hospital?.id || "hosp-max-ddn"}
              patientLocation={{ address: activeEmergency?.currentLocation || "Rajpur Road, Dehradun" }}
              ambulanceLocation={trackingSnapshot?.currentLocation || null}
              selectedHospital={hospital}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
