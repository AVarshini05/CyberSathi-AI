import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  X,
  Mic,
  MicOff,
  Send,
  Volume2,
  VolumeX,
  FileText,
  AlertTriangle,
  Loader2,
  Sparkles,
  Bot,
  User as UserIcon,
  Wifi,
  WifiOff,
} from 'lucide-react';

import aiAssistantService, { AIMessage } from '../../services/aiAssistantService';
import useVoiceRecorder from './useVoiceRecorder';
import { useSpeechRecognition } from './useSpeechRecognition';
import { useSpeechSynthesis } from './useSpeechSynthesis';
import './AIAssistant.css';

const DOMAIN_CORRECTIONS: Record<string, string> = {
  sdi: 'SBI',
  sbi: 'SBI',
  sbd: 'SBI',
  hdfc: 'HDFC',
  icici: 'ICICI',
  gpay: 'GPay',
  googlepay: 'GPay',
  'google pay': 'GPay',
  phonepe: 'PhonePe',
  'phone pe': 'PhonePe',
  paytm: 'Paytm',
  upi: 'UPI',
  upid: 'UPI ID',
  'upi id': 'UPI ID',
  insta: 'Instagram',
  instagram: 'Instagram',
  instergram: 'Instagram',
  instgram: 'Instagram',
  whatsapp: 'WhatsApp',
  whatsup: 'WhatsApp',
  telegram: 'Telegram',
  telegeram: 'Telegram'
};

const cleanTranscription = (text: string): string => {
  if (!text) return '';
  let cleaned = text;
  Object.entries(DOMAIN_CORRECTIONS).forEach(([wrong, right]) => {
    const regex = new RegExp(`\\b${wrong}\\b`, 'gi');
    cleaned = cleaned.replace(regex, right);
  });
  return cleaned;
};

const cleanTextForSpeech = (text: string): string => {
  if (!text) return '';
  // Strip markdown formatting characters
  let cleaned = text.replace(/[*#_`~\[\]()]/g, '');
  
  // Space out common abbreviations
  const abbreviations = {
    UPI: 'U P I',
    UTR: 'U T R',
    OTP: 'O T P',
    ATM: 'A T M',
    KYC: 'K Y C',
    SMS: 'S M S'
  };
  Object.entries(abbreviations).forEach(([abv, spoken]) => {
    const regex = new RegExp(`\\b${abv}\\b`, 'gi');
    cleaned = cleaned.replace(regex, spoken);
  });

  // Space out UPI IDs for spelling
  cleaned = cleaned.replace(/\b[a-zA-Z0-9.-]+@[a-zA-Z]{3,}\b/g, (match) => {
    const parts = match.split('@');
    const left = parts[0].split('').join(' ');
    const right = parts[1].split('').join(' ');
    return `${left} at ${right}`;
  });

  // Space mixed alphanumeric codes
  cleaned = cleaned.replace(/\b(?:[a-zA-Z]+\d+|\d+[a-zA-Z]+)[a-zA-Z0-9]*\b/g, (match) => {
    return match.split('').join(' ');
  });

  // Space pure digits of length >= 4
  cleaned = cleaned.replace(/\b\d{4,}\b/g, (match) => {
    return match.split('').join(' ');
  });

  return cleaned;
};

const LANGUAGES = [
  { code: 'en-IN', name: 'English' },
  { code: 'hi-IN', name: 'Hindi (हिंदी)' },
  { code: 'te-IN', name: 'Telugu (తెలుగు)' },
  { code: 'ta-IN', name: 'Tamil (தமிழ்)' },
  { code: 'mr-IN', name: 'Marathi (मराठी)' },
  { code: 'bn-IN', name: 'Bengali (বাংলা)' },
  { code: 'gu-IN', name: 'Gujarati (ગુજરાતી)' },
  { code: 'kn-IN', name: 'Kannada (ಕನ್ನಡ)' },
  { code: 'ml-IN', name: 'Malayalam (മലയാളം)' },
  { code: 'pa-IN', name: 'Punjabi (ਪੰਜਾਬੀ)' },
  { code: 'or-IN', name: 'Odia (ଓଡ଼ିଆ)' },
];

/**
 * Voice provider modes.
 * - "browser"  → Browser Web Speech API (Google-powered in Chrome)
 * - "sarvam"   → MediaRecorder → server /voice endpoint → Sarvam STT
 */
type VoiceProvider = 'browser' | 'sarvam';

export const AIAssistant: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading } = useAuth();

  // ─── Session & Chat State ─────────────────────────────────────────
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [language, setLanguage] = useState('en-IN');
  const [qualityScore, setQualityScore] = useState(10);
  const [isHighPriority, setIsHighPriority] = useState(false);
  const [detectedCategory, setDetectedCategory] = useState<string | null>(null);
  const [detectedSubcategory, setDetectedSubcategory] = useState<string | null>(null);
  const [isContinuousVoiceMode, setIsContinuousVoiceMode] = useState(false);
  const [progressBreakdown, setProgressBreakdown] = useState<Record<string, number>>({
    category: 0,
    victim: 0,
    incident: 0,
    suspect: 0,
    evidence: 0,
    overall: 10
  });

  // ─── UI States ────────────────────────────────────────────────────
  const [isLoading, setIsLoading] = useState(false);
  const [isTtsLoading, setIsTtsLoading] = useState<string | null>(null);
  const [playingMsgId, setPlayingMsgId] = useState<string | null>(null);

  // ─── Audio Playback (for Sarvam TTS fallback) ─────────────────────
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const lastProcessedBlobRef = useRef<Blob | null>(null);

  // ─── Voice Provider Detection ─────────────────────────────────────
  const speechRecognition = useSpeechRecognition({ lang: language, maxDuration: 30 });
  const speechSynthesis = useSpeechSynthesis();

  const voiceProvider: VoiceProvider = speechRecognition.isSupported ? 'browser' : 'sarvam';
  const ttsProvider = speechSynthesis.isSupported ? 'browser' : 'sarvam';

  // ─── Sarvam Fallback Recorder ─────────────────────────────────────
  const {
    isRecording,
    startRecording,
    stopRecording,
    audioBlob,
    error: recordingError,
    recordingTime,
  } = useVoiceRecorder();

  // ─── Auto-Scroll ──────────────────────────────────────────────────
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // ─── Audio Playback (Sarvam TTS) ─────────────────────────────────
  const playAudio = useCallback((base64Audio: string, msgId: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    if (playingMsgId === msgId) {
      setPlayingMsgId(null);
      return;
    }
    const audio = new Audio(`data:audio/wav;base64,${base64Audio}`);
    audioRef.current = audio;
    setPlayingMsgId(msgId);
    audio.play().catch((err) => console.error('Audio play error', err));
    audio.onended = () => setPlayingMsgId(null);
  }, [playingMsgId]);

  // ─── Stop All Audio / TTS Playback ────────────────────────────────
  const stopAllSpeech = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setPlayingMsgId(null);
    }
    speechSynthesis.stop();
  }, [speechSynthesis]);

  // ─── Browser TTS Speak ────────────────────────────────────────────
  const speakText = useCallback((text: string, msgId?: string) => {
    if (ttsProvider === 'browser' && speechSynthesis.isSupported) {
      const cleaned = cleanTextForSpeech(text);
      speechSynthesis.speak(cleaned, { lang: language, rate: 0.95, pitch: 1.05 });
    }
  }, [ttsProvider, speechSynthesis, language]);

  // ─── Handle AI Response (shared logic) ────────────────────────────
  const handleAIResponse = useCallback((res: any) => {
    const botMsg: AIMessage = {
      id: Math.random().toString(),
      role: 'assistant',
      text: res.data.response,
      timestamp: new Date(),
      audioBase64: res.data.audio_base_64 || undefined,
    };

    setMessages((prev) => [...prev, botMsg]);
    setQualityScore(res.data.quality_score || 10);
    setIsHighPriority(!!res.data.is_high_priority);
    if (res.data.detected_category) setDetectedCategory(res.data.detected_category);
    if (res.data.detected_subcategory) setDetectedSubcategory(res.data.detected_subcategory);
    if (res.data.progress_breakdown) {
      setProgressBreakdown(res.data.progress_breakdown);
    }

    if (res.data.form_data) {
      const prefillData = {
        ...res.data.form_data,
        step: res.data.step
      };
      window.dispatchEvent(new CustomEvent('ai-prefill-update', { detail: prefillData }));
    }

    // Auto-play TTS response
    if (ttsProvider === 'browser') {
      // Use browser TTS (primary)
      speakText(res.data.response, botMsg.id);
    } else if (res.data.audio_base_64) {
      // Use Sarvam TTS audio (fallback)
      playAudio(res.data.audio_base_64, botMsg.id);
    }

    // If backend reports authentication required, redirect user to login
    if (res.data.requires_auth) {
      setIsContinuousVoiceMode(false);
      speechRecognition.stopListening();
      setTimeout(() => {
        setIsOpen(false);
        navigate('/login', { state: { from: { pathname: '/file-complaint', search: '?ai=true' } } });
      }, 4000);
    }
  }, [ttsProvider, speakText, playAudio, setProgressBreakdown, navigate, speechRecognition]);

  // ─── Initialize Session ───────────────────────────────────────────
  const initSession = async () => {
    try {
      setIsLoading(true);
      const res = await aiAssistantService.startSession();
      const { session_id, greeting, audio_base_64, language: lang } = res.data;

      setSessionId(session_id);
      localStorage.setItem('ccrms_ai_session_id', session_id);
      setLanguage(lang || 'en-IN');

      const newGreeting: AIMessage = {
        id: 'greeting',
        role: 'assistant',
        text: greeting,
        timestamp: new Date(),
        audioBase64: audio_base_64 || undefined,
      };

      setMessages([newGreeting]);

      // Auto-play greeting
      if (ttsProvider === 'browser') {
        speakText(greeting, 'greeting');
      } else if (audio_base_64) {
        playAudio(audio_base_64, 'greeting');
      }
    } catch (err) {
      console.error('Failed to initialize AI session', err);
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Recover Session on Mount ─────────────────────────────────────
  const hasRecoveredRef = useRef(false);
  useEffect(() => {
    if (loading) return;
    if (hasRecoveredRef.current) return;
    hasRecoveredRef.current = true;

    const recoverSession = async () => {
      const savedSessionId = localStorage.getItem('ccrms_ai_session_id');
      if (savedSessionId) {
        try {
          setIsLoading(true);
          const res = await aiAssistantService.getSession(savedSessionId);
          if (res.data && !res.data.is_expired) {
            setSessionId(savedSessionId);
            setLanguage(res.data.language || 'en-IN');
            
            const history = res.data.conversation_history || [];
            const mappedMessages: AIMessage[] = history.map((h: any, idx: number) => ({
              id: h.id || `hist-${idx}`,
              role: h.role,
              text: h.text,
              timestamp: h.timestamp ? new Date(h.timestamp) : new Date(),
              audioBase64: h.audioBase64 || undefined
            }));
            
            setMessages(mappedMessages);
            
            const collected = res.data.collected_data || {};
            const stepVal = parseInt(collected.step || 1);
            const qualityVal = res.data.quality_score || collected.overall || (stepVal >= 6 ? 100 : stepVal * 15);
            setQualityScore(qualityVal);
            
            const catComp = res.data.detected_subcategory_id ? 100 : 0;
            const vicComp = stepVal > 2 ? 100 : 0;
            const incComp = stepVal > 3 ? 100 : 0;
            const susComp = stepVal > 4 ? 100 : 0;
            const evComp = stepVal > 5 ? 100 : 20;
            
            setProgressBreakdown({
              category: catComp,
              victim: vicComp,
              incident: incComp,
              suspect: susComp,
              evidence: evComp,
              overall: qualityVal
            });

            if (res.data.detected_category_id || res.data.detected_category) {
              setDetectedCategory("Detected");
            }
            if (res.data.detected_subcategory_id || res.data.detected_subcategory) {
              setDetectedSubcategory("Detected");
            }
            
            // Prefill update
            const formRes = await aiAssistantService.getFormData(savedSessionId);
            if (formRes.data) {
              const prefillData = {
                ...formRes.data,
                step: stepVal
              };
              window.dispatchEvent(new CustomEvent('ai-prefill-update', { detail: prefillData }));
            }

            // Auto-resume if category is detected and step is 1, and user is logged in
            if (stepVal === 1 && res.data.detected_subcategory_id && !!user) {
              try {
                const resumeRes = await aiAssistantService.sendMessage(savedSessionId, '/resume');
                handleAIResponse(resumeRes);
              } catch (err) {
                console.error("Failed to auto-resume session:", err);
              }
            }
          } else {
            localStorage.removeItem('ccrms_ai_session_id');
          }
        } catch (err) {
          console.error('Failed to recover AI session:', err);
          localStorage.removeItem('ccrms_ai_session_id');
        } finally {
          setIsLoading(false);
        }
      }
    };
    recoverSession();
  }, [loading, user, handleAIResponse]);

  // ─── Auto-open widget on query param check ────────────────────────
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('ai') === 'true') {
      setIsOpen(true);
      const savedSessionId = localStorage.getItem('ccrms_ai_session_id');
      if (!savedSessionId && !sessionId && !isLoading) {
        initSession();
      }
    }
  }, [location.search, sessionId, isLoading]);

  // ─── Open / Close Widget ──────────────────────────────────────────
  const toggleWidget = () => {
    if (!isOpen) {
      setIsOpen(true);
      if (!sessionId) {
        initSession();
      }
    } else {
      setIsOpen(false);
      setIsContinuousVoiceMode(false);
      // Stop all audio
      if (audioRef.current) {
        audioRef.current.pause();
        setPlayingMsgId(null);
      }
      speechSynthesis.stop();
      speechRecognition.stopListening();
    }
  };

  // ─── Language Change ──────────────────────────────────────────────
  const handleLanguageChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLang = e.target.value;
    setLanguage(newLang);
    setIsContinuousVoiceMode(false);
    stopAllSpeech();
    if (sessionId) {
      try {
        await aiAssistantService.setLanguage(sessionId, newLang);
        setIsLoading(true);
        const promptText = `Please switch your language and greet me in the language code ${newLang}.`;
        const res = await aiAssistantService.sendMessage(sessionId, promptText);
        handleAIResponse(res);
      } catch (err) {
        console.error('Language update failed', err);
      } finally {
        setIsLoading(false);
      }
    }
  };

  // ─── Text Send ────────────────────────────────────────────────────
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || !sessionId || isLoading) return;

    setIsContinuousVoiceMode(false);
    stopAllSpeech();

    const userText = inputValue;
    setInputValue('');

    const userMsg: AIMessage = {
      id: Math.random().toString(),
      role: 'user',
      text: userText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await aiAssistantService.sendMessage(sessionId, userText);
      handleAIResponse(res);
    } catch (err) {
      console.error('Send message failed', err);
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Browser STT: Process Final Transcript ────────────────────────
  const lastTranscriptRef = useRef('');

  useEffect(() => {
    const sendTranscript = async () => {
      const rawText = speechRecognition.transcript;
      const text = cleanTranscription(rawText);
      if (
        text &&
        text !== lastTranscriptRef.current &&
        sessionId &&
        !isLoading &&
        !speechRecognition.isListening
      ) {
        lastTranscriptRef.current = text;

        const userMsg: AIMessage = {
          id: Math.random().toString(),
          role: 'user',
          text,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMsg]);
        setIsLoading(true);

        try {
          const res = await aiAssistantService.sendMessage(sessionId, text);
          handleAIResponse(res);
        } catch (err) {
          console.error('Browser STT message send failed', err);
        } finally {
          setIsLoading(false);
        }
      }
    };

    sendTranscript();
  }, [speechRecognition.transcript, speechRecognition.isListening, sessionId, isLoading, handleAIResponse]);

  // ─── Sarvam Fallback: Process Voice Recording Upload ──────────────
  useEffect(() => {
    const uploadVoice = async () => {
      if (
        voiceProvider === 'sarvam' &&
        audioBlob &&
        sessionId &&
        audioBlob !== lastProcessedBlobRef.current
      ) {
        lastProcessedBlobRef.current = audioBlob;
        setIsLoading(true);
        try {
          const res = await aiAssistantService.sendVoice(sessionId, audioBlob);

          if (res.data.transcript) {
            const userMsg: AIMessage = {
              id: Math.random().toString(),
              role: 'user',
              text: res.data.transcript,
              timestamp: new Date(),
            };
            setMessages((prev) => [...prev, userMsg]);
          }

          handleAIResponse(res);
          if (res.data.language) setLanguage(res.data.language);
        } catch (err) {
          console.error('Voice submission failed', err);
        } finally {
          setIsLoading(false);
        }
      }
    };

    uploadVoice();
  }, [audioBlob, sessionId, voiceProvider, handleAIResponse]);

  // ─── Voice Button Handler ─────────────────────────────────────────
  const handleVoiceClick = () => {
    stopAllSpeech();
    if (voiceProvider === 'browser') {
      if (speechRecognition.isListening) {
        setIsContinuousVoiceMode(false);
        speechRecognition.stopListening();
      } else {
        setIsContinuousVoiceMode(true);
        speechRecognition.startListening();
      }
    } else {
      // Sarvam fallback: use MediaRecorder
      if (isRecording) {
        setIsContinuousVoiceMode(false);
        stopRecording();
      } else {
        setIsContinuousVoiceMode(true);
        startRecording();
      }
    }
  };

  // ─── Interruption Listener: stop TTS when listening starts ──────
  useEffect(() => {
    if (speechRecognition.isListening || isRecording) {
      stopAllSpeech();
    }
  }, [speechRecognition.isListening, isRecording, stopAllSpeech]);

  // ─── Continuous Voice Loop ────────────────────────────────────────
  useEffect(() => {
    if (!isOpen || !isContinuousVoiceMode || isLoading) return;

    const isBotSpeaking = speechSynthesis.isSpeaking || playingMsgId !== null;

    if (isBotSpeaking) {
      // While bot is speaking, ensure microphone is not listening to prevent feedback loop
      if (voiceProvider === 'browser' && speechRecognition.isListening) {
        speechRecognition.stopListening();
      } else if (voiceProvider === 'sarvam' && isRecording) {
        stopRecording();
      }
    } else {
      // Once bot is done speaking and not loading, restart listening automatically
      if (voiceProvider === 'browser') {
        if (!speechRecognition.isListening) {
          speechRecognition.startListening();
        }
      } else if (voiceProvider === 'sarvam') {
        if (!isRecording) {
          startRecording();
        }
      }
    }
  }, [
    isOpen,
    isContinuousVoiceMode,
    isLoading,
    speechSynthesis.isSpeaking,
    playingMsgId,
    voiceProvider,
    speechRecognition.isListening,
    isRecording,
    stopRecording,
    startRecording,
    speechRecognition,
    stopAllSpeech
  ]);

  // ─── TTS Read Aloud Button ────────────────────────────────────────
  const handleSpeak = async (msgId: string, text: string) => {
    // If browser TTS is active and speaking this message, stop it
    if (speechSynthesis.isSpeaking) {
      speechSynthesis.stop();
      return;
    }

    // If Sarvam audio is playing for this message, stop it
    if (playingMsgId === msgId) {
      if (audioRef.current) audioRef.current.pause();
      setPlayingMsgId(null);
      return;
    }

    // Try browser TTS first (primary)
    if (ttsProvider === 'browser') {
      speakText(text, msgId);
      return;
    }

    // Fallback: try cached Sarvam audio
    const msg = messages.find((m) => m.id === msgId);
    if (msg?.audioBase64) {
      playAudio(msg.audioBase64, msgId);
      return;
    }

    // Fallback: request Sarvam TTS from server
    try {
      setIsTtsLoading(msgId);
      const res = await aiAssistantService.textToSpeech(text, language);
      if (res.data.audio_base_64) {
        if (msg) msg.audioBase64 = res.data.audio_base_64;
        playAudio(res.data.audio_base_64, msgId);
      }
    } catch (err) {
      console.error('TTS generation failed', err);
    } finally {
      setIsTtsLoading(null);
    }
  };

  // ─── Prefill Form and Redirect ────────────────────────────────────
  const handlePrefillForm = async () => {
    if (!sessionId) return;
    try {
      setIsLoading(true);
      const res = await aiAssistantService.getFormData(sessionId);
      const formData = res.data;

      setIsOpen(false);
      if (audioRef.current) {
        audioRef.current.pause();
        setPlayingMsgId(null);
      }
      speechSynthesis.stop();

      navigate('/file-complaint', { state: { aiPrefillData: formData } });
    } catch (err) {
      console.error('Failed to retrieve prefill data', err);
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Computed State ───────────────────────────────────────────────
  const isVoiceActive = speechRecognition.isListening || isRecording;
  const voiceError = speechRecognition.error || recordingError;
  const liveTranscript = speechRecognition.interimTranscript || speechRecognition.transcript;

  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <button className="ai-assistant-fab" onClick={toggleWidget} aria-label="Open AI Assistant">
          <Sparkles className="h-6 w-6" />
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="ai-assistant-widget">
          {/* ─── Header ─── */}
          <div className="ai-assistant-header">
            <div className="ai-assistant-title">
              <Bot className="h-5 w-5 text-indigo-400" />
              <div>
                <h3>Crime AI Assistant</h3>
                <span className="ai-assistant-subtitle">Cybercrime Officer Persona</span>
              </div>
            </div>
            <div className="ai-assistant-header-actions">
              <span className={`ai-provider-badge ${voiceProvider === 'sarvam' ? 'fallback' : ''}`}>
                {voiceProvider === 'browser' ? (
                  <><Wifi className="h-3 w-3" /> Browser</>
                ) : (
                  <><WifiOff className="h-3 w-3" /> Server</>
                )}
              </span>
              <select className="ai-lang-select" value={language} onChange={handleLanguageChange}>
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
              <button className="ai-close-btn" onClick={toggleWidget} aria-label="Close widget">
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* ─── High Priority Banner ─── */}
          {isHighPriority && (
            <div className="ai-priority-banner">
              <AlertTriangle className="h-4 w-4 animate-bounce" />
              <span>HIGH PRIORITY DETECTED: Special assistance filing is active.</span>
            </div>
          )}

          {/* ─── Progress Score ─── */}
          <div className="ai-progress-section">
            <div className="ai-progress-header">
              <span>Report Completeness</span>
              <span className="ai-progress-score">{qualityScore}%</span>
            </div>
            <div className="ai-progress-bar-container">
              <div className="ai-progress-bar" style={{ width: `${qualityScore}%` }} />
            </div>
            <div className="ai-progress-breakdown">
              <div className="ai-progress-item">
                <span className="label">Category</span>
                <span className="value">{progressBreakdown.category}%</span>
              </div>
              <div className="ai-progress-item">
                <span className="label">Victim</span>
                <span className="value">{progressBreakdown.victim}%</span>
              </div>
              <div className="ai-progress-item">
                <span className="label">Incident</span>
                <span className="value">{progressBreakdown.incident}%</span>
              </div>
              <div className="ai-progress-item">
                <span className="label">Suspect</span>
                <span className="value">{progressBreakdown.suspect}%</span>
              </div>
              <div className="ai-progress-item">
                <span className="label">Evidence</span>
                <span className="value">{progressBreakdown.evidence}%</span>
              </div>
            </div>
          </div>

          {/* ─── Chat Messages ─── */}
          <div className="ai-messages-container">
            {messages.map((msg) => (
              <div key={msg.id} className={`ai-message ${msg.role}`}>
                <div className={`ai-msg-bubble ${speechSynthesis.isSpeaking && msg.role === 'assistant' ? 'ai-msg-speaking' : ''}`}>
                  {msg.text}
                </div>
                <div className="ai-msg-meta">
                  {msg.role === 'assistant' ? (
                    <>
                      <Bot className="h-3 w-3" />
                      <span>Officer</span>
                      <button
                        className="ai-speak-btn"
                        onClick={() => handleSpeak(msg.id, msg.text)}
                        title="Read Aloud"
                        disabled={isTtsLoading === msg.id}
                      >
                        {isTtsLoading === msg.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : speechSynthesis.isSpeaking || playingMsgId === msg.id ? (
                          <VolumeX className="h-3 w-3" />
                        ) : (
                          <Volume2 className="h-3 w-3" />
                        )}
                      </button>
                    </>
                  ) : (
                    <>
                      <UserIcon className="h-3 w-3" />
                      <span>You</span>
                    </>
                  )}
                  <span>•</span>
                  <span>
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="ai-message assistant">
                <div className="ai-msg-bubble">
                  <div className="ai-typing-indicator">
                    <div className="ai-typing-dot" />
                    <div className="ai-typing-dot" />
                    <div className="ai-typing-dot" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* ─── Input Section ─── */}
          <div className="ai-input-section">
            {/* Browser STT Listening State */}
            {speechRecognition.isListening && voiceProvider === 'browser' ? (
              <>
                <div className="ai-listening-bar">
                  <div className="ai-listening-status">
                    <div className="ai-listening-dot" />
                    <span>Listening...</span>
                  </div>
                  <div className="ai-waveform-container">
                    <div className="ai-wave-bar b1" />
                    <div className="ai-wave-bar b2" />
                    <div className="ai-wave-bar b3" />
                    <div className="ai-wave-bar b4" />
                    <div className="ai-wave-bar b5" />
                  </div>
                  <button className="ai-stop-listen-btn" onClick={speechRecognition.stopListening}>
                    Done
                  </button>
                </div>
                {/* Live Transcript */}
                {liveTranscript && (
                  <div className="ai-live-transcript">
                    <Mic className="h-4 w-4" />
                    <span className="interim">
                      {liveTranscript}
                      <span className="cursor-blink" />
                    </span>
                  </div>
                )}
              </>
            ) : isRecording && voiceProvider === 'sarvam' ? (
              /* Sarvam Fallback Recording State */
              <div className="ai-recording-bar">
                <div className="ai-rec-status">
                  <div className="ai-pulse-dot" />
                  <span>Recording ({recordingTime}s / 30s)</span>
                </div>
                <div className="ai-waveform-container">
                  <div className="ai-wave-bar b1" />
                  <div className="ai-wave-bar b2" />
                  <div className="ai-wave-bar b3" />
                  <div className="ai-wave-bar b4" />
                  <div className="ai-wave-bar b5" />
                </div>
                <button className="ai-stop-rec-btn" onClick={stopRecording}>
                  Stop
                </button>
              </div>
            ) : (
              /* Default Input Row */
              <form className="ai-input-row" onSubmit={handleSendMessage}>
                <input
                  type="text"
                  className="ai-text-input"
                  placeholder="Describe incident, ask questions..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className={`ai-icon-btn voice-rec ${isVoiceActive ? 'listening' : ''}`}
                  onClick={handleVoiceClick}
                  disabled={isLoading}
                  title={voiceProvider === 'browser' ? 'Speak (Browser)' : 'Record (Server)'}
                >
                  {isVoiceActive ? (
                    <MicOff className="h-5 w-5" />
                  ) : (
                    <Mic className="h-5 w-5" />
                  )}
                </button>
                <button
                  type="submit"
                  className="ai-icon-btn send-msg"
                  disabled={!inputValue.trim() || isLoading}
                  title="Send"
                >
                  <Send className="h-5 w-5" />
                </button>
              </form>
            )}

            {/* Error Notifications */}
            {voiceError && (
              <div className="text-red-400 text-xs px-1 text-center font-medium">
                {voiceError}
              </div>
            )}

            {/* Auto-fill Button */}
            {(detectedCategory || qualityScore >= 20) && (
              <div className="ai-actions-row">
                <button className="ai-prefill-btn" onClick={handlePrefillForm} disabled={isLoading}>
                  <FileText className="h-4 w-4" />
                  <span>
                    Auto-Fill Complaint Form {detectedSubcategory ? `(${detectedSubcategory})` : ''}
                  </span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default AIAssistant;
