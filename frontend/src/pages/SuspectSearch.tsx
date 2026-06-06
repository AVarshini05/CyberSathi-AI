import React, { useState } from 'react';
import api from '../services/api';
import { SuspectSearchResult } from '../types';
import { Search, ShieldAlert, ShieldCheck, AlertTriangle, AlertCircle, Info, Smartphone, Mail, Globe, Hash } from 'lucide-react';
import Layout from '../components/layout/Layout';

export const SuspectSearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [result, setResult] = useState<SuspectSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setError(null);
    setResult(null);
    setLoading(true);

    try {
      const response = await api.get(`/suspects/search?query=${searchQuery.trim()}`);
      setResult(response.data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred during search. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getRiskStyles = (risk: string) => {
    if (risk.includes('Safe')) {
      return {
        bg: 'bg-green-50 border-green-200',
        text: 'text-green-700',
        subtext: 'text-green-600',
        icon: <ShieldCheck className="h-10 w-10 text-green-600" />
      };
    } else if (risk.includes('Low')) {
      return {
        bg: 'bg-blue-50 border-blue-200',
        text: 'text-blue-700',
        subtext: 'text-blue-600',
        icon: <Info className="h-10 w-10 text-blue-600" />
      };
    } else if (risk.includes('Medium')) {
      return {
        bg: 'bg-orange-50 border-orange-200',
        text: 'text-orange-700',
        subtext: 'text-orange-600',
        icon: <AlertTriangle className="h-10 w-10 text-orange-600" />
      };
    } else {
      return {
        bg: 'bg-red-50 border-red-200',
        text: 'text-red-700',
        subtext: 'text-red-650',
        icon: <AlertCircle className="h-10 w-10 text-red-600 animate-bounce" />
      };
    }
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
        
        {/* Header */}
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h1 className="text-3xl font-black text-gov-navy font-sans tracking-tight">Suspect Repository Search</h1>
          <p className="text-sm text-gov-slate">
            Verify phone numbers, emails, websites, UPI IDs, or social handles before interacting. Aggregated from citizen reports.
          </p>
        </div>

        {/* Search Form */}
        <div className="max-w-2xl mx-auto bg-white p-5 border border-slate-200 rounded-2xl shadow-sm">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-grow">
              <Search className="absolute left-3 top-3.5 h-4 w-4 text-gov-slate" />
              <input
                type="text"
                required
                placeholder="Enter Phone, Email, UPI ID, URL or Handle"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-3 border border-gov-border rounded-lg text-sm outline-none focus:border-gov-indigo transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-orange-600 hover:bg-orange-700 text-white font-bold px-8 py-3 rounded-lg text-sm transition-all flex items-center justify-center space-x-2"
            >
              {loading ? 'Searching...' : 'Check Suspect'}
            </button>
          </form>

          {/* Quick instructions / Info icons */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center mt-6 pt-5 border-t border-slate-100 text-[10px] font-bold text-gov-slate uppercase tracking-wider">
            <div className="flex flex-col items-center">
              <Smartphone className="h-4 w-4 mb-1 text-gov-indigo" />
              <span>Mobile Phone</span>
            </div>
            <div className="flex flex-col items-center">
              <Mail className="h-4 w-4 mb-1 text-gov-indigo" />
              <span>Email Address</span>
            </div>
            <div className="flex flex-col items-center">
              <Globe className="h-4 w-4 mb-1 text-gov-indigo" />
              <span>Website URL</span>
            </div>
            <div className="flex flex-col items-center">
              <Hash className="h-4 w-4 mb-1 text-gov-indigo" />
              <span>UPI / Social ID</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="max-w-2xl mx-auto bg-red-50 text-red-650 text-xs font-bold p-4 rounded-xl border border-red-200">
            {error}
          </div>
        )}

        {/* Search Results Display */}
        {result && (
          <div className="max-w-3xl mx-auto space-y-6">
            
            {/* Risk Indicator Card */}
            {(() => {
              const styles = getRiskStyles(result.risk_level);
              return (
                <div className={`border p-6 rounded-2xl flex flex-col sm:flex-row items-center sm:items-start text-center sm:text-left gap-5 shadow-sm ${styles.bg}`}>
                  <div className="flex-shrink-0">{styles.icon}</div>
                  <div className="space-y-1.5">
                    <h3 className={`text-lg font-black ${styles.text}`}>
                      {result.risk_level}
                    </h3>
                    <p className="text-xs font-bold text-slate-800">
                      Query checked: <span className="underline select-all">{result.query}</span>
                    </p>
                    <p className="text-xs text-gov-slate leading-relaxed">
                      {result.report_count === 0
                        ? 'This identifier has not been reported to our cybercrime database. However, please continue to exercise caution before executing any banking transactions.'
                        : `Warning! This identifier is linked to ${result.report_count} filed citizen complaints. Do NOT click links or initiate banking payments.`}
                    </p>
                  </div>
                </div>
              );
            })()}

            {/* List of recent complaints linked to this suspect */}
            {result.recent_reports.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                <h3 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3">
                  Recent Reports Involving This Suspect
                </h3>
                <div className="divide-y divide-slate-100">
                  {result.recent_reports.map((rep, idx) => (
                    <div key={idx} className="py-4 first:pt-0 last:pb-0 text-xs leading-relaxed space-y-2">
                      <div className="flex justify-between items-center text-[10px] font-bold text-gov-slate uppercase">
                        <span>Report #{idx + 1}</span>
                        <span>{new Date(rep.created_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-slate-800 font-medium">
                        {rep.details ? rep.details : "Suspect details reported in transaction fraud / phishing case."}
                      </p>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-gov-slate font-bold">
                        {rep.suspect_name && <span>Name: {rep.suspect_name}</span>}
                        {rep.suspect_mobile && <span>Phone: {rep.suspect_mobile}</span>}
                        {rep.suspect_upi && <span>UPI: {rep.suspect_upi}</span>}
                        {rep.suspect_email && <span>Email: {rep.suspect_email}</span>}
                        {rep.suspect_url && <span>URL: {rep.suspect_url}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </Layout>
  );
};
export default SuspectSearch;
