import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '../context/AuthContext';
import { Shield, User, Mail, Smartphone, KeyRound, AlertCircle } from 'lucide-react';
import Layout from '../components/layout/Layout';

// Zod Schema matching requirements
const registerSchema = z.object({
  full_name: z.string().min(3, 'Full Name must be at least 3 characters.'),
  mobile_number: z.string().regex(/^\d{10}$/, 'Mobile number must be exactly 10 digits.'),
  email: z.string().email('Invalid email address.').or(z.literal('')),
  password: z.string().min(6, 'Password must be at least 6 characters.'),
  confirm_password: z.string()
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords do not match.",
  path: ["confirm_password"]
});

type RegisterFormValues = z.infer<typeof registerSchema>;

export const RegisterPage: React.FC = () => {
  const { register: authRegister } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Get redirect state if any
  const fromObj = (location.state as any)?.from;

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      mobile_number: '',
      email: '',
      password: '',
      confirm_password: ''
    }
  });

  const onSubmit = async (data: RegisterFormValues) => {
    setError(null);
    setLoading(true);
    try {
      await authRegister({
        full_name: data.full_name,
        mobile_number: data.mobile_number,
        email: data.email || null,
        password: data.password
      });
      // Redirect to login page on success, preserving the redirect location
      navigate('/login', { 
        state: { 
          info: 'Registration successful. Please sign in.',
          from: fromObj 
        } 
      });
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred during registration.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full bg-white border border-slate-200 shadow-lg rounded-2xl p-8 space-y-6">
          
          {/* Header */}
          <div className="text-center space-y-2">
            <div className="bg-orange-500/10 h-12 w-12 rounded-xl flex items-center justify-center text-orange-600 mx-auto">
              <Shield className="h-6 w-6" />
            </div>
            <h2 className="text-2xl font-black text-gov-navy tracking-tight font-sans">
              Register Citizen Account
            </h2>
            <p className="text-xs text-gov-slate">
              Create a secure account on the Cyber Crime Portal to file and track cases.
            </p>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-xs font-bold p-3 rounded-lg border border-red-200 flex items-start space-x-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            
            {/* Full Name */}
            <div className="flex flex-col">
              <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                <User className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                Full Name <span className="text-red-500 ml-0.5">*</span>
              </label>
              <input
                type="text"
                placeholder="Enter your full name"
                {...register('full_name')}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors.full_name ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
              {errors.full_name && (
                <span className="text-[10px] font-semibold text-red-500 mt-1">{errors.full_name.message}</span>
              )}
            </div>

            {/* Mobile Number */}
            <div className="flex flex-col">
              <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                <Smartphone className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                10-Digit Mobile Number <span className="text-red-500 ml-0.5">*</span>
              </label>
              <input
                type="tel"
                placeholder="Enter 10-digit mobile number"
                {...register('mobile_number')}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors.mobile_number ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
              {errors.mobile_number && (
                <span className="text-[10px] font-semibold text-red-500 mt-1">{errors.mobile_number.message}</span>
              )}
            </div>

            {/* Email */}
            <div className="flex flex-col">
              <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                <Mail className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                Email Address (Optional)
              </label>
              <input
                type="email"
                placeholder="Enter email address"
                {...register('email')}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors.email ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
              {errors.email && (
                <span className="text-[10px] font-semibold text-red-500 mt-1">{errors.email.message}</span>
              )}
            </div>

            {/* Password */}
            <div className="flex flex-col">
              <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                <KeyRound className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                Password <span className="text-red-500 ml-0.5">*</span>
              </label>
              <input
                type="password"
                placeholder="Create secure password"
                {...register('password')}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors.password ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
              {errors.password && (
                <span className="text-[10px] font-semibold text-red-500 mt-1">{errors.password.message}</span>
              )}
            </div>

            {/* Confirm Password */}
            <div className="flex flex-col">
              <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
                <KeyRound className="h-3.5 w-3.5 mr-1 text-gov-slate" />
                Confirm Password <span className="text-red-500 ml-0.5">*</span>
              </label>
              <input
                type="password"
                placeholder="Confirm password"
                {...register('confirm_password')}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors.confirm_password ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
              {errors.confirm_password && (
                <span className="text-[10px] font-semibold text-red-500 mt-1">{errors.confirm_password.message}</span>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gov-indigo hover:bg-slate-900 text-white font-bold py-2.5 rounded-lg text-sm transition-all shadow-md mt-2"
            >
              {loading ? 'Creating Account...' : 'Register Account'}
            </button>
          </form>

          <div className="text-center pt-2 border-t border-slate-150">
            <span className="text-xs text-gov-slate">Already have an account? </span>
            <Link to="/login" state={{ from: fromObj }} className="text-xs font-bold text-gov-indigo hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </Layout>
  );
};
export default RegisterPage;
