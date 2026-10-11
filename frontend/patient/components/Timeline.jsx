import React from 'react';
import { 
  Check, 
  CircleDot, 
  Circle, 
  Clock, 
  ChevronRight,
  RotateCcw,
  Sparkles
} from 'lucide-react';

export default function Timeline({ 
  steps, 
  currentStepIndex, 
  onAdvanceStep, 
  onResetTimeline 
}) {
  return (
    <div>
      {/* Simulation Toolbar for Mentor Demonstration */}
      <div style={{
        background: '#f8fafc',
        border: '1px dashed #cbd5e1',
        borderRadius: '10px',
        padding: '0.65rem 1rem',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#475569' }}>
          <Sparkles size={14} color="#0284c7" />
          <span style={{ fontWeight: 600 }}>Demo Simulation Control:</span>
          <span>Step {currentStepIndex + 1} of {steps.length}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {currentStepIndex < steps.length - 1 && (
            <button
              onClick={onAdvanceStep}
              className="btn btn-medical"
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.785rem', gap: '4px' }}
            >
              Advance Next Stage <ChevronRight size={13} />
            </button>
          )}

          <button
            onClick={onResetTimeline}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.785rem', gap: '4px' }}
            title="Reset to default coordination state"
          >
            <RotateCcw size={13} />
            Reset State
          </button>
        </div>
      </div>

      {/* Main Vertical Timeline */}
      <div className="timeline-container">
        <div className="timeline-line" />

        {steps.map((step, index) => {
          // Determine status based on index
          let stepStatus = "pending";
          if (index < currentStepIndex) {
            stepStatus = "completed";
          } else if (index === currentStepIndex) {
            stepStatus = "active";
          }

          return (
            <div key={step.id || index} className="timeline-step">
              {/* Marker icon */}
              <div className={`step-marker ${stepStatus}`}>
                {stepStatus === 'completed' && <Check size={20} strokeWidth={3} />}
                {stepStatus === 'active' && <CircleDot size={20} strokeWidth={2.5} />}
                {stepStatus === 'pending' && <Circle size={14} strokeWidth={2} />}
              </div>

              {/* Step Card */}
              <div className={`step-content ${stepStatus === 'active' ? 'active-step-card' : ''}`}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px', marginBottom: '0.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h4 style={{ 
                      fontSize: '1rem', 
                      fontWeight: 800, 
                      color: stepStatus === 'active' ? '#b91c1c' : stepStatus === 'completed' ? '#0f172a' : '#64748b' 
                    }}>
                      {step.title}
                    </h4>

                    {stepStatus === 'active' && (
                      <span className="badge badge-critical" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                        ● CURRENT ACTIVE STAGE
                      </span>
                    )}

                    {stepStatus === 'completed' && (
                      <span className="badge badge-success" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                        ✓ COMPLETED
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} />
                    {stepStatus === 'active' ? 'Real-Time Sync' : step.timestamp}
                  </div>
                </div>

                <p style={{ fontSize: '0.85rem', color: stepStatus === 'pending' ? '#94a3b8' : '#475569', lineHeight: 1.45 }}>
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
