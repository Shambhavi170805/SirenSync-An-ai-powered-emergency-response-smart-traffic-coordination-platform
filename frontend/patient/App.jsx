import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import EmergencyRequest from './pages/EmergencyRequest';
import HospitalRecommendations from './pages/HospitalRecommendations';
import HospitalSelected from './pages/HospitalSelected';
import EmergencyStatus from './pages/EmergencyStatus';
import { initialPatientProfile, mockHospitals } from './data/mockData';

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [patientProfile, setPatientProfile] = useState(initialPatientProfile);
  const [activeEmergency, setActiveEmergency] = useState(null);
  const [presetScenario, setPresetScenario] = useState(null);

  // Handlers for user flow
  const handleStartRequest = () => {
    setPresetScenario(null);
    setCurrentPage('request');
  };

  const handleQuickScenario = (scenario) => {
    setPresetScenario(scenario);
    setCurrentPage('request');
  };

  const handleSubmitEmergency = (emergencyData) => {
    setActiveEmergency(emergencyData);
    setCurrentPage('recommendations');
  };

  const handleSelectHospital = (hospital) => {
    setActiveEmergency(prev => ({
      ...prev,
      selectedHospital: hospital,
      status: "Hospital Selected"
    }));
    setCurrentPage('selected');
  };

  const handleViewStatus = () => {
    setCurrentPage('status');
  };

  const handleResetDemo = () => {
    setActiveEmergency(null);
    setPresetScenario(null);
    setCurrentPage('dashboard');
  };

  return (
    <div className="app-container">
      {/* Top Navigation */}
      <Navbar
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        activeEmergency={activeEmergency}
        onResetDemo={handleResetDemo}
      />

      {/* Primary Page Router */}
      <main style={{ flex: 1 }}>
        {currentPage === 'dashboard' && (
          <Dashboard
            patientProfile={patientProfile}
            activeEmergency={activeEmergency}
            onSubmitEmergency={handleSubmitEmergency}
            onStartRequest={handleStartRequest}
            onQuickScenario={handleQuickScenario}
            onNavigate={setCurrentPage}
          />
        )}

        {currentPage === 'request' && (
          <EmergencyRequest
            patientProfile={patientProfile}
            presetScenario={presetScenario}
            onSubmitEmergency={handleSubmitEmergency}
            onBack={() => setCurrentPage('dashboard')}
          />
        )}

        {currentPage === 'recommendations' && (
          <HospitalRecommendations
            activeEmergency={activeEmergency}
            onSelectHospital={handleSelectHospital}
            onBackToRequest={() => setCurrentPage('request')}
            onNavigate={setCurrentPage}
          />
        )}

        {currentPage === 'selected' && (
          <HospitalSelected
            activeEmergency={activeEmergency}
            onViewStatus={handleViewStatus}
            onChangeHospital={() => setCurrentPage('recommendations')}
          />
        )}

        {currentPage === 'status' && (
          <EmergencyStatus
            activeEmergency={activeEmergency}
            onBackToDashboard={() => setCurrentPage('dashboard')}
            onBackToHospitals={() => setCurrentPage('recommendations')}
          />
        )}
      </main>

      {/* Footer System Banner */}
      <footer className="phase-notice-banner">
        <div>
          <strong style={{ color: '#ffffff' }}>SirenSync Platform</strong> • Phase 2 Patient Frontend Prototype • Dehradun Regional EMS Node
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span>Current Flow: <strong>{currentPage.toUpperCase()}</strong></span>
          <span>Data Layer: <strong>Mock / Local In-Memory</strong></span>
        </div>
      </footer>
    </div>
  );
}
