import { useState, useRef, useCallback, useEffect } from 'react';

/* ------------------------------------------------------------------ */
/*  Public interfaces                                                  */
/* ------------------------------------------------------------------ */
export interface SpeakOptions {
  /** BCP-47 language tag, e.g. "en-US", "hi-IN" */
  lang?: string;
  /** Speaking rate: 0.1 – 10 (default: 1) */
  rate?: number;
  /** Pitch: 0 – 2 (default: 1) */
  pitch?: number;
  /** Volume: 0 – 1 (default: 1) */
  volume?: number;
}

export interface UseSpeechSynthesisReturn {
  /** Speak the given text. Automatically chunks long strings. */
  speak: (text: string, options?: SpeakOptions) => void;
  /** Immediately stop any current speech. */
  stop: () => void;
  /** Whether the synthesiser is currently speaking. */
  isSpeaking: boolean;
  /** Whether the browser supports the Web Speech Synthesis API. */
  isSupported: boolean;
  /** Currently available voices (populated asynchronously in Chrome). */
  voices: SpeechSynthesisVoice[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Check for speechSynthesis support. */
function isSynthesisSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

/**
 * Preferred voice names, ranked.  The first match wins.
 * We intentionally mix "Female" and known-female defaults from major vendors.
 */
const PREFERRED_VOICE_NAMES: readonly string[] = [
  'Google English (India)',
  'Microsoft Heera',      // Windows female EN-IN
  'Google UK English Female',
  'Google US English',
  'Microsoft Zira',       // Windows female EN-US
  'Microsoft Hazel',      // Windows female EN-GB
  'Samantha',             // macOS / iOS female EN
  'Karen',                // macOS AU female
  'Victoria',             // macOS EN female
] as const;

/**
 * Pick the best available voice for the requested language.
 *
 * Priority:
 *  1. Exact match against PREFERRED_VOICE_NAMES whose lang starts with the
 *     requested language subtag.
 *  2. Any voice whose name contains "Female" for the requested language.
 *  3. Any voice matching the requested language.
 *  4. A preferred voice in any language.
 *  5. The browser default (first voice, or undefined).
 */
function selectVoice(
  voices: SpeechSynthesisVoice[],
  lang: string,
): SpeechSynthesisVoice | undefined {
  if (voices.length === 0) return undefined;

  const langPrefix = lang.toLowerCase().split('-')[0]; // e.g. "en"

  // 1. Preferred name + language match
  for (const name of PREFERRED_VOICE_NAMES) {
    const v = voices.find(
      (v) =>
        v.name === name &&
        v.lang.toLowerCase().startsWith(langPrefix),
    );
    if (v) return v;
  }

  // 2. Any "female" voice matching the language
  const femaleForLang = voices.find(
    (v) =>
      v.lang.toLowerCase().startsWith(langPrefix) &&
      /female/i.test(v.name),
  );
  if (femaleForLang) return femaleForLang;

  // 3. Any voice for the exact requested locale (e.g. hi-IN)
  const exactLocale = voices.find(
    (v) => v.lang.toLowerCase() === lang.toLowerCase(),
  );
  if (exactLocale) return exactLocale;

  // 3b. Any voice matching the language subtag
  const anyLang = voices.find(
    (v) => v.lang.toLowerCase().startsWith(langPrefix),
  );
  if (anyLang) return anyLang;

  // 4. A globally preferred voice regardless of language
  for (const name of PREFERRED_VOICE_NAMES) {
    const v = voices.find((v) => v.name === name);
    if (v) return v;
  }

  // 5. Ultimate fallback – first voice
  return voices[0];
}

/**
 * Split long text into chunks at sentence boundaries.
 *
 * SpeechSynthesis on some browsers (especially Chrome on Android) silently
 * truncates utterances around 200-300 characters.  We split conservatively
 * at ~180 chars on sentence-ending punctuation so every chunk is well within
 * limits while still sounding natural.
 */
function chunkText(text: string, maxLen = 180): string[] {
  if (text.length <= maxLen) return [text];

  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLen) {
      chunks.push(remaining.trim());
      break;
    }

    // Try to break at sentence-ending punctuation within the window
    const window = remaining.slice(0, maxLen);
    // Find last sentence ender (.!? followed by space or end)
    const sentenceEndRegex = /[.!?]\s/g;
    let lastBreak = -1;
    let match: RegExpExecArray | null;
    while ((match = sentenceEndRegex.exec(window)) !== null) {
      lastBreak = match.index + 1; // include the punctuation char
    }

    if (lastBreak === -1) {
      // No sentence boundary – fall back to last space
      const lastSpace = window.lastIndexOf(' ');
      lastBreak = lastSpace > 0 ? lastSpace : maxLen;
    }

    chunks.push(remaining.slice(0, lastBreak).trim());
    remaining = remaining.slice(lastBreak).trim();
  }

  return chunks.filter(Boolean);
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */
export function useSpeechSynthesis(): UseSpeechSynthesisReturn {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  const isSupported = isSynthesisSupported();

  /** Queue of remaining chunks still to be spoken in the current call. */
  const chunkQueueRef = useRef<string[]>([]);
  /** Whether we intentionally cancelled speech. */
  const cancelledRef = useRef(false);

  /* ---- Load voices (they arrive asynchronously in Chrome) ---- */
  useEffect(() => {
    if (!isSupported) return;

    const loadVoices = () => {
      const available = window.speechSynthesis.getVoices();
      if (available.length > 0) {
        setVoices(available);
      }
    };

    // Voices may already be loaded (Firefox / Safari)
    loadVoices();

    // Chrome fires this event once voices are ready
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);

    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
    };
  }, [isSupported]);

  /* ---- stop ---- */
  const stop = useCallback(() => {
    if (!isSupported) return;
    cancelledRef.current = true;
    chunkQueueRef.current = [];
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, [isSupported]);

  /* ---- Internal: speak a single chunk ---- */
  const speakChunk = useCallback(
    (
      text: string,
      voice: SpeechSynthesisVoice | undefined,
      options: Required<Omit<SpeakOptions, 'lang'>> & { lang: string },
    ) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = options.lang;
      utterance.rate = options.rate;
      utterance.pitch = options.pitch;
      utterance.volume = options.volume;
      if (voice) utterance.voice = voice;

      utterance.onstart = () => {
        setIsSpeaking(true);
      };

      utterance.onend = () => {
        // Speak next queued chunk, if any
        const next = chunkQueueRef.current.shift();
        if (next && !cancelledRef.current) {
          speakChunk(next, voice, options);
        } else {
          setIsSpeaking(false);
        }
      };

      utterance.onerror = (event) => {
        // 'interrupted' fires when cancel() is called – not a real error
        if (event.error !== 'interrupted' && event.error !== 'canceled') {
          console.warn('[useSpeechSynthesis] utterance error:', event.error);
        }
        chunkQueueRef.current = [];
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    },
    [],
  );

  /* ---- speak (public) ---- */
  const speak = useCallback(
    (text: string, options: SpeakOptions = {}) => {
      if (!isSupported || !text.trim()) return;

      // Cancel anything currently playing
      cancelledRef.current = true;
      window.speechSynthesis.cancel();
      cancelledRef.current = false;

      const resolvedOptions = {
        lang: options.lang ?? 'en-US',
        rate: options.rate ?? 1,
        pitch: options.pitch ?? 1,
        volume: options.volume ?? 1,
      };

      const voice = selectVoice(voices, resolvedOptions.lang);
      const chunks = chunkText(text);

      if (chunks.length === 0) return;

      // Queue everything after the first chunk
      chunkQueueRef.current = chunks.slice(1);

      // Chrome sometimes pauses synthesis if the page has been idle.
      // A resume() call unblocks it.
      window.speechSynthesis.resume();

      speakChunk(chunks[0], voice, resolvedOptions);
    },
    [isSupported, voices, speakChunk],
  );

  /* ---- Cleanup on unmount ---- */
  useEffect(() => {
    return () => {
      if (isSupported) {
        chunkQueueRef.current = [];
        window.speechSynthesis.cancel();
      }
    };
  }, [isSupported]);

  return {
    speak,
    stop,
    isSpeaking,
    isSupported,
    voices,
  };
}

export default useSpeechSynthesis;
