import React, { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import api from '../services/api';
import { User } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (mobile: string, pass: string) => Promise<void>;
  register: (payload: any) => Promise<void>;
  logout: () => void;
  requestOTP: (mobile: string) => Promise<string | null>;
  verifyOTP: (mobile: string, otp: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchProfile = async () => {
    const token = localStorage.getItem('ccrms_token');
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const response = await api.post('/auth/test-token');
      setUser(response.data);
    } catch (error) {
      console.error('Session validation failed:', error);
      localStorage.removeItem('ccrms_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const login = async (mobile: string, pass: string) => {
    const response = await api.post('/auth/login', {
      mobile_number: mobile,
      password: pass,
    });
    localStorage.setItem('ccrms_token', response.data.access_token);
    await fetchProfile();
  };

  const register = async (payload: any) => {
    await api.post('/auth/register', payload);
  };

  const logout = () => {
    localStorage.removeItem('ccrms_token');
    setUser(null);
  };

  const requestOTP = async (mobile: string) => {
    const response = await api.post('/auth/otp/request', { mobile_number: mobile });
    return response.data.otp_code_dev_only || null;
  };

  const verifyOTP = async (mobile: string, otp: string) => {
    const response = await api.post('/auth/otp/verify', {
      mobile_number: mobile,
      otp,
    });
    localStorage.setItem('ccrms_token', response.data.access_token);
    await fetchProfile();
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, requestOTP, verifyOTP }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
