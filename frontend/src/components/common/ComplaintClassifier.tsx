import React, { useState } from 'react';
import { Sparkles, CheckCircle2, AlertCircle, RefreshCw, Globe, HelpCircle } from 'lucide-react';
import api from '../../services/api';

interface ClassifierResult {
  category_id: number;
  subcategory_id: number;
  category_name: string;
  subcategory_name: string;
  detected_language: string;
  translated_text: string;
  confidence: number;
  keywords: string[];
  explanation: string;
  ambiguous: boolean;
}

interface ComplaintClassifierProps {
  onAccept: (categoryId: number, subcategoryId: number, description: string) => void;
  onChangeSelection: () => void;
  onIgnore: () => void;
  initialDescription?: string;
}

export const ComplaintClassifier: React.FC<ComplaintClassifierProps> = ({
  onAccept,
  onChangeSelection,
  onIgnore,
  initialDescription = '',
}) => {
  const [description, setDescription] = useState(initialDescription);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClassifierResult | null>(null);
  const [actionTaken, setActionTaken] = useState<'accepted' | 'modified' | 'ignored' | null>(null);
  const [attempt, setAttempt] = useState<number>(1);
  const [clarificationAnswers, setClarificationAnswers] = useState({
    platform: '',
    lostMoney: '',
    accountHacked: '',
    blackmailThreats: '',
  });

  const handleAnalyze = async (textToAnalyze?: string): Promise<ClassifierResult | null> => {
    const targetText = textToAnalyze || description;
    if (!targetText.trim()) {
      setError('Please provide a brief description of the incident.');
      return null;
    }

    setLoading(true);
    setError(null);
    setActionTaken(null);

    try {
      const response = await api.post<ClassifierResult>('/ai/classify', {
        description: targetText,
      });
      const data = response.data;
      setResult(data);
      if (!data.ambiguous) {
        setAttempt(1);
        setClarificationAnswers({
          platform: '',
          lostMoney: '',
          accountHacked: '',
          blackmailThreats: '',
        });
      }
      return data;
    } catch (err: any) {
      console.error('AI Classification error:', err);
      setError(
        err.response?.data?.detail || 
        'AI classification is temporarily unavailable. Please proceed manually.'
      );
      return null;
    } finally {
      setLoading(false);
    }
  };

  const onInitialSubmit = async () => {
    await handleAnalyze(description);
  };

  const onAttempt1Submit = async () => {
    const res = await handleAnalyze(description);
    if (res && res.ambiguous) {
      setAttempt(2);
    }
  };

  const onAttempt2Submit = async () => {
    const parts: string[] = [];
    if (clarificationAnswers.platform && clarificationAnswers.platform !== 'None') {
      parts.push(`Platform: ${clarificationAnswers.platform}`);
    }
    if (clarificationAnswers.lostMoney === 'Yes') {
      parts.push('Lost Money: Yes');
    }
    if (clarificationAnswers.accountHacked === 'Yes') {
      parts.push('Account Hacked: Yes');
    }
    if (clarificationAnswers.blackmailThreats === 'Yes') {
      parts.push('Blackmail/Threats: Yes');
    }

    const contextStr = parts.length > 0 ? ` [${parts.join(', ')}]` : '';
    const combinedText = `${description}${contextStr}`;
    
    const res = await handleAnalyze(combinedText);
    if (res && res.ambiguous) {
      setAttempt(3);
    }
  };

  const handleFeedback = async (action: 'accepted' | 'modified' | 'ignored') => {
    setActionTaken(action);
    if (result) {
      try {
        await api.post('/ai/feedback', {
          description: description,
          suggested_category: result.category_name,
          suggested_subcategory: result.subcategory_name,
          action: action,
        });
      } catch (err) {
        console.error('Failed to log AI feedback:', err);
      }
    }

    if (action === 'accepted' && result) {
      onAccept(result.category_id, result.subcategory_id, description);
    } else if (action === 'modified') {
      onChangeSelection();
    } else {
      onIgnore();
    }
  };

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
      <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
        <Sparkles className="h-5 w-5 text-orange-500 animate-pulse" />
        <h3 className="font-extrabold text-sm text-gov-navy uppercase tracking-wider">
          AI CyberCrime Classifier
        </h3>
      </div>

      {!result && !error && (
        <div className="space-y-4">
          <p className="text-xs text-gov-slate leading-relaxed">
            Describe what happened in your own words (you can type in **English, Hindi, Telugu, Tamil, Malayalam, Kannada, Bengali, or Marathi**). The AI will identify the appropriate classification.
          </p>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-700 uppercase">
              Incident Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Someone hacked my Instagram profile and is demanding 5000 rupees by blackmailing me to leak my photos..."
              className="w-full min-h-[100px] text-xs p-3 border border-gov-border rounded-xl focus:ring-1 focus:ring-orange-500 focus:border-orange-500 outline-none text-slate-800 bg-white"
            />
          </div>
          <button
            onClick={onInitialSubmit}
            disabled={loading}
            className="w-full bg-slate-900 hover:bg-slate-850 text-white font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center space-x-1.5 transition-all shadow-sm disabled:opacity-50"
          >
            {loading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>Analyzing Incident Description...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Analyze Incident</span>
              </>
            )}
          </button>
        </div>
      )}

      {error && (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded-xl flex items-start space-x-3 text-xs leading-relaxed">
            <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0" />
            <div>
              <p className="font-bold">AI Assistant Unavailable</p>
              <p className="mt-0.5 text-amber-700">{error}</p>
            </div>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={() => setError(null)}
              className="flex-1 border border-slate-300 hover:bg-slate-100 text-slate-700 font-bold py-2 px-4 rounded-xl text-xs transition-colors"
            >
              Try Again
            </button>
            <button
              onClick={onIgnore}
              className="flex-1 bg-gov-indigo hover:bg-indigo-900 text-white font-bold py-2 px-4 rounded-xl text-xs transition-colors"
            >
              Continue Manually
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {!result.ambiguous ? (
            <div className="border border-slate-200 bg-white rounded-xl p-5 shadow-sm space-y-4 font-sans text-xs">
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <span className="bg-orange-50 text-orange-600 border border-orange-200 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  AI Suggested Classification
                </span>
                <div className="text-right">
                  <span className="text-gov-slate block text-[9px] uppercase font-semibold">Confidence</span>
                  <span className="font-black text-slate-800 text-sm">{result.confidence}%</span>
                </div>
              </div>

              {/* Multilingual Details */}
              {result.detected_language && result.detected_language.toLowerCase() !== 'english' && result.detected_language.toLowerCase() !== 'local classifier (fallback)' && (
                <div className="bg-slate-50 border border-slate-150 p-3 rounded-lg space-y-1.5">
                  <div className="flex items-center text-[10px] font-bold text-gov-indigo gap-1">
                    <Globe className="h-3.5 w-3.5" />
                    <span>Language Detected: {result.detected_language}</span>
                  </div>
                  <p className="text-[11px] text-gov-slate italic leading-relaxed">
                    Translated: "{result.translated_text}"
                  </p>
                </div>
              )}

              {/* Classification Mappings */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase font-bold text-gov-slate block">Category</span>
                  <span className="font-extrabold text-gov-navy text-sm block">{result.category_name}</span>
                </div>
                <div className="space-y-0.5">
                  <span className="text-[9px] uppercase font-bold text-gov-slate block">Subcategory</span>
                  <span className="font-extrabold text-gov-navy text-sm block">{result.subcategory_name}</span>
                </div>
              </div>

              {/* Explainable AI Elements */}
              {result.keywords && result.keywords.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[9px] uppercase font-bold text-gov-slate block">Trigger Keywords</span>
                  <div className="flex flex-wrap gap-1.5">
                    {result.keywords.map((kw, i) => (
                      <span key={i} className="bg-slate-100 border border-slate-200 text-slate-700 px-2 py-0.5 rounded text-[10px] font-medium">
                        ✓ {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {result.explanation && (
                <div className="space-y-1">
                  <span className="text-[9px] uppercase font-bold text-gov-slate block">Reasoning / Explanation</span>
                  <p className="text-gov-slate leading-relaxed bg-orange-50/30 p-2.5 rounded-lg border border-orange-100/50 text-[11px]">
                    {result.explanation}
                  </p>
                </div>
              )}

              {/* User Option Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 pt-3 border-t border-slate-100">
                <button
                  onClick={() => handleFeedback('accepted')}
                  disabled={actionTaken !== null}
                  className="flex-1 bg-orange-600 hover:bg-orange-700 text-white font-bold py-2 px-3 rounded-lg flex items-center justify-center space-x-1 transition-colors disabled:opacity-50"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Accept Suggestion</span>
                </button>
                <button
                  onClick={() => handleFeedback('modified')}
                  disabled={actionTaken !== null}
                  className="flex-1 border border-slate-350 hover:bg-slate-50 text-slate-700 font-bold py-2 px-3 rounded-lg transition-colors disabled:opacity-50"
                >
                  Change Category
                </button>
                <button
                  onClick={() => handleFeedback('ignored')}
                  disabled={actionTaken !== null}
                  className="flex-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 font-bold py-2 px-3 rounded-lg text-center transition-colors disabled:opacity-50"
                >
                  Ignore AI
                </button>
              </div>
            </div>
          ) : (
            // Low Confidence progressive re-prompt display
            <div className="space-y-4">
              {attempt === 1 && (
                <div className="space-y-4">
                  <div className="bg-slate-100 border border-slate-200 text-slate-700 p-4 rounded-xl flex items-start space-x-3 text-xs leading-relaxed">
                    <AlertCircle className="h-5 w-5 text-slate-500 flex-shrink-0" />
                    <div>
                      <p className="font-bold text-slate-800">More Details Needed</p>
                      <p className="mt-0.5 text-gov-slate">
                        Please tell us more about what happened. For example, mention specific payment apps, social media platform names, transaction amounts, or specific threats.
                      </p>
                    </div>
                  </div>
                  
                  <div className="bg-orange-50/50 border border-orange-100 p-3 rounded-lg text-[11px] text-orange-850 leading-relaxed font-sans">
                    <p className="font-bold mb-0.5 text-orange-800">Example Description:</p>
                    <p className="italic">
                      "I received a message on WhatsApp from an unknown number demanding money, claiming they have my private videos. They asked me to pay 10,000 rupees via UPI to a specific number."
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-700 uppercase">
                      Refined Incident Description
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="w-full min-h-[100px] text-xs p-3 border border-gov-border rounded-xl focus:ring-1 focus:ring-orange-500 focus:border-orange-500 outline-none text-slate-800 bg-white"
                    />
                  </div>

                  <button
                    onClick={onAttempt1Submit}
                    disabled={loading}
                    className="w-full bg-slate-900 hover:bg-slate-850 text-white font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center space-x-1.5 transition-all shadow-sm disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        <span>Analyze Again</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {attempt === 2 && (
                <div className="space-y-4">
                  <div className="bg-slate-100 border border-slate-200 text-slate-700 p-4 rounded-xl flex items-start space-x-3 text-xs leading-relaxed">
                    <AlertCircle className="h-5 w-5 text-slate-500 flex-shrink-0" />
                    <div>
                      <p className="font-bold text-slate-800">Clarification Questions</p>
                      <p className="mt-0.5 text-gov-slate">
                        Please answer these simple questions to help us identify your issue:
                      </p>
                    </div>
                  </div>

                  <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-4 text-xs font-sans text-slate-700 shadow-sm">
                    {/* Platform Involved */}
                    <div className="space-y-1.5">
                      <label className="block font-bold text-slate-800">1. Which platform was involved?</label>
                      <select
                        value={clarificationAnswers.platform}
                        onChange={(e) => setClarificationAnswers(prev => ({ ...prev, platform: e.target.value }))}
                        className="w-full p-2 border border-slate-300 rounded-lg bg-white text-xs text-slate-800 outline-none focus:border-orange-500"
                      >
                        <option value="">-- Select Platform --</option>
                        <option value="WhatsApp">WhatsApp</option>
                        <option value="Instagram">Instagram</option>
                        <option value="Facebook">Facebook</option>
                        <option value="UPI/GPay/PhonePe">UPI / GPay / PhonePe</option>
                        <option value="Loan App">Loan App</option>
                        <option value="Stock/Trading App">Stock / Trading App</option>
                        <option value="Crypto Wallet">Crypto Wallet</option>
                        <option value="Email">Email</option>
                        <option value="Other">Other Platform</option>
                        <option value="None">None</option>
                      </select>
                    </div>

                    {/* Did you lose money? */}
                    <div className="space-y-1.5">
                      <label className="block font-bold text-slate-800">2. Did you lose money?</label>
                      <div className="flex space-x-4">
                        {['Yes', 'No'].map((opt) => (
                          <label key={opt} className="flex items-center space-x-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name="lostMoney"
                              value={opt}
                              checked={clarificationAnswers.lostMoney === opt}
                              onChange={(e) => setClarificationAnswers(prev => ({ ...prev, lostMoney: e.target.value }))}
                              className="text-orange-500 focus:ring-orange-500"
                            />
                            <span>{opt}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Was an account hacked? */}
                    <div className="space-y-1.5">
                      <label className="block font-bold text-slate-800">3. Was an account hacked?</label>
                      <div className="flex space-x-4">
                        {['Yes', 'No'].map((opt) => (
                          <label key={opt} className="flex items-center space-x-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name="accountHacked"
                              value={opt}
                              checked={clarificationAnswers.accountHacked === opt}
                              onChange={(e) => setClarificationAnswers(prev => ({ ...prev, accountHacked: e.target.value }))}
                              className="text-orange-500 focus:ring-orange-500"
                            />
                            <span>{opt}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Was there blackmail or threats? */}
                    <div className="space-y-1.5">
                      <label className="block font-bold text-slate-800">4. Was there blackmail or threats?</label>
                      <div className="flex space-x-4">
                        {['Yes', 'No'].map((opt) => (
                          <label key={opt} className="flex items-center space-x-1.5 cursor-pointer">
                            <input
                              type="radio"
                              name="blackmailThreats"
                              value={opt}
                              checked={clarificationAnswers.blackmailThreats === opt}
                              onChange={(e) => setClarificationAnswers(prev => ({ ...prev, blackmailThreats: e.target.value }))}
                              className="text-orange-500 focus:ring-orange-500"
                            />
                            <span>{opt}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={onAttempt2Submit}
                    disabled={loading}
                    className="w-full bg-slate-900 hover:bg-slate-850 text-white font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center space-x-1.5 transition-all shadow-sm disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>Analyzing Answers...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        <span>Submit Clarification</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {attempt === 3 && (
                <div className="space-y-4">
                  <div className="bg-slate-100 border border-slate-200 text-slate-700 p-4 rounded-xl flex items-start space-x-3 text-xs leading-relaxed">
                    <AlertCircle className="h-5 w-5 text-slate-500 flex-shrink-0" />
                    <div>
                      <p className="font-bold text-slate-800">Unable to Confidently Classify</p>
                      <p className="mt-0.5 text-gov-slate">
                        I am unable to confidently classify this complaint. Please select the category manually.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={onChangeSelection}
                    className="w-full bg-gov-indigo hover:bg-indigo-900 text-white font-bold py-2.5 px-4 rounded-xl text-xs transition-colors"
                  >
                    Proceed to Manual Selection
                  </button>
                </div>
              )}
            </div>
          )}

          {actionTaken && (
            <p className="text-[10px] text-gov-slate text-center italic">
              Thank you! Your feedback has been registered to improve accuracy.
            </p>
          )}

          <div className="text-right">
            <button
              onClick={() => {
                setResult(null);
                setError(null);
                setActionTaken(null);
                setAttempt(1);
                setClarificationAnswers({
                  platform: '',
                  lostMoney: '',
                  accountHacked: '',
                  blackmailThreats: '',
                });
              }}
              className="text-[10px] font-bold text-gov-indigo hover:underline inline-flex items-center space-x-0.5"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Reset & Re-analyze</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComplaintClassifier;
