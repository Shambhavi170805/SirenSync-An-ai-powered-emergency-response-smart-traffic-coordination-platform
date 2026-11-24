import React, { useState } from 'react';
import {
  MapPin,
  Navigation2,
  Layers,
  Building2,
  ShieldCheck,
  Flame,
  Compass,
  AlertCircle
} from 'lucide-react';
import { mockHospitals } from '../data/mockData';

export default function MockMap({
  selectedHospitalId = null,
  onSelectHospital = null,
  patientLocation = { city: "Dehradun", state: "Uttarakhand", address: "Rajpur Road, Dehradun" },
  ambulanceLocation = null,
  selectedHospital = null
}) {
  const [showTraffic, setShowTraffic] = useState(true);
  const [showRadius, setShowRadius] = useState(true);

  // Coordinates for mock SVG canvas (width 800, height 400)
  // Patient is at center (x: 390, y: 220)
  const patientCoords = { x: 390, y: 220 };

  const selectedHospitalLat = Number(selectedHospital?.latitude ?? selectedHospital?.location?.latitude);
  const selectedHospitalLng = Number(selectedHospital?.longitude ?? selectedHospital?.location?.longitude);
  const hasSelectedHospitalCoords = Number.isFinite(selectedHospitalLat) && Number.isFinite(selectedHospitalLng);
  const hospitalPins = hasSelectedHospitalCoords ? [{
    id: selectedHospitalId || selectedHospital?.id,
    x: Math.max(40, Math.min(760, 390 + (selectedHospitalLng - 78.0437) * 2800)),
    y: Math.max(35, Math.min(365, 220 - (selectedHospitalLat - 30.3255) * 2800)),
    name: selectedHospital?.name || 'Selected Hospital', eta: '', dist: '', color: '#0284c7'
  }] : [];

  const selectedPin = hospitalPins[0] || null;
  const ambLat = Number(ambulanceLocation?.latitude);
  const ambLng = Number(ambulanceLocation?.longitude);
  const hasAmbulanceLocation = Number.isFinite(ambLat) && Number.isFinite(ambLng) && ambLat >= 30.20 && ambLat <= 30.48 && ambLng >= 77.90 && ambLng <= 78.18;
  const ambulancePoint = hasAmbulanceLocation ? {
    x: Math.max(40, Math.min(760, 390 + (ambLng - 78.0437) * 2800)),
    y: Math.max(35, Math.min(365, 220 - (ambLat - 30.3255) * 2800))
  } : null;

  return (
    <div style={{
      background: '#ffffff',
      borderRadius: '16px',
      border: '1px solid #e2e8f0',
      overflow: 'hidden',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
    }}>
      {/* Map Header Bar */}
      <div style={{
        padding: '0.85rem 1.25rem',
        background: '#0f172a',
        color: '#ffffff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div style={{
            background: 'rgba(220, 38, 38, 0.2)',
            color: '#ef4444',
            padding: '6px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Navigation2 size={18} style={{ transform: 'rotate(45deg)' }} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Emergency Location Overview</span>
              <span style={{ fontSize: '0.7rem', background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                ● {hasAmbulanceLocation ? 'GPS POSITION' : 'SCHEMATIC MAP'}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              {patientLocation.address || "Patient pickup location"}
            </div>
          </div>
        </div>

        {/* Map view controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={() => setShowTraffic(!showTraffic)}
            style={{
              background: showTraffic ? '#1e293b' : 'transparent',
              color: showTraffic ? '#38bdf8' : '#64748b',
              border: '1px solid #334155',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontWeight: 600
            }}
          >
            <Layers size={13} />
            Illustrative Overlay: {showTraffic ? 'ON' : 'OFF'}
          </button>

          <div style={{
            fontSize: '0.75rem',
            color: '#cbd5e1',
            background: '#1e293b',
            padding: '4px 8px',
            borderRadius: '6px',
            border: '1px solid #334155'
          }}>
            Radius: 10 km
          </div>
        </div>
      </div>

      {/* SVG Mock Map Canvas */}
      <div style={{ position: 'relative', width: '100%', height: '320px', background: '#0b1329', overflow: 'hidden' }}>
        <svg
          viewBox="0 0 800 400"
          style={{ width: '100%', height: '100%', display: 'block' }}
          preserveAspectRatio="xMidYMid slice"
        >
          {/* Map Base Grid */}
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#16223d" strokeWidth="0.8" />
            </pattern>
            <linearGradient id="routeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#06b6d4" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Grid background */}
          <rect width="800" height="400" fill="#0c162d" />
          <rect width="800" height="400" fill="url(#gridPattern)" />

          {/* District boundary contours */}
          <path d="M 50,80 Q 200,40 450,70 T 750,110 L 770,320 Q 500,370 200,350 Z" fill="#0f1f3d" opacity="0.4" />

          {/* Mock Roads / Arterials of Dehradun */}
          {/* Rajpur Road Spine */}
          <path d="M 490,50 L 440,150 L 390,220 L 350,290 L 320,380" stroke="#2a3b61" strokeWidth="9" fill="none" />
          <path d="M 490,50 L 440,150 L 390,220 L 350,290 L 320,380" stroke="#475569" strokeWidth="4" fill="none" />

          {/* Haridwar Road / East corridor */}
          <path d="M 390,220 L 480,270 L 580,310 L 720,360" stroke="#2a3b61" strokeWidth="7" fill="none" />
          <path d="M 390,220 L 480,270 L 580,310 L 720,360" stroke="#475569" strokeWidth="3" fill="none" />

          {/* Chakrata Road / West corridor */}
          <path d="M 390,220 L 290,190 L 190,170 L 90,160" stroke="#2a3b61" strokeWidth="7" fill="none" />
          <path d="M 390,220 L 290,190 L 190,170 L 90,160" stroke="#475569" strokeWidth="3" fill="none" />

          {/* Canal Road bypass */}
          <path d="M 440,150 L 320,130 L 220,150 L 170,230" stroke="#2a3b61" strokeWidth="5" fill="none" />

          {/* Ring road loop */}
          <path d="M 170,230 L 220,320 L 350,350 L 490,340 L 580,260" stroke="#223354" strokeWidth="4" strokeDasharray="6 4" fill="none" />

          {/* River Rispana / Bindal Mock representation */}
          <path d="M 520,30 Q 500,160 530,280 T 560,390" stroke="#172e54" strokeWidth="8" fill="none" opacity="0.6" />

          {/* Illustrative corridor overlay only. Real traffic is supplied by the backend Routes API when configured. */}
          {showTraffic && (
            <>
              {/* Green Corridor (Rajpur Rd to Max Hospital) */}
              <path d="M 390,220 L 440,150 L 490,80" stroke="#10b981" strokeWidth="4" strokeLinecap="round" fill="none" opacity="0.85" />

              {/* Low Traffic path (Canal Rd) */}
              <path d="M 390,220 L 290,190 L 220,150" stroke="#10b981" strokeWidth="3" strokeLinecap="round" fill="none" opacity="0.75" />

              {/* Moderate Traffic (East toward CMI) */}
              <path d="M 390,220 L 440,250 L 470,320" stroke="#f59e0b" strokeWidth="4" strokeLinecap="round" fill="none" opacity="0.8" />

              {/* Heavy Congestion near Clock Tower intersection */}
              <path d="M 390,220 L 350,290 L 290,350" stroke="#ef4444" strokeWidth="5" strokeLinecap="round" strokeDasharray="5 3" fill="none" opacity="0.9" />
            </>
          )}

          {/* Highlighted active route if hospital selected */}
          {selectedPin && (
            <path
              d={`M ${patientCoords.x},${patientCoords.y} Q ${(patientCoords.x + selectedPin.x) / 2},${(patientCoords.y + selectedPin.y) / 2 - 20} ${selectedPin.x},${selectedPin.y}`}
              stroke="url(#routeGrad)"
              strokeWidth="5"
              strokeDasharray="8 4"
              fill="none"
              filter="url(#glow)"
            />
          )}

          {/* Hospital Markers */}
          {hospitalPins.map((hosp) => {
            const isTarget = hosp.id === selectedHospitalId;
            return (
              <g
                key={hosp.id}
                transform={`translate(${hosp.x}, ${hosp.y})`}
                style={{ cursor: onSelectHospital ? 'pointer' : 'default' }}
                onClick={() => onSelectHospital && onSelectHospital(hosp.id)}
              >
                {/* Ping ring for selected or recommended */}
                {isTarget && (
                  <circle r="22" fill="none" stroke="#38bdf8" strokeWidth="2" opacity="0.6">
                    <animate attributeName="r" values="14;28;14" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.8;0.1;0.8" dur="2s" repeatCount="indefinite" />
                  </circle>
                )}

                {/* Hospital base pin */}
                <rect
                  x="-16"
                  y="-16"
                  width="32"
                  height="32"
                  rx="8"
                  fill={isTarget ? "#0284c7" : "#1e293b"}
                  stroke={isTarget ? "#ffffff" : "#475569"}
                  strokeWidth={isTarget ? "2.5" : "1.5"}
                />

                {/* Red cross icon */}
                <path d="M -7,0 L 7,0 M 0,-7 L 0,7" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />

                {/* Tag label */}
                <rect
                  x="-55"
                  y="20"
                  width="110"
                  height="22"
                  rx="5"
                  fill="#0f172a"
                  stroke={isTarget ? "#38bdf8" : "#334155"}
                  strokeWidth="1"
                  opacity="0.95"
                />
                <text
                  x="0"
                  y="34"
                  fill="#ffffff"
                  fontSize="9.5"
                  fontWeight="700"
                  textAnchor="middle"
                  fontFamily="sans-serif"
                >
                  {hosp.name.split(" ")[0]} • {hosp.eta}
                </text>
              </g>
            );
          })}

          {/* Patient Marker (Center Beacon) */}
          <g transform={`translate(${patientCoords.x}, ${patientCoords.y})`}>
            {/* Pulsing signal rings */}
            <circle r="32" fill="none" stroke="#dc2626" strokeWidth="1.5" opacity="0.3">
              <animate attributeName="r" values="16;45;16" dur="2.4s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.6;0.0;0.6" dur="2.4s" repeatCount="indefinite" />
            </circle>

            <circle r="18" fill="rgba(220, 38, 38, 0.25)" />
            <circle r="10" fill="#dc2626" stroke="#ffffff" strokeWidth="2.5" />

            {/* Patient callout card */}
            <rect
              x="-65"
              y="-42"
              width="130"
              height="26"
              rx="6"
              fill="#dc2626"
              stroke="#ffffff"
              strokeWidth="1.5"
              filter="url(#glow)"
            />
            <text
              x="0"
              y="-25"
              fill="#ffffff"
              fontSize="10"
              fontWeight="800"
              textAnchor="middle"
              fontFamily="sans-serif"
            >
              📍 YOUR LOCATION
            </text>
          </g>

          {ambulancePoint && (
            <g transform={`translate(${ambulancePoint.x}, ${ambulancePoint.y})`}>
              <circle r="20" fill="none" stroke="#fb7185" strokeWidth="3" opacity="0.85">
                <animate attributeName="r" values="12;25;12" dur="1.8s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.9;0.15;0.9" dur="1.8s" repeatCount="indefinite" />
              </circle>
              <circle r="9" fill="#e11d48" stroke="#ffffff" strokeWidth="3" />
              <text x="14" y="-12" fill="#ffffff" fontSize="12" fontWeight="700">AMBULANCE</text>
            </g>
          )}

          {/* Map Compass */}
          <g transform="translate(750, 45)">
            <circle r="18" fill="#1e293b" stroke="#334155" strokeWidth="1" />
            <path d="M 0,-12 L 4,0 L -4,0 Z" fill="#ef4444" />
            <path d="M 0,12 L 4,0 L -4,0 Z" fill="#94a3b8" />
            <text x="0" y="-14" fill="#ef4444" fontSize="8" fontWeight="bold" textAnchor="middle">N</text>
          </g>
        </svg>

        {/* Legend Overlay */}
        <div style={{
          position: 'absolute',
          bottom: '10px',
          left: '12px',
          background: 'rgba(15, 23, 42, 0.88)',
          backdropFilter: 'blur(6px)',
          borderRadius: '8px',
          padding: '6px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontSize: '0.725rem',
          color: '#cbd5e1',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#dc2626' }} />
            Patient
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#0284c7' }} />
            Hospitals
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '14px', height: '3px', background: '#10b981', borderRadius: '2px' }} />
            Illustrative Route
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '14px', height: '3px', background: '#ef4444', borderRadius: '2px' }} />
            Illustrative Congestion
          </span>
        </div>
      </div>

      {/* Map footer detail */}
      <div style={{
        padding: '0.65rem 1.25rem',
        background: '#f8fafc',
        fontSize: '0.8rem',
        color: '#64748b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderTop: '1px solid #e2e8f0'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldCheck size={15} color="#059669" />
          <span>Schematic corridor overlay only. No live signal preemption or green corridor control is active.</span>
        </div>
        <div style={{ fontWeight: 600, color: '#334155' }}>
          Dehradun EMS Zone #1
        </div>
      </div>
    </div>
  );
}
