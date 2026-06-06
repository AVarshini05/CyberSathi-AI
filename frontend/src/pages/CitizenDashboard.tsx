import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Complaint, DashboardStats } from '../types';
import Layout from '../components/layout/Layout';
import { Shield, FileText, CheckCircle2, Clock, Plus, Eye, Download, User as UserIcon, LogOut, Upload } from 'lucide-react';

export const CitizenDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  
  // Dashboard states
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [selectedCase, setSelectedCase] = useState<Complaint | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [extraFiles, setExtraFiles] = useState<FileList | null>(null);
  const [uploading, setUploading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const statsRes = await api.get('/complaints/dashboard-stats');
      setStats(statsRes.data);

      const listRes = await api.get('/complaints/user-complaints');
      setComplaints(listRes.data);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDownloadReceipt = async (complaintId: number, ackNumber: string) => {
    try {
      const response = await api.get(`/complaints/${complaintId}/receipt`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `CCRMS_ACK_${ackNumber}.pdf`;
      link.click();
    } catch (err) {
      console.error('Failed to download PDF receipt:', err);
      alert('Error downloading receipt.');
    }
  };

  const handleUploadExtraEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase || !extraFiles || extraFiles.length === 0) return;

    setUploading(true);
    const formData = new FormData();
    for (let i = 0; i < extraFiles.length; i++) {
      formData.append('files', extraFiles[i]);
    }

    try {
      await api.post(`/complaints/${selectedCase.id}/evidence`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('Evidence files uploaded successfully.');
      setExtraFiles(null);
      
      // Refresh details
      const detailRes = await api.get(`/complaints/${selectedCase.id}`);
      setSelectedCase(detailRes.data);
      fetchData();
    } catch (err) {
      console.error('Failed to upload evidence:', err);
      alert('Error uploading files.');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex h-[80vh] items-center justify-center bg-slate-50">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-gov-indigo border-t-transparent"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
        
        {/* Welcome Banner */}
        <div className="bg-slate-900 text-white rounded-2xl p-6 md:p-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border border-slate-800">
          <div className="space-y-1">
            <span className="text-orange-500 font-extrabold text-[10px] tracking-widest uppercase">Citizen Portal</span>
            <h1 className="text-xl md:text-2xl font-black font-sans">Welcome back, {user?.full_name}</h1>
            <p className="text-xs text-slate-400">Mobile ID: {user?.mobile_number} &bull; Email: {user?.email || 'N/A'}</p>
          </div>
          <Link
            to="/file-complaint"
            className="bg-orange-600 hover:bg-orange-700 text-white font-bold px-5 py-2.5 rounded-lg text-xs flex items-center space-x-1.5 transition-all shadow-md"
          >
            <Plus className="h-4 w-4" />
            <span>File New Incident</span>
          </Link>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex items-center space-x-4">
              <div className="bg-gov-light text-gov-indigo p-3.5 rounded-xl border border-gov-border">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gov-slate uppercase tracking-wider">Total Filed Cases</p>
                <p className="text-2xl font-black text-gov-navy mt-0.5">{stats.total_complaints}</p>
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex items-center space-x-4">
              <div className="bg-orange-50 text-orange-600 p-3.5 rounded-xl border border-orange-200">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gov-slate uppercase tracking-wider">Active Investigations</p>
                <p className="text-2xl font-black text-gov-navy mt-0.5">{stats.open_complaints}</p>
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex items-center space-x-4">
              <div className="bg-green-50 text-green-600 p-3.5 rounded-xl border border-green-200">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gov-slate uppercase tracking-wider">Resolved Cases</p>
                <p className="text-2xl font-black text-gov-navy mt-0.5">{stats.closed_complaints}</p>
              </div>
            </div>
          </div>
        )}

        {/* Grid: Case List vs Details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* List Table (2 Cols or full if no selection) */}
          <div className={`bg-white border border-slate-200 rounded-2xl p-6 shadow-sm ${selectedCase ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
            <h2 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3 mb-4">Complaint History</h2>
            
            {complaints.length === 0 ? (
              <div className="text-center py-12 text-xs font-bold text-gov-slate">
                No cybercrime complaints have been reported by this account yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left text-slate-800">
                  <thead className="text-[10px] font-bold text-gov-slate uppercase tracking-wider bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Acknowledgement No</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Subcategory</th>
                      <th className="py-3 px-4">Filed Date</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-150">
                    {complaints.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50">
                        <td className="py-3.5 px-4 font-bold text-gov-indigo select-all">{c.acknowledgement_number}</td>
                        <td className="py-3.5 px-4 font-semibold">{c.category.name}</td>
                        <td className="py-3.5 px-4 text-gov-slate">{c.subcategory.name}</td>
                        <td className="py-3.5 px-4 text-gov-slate">{new Date(c.submission_timestamp).toLocaleDateString()}</td>
                        <td className="py-3.5 px-4 text-center">
                          <span className="text-[9px] font-extrabold bg-orange-50 text-orange-600 border border-orange-200 px-2 py-0.5 rounded-full capitalize">
                            {c.current_status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right space-x-2">
                          <button
                            onClick={() => setSelectedCase(c)}
                            className="text-[10px] font-extrabold text-gov-indigo hover:underline inline-flex items-center space-x-0.5"
                          >
                            <Eye className="h-3 w-3" />
                            <span>View</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Details Sidebar Card */}
          {selectedCase && (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6 animate-slide-in">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <h3 className="font-extrabold text-sm text-gov-navy">Case Details</h3>
                  <span className="text-[10px] font-bold text-gov-indigo block select-all">{selectedCase.acknowledgement_number}</span>
                </div>
                <button
                  onClick={() => setSelectedCase(null)}
                  className="text-xs text-slate-400 hover:text-slate-600 font-bold"
                >
                  Close
                </button>
              </div>

              {/* Quick Info */}
              <div className="space-y-4 text-xs leading-relaxed">
                <div>
                  <span className="text-gov-slate font-bold block">Filing Mode:</span>
                  <span className="font-bold text-slate-800">{selectedCase.is_anonymous ? 'Anonymous' : 'Registered Citizen'}</span>
                </div>
                <div>
                  <span className="text-gov-slate font-bold block">Incident Description:</span>
                  <p className="text-slate-700 italic bg-slate-50 p-2.5 rounded border border-slate-150">{selectedCase.fraud_description}</p>
                </div>
                <div>
                  <span className="text-gov-slate font-bold block mb-1">Dynamic Questionnaire Answers:</span>
                  <div className="space-y-1.5">
                    {selectedCase.answers.map((ans, idx) => (
                      <div key={idx} className="flex justify-between border-b border-slate-100 py-1">
                        <span className="font-semibold text-slate-600">{ans.field_label || `Question ${ans.question_id}`}:</span>
                        <span className="font-bold text-slate-800">{ans.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* File list */}
                {selectedCase.evidence_files.length > 0 && (
                  <div>
                    <span className="text-gov-slate font-bold block mb-1">Evidences Attached:</span>
                    <ul className="space-y-1">
                      {selectedCase.evidence_files.map((ev, idx) => (
                        <li key={idx} className="text-[10px] text-gov-indigo hover:underline flex items-center space-x-1">
                          <span>&bull;</span>
                          <a href={`/uploads/${ev.file_path.split(/[\\/]/).pop()}`} target="_blank" rel="noreferrer">
                            {ev.file_name} ({Math.round(ev.file_size / 1024)} KB)
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Status action history timeline */}
                <div>
                  <span className="text-gov-slate font-bold block mb-1">Action Log:</span>
                  <div className="space-y-2.5 max-h-36 overflow-y-auto pr-1">
                    {selectedCase.status_history.map((hist, idx) => (
                      <div key={idx} className="border-l-2 border-gov-border pl-2 py-0.5 space-y-0.5">
                        <div className="flex justify-between text-[9px] font-bold">
                          <span className="text-gov-indigo">{hist.status}</span>
                          <span className="text-gov-slate">{new Date(hist.updated_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-[10px] text-gov-slate leading-normal">{hist.remarks}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Upload extra evidence form */}
                <form onSubmit={handleUploadExtraEvidence} className="border-t border-slate-100 pt-4 space-y-3">
                  <label className="text-[10px] font-bold text-slate-700 block">Add Additional Evidence File</label>
                  <input
                    type="file"
                    multiple
                    required
                    onChange={(e) => setExtraFiles(e.target.files)}
                    className="w-full text-[10px] file:mr-2 file:py-1 file:px-2 file:rounded-md file:border-0 file:text-[10px] file:font-semibold file:bg-gov-light file:text-gov-indigo file:cursor-pointer"
                  />
                  <button
                    type="submit"
                    disabled={uploading || !extraFiles}
                    className="w-full bg-gov-indigo hover:bg-slate-900 text-white font-bold py-2 rounded text-[10px] flex items-center justify-center space-x-1 transition-all"
                  >
                    <Upload className="h-3 w-3" />
                    <span>{uploading ? 'Uploading...' : 'Upload File'}</span>
                  </button>
                </form>

                {/* Download PDF button */}
                <button
                  onClick={() => handleDownloadReceipt(selectedCase.id, selectedCase.acknowledgement_number)}
                  className="w-full border border-gov-indigo text-gov-indigo hover:bg-gov-light font-bold py-2 rounded text-[10px] flex items-center justify-center space-x-1 transition-colors"
                >
                  <Download className="h-3 w-3" />
                  <span>Download Receipt (PDF)</span>
                </button>
              </div>
            </div>
          )}

        </div>

      </div>
    </Layout>
  );
};
export default CitizenDashboard;
