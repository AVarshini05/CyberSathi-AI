import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { ComplaintCategory, ComplaintSubcategory, ComplaintQuestion } from '../types';
import FileUpload from '../components/common/FileUpload';
import DynamicForm from '../components/common/DynamicForm';
import Layout from '../components/layout/Layout';
import { ShieldAlert, User, Info, Link as LinkIcon, Upload, CheckSquare, ChevronRight, ChevronLeft } from 'lucide-react';

export const ComplaintForm: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  // Form step controls
  const [step, setStep] = useState(1);
  const stepsList = ['Category Selection', 'Victim Info', 'Incident Details', 'Suspect Details', 'Evidence Upload', 'Review & Submit'];

  // Master Data
  const [categories, setCategories] = useState<ComplaintCategory[]>([]);
  const [subcategories, setSubcategories] = useState<ComplaintSubcategory[]>([]);
  const [questions, setQuestions] = useState<ComplaintQuestion[]>([]);

  // Selected Data IDs
  const [selectedCatId, setSelectedCatId] = useState<number | ''>('');
  const [selectedSubId, setSelectedSubId] = useState<number | ''>('');

  // Anonymous reporting toggle
  const [isAnonymous, setIsAnonymous] = useState(false);

  // Evidence Files State
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  // Suspects state
  const [suspects, setSuspects] = useState<any[]>([
    { suspect_name: '', suspect_mobile: '', suspect_email: '', suspect_url: '', suspect_upi: '', suspect_social_handle: '', details: '' }
  ]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors }
  } = useForm({
    defaultValues: {
      victim_name: '',
      victim_mobile: '',
      victim_email: '',
      victim_gender: '',
      victim_address: '',
      victim_state: '',
      fraud_description: ''
    }
  });

  // Watch fields for summary review
  const formValues = watch();

  // Load categories on mount
  useEffect(() => {
    const fetchCats = async () => {
      try {
        const response = await api.get('/complaints/categories');
        setCategories(response.data);
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    };
    fetchCats();
  }, []);

  // Load subcategories when category changes
  useEffect(() => {
    if (!selectedCatId) {
      setSubcategories([]);
      setSelectedSubId('');
      return;
    }
    const fetchSubs = async () => {
      try {
        const response = await api.get(`/complaints/categories/${selectedCatId}/subcategories`);
        setSubcategories(response.data);
        setSelectedSubId('');
      } catch (err) {
        console.error('Failed to load subcategories:', err);
      }
    };
    fetchSubs();

    // Anonymous toggle logic: only allow for Category 3 (Women/Children - code WC)
    const category = categories.find(c => c.id === Number(selectedCatId));
    if (category?.code !== 'WC') {
      setIsAnonymous(false);
    }
  }, [selectedCatId, categories]);

  // Load questions when subcategory changes
  useEffect(() => {
    if (!selectedSubId) {
      setQuestions([]);
      return;
    }
    const fetchQuestions = async () => {
      try {
        const response = await api.get(`/complaints/subcategories/${selectedSubId}/questions`);
        setQuestions(response.data);
      } catch (err) {
        console.error('Failed to load questions:', err);
      }
    };
    fetchQuestions();
  }, [selectedSubId]);

  const handleAddSuspect = () => {
    setSuspects([...suspects, { suspect_name: '', suspect_mobile: '', suspect_email: '', suspect_url: '', suspect_upi: '', suspect_social_handle: '', details: '' }]);
  };

  const handleRemoveSuspect = (index: number) => {
    const list = [...suspects];
    list.splice(index, 1);
    setSuspects(list);
  };

  const handleSuspectChange = (index: number, field: string, val: string) => {
    const list = [...suspects];
    list[index][field] = val;
    setSuspects(list);
  };

  const nextStep = () => setStep(prev => Math.min(prev + 1, 6));
  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

  const onSubmit = async () => {
    // Collect all form answers
    const answersPayload = questions.map(q => {
      const fieldVal = (formValues as any)[`dynamic_${q.id}`];
      return {
        question_id: q.id,
        value: fieldVal ? String(fieldVal) : ''
      };
    });

    // Clean suspect list
    const suspectsPayload = suspects.filter(s =>
      s.suspect_name || s.suspect_mobile || s.suspect_email || s.suspect_url || s.suspect_upi || s.suspect_social_handle || s.details
    );

    const payload = {
      category_id: Number(selectedCatId),
      subcategory_id: Number(selectedSubId),
      is_anonymous: isAnonymous,
      victim_name: isAnonymous ? 'Anonymous' : formValues.victim_name,
      victim_mobile: isAnonymous ? null : formValues.victim_mobile,
      victim_email: isAnonymous ? null : formValues.victim_email,
      victim_gender: isAnonymous ? null : formValues.victim_gender,
      victim_address: isAnonymous ? null : formValues.victim_address,
      victim_state: isAnonymous ? null : formValues.victim_state,
      fraud_description: formValues.fraud_description,
      answers: answersPayload,
      suspect_details: suspectsPayload
    };

    try {
      // 1. Submit complaint
      const response = await api.post('/complaints/file', payload);
      const createdComplaint = response.data;

      // 2. Upload evidence files if present
      if (selectedFiles.length > 0) {
        const formData = new FormData();
        selectedFiles.forEach(file => {
          formData.append('files', file);
        });

        await api.post(`/complaints/${createdComplaint.id}/evidence`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
      }

      // 3. Redirect to success page
      navigate('/complaint-success', { state: { complaint: createdComplaint } });

    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || 'An error occurred while submitting. Please try again.');
    }
  };

  const renderStepContent = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-6">
            <h3 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3 flex items-center">
              <ShieldAlert className="h-5 w-5 text-orange-600 mr-2" />
              Select Crime Classification
            </h3>
            
            <div className="flex flex-col">
              <label className="text-xs font-bold text-slate-700 mb-1.5">Crime Category <span className="text-red-500">*</span></label>
              <select
                required
                value={selectedCatId}
                onChange={(e) => setSelectedCatId(e.target.value ? Number(e.target.value) : '')}
                className="border border-gov-border rounded-lg p-2.5 text-sm outline-none bg-white focus:border-gov-indigo"
              >
                <option value="">-- Choose Category --</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            {selectedCatId && (
              <div className="flex flex-col">
                <label className="text-xs font-bold text-slate-700 mb-1.5">Incident Subcategory <span className="text-red-500">*</span></label>
                <select
                  required
                  value={selectedSubId}
                  onChange={(e) => setSelectedSubId(e.target.value ? Number(e.target.value) : '')}
                  className="border border-gov-border rounded-lg p-2.5 text-sm outline-none bg-white focus:border-gov-indigo"
                >
                  <option value="">-- Choose Subcategory --</option>
                  {subcategories.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Anonymous Toggle Option (For Women/Children category) */}
            {categories.find(c => c.id === Number(selectedCatId))?.code === 'WC' && (
              <div className="flex items-center space-x-3 bg-red-50 border border-red-200 p-4 rounded-xl">
                <input
                  type="checkbox"
                  id="anonCheckbox"
                  checked={isAnonymous}
                  onChange={(e) => setIsAnonymous(e.target.checked)}
                  className="h-4.5 w-4.5 text-gov-indigo border-gov-border rounded"
                />
                <label htmlFor="anonCheckbox" className="text-xs font-bold text-red-700 cursor-pointer">
                  File this complaint anonymously (Do not share victim details)
                </label>
              </div>
            )}
          </div>
        );
      case 2:
        return (
          <div className="space-y-6">
            <h3 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3 flex items-center">
              <User className="h-5 w-5 text-gov-indigo mr-2" />
              Victim Information
            </h3>

            {isAnonymous ? (
              <div className="p-6 bg-slate-100 border border-slate-200 rounded-2xl text-center text-xs font-bold text-gov-slate">
                Anonymous Mode Activated. Victim personal details will be omitted from the report.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="flex flex-col">
                  <label className="text-xs font-bold text-slate-700 mb-1.5">Victim Full Name</label>
                  <input
                    type="text"
                    placeholder="Enter name"
                    {...register('victim_name')}
                    className="border border-gov-border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo"
                  />
                </div>

                <div className="flex flex-col">
                  <label className="text-xs font-bold text-slate-700 mb-1.5">Mobile Number</label>
                  <input
                    type="tel"
                    placeholder="10-digit mobile"
                    {...register('victim_mobile')}
                    className="border border-gov-border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo"
                  />
                </div>

                <div className="flex flex-col">
                  <label className="text-xs font-bold text-slate-700 mb-1.5">Email Address</label>
                  <input
                    type="email"
                    placeholder="Enter email"
                    {...register('victim_email')}
                    className="border border-gov-border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo"
                  />
                </div>

                <div className="flex flex-col">
                  <label className="text-xs font-bold text-slate-700 mb-1.5">Gender</label>
                  <select
                    {...register('victim_gender')}
                    className="border border-gov-border rounded-lg p-2.5 text-sm outline-none bg-white focus:border-gov-indigo"
                  >
                    <option value="">-- Choose Gender --</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="flex flex-col sm:col-span-2">
                  <label className="text-xs font-bold text-slate-700 mb-1.5">Resident State</label>
                  <select
                    {...register('victim_state')}
                    className="border border-gov-border rounded-lg p-2.5 text-sm outline-none bg-white focus:border-gov-indigo"
                  >
                    <option value="">-- Select State --</option>
                    {['Andhra Pradesh', 'Assam', 'Bihar', 'Delhi', 'Gujarat', 'Karnataka', 'Kerala', 'Maharashtra', 'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'West Bengal'].map(st => (
                      <option key={st} value={st}>{st}</option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col sm:col-span-2">
                  <label className="text-xs font-bold text-slate-700 mb-1.5">Address</label>
                  <textarea
                    rows={2}
                    placeholder="Full residential address"
                    {...register('victim_address')}
                    className="border border-gov-border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo"
                  />
                </div>
              </div>
            )}
          </div>
        );
      case 3:
        return (
          <div className="space-y-6 font-sans">
            <h3 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3 flex items-center">
              <Info className="h-5 w-5 text-gov-indigo mr-2" />
              Incident Questionnaire Details
            </h3>

            {/* Render dynamic form fields based on database questions */}
            <DynamicForm questions={questions} register={register} errors={errors} />

            <div className="flex flex-col pt-2">
              <label className="text-xs font-bold text-slate-700 mb-1.5">Describe Incident / Modus Operandi <span className="text-red-500">*</span></label>
              <textarea
                rows={4}
                required
                placeholder="Provide details about what happened, how the fraud occurred, etc."
                {...register('fraud_description', { required: true })}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors.fraud_description ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
              {errors.fraud_description && (
                <span className="text-[10px] font-semibold text-red-500 mt-1">Description is required</span>
              )}
            </div>
          </div>
        );
      case 4:
        return (
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="font-extrabold text-sm text-gov-navy flex items-center">
                <LinkIcon className="h-5 w-5 text-gov-indigo mr-2" />
                Report Suspect Details
              </h3>
              <button
                type="button"
                onClick={handleAddSuspect}
                className="bg-gov-light hover:bg-slate-100 border border-gov-border text-gov-indigo font-bold px-3 py-1.5 rounded-lg text-xs"
              >
                + Add Suspect ID
              </button>
            </div>

            {suspects.map((suspect, idx) => (
              <div key={idx} className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-4 relative">
                {suspects.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveSuspect(idx)}
                    className="absolute top-4 right-4 text-xs font-bold text-red-500 hover:underline"
                  >
                    Remove
                  </button>
                )}
                <h4 className="font-bold text-xs text-gov-navy uppercase tracking-wider">Suspect #{idx + 1}</h4>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex flex-col">
                    <label className="text-[10px] font-bold text-slate-600 mb-1">Suspect Name</label>
                    <input
                      type="text"
                      placeholder="e.g. John Doe"
                      value={suspect.suspect_name}
                      onChange={(e) => handleSuspectChange(idx, 'suspect_name', e.target.value)}
                      className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
                    />
                  </div>
                  <div className="flex flex-col">
                    <label className="text-[10px] font-bold text-slate-600 mb-1">Mobile Number</label>
                    <input
                      type="tel"
                      placeholder="e.g. 9876543210"
                      value={suspect.suspect_mobile}
                      onChange={(e) => handleSuspectChange(idx, 'suspect_mobile', e.target.value)}
                      className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
                    />
                  </div>
                  <div className="flex flex-col">
                    <label className="text-[10px] font-bold text-slate-600 mb-1">Email Address</label>
                    <input
                      type="email"
                      placeholder="e.g. suspect@domain.com"
                      value={suspect.suspect_email}
                      onChange={(e) => handleSuspectChange(idx, 'suspect_email', e.target.value)}
                      className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
                    />
                  </div>
                  <div className="flex flex-col">
                    <label className="text-[10px] font-bold text-slate-600 mb-1">UPI ID</label>
                    <input
                      type="text"
                      placeholder="e.g. suspect@upi"
                      value={suspect.suspect_upi}
                      onChange={(e) => handleSuspectChange(idx, 'suspect_upi', e.target.value)}
                      className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
                    />
                  </div>
                  <div className="flex flex-col">
                    <label className="text-[10px] font-bold text-slate-600 mb-1">Website URL</label>
                    <input
                      type="url"
                      placeholder="e.g. http://fraud-web.com"
                      value={suspect.suspect_url}
                      onChange={(e) => handleSuspectChange(idx, 'suspect_url', e.target.value)}
                      className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
                    />
                  </div>
                  <div className="flex flex-col">
                    <label className="text-[10px] font-bold text-slate-600 mb-1">Social Handle</label>
                    <input
                      type="text"
                      placeholder="e.g. @suspect_insta"
                      value={suspect.suspect_social_handle}
                      onChange={(e) => handleSuspectChange(idx, 'suspect_social_handle', e.target.value)}
                      className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
                    />
                  </div>
                  <div className="flex flex-col sm:col-span-2">
                    <label className="text-[10px] font-bold text-slate-600 mb-1">Suspect Description / Details</label>
                    <textarea
                      rows={2}
                      placeholder="Enter physical description, chats, bank info, etc."
                      value={suspect.details}
                      onChange={(e) => handleSuspectChange(idx, 'details', e.target.value)}
                      className="border border-gov-border rounded-lg p-2 text-xs outline-none bg-white focus:border-gov-indigo"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
      case 5:
        return (
          <div className="space-y-6">
            <h3 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3 flex items-center">
              <Upload className="h-5 w-5 text-gov-indigo mr-2" />
              Evidence Attachment Upload
            </h3>
            
            <FileUpload
              selectedFiles={selectedFiles}
              onFilesSelected={(files) => setSelectedFiles([...selectedFiles, ...files])}
              onRemoveFile={(idx) => {
                const list = [...selectedFiles];
                list.splice(idx, 1);
                setSelectedFiles(list);
              }}
            />
          </div>
        );
      case 6:
        return (
          <div className="space-y-6 text-xs font-sans">
            <h3 className="font-extrabold text-sm text-gov-navy border-b border-slate-100 pb-3 flex items-center">
              <CheckSquare className="h-5 w-5 text-gov-indigo mr-2" />
              Review & Submit Complaint
            </h3>

            <div className="bg-slate-50 rounded-xl border border-slate-200 p-5 space-y-4">
              <div>
                <p className="font-bold text-gov-slate mb-1">Incident Classification</p>
                <p className="font-bold text-slate-800">
                  Category: {categories.find(c => c.id === Number(selectedCatId))?.name} &bull; Subcategory: {subcategories.find(s => s.id === Number(selectedSubId))?.name}
                </p>
                {isAnonymous && <span className="text-[10px] bg-red-150 text-red-700 px-2 py-0.5 rounded font-black uppercase mt-1 inline-block">Anonymous Report</span>}
              </div>

              {!isAnonymous && (
                <div>
                  <p className="font-bold text-gov-slate mb-1">Victim Info</p>
                  <p className="font-bold text-slate-800">
                    Name: {formValues.victim_name || 'Not provided'} &bull; Phone: {formValues.victim_mobile || 'Not provided'}
                  </p>
                </div>
              )}

              <div>
                <p className="font-bold text-gov-slate mb-1">Incident Summary</p>
                <p className="text-slate-800 italic leading-relaxed">{formValues.fraud_description}</p>
              </div>

              {selectedFiles.length > 0 && (
                <div>
                  <p className="font-bold text-gov-slate mb-1">Attached Evidences ({selectedFiles.length})</p>
                  <p className="font-bold text-slate-800">
                    {selectedFiles.map(f => f.name).join(', ')}
                  </p>
                </div>
              )}
            </div>

            <div className="p-4 bg-orange-50 border border-orange-200 rounded-xl text-orange-850 font-bold leading-relaxed">
              DECLARATION: I hereby declare that the information provided in this complaint is true and accurate to the best of my knowledge. Filing false police reports is a punishable legal offense.
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white border border-slate-200 shadow-xl rounded-2xl p-6 md:p-8 space-y-8">
          
          {/* Header */}
          <div className="border-b border-slate-100 pb-5">
            <h1 className="text-2xl font-black text-gov-navy font-sans tracking-tight">File Online Cyber Crime Complaint</h1>
            <p className="text-xs text-gov-slate mt-1">Fill out the official multi-step questionnaire to register the incident.</p>
          </div>

          {/* Stepper indicators */}
          <div className="hidden sm:flex justify-between text-[10px] font-bold text-gov-slate uppercase tracking-wider">
            {stepsList.map((stName, idx) => (
              <div
                key={idx}
                className={`flex items-center space-x-1.5 ${
                  step === idx + 1 ? 'text-gov-indigo' : step > idx + 1 ? 'text-green-600' : 'text-slate-300'
                }`}
              >
                <span>{idx + 1}. {stName}</span>
                {idx < 5 && <span className="text-slate-300">&rarr;</span>}
              </div>
            ))}
          </div>

          {/* Step content */}
          <div className="min-h-[250px]">{renderStepContent()}</div>

          {/* Action buttons */}
          <div className="flex justify-between pt-6 border-t border-slate-100">
            {step > 1 ? (
              <button
                type="button"
                onClick={prevStep}
                className="border border-gov-border hover:bg-slate-50 text-slate-750 font-bold px-6 py-2.5 rounded-lg text-xs flex items-center space-x-1"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Previous</span>
              </button>
            ) : (
              <div></div>
            )}

            {step < 6 ? (
              <button
                type="button"
                onClick={nextStep}
                disabled={step === 1 && (!selectedCatId || !selectedSubId)}
                className="bg-gov-indigo hover:bg-slate-900 text-white font-bold px-8 py-2.5 rounded-lg text-xs flex items-center space-x-1 transition-all disabled:opacity-50"
              >
                <span>Next Step</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onSubmit}
                className="bg-orange-600 hover:bg-orange-700 text-white font-bold px-10 py-3 rounded-lg text-xs flex items-center space-x-1 transition-all shadow-md"
              >
                <span>Confirm & Submit Report</span>
              </button>
            )}
          </div>

        </div>
      </div>
    </Layout>
  );
};
export default ComplaintForm;
