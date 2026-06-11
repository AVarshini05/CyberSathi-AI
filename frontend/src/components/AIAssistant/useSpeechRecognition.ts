import { useState, useRef, useCallback, useEffect } from 'react';

/* ------------------------------------------------------------------ */
/*  Type augmentation – webkitSpeechRecognition is non-standard        */
/* ------------------------------------------------------------------ */
interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message?: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

/* ------------------------------------------------------------------ */
/*  Public interfaces                                                  */
/* ------------------------------------------------------------------ */
export interface UseSpeechRecognitionConfig {
  /** BCP-47 language tag, e.g. "en-US", "hi-IN" */
  lang?: string;
  /** Keep recognition running until explicitly stopped (default: false) */
  continuous?: boolean;
  /** Provide interim (partial) results while the user is speaking (default: true) */
  interimResults?: boolean;
  /** Maximum listening duration in seconds (default: 30) */
  maxDuration?: number;
}

export interface UseSpeechRecognitionReturn {
  /** Whether the recogniser is currently listening */
  isListening: boolean;
  /** Final, committed transcript text */
  transcript: string;
  /** Real-time partial transcript (updates as user speaks) */
  interimTranscript: string;
  /** Begin a new recognition session */
  startListening: () => void;
  /** Manually stop the current session */
  stopListening: () => void;
  /** Whether the browser supports SpeechRecognition */
  isSupported: boolean;
  /** Human-readable error message, or null */
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Resolve the SpeechRecognition constructor across vendors. */
function getSpeechRecognitionCtor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') return null;

  const w = window as unknown as Record<string, unknown>;
  return (
    (w.SpeechRecognition as SpeechRecognitionConstructor | undefined) ??
    (w.webkitSpeechRecognition as SpeechRecognitionConstructor | undefined) ??
    null
  );
}

/** Map raw error codes to user-friendly messages. */
function friendlyError(errorCode: string): string {
  switch (errorCode) {
    case 'not-allowed':
      return 'Microphone access was denied. Please allow microphone permissions and try again.';
    case 'no-speech':
      return 'No speech was detected. Please try again.';
    case 'audio-capture':
      return 'No microphone was found. Please connect a microphone and try again.';
    case 'network':
      return 'A network error occurred. Please check your connection.';
    case 'aborted':
      return 'Speech recognition was aborted.';
    case 'service-not-allowed':
      return 'Speech recognition service is not allowed. Please check browser settings.';
    case 'language-not-supported':
      return 'The selected language is not supported by your browser.';
    default:
      return `Speech recognition error: ${errorCode}`;
  }
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */
export function useSpeechRecognition(
  config: UseSpeechRecognitionConfig = {},
): UseSpeechRecognitionReturn {
  const {
    lang = 'en-US',
    continuous = false,
    interimResults = true,
    maxDuration = 30,
  } = config;

  /* ---- state ---- */
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  /* ---- refs (survive re-renders) ---- */
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const maxDurationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isListeningRef = useRef(false); // avoids stale-closure issues

  /* ---- browser support (computed once) ---- */
  const isSupported = getSpeechRecognitionCtor() !== null;

  /* ---- cleanup helpers ---- */
  const clearMaxDurationTimer = useCallback(() => {
    if (maxDurationTimerRef.current !== null) {
      clearTimeout(maxDurationTimerRef.current);
      maxDurationTimerRef.current = null;
    }
  }, []);

  const destroyRecognition = useCallback(() => {
    clearMaxDurationTimer();
    const rec = recognitionRef.current;
    if (rec) {
      // Detach handlers before aborting to avoid triggering onend logic
      rec.onresult = null;
      rec.onerror = null;
      rec.onend = null;
      rec.onstart = null;
      try {
        rec.abort();
      } catch {
        // ignore – may already be stopped
      }
      recognitionRef.current = null;
    }
    isListeningRef.current = false;
    setIsListening(false);
    setInterimTranscript('');
  }, [clearMaxDurationTimer]);

  /* ---- stopListening (user-facing) ---- */
  const stopListening = useCallback(() => {
    clearMaxDurationTimer();
    const rec = recognitionRef.current;
    if (rec && isListeningRef.current) {
      try {
        rec.stop(); // triggers onend → finalises results
      } catch {
        // Already stopped
        destroyRecognition();
      }
    }
  }, [clearMaxDurationTimer, destroyRecognition]);

  /* ---- startListening ---- */
  const startListening = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setError('Speech recognition is not supported in this browser.');
      return;
    }

    // Tear down any existing session first
    destroyRecognition();

    // Reset state for the new session
    setTranscript('');
    setInterimTranscript('');
    setError(null);

    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.continuous = continuous;
    recognition.interimResults = interimResults;
    recognitionRef.current = recognition;

    /* -- event: start -- */
    recognition.onstart = () => {
      isListeningRef.current = true;
      setIsListening(true);
    };

    /* -- event: result -- */
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalText = '';
      let partialText = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0]?.transcript ?? '';

        if (result.isFinal) {
          finalText += text;
        } else {
          partialText += text;
        }
      }

      if (finalText) {
        setTranscript((prev) => (prev ? `${prev} ${finalText}` : finalText).trim());
      }
      setInterimTranscript(partialText);
    };

    /* -- event: error -- */
    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      // 'no-speech' is benign in many cases; still surface it but don't
      // destroy the session because onend will fire next.
      setError(friendlyError(event.error));
    };

    /* -- event: end (silence detected / manual stop / error aftermath) -- */
    recognition.onend = () => {
      isListeningRef.current = false;
      setIsListening(false);
      setInterimTranscript('');
      clearMaxDurationTimer();
      recognitionRef.current = null;
    };

    /* -- kick off -- */
    try {
      recognition.start();
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : 'Failed to start speech recognition.';
      setError(msg);
      destroyRecognition();
      return;
    }

    /* -- max-duration safety net -- */
    if (maxDuration > 0) {
      maxDurationTimerRef.current = setTimeout(() => {
        stopListening();
      }, maxDuration * 1000);
    }
  }, [lang, continuous, interimResults, maxDuration, destroyRecognition, stopListening, clearMaxDurationTimer]);

  /* ---- unmount cleanup ---- */
  useEffect(() => {
    return () => {
      destroyRecognition();
    };
  }, [destroyRecognition]);

  return {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    isSupported,
    error,
  };
}

export default useSpeechRecognition;
