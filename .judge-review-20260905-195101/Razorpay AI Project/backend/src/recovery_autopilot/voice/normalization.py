"""
Multilingual Normalization and Transliteration Layer.
Normalizes Indian currency, relative dates/times, and payment domain terminology
across English and 6 Indian languages (Hindi, Kannada, Tamil, Telugu, Marathi, Bengali)
and 6 code-switched forms (Hinglish, Kanglish, Tanglish, Tenglish, Marathi-English, Bengali-English).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from recovery_autopilot.voice.voice_models import LanguageDetected, TranscriptMetadata


class MultilingualNormalizer:
    """
    Normalizes spoken speech transcripts from Indian vernaculars and code-switched dialects
    without modifying the original customer transcript used for UI presentation.
    """

    # Domain term standardizations
    DOMAIN_SYNONYMS = [
        (r"\b(?:razor\s*pay|rezer\s*pay|rayzorpay)\b", "Razorpay"),
        (r"\b(?:u\s*p\s*i|you\s*pee\s*eye|youpi)\b", "UPI"),
        (r"\b(?:g\s*pay|google\s*pay|gpay)\b", "GPay"),
        (r"\b(?:phone\s*pe|phone\s*pay|fonepe|fonepay)\b", "PhonePe"),
        (r"\b(?:pay\s*tm|paytm)\b", "Paytm"),
        (r"\b(?:watsapp|whatsap|whatsapp|whats\s*app)\b", "WhatsApp"),
        (r"\b(?:e\s*mandate|emandate|auto\s*debit|autopay)\b", "mandate"),
        (r"\b(?:d\s*n\s*d|do\s*not\s*disturb)\b", "DND"),
    ]

    # Currency regexes
    CURRENCY_WORDS = {
        "lakh": 100000,
        "lacs": 100000,
        "lac": 100000,
        "crore": 10000000,
        "crores": 10000000,
        "cr": 10000000,
        "k": 1000,
        "thousand": 1000,
        "hazaar": 1000,
        "saavira": 1000,
        "aayiram": 1000,
        "veyi": 1000,
    }

    # Transliteration & code-switching keyword dictionaries
    LANGUAGE_MARKERS = {
        LanguageDetected.HINDI: {
            "script": r"[\u0900-\u097F]",
            "words": ["भुगतान", "पैसे", "कल", "शाम", "लिंक", "भेज", "रद्द", "करो", "मत", "अधिकारी", "खाते"],
        },
        LanguageDetected.KANNADA: {
            "script": r"[\u0C80-\u0CFF]",
            "words": ["ಪಾವತಿ", "ನಾಳೆ", "ದುಡ್ಡು", "ಖಾತೆಯಿಂದ", "ಮಾಡ್ತೀನಿ", "ಕಳುಹಿಸಿ", "ಫೋನ್", "ಮಾಡಬೇಡಿ", "ಬೇಡ"],
        },
        LanguageDetected.TAMIL: {
            "script": r"[\u0B80-\u0BFF]",
            "words": ["பணம்", "நாளைக்கு", "கணக்கு", "அனுப்புங்க", "பண்ணுறேன்", "கால்", "பண்ணாதீங்க", "வேண்டாம்"],
        },
        LanguageDetected.TELUGU: {
            "script": r"[\u0C00-\u0C7F]",
            "words": ["చెల్లింపు", "రేపు", "డబ్బులు", "పంపండి", "చేస్తాను", "కాల్", "చేయవద్దు", "ఖాతా"],
        },
        LanguageDetected.MARATHI: {
            "script": r"[\u0900-\u097F]",
            "words": ["मला", "पाठवा", "उद्या", "खात्यातून", "करतो", "फोन", "करू", "नका", "कपात", "पैसे"],
        },
        LanguageDetected.BENGALI: {
            "script": r"[\u0980-\u09FF]",
            "words": ["টাকা", "কাল", "আগামীকাল", "পাঠান", "করব", "फोन", "করবেন", "না", "কেটে"],
        },
        # Latin script transliterations (code-switched)
        LanguageDetected.KANGLISH: {
            "words": [
                "naale", "baratte", "sanje", "madtini", "maadthini", "kalhsi", "kalsi",
                "duddu", "naadiddu", "belagge", "phone madbedi", "call madbedi", "kat aagide",
                "kat aayithu", "beda", "payment madtini", "link kalsi", "duffar", "hege", "enu", "kodtini"
            ]
        },
        LanguageDetected.TANGLISH: {
            "words": [
                "naalaiki", "naalaikku", "maalaikku", "panam", "pannuren", "panren", "anupunga", "anuppunga",
                "naalanki", "kaalai", "call pannathinga", "phone pannathenga", "cut aachu", "debit aachu",
                "vendam", "payment panren", "link anupunga", "enaku", "enna", "kuduthuten"
            ]
        },
        LanguageDetected.TENGLISH: {
            "words": [
                "repu", "saayantram", "raagane", "chestanu", "chestha", "pampandi", "pampinchandi",
                "ellundi", "dabbu", "dabbulu", "udayam", "call cheyyavaddhu", "phone cheyyodhu",
                "cut aindi", "debit aindi", "vaddu", "payment chestanu", "link pampandi", "naaku", "icchanu"
            ]
        },
        LanguageDetected.MARATHI_ENGLISH: {
            "words": [
                "udya", "parva", "paise", "karto", "pathva", "pathva link", "phone karu naka",
                "cut jhale", "debit jhale", "nako", "sakali", "sandhyakali", "aata", "kasa"
            ]
        },
        LanguageDetected.BENGALI_ENGLISH: {
            "words": [
                "kaal", "aagami kaal", "porshu", "taka", "korbo", "pathan", "pathiye din", "phone korben na",
                "kete geche", "debit hoyeche", "lagbe na", "shokale", "shondhaye", "aami", "koto"
            ]
        },
        LanguageDetected.HINGLISH: {
            "words": [
                "haan", "nahi", "bhejo", "kar deta", "kardo", "aayega", "dunga", "dungaa",
                "paise", "kat gaye", "dubara", "mat karo", "mujhe", "mera", "kal", "shaam",
                "parso", "baad me", "abhi", "karo", "boliye", "batao", "link bhej"
            ]
        },
    }

    @classmethod
    def identify_language_and_dialect(
        cls, text: str, previous_language_hint: Optional[str] = None
    ) -> Tuple[LanguageDetected, float, List[str], bool]:
        """
        Detects primary language, confidence, alternative candidate languages,
        and whether the utterance is code-switched with English/Latin terms.
        """
        raw_text = text.strip()
        lower = raw_text.lower()
        if not raw_text:
            return LanguageDetected.ENGLISH, 0.5, [], False

        # 1. Native script detection (high confidence 0.98)
        if re.search(r"[\u0C80-\u0CFF]", raw_text):
            return LanguageDetected.KANNADA, 0.98, ["kanglish"], True if re.search(r"[a-zA-Z]", raw_text) else False
        if re.search(r"[\u0B80-\u0BFF]", raw_text):
            return LanguageDetected.TAMIL, 0.98, ["tanglish"], True if re.search(r"[a-zA-Z]", raw_text) else False
        if re.search(r"[\u0C00-\u0C7F]", raw_text):
            return LanguageDetected.TELUGU, 0.98, ["tenglish"], True if re.search(r"[a-zA-Z]", raw_text) else False
        if re.search(r"[\u0980-\u09FF]", raw_text):
            return LanguageDetected.BENGALI, 0.98, ["bengali_english"], True if re.search(r"[a-zA-Z]", raw_text) else False
        if re.search(r"[\u0900-\u097F]", raw_text):
            # Differentiate Marathi vs Hindi
            if any(w in raw_text for w in ["मला", "पाठवा", "उद्या", "करतो", "आहे", "नाही", "पाहिजे", "कपात", "खात्यातून", "व्हॉट्सॲपवर", "भरतो", "पैसे", "नका"]):
                return LanguageDetected.MARATHI, 0.98, ["hindi"], False
            return LanguageDetected.HINDI, 0.97, ["hinglish"], True if re.search(r"[a-zA-Z]", raw_text) else False

        # 2. Latin script / Code-switched transliteration detection
        scores: Dict[LanguageDetected, int] = {}
        for lang_enum, data in cls.LANGUAGE_MARKERS.items():
            words = data.get("words", [])
            match_count = sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", lower))
            if match_count > 0:
                scores[lang_enum] = match_count

        if scores:
            best_lang = max(scores, key=scores.get)
            match_val = scores[best_lang]
            confidence = min(0.95, 0.75 + (match_val * 0.08))
            alternatives = [l.value for l in scores if l != best_lang]
            is_code_switched = best_lang in [
                LanguageDetected.HINGLISH,
                LanguageDetected.KANGLISH,
                LanguageDetected.TANGLISH,
                LanguageDetected.TENGLISH,
                LanguageDetected.MARATHI_ENGLISH,
                LanguageDetected.BENGALI_ENGLISH,
            ] or bool(re.search(r"[a-zA-Z]", raw_text))
            return best_lang, confidence, alternatives, is_code_switched

        # 3. Default to English (en-IN)
        return LanguageDetected.ENGLISH, 0.85, ["hinglish"], False

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalizes currency expressions, acronyms, and whitespace while preserving original tokens.
        """
        norm = text.strip()

        # Domain term standardization
        for pattern, replacement in cls.DOMAIN_SYNONYMS:
            norm = re.sub(pattern, replacement, norm, flags=re.IGNORECASE)

        # Standardize Indian currency numbers: "5 k" -> "5000", "2.5 lakh" -> "250000"
        def _replace_currency(match: re.Match) -> str:
            val_str = match.group(1).replace(",", "")
            unit = match.group(2).lower()
            try:
                num = float(val_str)
                multiplier = cls.CURRENCY_WORDS.get(unit, 1)
                total = int(num * multiplier) if (num * multiplier).is_integer() else (num * multiplier)
                return f"₹{total}"
            except Exception:
                return match.group(0)

        norm = re.sub(
            r"(?:rs\.?|inr|rupees|₹)?\s*(\d+(?:\.\d+)?)\s*(lakh|lacs|lac|crore|crores|cr|k|thousand|hazaar)\b",
            _replace_currency,
            norm,
            flags=re.IGNORECASE,
        )

        # Standardize "500 rs" or "500 rupees" -> "₹500"
        norm = re.sub(
            r"\b(?:rs\.?|inr|rupees|rupaye|duddu|panam|dabbu|taka)\s*(\d+)\b",
            r"₹\1",
            norm,
            flags=re.IGNORECASE,
        )
        norm = re.sub(
            r"\b(\d+)\s*(?:rs\.?|inr|rupees|rupaye|duddu|panam|dabbu|taka)\b",
            r"₹\1",
            norm,
            flags=re.IGNORECASE,
        )

        return re.sub(r"\s+", " ", norm).strip()

    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, Any]:
        """
        Extracts dates, times, amounts, and language preferences across Indian languages.
        """
        lower = text.lower()
        entities: Dict[str, Any] = {}

        # Amount extraction (₹500 or 5000)
        amount_match = re.search(r"₹(\d+(?:\.\d+)?)", cls.normalize_text(text))
        if amount_match:
            try:
                entities["amount"] = float(amount_match.group(1))
            except Exception:
                pass

        # Date & Relative Day Extraction
        # Tomorrow
        if any(w in lower for w in [
            "tomorrow", "kal", "naale", "naalaiki", "naalaikku", "repu", "udya", "aagami kaal", "kaal"
        ]):
            entities["promise_date"] = "tomorrow"
            entities["promised_date"] = "tomorrow"
        # Day after tomorrow
        elif any(w in lower for w in [
            "day after tomorrow", "parso", "naadiddu", "naalanki", "ellundi", "parva", "porshu"
        ]):
            entities["promise_date"] = "day_after_tomorrow"
            entities["promised_date"] = "day_after_tomorrow"
        # Next week / Monday
        elif any(w in lower for w in ["next monday", "agle somvaar", "munde somavara", "adutha thingal", "vache somavaram"]):
            entities["promise_date"] = "next_monday"
            entities["promised_date"] = "next_monday"
        elif "next week" in lower or "agle hafte" in lower or "adutha vaaram" in lower:
            entities["promise_date"] = "next_week"
            entities["promised_date"] = "next_week"
        elif re.search(r"\b(\d+)\s*(?:days?|din|dina|naal|roj)\b", lower):
            days_match = re.search(r"\b(\d+)\s*(?:days?|din|dina|naal|roj)\b", lower)
            if days_match:
                d_str = f"in_{days_match.group(1)}_days"
                entities["promise_date"] = d_str
                entities["promised_date"] = d_str

        # Time extraction: "evening", "5 PM", "shaam", "sanje", "maalaikku", "saayantram"
        if any(w in lower for w in ["evening", "shaam", "sanje", "maalaikku", "saayantram", "sandhyakali", "shondhaye"]):
            entities["promised_time"] = "evening"
        elif any(w in lower for w in ["morning", "subah", "belagge", "kaalai", "udayam", "sakali", "shokale"]):
            entities["promised_time"] = "morning"
        elif any(w in lower for w in ["afternoon", "dopahar", "madyahna", "madhyanam"]):
            entities["promised_time"] = "afternoon"

        time_clock = re.search(r"\b(\d{1,2}(?::\d{2})?)\s*(am|pm|baje|ghante)?\b", lower)
        if time_clock and ("baje" in lower or "pm" in lower or "am" in lower or ":" in time_clock.group(0)):
            entities["promised_time"] = time_clock.group(0)

        # Language Change Request Extraction
        if any(w in lower for w in ["speak in kannada", "kannada dalli", "kannada me"]):
            entities["requested_language"] = "kannada"
        elif any(w in lower for w in ["speak in tamil", "tamil la", "tamil me"]):
            entities["requested_language"] = "tamil"
        elif any(w in lower for w in ["speak in telugu", "telugu lo", "telugu me"]):
            entities["requested_language"] = "telugu"
        elif any(w in lower for w in ["speak in hindi", "hindi me", "hindi lo"]):
            entities["requested_language"] = "hindi"
        elif any(w in lower for w in ["speak in bengali", "bangla te", "bengali me"]):
            entities["requested_language"] = "bengali"
        elif any(w in lower for w in ["speak in marathi", "marathi madhe", "marathi me"]):
            entities["requested_language"] = "marathi"
        elif any(w in lower for w in ["speak in english", "english please"]):
            entities["requested_language"] = "english"

        return entities

    @classmethod
    def build_transcript_metadata(
        cls,
        raw_text: str,
        previous_language_hint: Optional[str] = None,
        transcription_confidence: float = 1.0,
    ) -> TranscriptMetadata:
        """
        Constructs the structured TranscriptMetadata schema expected by the domain contracts.
        """
        detected_lang, lang_conf, alt_langs, is_code_switched = cls.identify_language_and_dialect(
            raw_text, previous_language_hint
        )
        normalized = cls.normalize_text(raw_text)
        needs_clarification = transcription_confidence < 0.65 or len(raw_text.strip()) == 0

        return TranscriptMetadata(
            original_transcript=raw_text,
            normalized_transcript=normalized,
            detected_language=detected_lang.value,
            language_confidence=lang_conf,
            alternative_languages=alt_langs,
            code_switched=is_code_switched,
            transcription_confidence=transcription_confidence,
            needs_clarification=needs_clarification,
        )
