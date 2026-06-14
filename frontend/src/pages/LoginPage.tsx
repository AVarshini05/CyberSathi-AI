import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, KeyRound, Smartphone, AlertCircle } from 'lucide-react';
import Layout from '../components/layout/Layout';

const getErrorMessage = (err: any, fallback: string): string => {
  const detail = err.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first && first.msg) {
      const field = first.loc && first.loc.length > 1 ? first.loc[1] : '';
      return field ? `${field}: ${first.msg}` : first.msg;
    }
  }
  return fallback;
};

export const LoginPage: React.FC = () => {
  const { login, requestOTP, verifyOTP } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [loginMethod, setLoginMethod] = useState<'password' | 'otp'>('password');
  
  // Inputs state
  const [mobileNumber, setMobileNumber] = useState('');
  const [password, setPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  
  // Verification progress
  const [otpSent, setOtpSent] = useState(false);
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);
  
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Get path to redirect back to, preserving query parameters (e.g. ?cat=FF)
  const fromObj = (location.state as any)?.from;
  const from = fromObj ? `${fromObj.pathname}${fromObj.search || ''}` : '/dashboard';

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(mobileNumber, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      console.error(err);
      setError(getErrorMessage(err, 'Invalid email/mobile number or password.'));
    } finally {
      setLoading(false);
    }
  };

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const hint = await requestOTP(mobileNumber);
      setOtpSent(true);
      setDevOtpHint(hint);
    } catch (err: any) {
      setError(getErrorMessage(err, 'Mobile number not found. Please register first.'));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await verifyOTP(mobileNumber, otpCode);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(getErrorMessage(err, 'Invalid OTP code.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="min-h-[75vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full bg-white border border-slate-200 shadow-lg rounded-2xl p-8 space-y-6">
          
          {/* Top Logo Header */}
          <div className="text-center space-y-2">
            <div className="bg-orange-500/10 h-12 w-12 rounded-xl flex items-center justify-center text-orange-600 mx-auto">
              <Shield className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-black text-gov-navy tracking-tight font-sans">
              Sign In to CyberSathi-AI
            </h2>
            <p className="text-xs text-gov-slate">
              Access the secure Citizen Portal to report or track complaints.
            </p>
          </div>

          {/* Toggle Tabs */}
          <div className="grid grid-cols-2 bg-slate-100 rounded-lg p-1 text-xs font-bold text-gov-slate">
            <button
              onClick={() => { setLoginMethod('password'); setError(null); }}
              className={`py-2 rounded-md transition-all ${
                loginMethod === 'password' ? 'bg-white text-gov-navy shadow-sm' : 'hover:text-gov-navy'
              }`}
            >
              Password Login
            </button>
            <button
              onClick={() => { setLoginMethod('otp'); setError(null); }}
              className={`py-2 rounded-md transition-all ${
                loginMethod === 'otp' ? 'bg-white text-gov-navy shadow-sm' : 'hover:text-gov-navy'
              }`}
            >
              Mobile OTP Login
            </button>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-xs font-bold p-3 rounded-lg border border-red-200 flex items-start space-x-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* HINT for Dev only */}
          {devOtpHint && (
            <div className="bg-blue-50 text-blue-700 text-xs font-bold p-3 rounded-lg border border-blue-200">
              [DEVELOPER SIMULATOR]: OTP sent to phone is: <span className="underline font-black text-sm">{devOtpHint}</span>
            </div>
          )}

          {/* Dynamic Login Form */}
          {loginMethod === 'password' ? (
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div className="flex flex-col">
                <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                  <Smartphone className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                  Mobile Number / Email Address
                </label>
                <input
                  type="text"
                  required
                  placeholder="Enter mobile number or email"
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value)}
                  className="border border-gov-border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors"
                />
              </div>

              <div className="flex flex-col">
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-bold text-slate-700 flex items-center">
                    <KeyRound className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                    Password
                  </label>
                  <Link to="/forgot-password" className="text-[10px] font-bold text-gov-indigo hover:underline">
                    Forgot Password?
                  </Link>
                </div>
                <input
                  type="password"
                  required
                  placeholder="Enter secure password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="border border-gov-border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gov-indigo hover:bg-slate-900 text-white font-bold py-2.5 rounded-lg text-sm transition-all shadow-md"
              >
                {loading ? 'Authenticating...' : 'Secure Sign In'}
              </button>
            </form>
          ) : (
            /* OTP LOGIN FLOW */
            <div className="space-y-4">
              {!otpSent ? (
                <form onSubmit={handleRequestOTP} className="space-y-4">
                  <div className="flex flex-col">
                    <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                      <Smartphone className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                      Mobile Number
                    </label>
                    <input
                      type="tel"
                      required
                      placeholder="Enter registered mobile number"
                      value={mobileNumber}
                      onChange={(e) => setMobileNumber(e.target.value)}
                      className="border border-gov-border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-2.5 rounded-lg text-sm transition-all shadow-md"
                  >
                    {loading ? 'Requesting...' : 'Request OTP Code'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyOTP} className="space-y-4">
                  <div className="flex flex-col">
                    <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                      <KeyRound className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                      One-Time Password (OTP)
                    </label>
                    <input
                      type="text"
                      required
                      maxLength={6}
                      placeholder="Enter 6-digit OTP code"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      className="border border-gov-border rounded-lg p-2.5 text-sm outline-none text-center font-bold tracking-widest focus:border-gov-indigo transition-colors"
                    />
                    <span className="text-[10px] text-gov-slate mt-1.5">
                      OTP code sent to <span className="font-bold text-slate-800">{mobileNumber}</span>.
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setOtpSent(false)}
                      className="w-1/3 border border-gov-border hover:bg-slate-50 text-slate-750 font-bold py-2.5 rounded-lg text-xs"
                    >
                      Back
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-2/3 bg-gov-indigo hover:bg-slate-900 text-white font-bold py-2.5 rounded-lg text-sm transition-all shadow-md"
                    >
                      {loading ? 'Verifying...' : 'Verify & Login'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          <div className="text-center pt-2 border-t border-slate-150">
            <span className="text-xs text-gov-slate">New citizen user? </span>
            <Link to="/register" state={{ from: fromObj }} className="text-xs font-bold text-gov-indigo hover:underline">
              Create portal account
            </Link>
          </div>
        </div>
      </div>
    </Layout>
  );
};
export default LoginPage;
