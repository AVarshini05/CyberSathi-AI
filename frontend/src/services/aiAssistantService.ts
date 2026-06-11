import api from './api';

export interface AIMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
  audioBase64?: string;
  isHighPriority?: boolean;
}

export interface QualityDetail {
  field: string;
  status: 'complete' | 'missing';
}

export interface ChatResponse {
  response: string;
  session_id: string;
  detected_category?: string;
  detected_subcategory?: string;
  quality_score?: number;
  quality_details?: QualityDetail[];
  is_high_priority?: boolean;
  audio_base_64?: string;
  language?: string;
  transcript?: string;
  detected_language?: string;
  form_data?: FormDataResponse;
  conversation_state?: any;
}

export interface FormDataResponse {
  category_id?: number;
  subcategory_id?: number;
  victim_name?: string;
  victim_mobile?: string;
  victim_email?: string;
  fraud_description?: string;
  answers?: Array<{ question_id: number; value: string }>;
  is_anonymous?: boolean;
  quality_score?: number;
  suspect_name?: string;
  suspect_mobile?: string;
}

export interface StartSessionResponse {
  session_id: string;
  greeting: string;
  audio_base_64?: string;
  language?: string;
}


export const aiAssistantService = {
  startSession: () =>
    api.post<StartSessionResponse>('/ai-assistant/start'),

  sendMessage: (sessionId: string, message: string) =>
    api.post<ChatResponse>('/ai-assistant/chat', {
      session_id: sessionId,
      message,
    }),

  sendVoice: (sessionId: string, audioBlob: Blob) => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('audio_file', audioBlob, 'recording.webm');
    return api.post<ChatResponse>('/ai-assistant/voice', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getFormData: (sessionId: string) =>
    api.get<FormDataResponse>(`/ai-assistant/form-data/${sessionId}`),

  getSession: (sessionId: string) =>
    api.get<any>(`/ai-assistant/session/${sessionId}`),

  setLanguage: (sessionId: string, language: string) =>
    api.post<{ status: string }>('/ai-assistant/language', {
      session_id: sessionId,
      language,
    }),

  textToSpeech: (text: string, language: string) =>
    api.post<{ audio_base_64: string }>('/ai-assistant/tts', {
      text,
      language,
    }),


  endSession: (sessionId: string) =>
    api.delete(`/ai-assistant/session/${sessionId}`),
};

export default aiAssistantService;
