import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import TrackComplaint from '../pages/TrackComplaint';
import SuspectSearch from '../pages/SuspectSearch';
import ComplaintSuccess from '../pages/ComplaintSuccess';
import ComplaintForm from '../pages/ComplaintForm';
import CitizenDashboard from '../pages/CitizenDashboard';
import AdminDashboard from '../pages/AdminDashboard';
import { ProtectedRoute } from './ProtectedRoute';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Pages */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/track" element={<TrackComplaint />} />
      <Route path="/suspect-search" element={<SuspectSearch />} />
      <Route path="/complaint-success" element={<ComplaintSuccess />} />
      <Route
        path="/file-complaint"
        element={
          <ProtectedRoute allowedRoles={['citizen']}>
            <ComplaintForm />
          </ProtectedRoute>
        }
      />

      {/* Citizen Protected Pages */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute allowedRoles={['citizen']}>
            <CitizenDashboard />
          </ProtectedRoute>
        }
      />

      {/* Back Office Officer Protected Pages */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['officer', 'admin']}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />

      {/* Fallback redirect */}
      <Route path="*" element={<LandingPage />} />
    </Routes>
  );
};
export default AppRoutes;
