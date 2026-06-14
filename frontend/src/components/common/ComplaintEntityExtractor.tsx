import React, { useState, useEffect } from 'react';
import { Sparkles, CheckCircle2, AlertTriangle, RefreshCw, Eye, ShieldAlert, Check, X } from 'lucide-react';
import api from '../../services/api';

interface ExtractedField {
  value: string | null;
  source: string | null;
  status: 'valid' | 'needs_review';
  currency?: string | null;
}

interface ExtractionResponse {
  extracted_fields: Record<string, ExtractedField>;
  confidence_scores: Record<string, number>;
  evidence_flags: Record<string, boolean>;
  warnings: string[];
}

interface ComplaintEntityExtractorProps {
  description: string;
  onApply: (fields: Record<string, string>, evidenceFlags: Record<string, boolean>) => void;
  onIgnore: () => void;
}

export const ComplaintEntityExtractor: React.FC<ComplaintEntityExtractorProps> = ({
  description,
  onApply,
  onIgnore,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ExtractionResponse | null>(null);
  const [localFields, setLocalFields] = useState<Record<string, string>>({});
  const [actionTaken, setActionTaken] = useState<'applied' | 'ignored' | null>(null);

  useEffect(() => {
    const runExtraction = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.post<ExtractionResponse>('/ai/extract', {
          description,
        });
        setData(response.data);
        
        // Initialize local editable fields
        const initialFields: Record<string, string> = {};
        Object.keys(response.data.extracted_fields).forEach((key) => {
          // If status is needs_review, do NOT prefill the field in form by default, but let user see it inside extraction card
          initialFields[key] = response.data.extracted_fields[key].value || '';
        });
        setLocalFields(initialFields);
      } catch (err: any) {
        console.error('AI Extraction error:', err);
        setError(
          err.response?.data?.detail || 
          'AI detail extraction is temporarily unavailable. Please fill the questionnaire manually.'
        );
      } finally {
        setLoading(false);
      }
    };

    if (description.trim()) {
      runExtraction();
    }
  }, [description]);

  const handleApply = () => {
    if (!data) return;
    
    // Clean up fields to only apply valid ones (non needs_review ones by default or verified user entries)
    const finalFields: Record<string, string> = {};
    Object.keys(localFields).forEach((key) => {
      const fieldData = data.extracted_fields[key];
      // If the field was invalid initially and the user didn't modify it, do not apply it
      if (fieldData?.status === 'needs_review' && localFields[key] === fieldData.value) {
        finalFields[key] = '';
      } else {
        finalFields[key] = localFields[key];
      }
    });

    setActionTaken('applied');
    onApply(finalFields, data.evidence_flags);
  };

  const handleIgnore = () => {
    setActionTaken('ignored');
    onIgnore();
  };

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col items-center justify-center space-y-3 font-sans text-xs">
        <RefreshCw className="h-6 w-6 text-orange-500 animate-spin" />
        <span className="text-gov-navy font-bold">AI is extracting details from your description...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded-2xl flex items-start space-x-3 text-xs leading-relaxed font-sans">
        <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
        <div>
          <p className="font-bold">Extraction Unavailable</p>
          <p className="mt-0.5 text-amber-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // Render groupings helper
  const renderFieldInput = (label: string, fieldName: string) => {
    const fieldData = data.extracted_fields[fieldName];
    if (!fieldData) return null;

    const val = localFields[fieldName] || '';
    const conf = data.confidence_scores[fieldName] || 0;
    const isReview = fieldData.status === 'needs_review';

    let badgeClass = 'bg-red-50 text-red-700 border-red-200';
    let badgeText = 'Needs Review';
    if (!isReview) {
      if (conf >= 80) {
        badgeClass = 'bg-green-50 text-green-700 border-green-200';
        badgeText = `${conf}% High`;
      } else if (conf >= 70) {
        badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
        badgeText = `${conf}% Med`;
      } else if (conf > 0) {
        badgeClass = 'bg-red-50 text-red-700 border-red-200';
        badgeText = `${conf}% Low`;
      } else {
        return null; // Don't show fields that were not extracted
      }
    }

    return (
      <div className="space-y-1 bg-slate-50 border border-slate-150 p-3 rounded-xl shadow-xs" key={fieldName}>
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-bold text-slate-700 uppercase tracking-tight">{label}</span>
          <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${badgeClass}`}>
            {badgeText}
          </span>
        </div>
        <input
          type="text"
          value={val}
          onChange={(e) => setLocalFields((prev) => ({ ...prev, [fieldName]: e.target.value }))}
          className={`w-full text-xs p-2 border rounded-lg focus:ring-1 focus:ring-orange-500 focus:border-orange-500 outline-none bg-white text-slate-800 ${
            isReview ? 'border-red-300 bg-red-50/10' : 'border-slate-300'
          }`}
        />
        {fieldData.source && (
          <p className="text-[9px] text-gov-slate leading-tight font-medium italic mt-0.5">
            Source: "{fieldData.source}"
          </p>
        )}
      </div>
    );
  };

  const hasExtractedFields = Object.values(data.confidence_scores).some((score) => score > 0);

  return (
    <div className="border border-slate-200 bg-white rounded-2xl p-5 shadow-sm space-y-4 font-sans text-xs">
      <div className="flex justify-between items-center border-b border-slate-100 pb-3">
        <span className="bg-orange-50 text-orange-600 border border-orange-200 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase flex items-center gap-1">
          <Sparkles className="h-3 w-3" />
          AI Extracted Details Preview
        </span>
        <span className="text-gov-slate text-[10px] font-medium italic">
          Human-in-the-Loop Review
        </span>
      </div>

      {data.warnings.length > 0 && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-3.5 rounded-xl space-y-1">
          <div className="flex items-center space-x-1.5 font-bold text-red-900">
            <ShieldAlert className="h-4 w-4 text-red-700" />
            <span>AI Entity Validation Warnings</span>
          </div>
          <ul className="list-disc list-inside text-[10px] text-red-700 leading-normal pl-1">
            {data.warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {hasExtractedFields ? (
        <div className="space-y-4 max-h-[350px] overflow-y-auto pr-1">
          {/* Victim Details Group */}
          {Object.keys(localFields).some((k) => k.startsWith('victim_') && (data.confidence_scores[k] > 0 || data.extracted_fields[k].status === 'needs_review')) && (
            <div className="space-y-2">
              <h4 className="font-extrabold text-[10px] text-gov-navy uppercase tracking-wider border-b border-slate-100 pb-1">
                Victim Details
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {renderFieldInput('Victim Name', 'victim_name')}
                {renderFieldInput('Victim Mobile', 'victim_mobile')}
                {renderFieldInput('Victim Email', 'victim_email')}
                {renderFieldInput('Victim Gender', 'victim_gender')}
                {renderFieldInput('Victim State', 'victim_state')}
                {renderFieldInput('Victim City', 'victim_city')}
              </div>
            </div>
          )}

          {/* Incident Details Group */}
          {Object.keys(localFields).some((k) => 
            (k.startsWith('incident_') || k === 'platform' || k === 'account_id' || k === 'amount_lost' || k === 'amount_demanded' || k === 'threat_type') && 
            (data.confidence_scores[k] > 0 || data.extracted_fields[k]?.status === 'needs_review')
          ) && (
            <div className="space-y-2">
              <h4 className="font-extrabold text-[10px] text-gov-navy uppercase tracking-wider border-b border-slate-100 pb-1">
                Incident Details
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {renderFieldInput('Incident Date', 'incident_date')}
                {renderFieldInput('Incident Time', 'incident_time')}
                {renderFieldInput('Platform Involved', 'platform')}
                {renderFieldInput('Account/User ID', 'account_id')}
                {renderFieldInput(
                  `Amount Lost (${data.extracted_fields.amount_lost?.currency || '₹'})`,
                  'amount_lost'
                )}
                {renderFieldInput(
                  `Amount Demanded (${data.extracted_fields.amount_demanded?.currency || '₹'})`,
                  'amount_demanded'
                )}
                {renderFieldInput('Threat Type', 'threat_type')}
                {renderFieldInput('Fraud Channel', 'fraud_channel')}
              </div>
            </div>
          )}

          {/* Cybercrime Indicators Section */}
          {(data.extracted_fields.account_compromised?.value ||
            data.extracted_fields.blackmail_indicator?.value ||
            data.extracted_fields.sextortion_indicator?.value ||
            data.extracted_fields.impersonation_indicator?.value) && (
            <div className="space-y-2">
              <h4 className="font-extrabold text-[10px] text-gov-navy uppercase tracking-wider border-b border-slate-100 pb-1">
                Cybercrime Indicators Detected
              </h4>
              <div className="flex flex-wrap gap-2 py-1">
                {data.extracted_fields.account_compromised?.value && (
                  <span className="bg-red-50 text-red-700 border border-red-200 px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 shadow-xs">
                    ⚠️ Account Compromised
                  </span>
                )}
                {data.extracted_fields.blackmail_indicator?.value && (
                  <span className="bg-purple-50 text-purple-700 border border-purple-200 px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 shadow-xs">
                    ⚠️ Blackmail Detected
                  </span>
                )}
                {data.extracted_fields.sextortion_indicator?.value && (
                  <span className="bg-rose-50 text-rose-750 border border-rose-200 px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 shadow-xs">
                    ⚠️ Sextortion Detected
                  </span>
                )}
                {data.extracted_fields.impersonation_indicator?.value && (
                  <span className="bg-amber-50 text-amber-700 border border-amber-250 px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 shadow-xs">
                    ⚠️ Impersonation Detected
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Financial Details Group */}
          {Object.keys(localFields).some((k) => (k === 'upi_id' || k === 'account_number' || k === 'transaction_id' || k === 'utr_number' || k === 'reference_number' || k === 'crypto_wallet_address' || k === 'crypto_type') && (data.confidence_scores[k] > 0 || data.extracted_fields[k]?.status === 'needs_review')) && (
            <div className="space-y-2">
              <h4 className="font-extrabold text-[10px] text-gov-navy uppercase tracking-wider border-b border-slate-100 pb-1">
                Financial Details
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {renderFieldInput('UPI ID', 'upi_id')}
                {renderFieldInput('Account Number', 'account_number')}
                {renderFieldInput('Transaction ID', 'transaction_id')}
                {renderFieldInput('UTR Number', 'utr_number')}
                {renderFieldInput('Reference Number', 'reference_number')}
                {renderFieldInput('Crypto Wallet Address', 'crypto_wallet_address')}
                {renderFieldInput('Crypto Coin Type', 'crypto_type')}
              </div>
            </div>
          )}

          {/* Suspect Details Group */}
          {Object.keys(localFields).some((k) => (k.startsWith('suspect_') || k === 'claimed_identity') && (data.confidence_scores[k] > 0 || data.extracted_fields[k]?.status === 'needs_review')) && (
            <div className="space-y-2">
              <h4 className="font-extrabold text-[10px] text-gov-navy uppercase tracking-wider border-b border-slate-100 pb-1">
                Suspect Details
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {renderFieldInput('Suspect Name', 'suspect_name')}
                {renderFieldInput('Suspect Mobile', 'suspect_mobile')}
                {renderFieldInput('Suspect UPI ID', 'suspect_upi')}
                {renderFieldInput('Suspect Account', 'suspect_account_number')}
                {renderFieldInput('Suspect Social Media ID', 'suspect_social_media_id')}
                {renderFieldInput('Website URL', 'website_url')}
                {renderFieldInput('Claimed Identity', 'claimed_identity')}
              </div>
            </div>
          )}

          {/* Evidence Flag Indicators */}
          {Object.values(data.evidence_flags).some((flag) => flag) && (
            <div className="space-y-2">
              <h4 className="font-extrabold text-[10px] text-gov-navy uppercase tracking-wider border-b border-slate-100 pb-1">
                AI Detected Evidence Mentions
              </h4>
              <div className="flex flex-wrap gap-2 py-1">
                {data.evidence_flags.screenshot_mentioned && (
                  <span className="bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded text-[10px] font-bold">
                    ✓ Screenshot Mentioned
                  </span>
                )}
                {data.evidence_flags.bank_receipt_mentioned && (
                  <span className="bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded text-[10px] font-bold">
                    ✓ Bank Receipt Mentioned
                  </span>
                )}
                {data.evidence_flags.chat_screenshot_mentioned && (
                  <span className="bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded text-[10px] font-bold">
                    ✓ Chat Screenshot Mentioned
                  </span>
                )}
                {data.evidence_flags.video_mentioned && (
                  <span className="bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded text-[10px] font-bold">
                    ✓ Video Mentioned
                  </span>
                )}
                {data.evidence_flags.audio_mentioned && (
                  <span className="bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded text-[10px] font-bold">
                    ✓ Audio Mentioned
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-slate-50 border border-slate-200 text-slate-500 py-6 text-center rounded-xl leading-relaxed italic">
          No relevant details could be confidently extracted from the description text.
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 pt-3 border-t border-slate-100">
        <button
          onClick={handleApply}
          disabled={actionTaken !== null || !hasExtractedFields}
          className="flex-1 bg-orange-600 hover:bg-orange-700 text-white font-bold py-2.5 px-4 rounded-xl flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
        >
          <CheckCircle2 className="h-4 w-4" />
          <span>Apply Extracted Data</span>
        </button>
        <button
          onClick={handleIgnore}
          disabled={actionTaken !== null}
          className="flex-1 border border-slate-350 hover:bg-slate-50 text-slate-700 font-bold py-2.5 px-4 rounded-xl transition-colors disabled:opacity-50"
        >
          Ignore AI Extraction
        </button>
      </div>

      {actionTaken && (
        <p className="text-[10px] text-gov-slate text-center italic mt-2">
          {actionTaken === 'applied' 
            ? '✓ Extracted details successfully pre-filled. Please review them in subsequent steps.' 
            : 'AI extraction ignored. Manual entry remains the source of truth.'}
        </p>
      )}
    </div>
  );
};

export default ComplaintEntityExtractor;
