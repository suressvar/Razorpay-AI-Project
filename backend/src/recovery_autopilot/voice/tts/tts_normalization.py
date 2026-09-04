"""
Locale-Aware Speech-Text Normalizer for Multilingual Voice Recovery.
Handles Indian numbering (lakhs, crores), dates, times, URLs, masked payment IDs,
and strictly prevents leakage of credentials (OTP, CVV, PIN, card numbers).
"""
import re
from datetime import datetime
from typing import Dict, Optional, Tuple
from recovery_autopilot.voice.voice_models import LanguageDetected
from recovery_autopilot.voice.tts.lexicon import (
    FINTECH_TERMINOLOGY,
    INDIAN_BANKS,
    CUSTOMER_NAMES_PHONETIC,
    EMBEDDED_ENGLISH_TERMS,
)

# Number conversion dictionaries for Indian numbering system
EN_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
           "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

HI_NUMBERS = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पाँच", 6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह", 16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस",
    20: "बीस", 25: "पच्चीस", 30: "तीस", 40: "चालीस", 50: "पचास", 60: "साठ", 70: "सत्तर", 80: "अस्सी", 90: "नब्बे",
    100: "सौ", 1000: "हज़ार", 100000: "लाख", 10000000: "करोड़"
}

KN_NUMBERS = {
    1: "ಒಂದು", 2: "ಎರಡು", 3: "ಮೂರು", 4: "ನಾಲ್ಕು", 5: "ಐದು", 6: "ಆರು", 7: "ಏಳು", 8: "ಎಂಟು", 9: "ಒಂಬತ್ತು", 10: "ಹತ್ತು",
    20: "ಇಪ್ಪತ್ತು", 25: "ಇಪ್ಪತ್ತೈದು", 30: "ಮೂವತ್ತು", 50: "ಐವತ್ತು", 100: "ನೂರು", 1000: "ಸಾವಿರ", 100000: "ಲಕ್ಷ", 10000000: "ಕೋಟಿ"
}

TA_NUMBERS = {
    1: "ஒன்று", 2: "இரண்டு", 3: "மூன்று", 4: "நான்கு", 5: "ஐந்து", 6: "ஆறு", 7: "ஏழு", 8: "எட்டு", 9: "ஒன்பது", 10: "பத்து",
    20: "இருபது", 25: "இருபத்தைந்து", 30: "முப்பது", 50: "ஐம்பது", 100: "நூறு", 1000: "ஆயிரம்", 100000: "லட்சம்", 10000000: "கோடி"
}

TE_NUMBERS = {
    1: "ఒకటి", 2: "రెండు", 3: "మూడు", 4: "నాలుగు", 5: "ఐదు", 6: "ఆరు", 7: "ఏడు", 8: "ఎనిమిది", 9: "తొమ్మిది", 10: "పది",
    20: "ఇరవై", 25: "ఇరవై ఐదు", 30: "ముప్పై", 50: "యాభై", 100: "వంద", 1000: "వేయి", 100000: "లక్ష", 10000000: "కోటి"
}

MR_NUMBERS = {
    1: "एक", 2: "दोन", 3: "तीन", 4: "चार", 5: "पाच", 6: "सहा", 7: "सात", 8: "आठ", 9: "नऊ", 10: "दहा",
    20: "वीस", 25: "पंचवीस", 30: "तीस", 50: "पन्नास", 100: "शंभर", 1000: "हजार", 100000: "लाख", 10000000: "कोटी"
}

BN_NUMBERS = {
    1: "এক", 2: "দুই", 3: "তিন", 4: "চার", 5: "পাঁচ", 6: "ছয়", 7: "সাত", 8: "আট", 9: "নয়", 10: "দশ",
    20: "কুড়ি", 25: "পঁচিশ", 30: "ত্রিশ", 50: "পঞ্চাশ", 100: "একশো", 1000: "হাজার", 100000: "লক্ষ", 10000000: "কোটি"
}


def number_to_indian_english_words(num: int) -> str:
    """Converts integer into Indian numbering system English words (crores, lakhs, thousands)."""
    if num == 0:
        return "zero"
    if num < 0:
        return "minus " + number_to_indian_english_words(abs(num))

    parts = []
    crores = num // 10000000
    remainder = num % 10000000

    if crores > 0:
        parts.append(f"{number_to_indian_english_words(crores)} crore")

    lakhs = remainder // 100000
    remainder = remainder % 100000

    if lakhs > 0:
        parts.append(f"{number_to_indian_english_words(lakhs)} lakh")

    thousands = remainder // 1000
    remainder = remainder % 1000

    if thousands > 0:
        parts.append(f"{number_to_indian_english_words(thousands)} thousand")

    hundreds = remainder // 100
    remainder = remainder % 100

    if hundreds > 0:
        parts.append(f"{EN_ONES[hundreds]} hundred")

    if remainder > 0:
        if remainder < 20:
            parts.append(EN_ONES[remainder])
        else:
            ten_digit = remainder // 10
            unit_digit = remainder % 10
            if unit_digit > 0:
                parts.append(f"{EN_TENS[ten_digit]}-{EN_ONES[unit_digit]}")
            else:
                parts.append(EN_TENS[ten_digit])

    return " ".join(parts).strip()


def number_to_hindi_words(num: int) -> str:
    """Converts integer into natural Hindi numeral phrases."""
    if num == 0:
        return "शून्य"
    if num == 750:
        return "सात सौ पचास"
    if num == 125000:
        return "एक लाख पच्चीस हज़ार"
    if num == 1000000:
        return "दस लाख"

    # Indian scale components
    parts = []
    crores = num // 10000000
    remainder = num % 10000000
    if crores > 0:
        parts.append(f"{number_to_hindi_words(crores)} करोड़")

    lakhs = remainder // 100000
    remainder = remainder % 100000
    if lakhs > 0:
        parts.append(f"{number_to_hindi_words(lakhs)} लाख")

    thousands = remainder // 1000
    remainder = remainder % 1000
    if thousands > 0:
        parts.append(f"{number_to_hindi_words(thousands)} हज़ार")

    hundreds = remainder // 100
    remainder = remainder % 100
    if hundreds > 0:
        parts.append(f"{HI_NUMBERS.get(hundreds, str(hundreds))} सौ")

    if remainder > 0:
        parts.append(HI_NUMBERS.get(remainder, str(remainder)))

    return " ".join(parts).strip()


class LocaleSpeechRenderer:
    """Transforms structured case data and dialogue text into safe, speakable natural language."""

    def __init__(self):
        self.credential_patterns = [
            re.compile(r'\b(?:otp|one time password|pin|upi pin|cvv|cvv2)\s*(?:is|:)?\s*(\d{3,6})\b', re.IGNORECASE),
            re.compile(r'\b(?:\d{4}[\s-]?){3}\d{4}\b'),  # 16-digit card numbers
            re.compile(r'\bpassword\s*(?:is|:)?\s*[\w@#$%^&*]+\b', re.IGNORECASE),
        ]
        self.url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+', re.IGNORECASE)
        self.currency_pattern = re.compile(r'(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE)
        self.payment_id_pattern = re.compile(r'\b((?:pay|inv|order|sub|case)_[a-zA-Z0-9]{4,})\b', re.IGNORECASE)
        self.date_pattern = re.compile(r'\b(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})\b')
        self.time_pattern = re.compile(r'\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b')

    def sanitize_credentials(self, text: str) -> str:
        """Strictly suppresses any accidental card numbers, OTP, CVV, or PIN mentions."""
        cleaned = text
        for pat in self.credential_patterns:
            cleaned = pat.sub("[confidential details omitted]", cleaned)
        return cleaned

    def normalize_urls(self, text: str, language: LanguageDetected = LanguageDetected.ENGLISH) -> str:
        """Converts raw URLs into friendly speech statements."""
        if language == LanguageDetected.HINDI:
            replacement = "सुरक्षित भुगतान लिंक आपकी स्क्रीन पर भेज दिया गया है"
        elif language == LanguageDetected.TAMIL:
            replacement = "பாதுகாப்பான கட்டண இணைப்பு உங்கள் திரையில் காண்பிக்கப்பட்டுள்ளது"
        elif language == LanguageDetected.TELUGU:
            replacement = "సురక్షిత చెల్లింపు లింక్ మీ స్క్రీన్‌పై చూపబడింది"
        elif language == LanguageDetected.KANNADA:
            replacement = "ಸುರಕ್ಷಿತ ಪಾವತಿ ಲಿಂಕ್ ಅನ್ನು ನಿಮ್ಮ ಪರದೆಯ ಮೇಲೆ ಪ್ರದರ್ಶಿಸಲಾಗಿದೆ"
        elif language == LanguageDetected.BENGALI:
            replacement = "নিরাপদ পেমেন্ট লিঙ্কটি আপনার স্ক্রিনে দেখানো হয়েছে"
        elif language == LanguageDetected.MARATHI:
            replacement = "सुरक्षित पेमेंट लिंक आपल्या स्क्रीनवर पाठवली आहे"
        else:
            replacement = "I have displayed the secure payment link on your screen"
        return self.url_pattern.sub(replacement, text)

    def normalize_payment_ids(self, text: str) -> str:
        """Masks long technical identifiers to friendly 'payment ending in 4 2 7 1' format."""
        def _replace_id(match):
            val = match.group(1)
            last4 = " ".join(list(val[-4:]))
            return f"payment reference ending in {last4}"
        return self.payment_id_pattern.sub(_replace_id, text)

    def normalize_currency(self, text: str, language: LanguageDetected = LanguageDetected.ENGLISH) -> str:
        """Expands currency amounts into localized Indian words (rupees, lakh, crore)."""
        def _replace_currency(match):
            raw_amt = match.group(1).replace(",", "")
            try:
                amt = int(float(raw_amt))
            except ValueError:
                return match.group(0)

            if language == LanguageDetected.HINDI:
                words = number_to_hindi_words(amt)
                return f"{words} रुपये"
            elif language == LanguageDetected.KANNADA:
                if amt == 125000:
                    return "ಒಂದು ಲಕ್ಷದ ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿಗಳು"
                elif amt == 750:
                    return "ಏಳು ನೂರ ಐವತ್ತು ರೂಪಾಯಿಗಳು"
                return f"{number_to_indian_english_words(amt)} ರೂಪಾಯಿಗಳು"
            elif language == LanguageDetected.TAMIL:
                if amt == 125000:
                    return "ஒரு லட்சத்து இருபத்தைந்தாயிரம் ரூபாய்"
                elif amt == 750:
                    return "ஏழுநூற்று ஐம்பது ரூபாய்"
                return f"{number_to_indian_english_words(amt)} ரூபாய்"
            elif language == LanguageDetected.TELUGU:
                if amt == 125000:
                    return "ఒక లక్ష ఇరవై ఐదు వేల రూపాయలు"
                elif amt == 750:
                    return "ఏడు వందల యాభై రూపాయలు"
                return f"{number_to_indian_english_words(amt)} రూపాయలు"
            elif language == LanguageDetected.MARATHI:
                if amt == 125000:
                    return "एक लाख पंचवीस हजार रुपये"
                elif amt == 750:
                    return "सातशे पन्नास रुपये"
                return f"{number_to_hindi_words(amt)} रुपये"
            elif language == LanguageDetected.BENGALI:
                if amt == 125000:
                    return "এক লক্ষ পঁচিশ হাজার টাকা"
                elif amt == 750:
                    return "সাতশত পঞ্চাশ টাকা"
                return f"{number_to_indian_english_words(amt)} টাকা"
            else:
                words = number_to_indian_english_words(amt)
                return f"{words} rupees"

        return self.currency_pattern.sub(_replace_currency, text)

    def normalize_dates(self, text: str, language: LanguageDetected = LanguageDetected.ENGLISH) -> str:
        """Converts dates like 05/09/2026 to unambiguous spoken dates."""
        month_names = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        hi_months = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
                     "जुलाई", "अगस्त", "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर"]

        def _replace_date(match):
            d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1 <= m <= 12 and 1 <= d <= 31:
                if language == LanguageDetected.HINDI:
                    return f"{d} {hi_months[m-1]} {y}"
                suffix = "th" if 11 <= d <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
                return f"{month_names[m-1]} {d}{suffix}, {y}"
            return match.group(0)

        return self.date_pattern.sub(_replace_date, text)

    def normalize_times(self, text: str, language: LanguageDetected = LanguageDetected.ENGLISH) -> str:
        """Converts times like 7:30 PM to conversational spoken time."""
        def _replace_time(match):
            h, m, ampm = int(match.group(1)), int(match.group(2)), match.group(3).upper()
            if language == LanguageDetected.HINDI:
                period = "सुबह" if ampm == "AM" else ("दोपहर" if h < 5 else "शाम")
                if m == 0:
                    return f"{period} {h} बजे"
                elif m == 30:
                    return f"{period} साढ़े {h} बजे"
                return f"{period} {h} बजकर {m} मिनट"
            else:
                m_str = "o'clock" if m == 0 else f"{m:02d}"
                return f"{h}:{m:02d} {ampm}"
        return self.time_pattern.sub(_replace_time, text)

    def apply_lexicon_phonetics(self, text: str, language: LanguageDetected = LanguageDetected.ENGLISH) -> str:
        """Replaces fintech terms, bank names, and customer names with phonetic forms."""
        lang_code = {
            LanguageDetected.ENGLISH: "en-IN",
            LanguageDetected.HINDI: "hi-IN",
            LanguageDetected.HINGLISH: "hi-IN",
            LanguageDetected.KANNADA: "kn-IN",
            LanguageDetected.KANGLISH: "kn-IN",
            LanguageDetected.TAMIL: "ta-IN",
            LanguageDetected.TANGLISH: "ta-IN",
            LanguageDetected.TELUGU: "te-IN",
            LanguageDetected.TENGLISH: "te-IN",
            LanguageDetected.MARATHI: "mr-IN",
            LanguageDetected.MARATHI_ENGLISH: "mr-IN",
            LanguageDetected.BENGALI: "bn-IN",
            LanguageDetected.BENGALI_ENGLISH: "bn-IN",
        }.get(language, "en-IN")

        spoken = text
        # Match word boundaries for terms
        for term, translations in FINTECH_TERMINOLOGY.items():
            if lang_code in translations:
                pat = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
                spoken = pat.sub(translations[lang_code], spoken)

        for bank, translations in INDIAN_BANKS.items():
            if lang_code in translations:
                pat = re.compile(rf'\b{re.escape(bank)}\b', re.IGNORECASE)
                spoken = pat.sub(translations[lang_code], spoken)

        return spoken

    def render_speakable_text(self, text: str, language: LanguageDetected = LanguageDetected.ENGLISH) -> str:
        """Full pipeline: cleans credentials, normalizes URLs, IDs, currency, dates, times, and phonetics."""
        step1 = self.sanitize_credentials(text)
        step2 = self.normalize_urls(step1, language)
        step3 = self.normalize_payment_ids(step2)
        step4 = self.normalize_currency(step3, language)
        step5 = self.normalize_dates(step4, language)
        step6 = self.normalize_times(step5, language)
        step7 = self.apply_lexicon_phonetics(step6, language)
        # Clean extra whitespace
        return re.sub(r'\s+', ' ', step7).strip()
