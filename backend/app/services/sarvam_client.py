"""
Sarvam AI API Client — Optional Fallback Provider.

Async HTTP client for Speech-to-Text, Text-to-Speech, and Translation APIs.
Uses httpx.AsyncClient for non-blocking HTTP calls.

IMPORTANT: Sarvam is an OPTIONAL fallback. All functions are designed to
fail gracefully and never raise uncaught exceptions to callers.
The Voice Agent must work even when Sarvam is completely unavailable.
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("sarvam_client")

SARVAM_BASE_URL = "https://api.sarvam.ai"
SARVAM_STT_URL = f"{SARVAM_BASE_URL}/speech-to-text"
SARVAM_TTS_URL = f"{SARVAM_BASE_URL}/text-to-speech"
SARVAM_TRANSLATE_URL = f"{SARVAM_BASE_URL}/translate"

# Default timeout for Sarvam API calls (seconds)
_TIMEOUT = 30.0


def is_available() -> bool:
    """Check if Sarvam API key is configured and non-empty."""
    return bool(settings.SARVAM_API_KEY and settings.SARVAM_API_KEY.strip())


def _get_headers(content_type: Optional[str] = None) -> dict:
    """Build common headers for Sarvam API calls."""
    headers = {
        "api-subscription-key": settings.SARVAM_API_KEY,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def speech_to_text(
    audio_bytes: bytes,
    filename: str = "audio.wav",
) -> dict:
    """
    Transcribe audio using Sarvam STT API.

    Args:
        audio_bytes: Raw audio file bytes.
        filename: Original filename (used for content-type inference).

    Returns:
        dict with keys: transcript (str), language_code (str)
        Returns empty dict on any failure.
    """
    if not is_available():
        logger.info("Sarvam STT skipped — API key not configured.")
        return {"transcript": "", "language_code": "en-IN", "error": "sarvam_unavailable"}

    logger.info("Sarvam STT request — file=%s, size=%d bytes", filename, len(audio_bytes))

    # Determine content type from extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
    mime_map = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "webm": "audio/webm",
        "flac": "audio/flac",
    }
    mime = mime_map.get(ext, "audio/wav")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                SARVAM_STT_URL,
                headers={"api-subscription-key": settings.SARVAM_API_KEY},
                files={"file": (filename, audio_bytes, mime)},
                data={
                    "model": "saaras:v3",
                    "language_code": "unknown",
                    "mode": "transcribe",
                },
            )
            response.raise_for_status()
            data = response.json()

        transcript = data.get("transcript", "")
        language_code = data.get("language_code", "en-IN")
        logger.info(
            "Sarvam STT success — language=%s, transcript_len=%d",
            language_code,
            len(transcript),
        )
        return {"transcript": transcript, "language_code": language_code}

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Sarvam STT HTTP error %s: %s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        return {"transcript": "", "language_code": "en-IN", "error": f"http_{exc.response.status_code}"}
    except Exception as exc:
        logger.warning("Sarvam STT error: %s", str(exc)[:200])
        return {"transcript": "", "language_code": "en-IN", "error": str(exc)[:100]}


import re

def clean_text_for_speech(text: str) -> str:
    """
    Cleans up response text before speaking via TTS.
    - Strips markdown format characters like asterisks, hashes, brackets, etc.
    - Spaces out abbreviations (e.g. UPI -> U P I, OTP -> O T P).
    - Digit-spaces critical numeric fields or large numbers that represent codes/identifiers.
    """
    if not text:
        return ""
    # 1. Strip markdown chars
    text = re.sub(r'[*#_`~\[\]()]', '', text)
    
    # 2. Spacing abbreviations (case-insensitive boundary checks)
    abbreviations = {
        "UPI": "U P I",
        "UTR": "U T R",
        "OTP": "O T P",
        "ATM": "A T M",
        "KYC": "K Y C",
        "SMS": "S M S"
    }
    for abv, spoken in abbreviations.items():
        text = re.sub(r'\b' + abv + r'\b', spoken, text, flags=re.IGNORECASE)

    # 3. Match UPI IDs like abc123@ybl and split them
    def clean_upi_speech(match):
        parts = match.group(0).split('@')
        left = " ".join(list(parts[0]))
        right = " ".join(list(parts[1]))
        return f"{left} at {right}"
    text = re.sub(r'\b[a-zA-Z0-9.-]+@[a-zA-Z]{3,}\b', clean_upi_speech, text)

    # 4. Spacing out alphanumeric mixed codes (e.g. 956XT439, TXN987654321)
    text = re.sub(r'\b(?:[a-zA-Z]+\d+|\d+[a-zA-Z]+)[a-zA-Z0-9]*\b', lambda m: " ".join(list(m.group(0))), text)

    # 5. Spacing out pure digits of length >= 4 (e.g. 1543216739432, 9876543210)
    text = re.sub(r'\b\d{4,}\b', lambda m: " ".join(list(m.group(0))), text)

    return text


async def text_to_speech(
    text: str,
    language: str = "en-IN",
    speaker: str = "ritu",
) -> Optional[str]:
    """
    Convert text to speech using Sarvam TTS API.

    Args:
        text: The text to synthesize.
        language: Target language code (e.g. "en-IN", "hi-IN").
        speaker: Voice name.

    Returns:
        Base64-encoded audio string (WAV format), or None on failure.
    """
    if not is_available():
        logger.info("Sarvam TTS skipped — API key not configured.")
        return None

    # Preprocess text to strip markdown and format abbreviations/numbers digit-by-digit
    cleaned_text = clean_text_for_speech(text)

    logger.info(
        "Sarvam TTS request — lang=%s, speaker=%s, original_len=%d, cleaned_len=%d",
        language,
        speaker,
        len(text),
        len(cleaned_text),
    )

    # TTS has a ~500 char limit per call; chunk if needed
    chunks = _chunk_text(cleaned_text, max_chars=480)
    all_audio_b64 = []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for i, chunk in enumerate(chunks):
                payload = {
                    "text": chunk,
                    "target_language_code": language,
                    "speaker": speaker,
                    "model": "bulbul:v3",
                    "sample_rate": 24000,
                    "output_audio_format": "wav",
                }
                response = await client.post(
                    SARVAM_TTS_URL,
                    headers=_get_headers("application/json"),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                audios = data.get("audios", [])
                if audios:
                    all_audio_b64.append(audios[0])
                    logger.debug("Sarvam TTS chunk %d/%d ok", i + 1, len(chunks))

        result = all_audio_b64[0] if all_audio_b64 else None
        if result:
            logger.info("Sarvam TTS success — audio_chunks=%d", len(all_audio_b64))
        return result

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Sarvam TTS HTTP error %s: %s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        return None
    except Exception as exc:
        logger.warning("Sarvam TTS error: %s", str(exc)[:200])
        return None


async def translate(
    text: str,
    source_lang: str = "auto",
    target_lang: str = "en-IN",
) -> dict:
    """
    Translate text using Sarvam Translation API.

    Args:
        text: Input text to translate.
        source_lang: Source language code or "auto" for detection.
        target_lang: Target language code (default English-India).

    Returns:
        dict with keys: translated_text (str), source_language_code (str)
        Returns original text on failure.
    """
    if not is_available():
        logger.info("Sarvam Translate skipped — API key not configured.")
        return {"translated_text": text, "source_language_code": source_lang}

    logger.info(
        "Sarvam Translate request — src=%s, tgt=%s, text_len=%d",
        source_lang,
        target_lang,
        len(text),
    )

    payload = {
        "input": text,
        "source_language_code": source_lang,
        "target_language_code": target_lang,
        "model": "sarvam-translate:v1",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                SARVAM_TRANSLATE_URL,
                headers=_get_headers("application/json"),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        translated_text = data.get("translated_text", text)
        source_language_code = data.get("source_language_code", source_lang)
        logger.info(
            "Sarvam Translate success — detected_src=%s", source_language_code
        )
        return {
            "translated_text": translated_text,
            "source_language_code": source_language_code,
        }

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Sarvam Translate HTTP error %s: %s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        return {"translated_text": text, "source_language_code": source_lang}
    except Exception as exc:
        logger.warning("Sarvam Translate error: %s", str(exc)[:200])
        return {"translated_text": text, "source_language_code": source_lang}


def _chunk_text(text: str, max_chars: int = 480) -> list[str]:
    """Split text into chunks respecting sentence boundaries when possible."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = ""
    # Split by sentences first
    sentences = text.replace("।", ".").replace("。", ".").split(".")

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{current}. {sentence}" if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            # If single sentence exceeds limit, split by words
            if len(sentence) > max_chars:
                words = sentence.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= max_chars:
                        current = f"{current} {word}" if current else word
                    else:
                        if current:
                            chunks.append(current.strip())
                        current = word
            else:
                current = sentence

    if current:
        chunks.append(current.strip())

    return chunks if chunks else [text]
