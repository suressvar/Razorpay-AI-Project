"""
Pronunciation Lexicon and SSML Generator for Multilingual Voice Recovery.
Covers Razorpay payment terminology, major Indian banks, demo customer names,
and code-switched English vocabulary for Indian languages.
"""
from typing import Dict, Optional
from recovery_autopilot.voice.voice_models import LanguageDetected

LEXICON_VERSION = "2026.1"

# Payment and Fintech terminology phonetic expansions
FINTECH_TERMINOLOGY: Dict[str, Dict[str, str]] = {
    "Razorpay": {
        "en-IN": "Razor-pay",
        "hi-IN": "रेज़र-पे",
        "kn-IN": "ರೇಜರ್-ಪೇ",
        "ta-IN": "ரேஸர்-பே",
        "te-IN": "రేజర్-పే",
        "mr-IN": "रेझर-पे",
        "bn-IN": "রেজর-পে",
    },
    "UPI": {
        "en-IN": "U P I",
        "hi-IN": "यू पी आई",
        "kn-IN": "ಯೂ ಪೀ ಐ",
        "ta-IN": "யூ பீ ஐ",
        "te-IN": "యూ పీ ఐ",
        "mr-IN": "यू पी आय",
        "bn-IN": "ইউ পি আই",
    },
    "EMI": {
        "en-IN": "E M I",
        "hi-IN": "ई एम आई",
        "kn-IN": "ಈ ಎಮ್ ಐ",
        "ta-IN": "ஈ எம் ஐ",
        "te-IN": "ఈ ఎమ్ ఐ",
        "mr-IN": "ई एम आय",
        "bn-IN": "ই এম আই",
    },
    "NPCI": {
        "en-IN": "N P C I",
        "hi-IN": "एन पी सी आई",
        "kn-IN": "ಎನ್ ಪಿ ಸಿ ಐ",
        "ta-IN": "என் பீ சீ ஐ",
        "te-IN": "ఎన్ పీ సీ ఐ",
        "mr-IN": "एन पी सी आय",
        "bn-IN": "এন পি সি আই",
    },
    "IMPS": {
        "en-IN": "I M P S",
        "hi-IN": "आई एम पी एस",
        "kn-IN": "ಐ ಎಮ್ ಪಿ ಎಸ್",
        "ta-IN": "ஐ எம் பீ எஸ்",
        "te-IN": "ఐ ఎమ్ పీ ఎస్",
        "mr-IN": "आय एम पी एस",
        "bn-IN": "আই এম পি এস",
    },
    "NEFT": {
        "en-IN": "N E F T",
        "hi-IN": "एन ई एफ टी",
        "kn-IN": "ಎನ್ ಈ ಎಫ್ ಟೀ",
        "ta-IN": "என் ஈ எஃப் டீ",
        "te-IN": "ఎన్ ఈ ఎఫ్ టీ",
        "mr-IN": "एन ई एफ टी",
        "bn-IN": "এন ই এফ টি",
    },
    "RTGS": {
        "en-IN": "R T G S",
        "hi-IN": "आर टी जी एस",
        "kn-IN": "ಆರ್ ಟೀ ಜೀ ಎಸ್",
        "ta-IN": "ஆர் டீ ஜீ எஸ்",
        "te-IN": "ఆర్ టీ జీ ఎస్",
        "mr-IN": "आर टी जी एस",
        "bn-IN": "আর টি জি এস",
    },
    "Autopay": {
        "en-IN": "Auto-pay",
        "hi-IN": "ऑटो-पे",
        "kn-IN": "ಆಟೋ-ಪೇ",
        "ta-IN": "ஆட்டோ-பே",
        "te-IN": "ఆటో-పే",
        "mr-IN": "ऑटो-पे",
        "bn-IN": "অটো-পে",
    },
    "Mandate": {
        "en-IN": "Mandate",
        "hi-IN": "मैंडेट",
        "kn-IN": "ಮ್ಯಾಂಡೇಟ್",
        "ta-IN": "மேன்டேட்",
        "te-IN": "మాండేట్",
        "mr-IN": "मँडेट",
        "bn-IN": "ম্যান্ডেট",
    },
}

# Major Indian Bank Names phonetic pronunciations
INDIAN_BANKS: Dict[str, Dict[str, str]] = {
    "HDFC Bank": {
        "en-IN": "H D F C Bank",
        "hi-IN": "एच डी एफ सी बैंक",
        "kn-IN": "ಎಚ್ ಡಿ ಎಫ್ ಸಿ ಬ್ಯಾಂಕ್",
        "ta-IN": "ஹெச் டி எஃப் சி வங்கி",
        "te-IN": "హెచ్ డి ఎఫ్ సి బ్యాంక్",
        "mr-IN": "एच डी एफ सी बँक",
        "bn-IN": "এইচ ডি এফ সি ব্যাঙ্ক",
    },
    "ICICI Bank": {
        "en-IN": "I C I C I Bank",
        "hi-IN": "आईसीआईसीआई बैंक",
        "kn-IN": "ಐ ಸಿ ಐ ಸಿ ಐ ಬ್ಯಾಂಕ್",
        "ta-IN": "ஐ சி ஐ சி ஐ வங்கி",
        "te-IN": "ఐ సి ఐ సి ఐ బ్యాంక్",
        "mr-IN": "आयसीआयसीआय बँक",
        "bn-IN": "আই সি আই সি আই ব্যাঙ্ক",
    },
    "SBI": {
        "en-IN": "S B I",
        "hi-IN": "एस बी आई",
        "kn-IN": "ಎಸ್ ಬಿ ಐ",
        "ta-IN": "எஸ் பி ஐ",
        "te-IN": "ఎస్ బి ఐ",
        "mr-IN": "एस बी आय",
        "bn-IN": "এস বি আই",
    },
    "State Bank of India": {
        "en-IN": "State Bank of India",
        "hi-IN": "स्टेट बैंक ऑफ़ इंडिया",
        "kn-IN": "ಸ್ಟೇಟ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ",
        "ta-IN": "ஸ்டேட் பாங்க் ஆஃப் இந்தியா",
        "te-IN": "స్టేట్ బ్యాంక్ ఆఫ్ ఇండియా",
        "mr-IN": "स्टेट बँक ऑफ इंडिया",
        "bn-IN": "স্টেট ব্যাঙ্ক অফ ইন্ডিয়া",
    },
    "Axis Bank": {
        "en-IN": "Axis Bank",
        "hi-IN": "एक्सिस बैंक",
        "kn-IN": "ಆಕ್ಸಿಸ್ ಬ್ಯಾಂಕ್",
        "ta-IN": "ஆக்சிஸ் வங்கி",
        "te-IN": "యాక్సిస్ బ్యాంక్",
        "mr-IN": "अ‍ॅक्सिस बँक",
        "bn-IN": "অ্যাক্সিস ব্যাঙ্ক",
    },
    "Kotak Mahindra Bank": {
        "en-IN": "Kotak Mahindra Bank",
        "hi-IN": "कोटक महिंद्रा बैंक",
        "kn-IN": "ಕೋಟಕ್ ಮಹಿಂದ್ರಾ ಬ್ಯಾಂಕ್",
        "ta-IN": "கோடக் மஹிந்திரா வங்கி",
        "te-IN": "కోటక్ మహీంద్రా బ్యాంక్",
        "mr-IN": "कोटक महिंद्रा बँक",
        "bn-IN": "কোটাক মহিন্দ্রা ব্যাঙ্ক",
    },
    "Punjab National Bank": {
        "en-IN": "Punjab National Bank",
        "hi-IN": "पंजाब नेशनल बैंक",
        "kn-IN": "ಪಂಜಾಬ್ ನ್ಯಾಷನಲ್ ಬ್ಯಾಂಕ್",
        "ta-IN": "பஞ்சாப் நேஷனல் வங்கி",
        "te-IN": "పంజాబ్ నేషనల్ బ్యాంక్",
        "mr-IN": "पंजाब नॅशनल बँक",
        "bn-IN": "পাঞ্জাব ন্যাশনাল ব্যাঙ্ক",
    },
    "Bank of Baroda": {
        "en-IN": "Bank of Baroda",
        "hi-IN": "बैंक ऑफ़ बड़ौदा",
        "kn-IN": "ಬ್ಯಾಂಕ್ ಆಫ್ ಬರೋಡಾ",
        "ta-IN": "பாங்க் ஆஃப் பரோடா",
        "te-IN": "బ్యాంక్ ఆఫ్ బరోడా",
        "mr-IN": "बँक ऑफ बडोदा",
        "bn-IN": "ব্যাঙ্ক অফ বরোদা",
    },
    "Canara Bank": {
        "en-IN": "Canara Bank",
        "hi-IN": "केनरा बैंक",
        "kn-IN": "ಕೆನರಾ ಬ್ಯಾಂಕ್",
        "ta-IN": "கனரா வங்கி",
        "te-IN": "కెనరా బ్యాంక్",
        "mr-IN": "कॅनरा बँक",
        "bn-IN": "কানাড়া ব্যাঙ্ক",
    },
}

# Common customer names pronunciation map to ensure natural cadence
CUSTOMER_NAMES_PHONETIC: Dict[str, Dict[str, str]] = {
    "Aarav Sharma": {"en-IN": "Aarav Sharma", "hi-IN": "आरव शर्मा", "ta-IN": "ஆரவ் ஷர்மா"},
    "Priya Patel": {"en-IN": "Priya Patel", "hi-IN": "प्रिया पटेल", "gu-IN": "પ્રિયા પટેલ"},
    "Rohan Verma": {"en-IN": "Rohan Verma", "hi-IN": "रोहन वर्मा"},
    "Ananya Iyer": {"en-IN": "Ananya Iyer", "ta-IN": "அனன்யா ஐயர்", "kn-IN": "ಅನನ್ಯಾ ಅಯ್ಯರ್"},
    "Vikram Rao": {"en-IN": "Vikram Rao", "te-IN": "విక్రమ్ రావు", "kn-IN": "ವಿಕ್ರಮ್ ರಾವ್"},
    "Kavita Reddy": {"en-IN": "Kavita Reddy", "te-IN": "కవిత రెడ్డి"},
    "Suresh Kumar": {"en-IN": "Suresh Kumar", "ta-IN": "சுரேஷ் குமார்", "hi-IN": "सुरेश कुमार"},
    "Sneha Sen": {"en-IN": "Sneha Sen", "bn-IN": "স্নেহা সেন"},
    "Debjit Roy": {"en-IN": "Debjit Roy", "bn-IN": "দেবজিৎ রায়"},
    "Gaurav Joshi": {"en-IN": "Gaurav Joshi", "mr-IN": "गौरव जोशी", "hi-IN": "गौरव जोशी"},
}

# Embedded English terms frequently used in conversational regional speech
EMBEDDED_ENGLISH_TERMS: Dict[str, Dict[str, str]] = {
    "payment link": {
        "hi-IN": "पेमेंट लिंक",
        "kn-IN": "ಪೇಮೆಂಟ್ ಲಿಂಕ್",
        "ta-IN": "பேமென்ட் லிங்க்",
        "te-IN": "పేమెంట్ లింక్",
        "mr-IN": "पेमेंट लिंक",
        "bn-IN": "পেমেন্ট লিঙ্ক",
    },
    "server timeout": {
        "hi-IN": "सर्वर टाइमआउट",
        "kn-IN": "ಸರ್ವರ್ ಟೈಮೌಟ್",
        "ta-IN": "சர்வர் டைம்அவுட்",
        "te-IN": "సర్వర్ టైమ్‌అవుట్",
        "mr-IN": "सर्व्हर टाईमआऊट",
        "bn-IN": "সার্ভার টাইমআউট",
    },
    "technical issue": {
        "hi-IN": "तकनीकी समस्या",
        "kn-IN": "ತಾಂತ್ರಿಕ ಸಮಸ್ಯೆ",
        "ta-IN": "தொழில்நுட்ப சிக்கல்",
        "te-IN": "సాంకేతిక సమస్య",
        "mr-IN": "तांत्रिक अडचण",
        "bn-IN": "প্রযুক্তিগত সমস্যা",
    },
    "discount": {
        "hi-IN": "डिस्काउंट",
        "kn-IN": "ಡಿಸ್ಕೌಂಟ್",
        "ta-IN": "டிஸ்கவுண்ட்",
        "te-IN": "డిస్కౌంట్",
        "mr-IN": "सवलत किंवा डिस्काउंट",
        "bn-IN": "ডিসকাউন্ট",
    },
}


def get_term_pronunciation(term: str, locale_code: str = "en-IN") -> str:
    """Retrieves the phonetic transcription for a term according to locale."""
    for category in [FINTECH_TERMINOLOGY, INDIAN_BANKS, CUSTOMER_NAMES_PHONETIC, EMBEDDED_ENGLISH_TERMS]:
        if term in category:
            return category[term].get(locale_code, category[term].get("en-IN", term))
    return term


def generate_ssml(text: str, language: LanguageDetected = LanguageDetected.ENGLISH, rate: float = 1.0) -> str:
    """Wraps text in standard SSML with voice-first prosody and natural pauses."""
    speed_percent = f"{int(rate * 100)}%"
    lang_tag = "en-IN"
    if language == LanguageDetected.HINDI:
        lang_tag = "hi-IN"
    elif language == LanguageDetected.KANNADA:
        lang_tag = "kn-IN"
    elif language == LanguageDetected.TAMIL:
        lang_tag = "ta-IN"
    elif language == LanguageDetected.TELUGU:
        lang_tag = "te-IN"
    elif language == LanguageDetected.MARATHI:
        lang_tag = "mr-IN"
    elif language == LanguageDetected.BENGALI:
        lang_tag = "bn-IN"

    # Insert slight pause after commas and periods for conversational rhythm
    ssml_body = text.replace(". ", '. <break time="300ms"/> ').replace("? ", '? <break time="350ms"/> ')
    return f'<speak><p><prosody rate="{speed_percent}"><voice xml:lang="{lang_tag}">{ssml_body}</voice></prosody></p></speak>'
