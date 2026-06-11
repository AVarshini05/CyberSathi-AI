import React from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { CheckCircle2, Download, Printer, FileText, LayoutDashboard } from 'lucide-react';
import Layout from '../components/layout/Layout';

export const ComplaintSuccess: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Retrieve complaint details passed from the filing page
  const { complaint } = (location.state as any) || {};

  if (!complaint) {
    return (
      <Layout>
        <div className="max-w-md mx-auto my-16 text-center space-y-4 p-8 bg-white border border-slate-200 rounded-2xl shadow-sm">
          <p className="text-sm text-gov-slate">No recent complaint submission record was found in the session history.</p>
          <Link to="/" className="inline-block bg-gov-indigo text-white px-6 py-2 rounded-lg text-xs font-bold">
            Return to Home
          </Link>
        </div>
      </Layout>
    );
  }

  const handleDownloadReceipt = async () => {
    try {
      const response = await api.get(`/complaints/${complaint.id}/receipt`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `CyberSathi_ACK_${complaint.acknowledgement_number}.pdf`;
      link.click();
    } catch (err) {
      console.error('Failed to download receipt PDF:', err);
      alert('Error downloading receipt PDF. Please try again.');
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto py-16 px-4">
        <div className="bg-white border border-slate-200 shadow-xl rounded-2xl p-8 space-y-8 text-center">
          
          {/* Success Header */}
          <div className="space-y-3">
            <CheckCircle2 className="h-16 w-16 text-green-600 fill-green-50 mx-auto" />
            <h1 className="text-2xl md:text-3xl font-black text-gov-navy font-sans tracking-tight">
              Complaint Submitted Successfully
            </h1>
            <p className="text-xs text-gov-slate">
              Your incident report has been registered in the database. Notifications have been dispatched.
            </p>
          </div>

          {/* Acknowledgement Box */}
          <div className="bg-gov-light border border-gov-border rounded-xl p-6 text-left text-xs space-y-4">
            <div className="flex justify-between items-center py-2.5 border-b border-slate-200">
              <span className="font-bold text-gov-slate">Acknowledgement Number</span>
              <span className="font-extrabold text-sm text-gov-indigo select-all">{complaint.acknowledgement_number}</span>
            </div>
            <div className="flex justify-between items-center py-2.5 border-b border-slate-200">
              <span className="font-bold text-gov-slate">Complaint Category</span>
              <span className="font-bold text-slate-800">{complaint.category?.name || "Cyber Crime"}</span>
            </div>
            <div className="flex justify-between items-center py-2.5 border-b border-slate-200">
              <span className="font-bold text-gov-slate">Submission Date</span>
              <span className="font-bold text-slate-800">
                {new Date(complaint.submission_timestamp).toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center py-2.5">
              <span className="font-bold text-gov-slate">Current Status</span>
              <span className="text-[10px] bg-orange-600 text-white px-2 py-0.5 rounded-full font-bold uppercase">
                {complaint.current_status}
              </span>
            </div>
          </div>

          {/* Buttons Action Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 border-t border-slate-100">
            <button
              onClick={handleDownloadReceipt}
              className="bg-gov-indigo hover:bg-slate-900 text-white font-bold py-3 rounded-lg text-xs flex items-center justify-center space-x-2 transition-all shadow-md"
            >
              <Download className="h-4 w-4" />
              <span>Download Acknowledgement PDF</span>
            </button>
            <button
              onClick={handlePrint}
              className="bg-slate-850 hover:bg-slate-800 text-slate-350 border border-slate-700 hover:text-white font-bold py-3 rounded-lg text-xs flex items-center justify-center space-x-2 transition-all"
            >
              <Printer className="h-4 w-4" />
              <span>Print Receipt</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Link
              to={`/track?query=${complaint.acknowledgement_number}`}
              className="border border-gov-border hover:bg-slate-50 text-gov-indigo font-bold py-3 rounded-lg text-xs flex items-center justify-center space-x-2 transition-colors"
            >
              <FileText className="h-4 w-4" />
              <span>Track Complaint Timeline</span>
            </Link>
            <Link
              to="/dashboard"
              className="border border-gov-border hover:bg-slate-50 text-slate-700 font-bold py-3 rounded-lg text-xs flex items-center justify-center space-x-2 transition-colors"
            >
              <LayoutDashboard className="h-4 w-4" />
              <span>Go to Citizen Dashboard</span>
            </Link>
          </div>

        </div>
      </div>
    </Layout>
  );
};
export default ComplaintSuccess;
