import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import EmergencyRequest from './pages/EmergencyRequest';
import HospitalRecommendations from './pages/HospitalRecommendations';
import HospitalSelected from './pages/HospitalSelected';
import EmergencyStatus from './pages/EmergencyStatus';
import Auth from './pages/Auth';
import { initialPatientProfile } from './data/mockData';
import authService from './services/authService';

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [currentUser, setCurrentUser] = useState(null);
  const [patientProfile, setPatientProfile] = useState(initialPatientProfile);
  const [activeEmergency, setActiveEmergency] = useState(null);
  const [presetScenario, setPresetScenario] = useState(null);

  // Check persistent authentication session from backend on mount
  useEffect(() => {
    async function checkAuthSession() {
      try {
        const patient = await authService.getCurrentPatient();
        if (patient) {
          setCurrentUser(patient);
          setPatientProfile(prev => ({
            ...prev,
            id: patient.id,
            name: patient.full_name,
            email: patient.email,
            phone: patient.phone || prev.phone,
            bloodGroup: patient.blood_group || prev.bloodGroup,
            emergencyContact: {
              ...prev.emergencyContact,
              name: patient.emergency_contact_name || prev.emergencyContact.name,
              phone: patient.emergency_contact_phone || prev.emergencyContact.phone
            }
          }));
        }
      } catch (err) {
        console.warn('Initial session check error:', err);
      }
    }
    checkAuthSession();
  }, []);

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

  const handleAuthSuccess = (patient) => {
    setCurrentUser(patient);
    setPatientProfile(prev => ({
      ...prev,
      id: patient.id,
      name: patient.full_name,
      email: patient.email,
      phone: patient.phone || prev.phone,
      bloodGroup: patient.blood_group || prev.bloodGroup
    }));
    // Return to dashboard or active workflow
    setCurrentPage('dashboard');
  };

  const handleLogout = async () => {
    await authService.logout();
    setCurrentUser(null);
    setPatientProfile(initialPatientProfile);
  };

  return (
    <div className="app-container">
      {/* Top Navigation */}
      <Navbar
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        activeEmergency={activeEmergency}
        onResetDemo={handleResetDemo}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      {/* Primary Page Router */}
      <main style={{ flex: 1 }}>
        {currentPage === 'auth' && (
          <Auth
            onAuthSuccess={handleAuthSuccess}
            onBackToEmergency={() => setCurrentPage('dashboard')}
            initialMode="signin"
          />
        )}

        {currentPage === 'dashboard' && (
          <Dashboard
            currentUser={currentUser}
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
          <strong style={{ color: '#ffffff' }}>SirenSync Platform</strong> • Patient Authentication & Emergency Coordination Node • Dehradun
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span>Current Flow: <strong>{currentPage.toUpperCase()}</strong></span>
          <span>Auth Status: <strong>{currentUser ? `Active (${currentUser.email})` : 'Guest / Unauthenticated'}</strong></span>
          <span>Data Layer: <strong>FastAPI + SQLite (Persistent)</strong></span>
        </div>
      </footer>
    </div>
  );
}
