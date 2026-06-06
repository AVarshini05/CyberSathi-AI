import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { Complaint } from '../types';
import { Search, ShieldAlert, FileText, Download, CheckCircle2, Clock, MapPin, Eye, FileDigit } from 'lucide-react';
import Layout from '../components/layout/Layout';

export const TrackComplaint: React.FC = () => {
  const [searchParams] = useSearchParams();
  const queryParam = searchParams.get('query') || '';

  const [searchQuery, setSearchQuery] = useState(queryParam);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setError(null);
    setComplaints([]);
    setSelectedComplaint(null);
    setLoading(true);

    try {
      const response = await api.get(`/complaints/track?query=${searchQuery.trim()}`);
      setComplaints(response.data);
      if (response.data.length === 1) {
        setSelectedComplaint(response.data[0]);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'No complaints found for the entered credentials.');
    } finally {
      setLoading(false);
    }
  };

  // Run automatically if query URL param exists
  useEffect(() => {
    if (queryParam) {
      setSearchQuery(queryParam);
      handleSearch();
    }
  }, [queryParam]);

  const handleDownloadReceipt = async (complaintId: number, ackNumber: string) => {
    try {
      const response = await api.get(`/complaints/${complaintId}/receipt`, {
        responseType: 'blob',
      });
      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `CCRMS_ACK_${ackNumber}.pdf`;
      link.click();
    } catch (err) {
      console.error('Failed to download PDF receipt:', err);
      alert('Error downloading receipt. Please try again.');
    }
  };

  // Status mapping to timeline steps
  const statusSteps = [
    { name: 'Submitted', key: 'Submitted' },
    { name: 'Assigned', key: 'Assigned' },
    { name: 'Under Review', key: 'Under Review' },
    { name: 'Investigation', key: 'Investigation In Progress' },
    { name: 'Info Required', key: 'Additional Information Required' },
    { name: 'Closed', key: 'Closed' }
  ];

  const getStatusIndex = (currentStatus: string) => {
    // Return index of status inside our steps
    return statusSteps.findIndex(step => step.key === currentStatus);
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
        
        {/* Header section */}
        <div className="text-center max-w-xl mx-auto mb-8 space-y-2">
          <h1 className="text-3xl font-black text-gov-navy font-sans tracking-tight">Track Your Complaint</h1>
          <p className="text-sm text-gov-slate">
            Enter your 18-digit Acknowledgement Number or the victim's registered mobile number to fetch the timeline.
          </p>
        </div>

        {/* Search bar */}
        <div className="max-w-2xl mx-auto bg-white p-4 border border-slate-200 rounded-2xl shadow-sm">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-grow">
              <Search className="absolute left-3 top-3.5 h-4 w-4 text-gov-slate" />
              <input
                type="text"
                placeholder="e.g. CCRMS-FF-2026-000001 or 9876543210"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-3 border border-gov-border rounded-lg text-sm outline-none focus:border-gov-indigo transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-gov-indigo hover:bg-slate-900 text-white font-bold px-6 py-3 rounded-lg text-sm transition-all flex items-center justify-center space-x-2"
            >
              {loading ? 'Searching...' : 'Track Status'}
            </button>
          </form>
        </div>

        {error && (
          <div className="max-w-2xl mx-auto bg-red-50 text-red-600 text-xs font-bold p-4 rounded-xl border border-red-200 flex items-start space-x-3">
            <ShieldAlert className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Multiple complaints list */}
        {complaints.length > 1 && !selectedComplaint && (
          <div className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
            <h2 className="font-extrabold text-sm text-gov-navy mb-4">Multiple Cases Found ({complaints.length})</h2>
            <div className="space-y-3">
              {complaints.map((c) => (
                <div
                  key={c.id}
                  onClick={() => setSelectedComplaint(c)}
                  className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 border border-slate-200 rounded-xl hover:border-gov-indigo cursor-pointer transition-colors"
                >
                  <div>
                    <span className="text-xs font-black text-gov-indigo block">{c.acknowledgement_number}</span>
                    <span className="text-[11px] text-gov-slate mt-0.5 block">{c.category.name} &bull; {c.subcategory.name}</span>
                  </div>
                  <div className="flex items-center space-x-3 mt-2 sm:mt-0">
                    <span className="text-[10px] bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full font-bold">
                      {c.current_status}
                    </span>
                    <button className="text-xs font-bold text-gov-indigo flex items-center space-x-1">
                      <Eye className="h-3.5 w-3.5" />
                      <span>View Details</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Selected Complaint Tracking Details */}
        {selectedComplaint && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
            
            {/* Visual Progress Timeline (2 Cols) */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Timeline Card */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 md:p-8 shadow-sm">
                <div className="flex justify-between items-start border-b border-slate-100 pb-4 mb-8">
                  <div>
                    <span className="text-xs font-bold text-gov-slate uppercase tracking-wider block">Acknowledgement Status</span>
                    <h2 className="text-xl font-extrabold text-gov-navy font-sans mt-0.5">{selectedComplaint.acknowledgement_number}</h2>
                  </div>
                  <button
                    onClick={() => handleDownloadReceipt(selectedComplaint.id, selectedComplaint.acknowledgement_number)}
                    className="bg-gov-light hover:bg-slate-100 text-gov-indigo border border-gov-border rounded-lg px-4 py-2 text-xs font-bold flex items-center space-x-1.5 transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    <span>Download Receipt</span>
                  </button>
                </div>

                {/* Progress Indicators */}
                <div className="relative">
                  {/* Timeline Bar Line */}
                  <div className="absolute left-4 top-2 bottom-2 w-1 bg-slate-200 z-0"></div>

                  <div className="space-y-8 relative z-10">
                    {statusSteps.map((step, idx) => {
                      const currentStatusIndex = getStatusIndex(selectedComplaint.current_status);
                      const isCompleted = idx < currentStatusIndex;
                      const isCurrent = idx === currentStatusIndex;

                      return (
                        <div key={idx} className="flex items-start pl-8 relative">
                          {/* Dot / Icon */}
                          <div className="absolute left-1.5 top-0.5 -translate-x-1/2 flex items-center justify-center">
                            {isCompleted ? (
                              <div className="bg-white rounded-full">
                                <CheckCircle2 className="h-6 w-6 text-green-600 fill-green-50" />
                              </div>
                            ) : isCurrent ? (
                              <div className="bg-white rounded-full">
                                <Clock className="h-6 w-6 text-orange-500 fill-orange-50 animate-spin-slow" />
                              </div>
                            ) : (
                              <div className="h-4 w-4 rounded-full bg-slate-200 border-4 border-white mt-1"></div>
                            )}
                          </div>

                          <div className="space-y-1">
                            <h4 className={`text-sm font-bold ${
                              isCompleted ? 'text-green-700' : isCurrent ? 'text-orange-600' : 'text-slate-400'
                            }`}>
                              {step.name}
                            </h4>
                            <p className="text-xs text-gov-slate">
                              {isCurrent
                                ? `Current Stage: Your complaint is undergoing ${step.name.toLowerCase()} updates.`
                                : isCompleted
                                ? `Completed Stage.`
                                : `Awaiting this stage.`}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Status Remarks History */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                <h3 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3">Status Action History</h3>
                <div className="space-y-4">
                  {selectedComplaint.status_history.map((hist, idx) => (
                    <div key={idx} className="flex items-start space-x-3 text-xs leading-relaxed">
                      <div className="bg-gov-light text-gov-indigo p-2 rounded-lg flex-shrink-0">
                        <FileDigit className="h-4 w-4" />
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-800 uppercase">{hist.status}</span>
                          <span className="text-[10px] text-gov-slate">
                            {new Date(hist.updated_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-gov-slate font-medium">{hist.remarks || "No comments entered."}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Complaint Summary Card (1 Col) */}
            <div className="space-y-6">
              <div className="bg-slate-900 text-white border border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
                <h3 className="font-black text-sm border-b border-slate-800 pb-3 uppercase tracking-wider text-orange-500">
                  Complaint Details
                </h3>

                <div className="space-y-4 text-xs">
                  <div>
                    <span className="text-slate-400 block font-medium">Category</span>
                    <span className="font-bold text-white block mt-0.5">{selectedComplaint.category.name}</span>
                  </div>

                  <div>
                    <span className="text-slate-400 block font-medium">Subcategory</span>
                    <span className="font-bold text-white block mt-0.5">{selectedComplaint.subcategory.name}</span>
                  </div>

                  <div>
                    <span className="text-slate-400 block font-medium">Victim / Reporting Name</span>
                    <span className="font-bold text-white block mt-0.5">
                      {selectedComplaint.is_anonymous ? 'Anonymous' : (selectedComplaint.victim_name || 'Not Provided')}
                    </span>
                  </div>

                  {selectedComplaint.victim_mobile && (
                    <div>
                      <span className="text-slate-400 block font-medium">Mobile Number</span>
                      <span className="font-bold text-white block mt-0.5">{selectedComplaint.victim_mobile}</span>
                    </div>
                  )}

                  <div>
                    <span className="text-slate-400 block font-medium">Incident Description</span>
                    <p className="text-slate-300 leading-relaxed mt-1">{selectedComplaint.fraud_description}</p>
                  </div>
                </div>

                {/* Return button if multiple found */}
                {complaints.length > 1 && (
                  <button
                    onClick={() => setSelectedComplaint(null)}
                    className="w-full text-center bg-slate-800 hover:bg-slate-700 text-white font-bold py-2.5 rounded-lg text-xs"
                  >
                    Back to search results
                  </button>
                )}
              </div>
            </div>

          </div>
        )}

      </div>
    </Layout>
  );
};
export default TrackComplaint;
