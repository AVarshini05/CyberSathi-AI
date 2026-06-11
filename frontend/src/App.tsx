import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AppRoutes from './routes/AppRoutes';
import AIAssistant from './components/AIAssistant/AIAssistant';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <AIAssistant />
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
