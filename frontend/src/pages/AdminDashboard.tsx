import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Complaint, DashboardStats } from '../types';
import Layout from '../components/layout/Layout';
import { Search, Shield, Eye, ShieldAlert, FileText, CheckCircle2, Clock, CheckSquare, Edit, Download, RefreshCw } from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  
  // Dashboard lists and metrics
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [selectedCase, setSelectedCase] = useState<Complaint | null>(null);
  const [loading, setLoading] = useState(true);

  // Search Filter state
  const [filterAck, setFilterAck] = useState('');
  const [filterMobile, setFilterMobile] = useState('');
  const [filterName, setFilterName] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Status update forms state
  const [newStatus, setNewStatus] = useState('');
  const [statusRemarks, setStatusRemarks] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Edit mode state for Pending Employee Review
  const [editVictimName, setEditVictimName] = useState('');
  const [editVictimMobile, setEditVictimMobile] = useState('');
  const [editVictimEmail, setEditVictimEmail] = useState('');
  const [editVictimState, setEditVictimState] = useState('');
  const [editVictimAddress, setEditVictimAddress] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editAnswers, setEditAnswers] = useState<Record<number, string>>({}); // question_id -> value
  const [editSuspect, setEditSuspect] = useState<any>({
    id: null,
    suspect_name: '',
    suspect_mobile: '',
    suspect_email: '',
    suspect_url: '',
    suspect_upi: '',
    suspect_social_handle: '',
    details: ''
  });
  const [savingEdit, setSavingEdit] = useState(false);

  const isHighlight = (val: string) => val === 'REVIEW REQUIRED' || val === 'UNKNOWN';

  const fetchData = async () => {
    setLoading(true);
    try {
      // Load stats
      const statsRes = await api.get('/complaints/dashboard-stats');
      setStats(statsRes.data);

      // Load filtered complaints list
      const queryParams = new URLSearchParams();
      if (filterAck) queryParams.append('ack_number', filterAck);
      if (filterMobile) queryParams.append('mobile_number', filterMobile);
      if (filterName) queryParams.append('citizen_name', filterName);
      if (filterStatus) queryParams.append('status', filterStatus);

      const listRes = await api.get(`/complaints/user-complaints?${queryParams.toString()}`);
      setComplaints(listRes.data);
    } catch (err) {
      console.error('Failed to load admin dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterStatus]); // Auto refresh on status select dropdown change

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const handleClearFilters = () => {
    setFilterAck('');
    setFilterMobile('');
    setFilterName('');
    setFilterStatus('');
    // Trigger list fetch
    setTimeout(() => fetchData(), 50);
  };
  useEffect(() => {
    if (selectedCase) {
      setEditVictimName(selectedCase.victim_name || '');
      setEditVictimMobile(selectedCase.victim_mobile || '');
      setEditVictimEmail(selectedCase.victim_email || '');
      setEditVictimState(selectedCase.victim_state || '');
      setEditVictimAddress(selectedCase.victim_address || '');
      setEditDescription(selectedCase.fraud_description || '');
      
      const answersMap: Record<number, string> = {};
      selectedCase.answers.forEach(ans => {
        answersMap[ans.question_id] = ans.value;
      });
      setEditAnswers(answersMap);

      if (selectedCase.suspect_reports && selectedCase.suspect_reports.length > 0) {
        const s = selectedCase.suspect_reports[0];
        setEditSuspect({
          id: s.id,
          suspect_name: s.suspect_name || '',
          suspect_mobile: s.suspect_mobile || '',
          suspect_email: s.suspect_email || '',
          suspect_url: s.suspect_url || '',
          suspect_upi: s.suspect_upi || '',
          suspect_social_handle: s.suspect_social_handle || '',
          details: s.details || ''
        });
      } else {
        setEditSuspect({
          id: null,
          suspect_name: '',
          suspect_mobile: '',
          suspect_email: '',
          suspect_url: '',
          suspect_upi: '',
          suspect_social_handle: '',
          details: ''
        });
      }
    }
  }, [selectedCase]);

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;

    setSavingEdit(true);
    
    // Format answers payload
    const answersPayload = Object.keys(editAnswers).map(qIdStr => ({
      question_id: Number(qIdStr),
      value: editAnswers[Number(qIdStr)]
    }));

    // Format suspects payload
    const suspectsPayload = [
      {
        suspect_name: editSuspect.suspect_name || 'UNKNOWN',
        suspect_mobile: editSuspect.suspect_mobile || 'UNKNOWN',
        suspect_email: editSuspect.suspect_email || 'UNKNOWN',
        suspect_url: editSuspect.suspect_url || 'UNKNOWN',
        suspect_upi: editSuspect.suspect_upi || 'UNKNOWN',
        suspect_social_handle: editSuspect.suspect_social_handle || 'UNKNOWN',
        details: editSuspect.details || 'UNKNOWN'
      }
    ];

    const payload = {
      victim_name: selectedCase.is_anonymous ? 'Anonymous' : (editVictimName || null),
      victim_mobile: (selectedCase.is_anonymous || !editVictimMobile) ? null : editVictimMobile,
      victim_email: (selectedCase.is_anonymous || !editVictimEmail) ? null : editVictimEmail,
      victim_gender: selectedCase.victim_gender,
      victim_address: (selectedCase.is_anonymous || !editVictimAddress) ? null : editVictimAddress,
      victim_state: (selectedCase.is_anonymous || !editVictimState) ? null : editVictimState,
      fraud_description: editDescription,
      answers: answersPayload,
      suspect_details: suspectsPayload
    };

    try {
      const response = await api.put(`/complaints/${selectedCase.id}/review-update`, payload);
      setSelectedCase(response.data);
      fetchData(); // Refresh list and stats
      alert('Complaint verified and successfully submitted to NCRP.');
    } catch (err) {
      console.error('Failed to submit review:', err);
      alert('Error finalizing complaint review.');
    } finally {
      setSavingEdit(false);
    }
  };
  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase || !newStatus) return;

    setUpdatingStatus(true);
    try {
      const response = await api.put(`/complaints/${selectedCase.id}/status`, {
        status: newStatus,
        remarks: statusRemarks
      });
      setSelectedCase(response.data);
      setStatusRemarks('');
      setNewStatus('');
      fetchData(); // Refresh list and stats
      alert('Complaint status updated successfully.');
    } catch (err) {
      console.error('Failed to update status:', err);
      alert('Error updating status.');
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleDownloadReceipt = async (complaintId: number, ackNumber: string) => {
    try {
      const response = await api.get(`/complaints/${complaintId}/receipt`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `CyberSathi_ACK_${ackNumber}.pdf`;
      link.click();
    } catch (err) {
      console.error('Failed to download PDF receipt:', err);
    }
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
        
        {/* Banner */}
        <div className="bg-slate-900 text-white rounded-2xl p-6 md:p-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border border-slate-800">
          <div className="space-y-1">
            <span className="bg-orange-500/20 text-orange-400 border border-orange-500/30 px-3 py-0.5 rounded-full text-[9px] font-extrabold tracking-widest uppercase inline-block">
              Investigation Control
            </span>
            <h1 className="text-xl md:text-2xl font-black font-sans">Investigation Officer Console</h1>
            <p className="text-xs text-slate-400">Authenticated user: {user?.full_name} &bull; Access: {user?.role.toUpperCase()}</p>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex items-center space-x-4">
              <div className="bg-gov-light text-gov-indigo p-3.5 rounded-xl border border-gov-border">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gov-slate uppercase tracking-wider">Total Received Complaints</p>
                <p className="text-2xl font-black text-gov-navy mt-0.5">{stats.total_complaints}</p>
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex items-center space-x-4">
              <div className="bg-orange-50 text-orange-600 p-3.5 rounded-xl border border-orange-200">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gov-slate uppercase tracking-wider">Open Investigations</p>
                <p className="text-2xl font-black text-gov-navy mt-0.5">{stats.open_complaints}</p>
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex items-center space-x-4">
              <div className="bg-green-50 text-green-600 p-3.5 rounded-xl border border-green-200">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gov-slate uppercase tracking-wider">Resolved / Closed</p>
                <p className="text-2xl font-black text-gov-navy mt-0.5">{stats.closed_complaints}</p>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h2 className="font-extrabold text-xs text-gov-navy mb-4 uppercase tracking-wider">Search Filters</h2>
          <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
            <div className="flex flex-col">
              <label className="text-[10px] font-bold text-slate-700 mb-1">ACK Number</label>
              <input
                type="text"
                placeholder="e.g. CYBERSATHI-FF-"
                value={filterAck}
                onChange={(e) => setFilterAck(e.target.value)}
                className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
              />
            </div>
            <div className="flex flex-col">
              <label className="text-[10px] font-bold text-slate-700 mb-1">Mobile Number</label>
              <input
                type="text"
                placeholder="Victim phone"
                value={filterMobile}
                onChange={(e) => setFilterMobile(e.target.value)}
                className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
              />
            </div>
            <div className="flex flex-col">
              <label className="text-[10px] font-bold text-slate-700 mb-1">Citizen Name</label>
              <input
                type="text"
                placeholder="Victim name"
                value={filterName}
                onChange={(e) => setFilterName(e.target.value)}
                className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
              />
            </div>
            <div className="flex flex-col">
              <label className="text-[10px] font-bold text-slate-700 mb-1">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="border border-gov-border rounded-lg p-2.5 text-xs outline-none bg-white focus:border-gov-indigo"
              >
                <option value="">-- All --</option>
                {['Pending Employee Review', 'Submitted', 'Under Review', 'Assigned', 'Investigation In Progress', 'Additional Information Required', 'Closed'].map(st => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                className="w-1/2 bg-gov-indigo hover:bg-slate-900 text-white font-bold py-2 rounded-lg text-xs"
              >
                Search
              </button>
              <button
                type="button"
                onClick={handleClearFilters}
                className="w-1/2 border border-gov-border hover:bg-slate-50 text-slate-700 font-bold py-2 rounded-lg text-xs"
              >
                Reset
              </button>
            </div>
          </form>
        </div>

        {/* List Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Table list */}
          <div className={`bg-white border border-slate-200 rounded-2xl p-6 shadow-sm ${selectedCase ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
            <h2 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3 mb-4">Received Cases Logs</h2>
            
            {loading ? (
              <div className="flex py-12 items-center justify-center">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-gov-indigo border-t-transparent"></div>
              </div>
            ) : complaints.length === 0 ? (
              <div className="text-center py-12 text-xs font-bold text-gov-slate">
                No complaints matching the specified filters were found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left text-slate-800">
                  <thead className="text-[10px] font-bold text-gov-slate uppercase tracking-wider bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">ACK Number</th>
                      <th className="py-3 px-4">Victim Name</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Date Filed</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-150">
                    {complaints.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50">
                        <td className="py-3.5 px-4 font-bold text-gov-indigo select-all">{c.acknowledgement_number}</td>
                        <td className="py-3.5 px-4 font-semibold">{c.is_anonymous ? 'Anonymous' : (c.victim_name || 'N/A')}</td>
                        <td className="py-3.5 px-4">{c.category.name}</td>
                        <td className="py-3.5 px-4 text-gov-slate">{new Date(c.submission_timestamp).toLocaleDateString()}</td>
                        <td className="py-3.5 px-4 text-center">
                          <span className={`text-[9px] font-extrabold border px-2 py-0.5 rounded-full uppercase ${
                            c.current_status === 'Pending Employee Review'
                              ? 'bg-red-50 text-red-650 border-red-200 animate-pulse'
                              : 'bg-orange-55 text-orange-600 border border-orange-200'
                          }`}>
                            {c.current_status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => setSelectedCase(c)}
                            className="text-[10px] font-extrabold text-gov-indigo hover:underline inline-flex items-center space-x-0.5"
                          >
                            <Eye className="h-3 w-3" />
                            <span>Inspect</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Inspection sidebar */}
          {selectedCase && (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6 max-h-[750px] overflow-y-auto">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <h3 className="font-extrabold text-sm text-gov-navy uppercase">Case Inspection</h3>
                  <span className="text-[10px] font-bold text-gov-indigo block select-all">{selectedCase.acknowledgement_number}</span>
                </div>
                <button
                  onClick={() => { setSelectedCase(null); setNewStatus(''); }}
                  className="text-xs text-slate-400 hover:text-slate-600 font-bold"
                >
                  Close
                </button>
              </div>

              {selectedCase.current_status === 'Pending Employee Review' ? (
                <form onSubmit={handleReviewSubmit} className="space-y-4 text-xs font-sans">
                  <div className="bg-red-50 border border-red-200 text-red-800 p-3.5 rounded-xl font-bold mb-2 leading-relaxed">
                    CRITICAL: Resolve all highlighted `REVIEW REQUIRED` and `UNKNOWN` fields before finalizing.
                  </div>

                  {/* Victim details */}
                  {!selectedCase.is_anonymous && (
                    <div className="space-y-3 border-b border-slate-100 pb-4">
                      <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Victim Details</h4>
                      
                      <div className="flex flex-col">
                        <label className="text-[10px] font-bold text-slate-650 mb-1">Victim Name</label>
                        <input
                          type="text"
                          value={editVictimName}
                          onChange={(e) => setEditVictimName(e.target.value)}
                          className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                            isHighlight(editVictimName) ? 'border-red-500 bg-red-50 text-red-900 font-bold' : 'border-gov-border bg-white text-slate-800'
                          }`}
                        />
                      </div>

                      <div className="flex flex-col">
                        <label className="text-[10px] font-bold text-slate-655 mb-1">Victim Mobile</label>
                        <input
                          type="text"
                          value={editVictimMobile}
                          onChange={(e) => setEditVictimMobile(e.target.value)}
                          className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                            isHighlight(editVictimMobile) ? 'border-red-500 bg-red-50 text-red-900 font-bold' : 'border-gov-border bg-white text-slate-800'
                          }`}
                        />
                      </div>

                      <div className="flex flex-col">
                        <label className="text-[10px] font-bold text-slate-660 mb-1">Victim Email</label>
                        <input
                          type="text"
                          value={editVictimEmail}
                          onChange={(e) => setEditVictimEmail(e.target.value)}
                          className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                            isHighlight(editVictimEmail) ? 'border-red-500 bg-red-50 text-red-900 font-bold' : 'border-gov-border bg-white text-slate-800'
                          }`}
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex flex-col">
                          <label className="text-[10px] font-bold text-slate-665 mb-1">Victim State</label>
                          <input
                            type="text"
                            value={editVictimState}
                            onChange={(e) => setEditVictimState(e.target.value)}
                            className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                              isHighlight(editVictimState) ? 'border-red-500 bg-red-50 text-red-900 font-bold' : 'border-gov-border bg-white text-slate-800'
                            }`}
                          />
                        </div>
                        <div className="flex flex-col">
                          <label className="text-[10px] font-bold text-slate-670 mb-1">Victim Address</label>
                          <input
                            type="text"
                            value={editVictimAddress}
                            onChange={(e) => setEditVictimAddress(e.target.value)}
                            className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                              isHighlight(editVictimAddress) ? 'border-red-500 bg-red-50 text-red-900 font-bold' : 'border-gov-border bg-white text-slate-800'
                            }`}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Answers & description */}
                  <div className="space-y-3 border-b border-slate-100 pb-4">
                    <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Incident Description & Parameters</h4>
                    
                    <div className="flex flex-col">
                      <label className="text-[10px] font-bold text-slate-600 mb-1">Crime Description Narrative</label>
                      <textarea
                        rows={4}
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        className="border border-gov-border rounded-lg p-2.5 text-xs outline-none bg-white focus:border-gov-indigo text-slate-800 leading-relaxed font-sans"
                      />
                    </div>

                    <div className="space-y-2 mt-2">
                      {selectedCase.answers.map((ans, idx) => (
                        <div key={idx} className="flex flex-col">
                          <label className="text-[10px] font-bold text-slate-600 mb-0.5">{ans.field_label}</label>
                          <input
                            type="text"
                            value={editAnswers[ans.question_id] || ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              setEditAnswers(prev => ({
                                ...prev,
                                [ans.question_id]: val
                              }));
                            }}
                            className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                              isHighlight(editAnswers[ans.question_id]) ? 'border-red-500 bg-red-50 text-red-900 font-bold' : 'border-gov-border bg-white text-slate-800'
                            }`}
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Suspect Details */}
                  <div className="space-y-3 border-b border-slate-100 pb-4">
                    <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px] text-amber-700">Suspect Information</h4>
                    
                    <div className="flex flex-col">
                      <label className="text-[10px] font-bold text-slate-600 mb-1">Suspect Name</label>
                      <input
                        type="text"
                        value={editSuspect.suspect_name}
                        onChange={(e) => setEditSuspect({ ...editSuspect, suspect_name: e.target.value })}
                        className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                          isHighlight(editSuspect.suspect_name) ? 'border-amber-500 bg-amber-50 text-amber-900 font-semibold' : 'border-gov-border bg-white text-slate-800'
                        }`}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex flex-col">
                        <label className="text-[10px] font-bold text-slate-600 mb-1">Suspect Phone</label>
                        <input
                          type="text"
                          value={editSuspect.suspect_mobile}
                          onChange={(e) => setEditSuspect({ ...editSuspect, suspect_mobile: e.target.value })}
                          className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                            isHighlight(editSuspect.suspect_mobile) ? 'border-amber-500 bg-amber-50 text-amber-900 font-semibold' : 'border-gov-border bg-white text-slate-800'
                          }`}
                        />
                      </div>
                      <div className="flex flex-col">
                        <label className="text-[10px] font-bold text-slate-600 mb-1">Suspect UPI ID</label>
                        <input
                          type="text"
                          value={editSuspect.suspect_upi}
                          onChange={(e) => setEditSuspect({ ...editSuspect, suspect_upi: e.target.value })}
                          className={`border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo ${
                            isHighlight(editSuspect.suspect_upi) ? 'border-amber-500 bg-amber-50 text-amber-900 font-semibold' : 'border-gov-border bg-white text-slate-800'
                          }`}
                        />
                      </div>
                    </div>

                    <div className="flex flex-col">
                      <label className="text-[10px] font-bold text-slate-600 mb-1">Suspect Description</label>
                      <textarea
                        rows={3}
                        value={editSuspect.details}
                        onChange={(e) => setEditSuspect({ ...editSuspect, details: e.target.value })}
                        className={`border rounded-lg p-2.5 text-xs outline-none focus:border-gov-indigo ${
                          isHighlight(editSuspect.details) ? 'border-amber-500 bg-amber-50 text-amber-900 font-semibold' : 'border-gov-border bg-white text-slate-800'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Submit button */}
                  <button
                    type="submit"
                    disabled={savingEdit}
                    className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 rounded-lg text-xs transition-all shadow-md flex items-center justify-center space-x-1.5"
                  >
                    {savingEdit ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Submitting to NCRP...</span>
                      </>
                    ) : (
                      <>
                        <CheckSquare className="h-4 w-4" />
                        <span>Confirm & Submit to NCRP</span>
                      </>
                    )}
                  </button>
                </form>
              ) : (
                <>
                  {/* Victim profile */}
                  <div className="space-y-3 border-b border-slate-100 pb-4">
                    <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Victim Information</h4>
                    {selectedCase.is_anonymous ? (
                      <p className="text-red-650 italic font-bold">Anonymous Filing (No profile details shared)</p>
                    ) : (
                      <div className="grid grid-cols-2 gap-y-2">
                        <div>
                          <span className="text-gov-slate font-medium block">Name</span>
                          <span className="font-bold text-slate-800">{selectedCase.victim_name || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-gov-slate font-medium block">Mobile</span>
                          <span className="font-bold text-slate-800">{selectedCase.victim_mobile || 'N/A'}</span>
                        </div>
                        <div className="col-span-2">
                          <span className="text-gov-slate font-medium block">Email</span>
                          <span className="font-bold text-slate-800">{selectedCase.victim_email || 'N/A'}</span>
                        </div>
                        <div className="col-span-2">
                          <span className="text-gov-slate font-medium block">State & Address</span>
                          <span className="font-bold text-slate-800">{selectedCase.victim_state || 'N/A'}, {selectedCase.victim_address || 'N/A'}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Answers */}
                  <div className="space-y-2 border-b border-slate-100 pb-4 text-xs">
                    <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Answers & Description</h4>
                    <p className="text-slate-750 font-medium italic bg-slate-50 p-2.5 rounded border border-slate-150">{selectedCase.fraud_description}</p>
                    
                    <div className="space-y-1 mt-3">
                      {selectedCase.answers.map((ans, idx) => (
                        <div key={idx} className="flex justify-between border-b border-slate-50 py-1">
                          <span className="font-semibold text-slate-500">{ans.field_label}:</span>
                          <span className="font-bold text-slate-800">{ans.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Suspect reports */}
                  {selectedCase.suspect_reports.length > 0 && (
                    <div className="space-y-2 border-b border-slate-100 pb-4 text-xs">
                      <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px] text-red-650">Suspect Registry Entries</h4>
                      {selectedCase.suspect_reports.map((s, idx) => (
                        <div key={idx} className="bg-red-50/20 border border-red-200/50 p-3 rounded-lg space-y-1">
                          {s.suspect_name && <p><span className="font-bold">Name:</span> {s.suspect_name}</p>}
                          {s.suspect_mobile && <p><span className="font-bold">Phone:</span> {s.suspect_mobile}</p>}
                          {s.suspect_upi && <p><span className="font-bold">UPI ID:</span> {s.suspect_upi}</p>}
                          {s.suspect_email && <p><span className="font-bold">Email:</span> {s.suspect_email}</p>}
                          {s.suspect_url && <p><span className="font-bold">URL:</span> {s.suspect_url}</p>}
                          {s.details && <p className="italic text-gov-slate mt-1">Details: {s.details}</p>}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Evidences list */}
                  {selectedCase.evidence_files.length > 0 && (
                    <div className="space-y-2 border-b border-slate-100 pb-4 text-xs">
                      <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Evidence attachments</h4>
                      <ul className="space-y-1.5">
                        {selectedCase.evidence_files.map((ev, idx) => (
                          <li key={idx} className="text-[10px] text-gov-indigo hover:underline flex items-center space-x-1.5">
                            <span>&bull;</span>
                            <a href={`/uploads/${ev.file_path.split(/[\\/]/).pop()}`} target="_blank" rel="noreferrer" className="flex items-center space-x-1">
                              <span>{ev.file_name}</span>
                              <span className="text-[8px] text-gov-slate">({Math.round(ev.file_size / 1024)} KB)</span>
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Update Status form */}
                  <div className="space-y-3 bg-slate-50 border border-slate-200 p-4 rounded-xl text-xs">
                    <h4 className="font-bold text-slate-700 uppercase tracking-wider text-[10px] flex items-center">
                      <Edit className="h-3.5 w-3.5 mr-1 text-gov-indigo" />
                      Action: Update Complaint Status
                    </h4>

                    <form onSubmit={handleUpdateStatus} className="space-y-3">
                      <div className="flex flex-col">
                        <label className="text-[9px] font-bold text-slate-700 mb-1">New status</label>
                        <select
                          required
                          value={newStatus}
                          onChange={(e) => setNewStatus(e.target.value)}
                          className="border border-gov-border rounded-lg p-2 text-xs bg-white outline-none focus:border-gov-indigo"
                        >
                          <option value="">-- Choose --</option>
                          {['Under Review', 'Assigned', 'Investigation In Progress', 'Additional Information Required', 'Closed'].map(st => (
                            <option key={st} value={st}>{st}</option>
                          ))}
                        </select>
                      </div>
                      <div className="flex flex-col">
                        <label className="text-[9px] font-bold text-slate-700 mb-1">Remarks / Comments</label>
                        <textarea
                          required
                          rows={3}
                          placeholder="Specify comments or status update reasons"
                          value={statusRemarks}
                          onChange={(e) => setStatusRemarks(e.target.value)}
                          className="border border-gov-border rounded-lg p-2 text-xs outline-none focus:border-gov-indigo"
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={updatingStatus || !newStatus}
                        className="w-full bg-gov-indigo hover:bg-slate-900 text-white font-bold py-2 rounded text-[10px] transition-all shadow-sm"
                      >
                        {updatingStatus ? 'Updating status...' : 'Submit Status Update'}
                      </button>
                    </form>

                    <button
                      onClick={() => handleDownloadReceipt(selectedCase.id, selectedCase.acknowledgement_number)}
                      className="w-full border border-gov-border hover:bg-slate-100 font-bold py-2 rounded text-[10px] transition-colors flex items-center justify-center space-x-1"
                    >
                      <Download className="h-3 w-3" />
                      <span>Download receipt (PDF)</span>
                    </button>
                  </div>
                </>
              )}

            </div>
          )}

        </div>

      </div>
    </Layout>
  );
};
export default AdminDashboard;
