"""
Multilingual Voice Recovery Agent Engine.
Supports English plus 6 Indian languages, 6 code-switched dialects, hybrid intent classification,
Structured Intent Contracts, and Safety Guardrails.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from recovery_autopilot.voice.normalization import MultilingualNormalizer
from recovery_autopilot.voice.prompts import VOICE_AGENT_MASTER_PROMPT
from recovery_autopilot.voice.voice_guardrails import VoiceGuardrails
from recovery_autopilot.voice.voice_models import (
    IntentEntities,
    LanguageDetected,
    StructuredIntentResult,
    TranscriptMetadata,
    VoiceAgentAnalysis,
    VoiceIntent,
)

logger = logging.getLogger("recovery_autopilot.voice.voice_agent")
VOICE_AGENT_SYSTEM_PROMPT = VOICE_AGENT_MASTER_PROMPT


class VoiceRecoveryAgent:
    """
    Multilingual AI voice recovery agent for customer communication.
    Supports English, Hindi, Kannada, Tamil, Telugu, Marathi, Bengali, and code-switched dialects.
    """

    def __init__(self, provider_name: str = "fake", api_key: Optional[str] = None):
        self.provider_name = provider_name
        self.api_key = api_key

    def _generate_localized_responses(
        self,
        intent: VoiceIntent,
        amount: float,
        entities: Dict[str, Any],
        clarification_q: Optional[str] = None,
    ) -> Dict[str, str]:
        amt_str = f"₹{int(amount)}"
        date_str = entities.get("promise_date", "tomorrow")

        if clarification_q:
            return {
                "english": clarification_q,
                "hinglish": "Kya aap please repeat kar sakte hain? Aap payment link chahte hain ya kal pay karna prefer karenge?",
                "hindi": "क्या आप दोहरा सकते हैं? क्या आप भुगतान लिंक चाहते हैं या कल भुगतान करेंगे?",
                "kannada": "ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಹೇಳಬಹುದೇ? ನೀವು ಲಿಂಕ್ ಬಯಸುತ್ತೀರಾ ಅಥವಾ ನಾಳೆ ಪಾವತಿಸುತ್ತೀರಾ?",
                "tamil": "தயவுசெய்து மீண்டும் கூற முடியுமா? நீங்கள் லிங்க் பெற விரும்புகிறீர்களா?",
                "telugu": "దయచేసి మళ్లీ చెప్పగలరా? మీరు పేమెంట్ లింక్ కోరుకుంటున్నారా?",
                "marathi": "कृपया पुन्हा सांगू शकता का? आपण पेमेंट लिंक इच्छिता का?",
                "bengali": "দয়া করে আবার বলবেন কি? আপনি কি পেমেন্ট লিংক চান?",
            }

        if intent == VoiceIntent.STOP_CONTACT:
            return {
                "english": "I have registered your number on the Do Not Disturb list. You will not receive further recovery calls. Thank you.",
                "hinglish": "Maine aapka number DND list me update kar diya hai. Ab aapko koi calls nahi aayengi. Thank you.",
                "hindi": "मैंने आपका नंबर डीएनडी सूची में दर्ज कर लिया है। आपको आगे कोई कॉल नहीं आएगी।",
                "kannada": "ನಿಮ್ಮ ಸಂಖ್ಯೆಯನ್ನು DND ಪಟ್ಟಿಯಲ್ಲಿ ನೋಂದಾಯಿಸಲಾಗಿದೆ. ಇನ್ನು ಮುಂದೆ ಯಾವುದೇ ಕರೆಗಳು ಬರುವುದಿಲ್ಲ. ಧನ್ಯವಾದಗಳು.",
                "tamil": "உங்கள் எண் DND பட்டியலில் சேர்க்கப்பட்டது. இனிமேல் அழைப்புகள் வராது. நன்றி.",
                "telugu": "మీ నంబర్ DND లిస్ట్‌లో నమోదు చేయబడింది. ఇకపై కాల్స్ రావు. ధన్యవాదాలు.",
                "marathi": "मी आपला नंबर DND यादीत नोंदवला आहे. यापुढे कॉल येणार नाहीत. धन्यवाद.",
                "bengali": "আপনার নম্বরটি DND তালিকায় যোগ করা হয়েছে। আর কোনো কল আসবে না। ধন্যবাদ।",
            }

        if intent == VoiceIntent.ALREADY_PAID:
            return {
                "english": "Since your account has already been debited, I am escalating this to our finance team to verify bank reconciliation.",
                "hinglish": "Agar aapke account se paise kat chuke hain, toh main turant hamare finance support team ko escalate kar deta hoon payment verify karne ke liye.",
                "hindi": "चूंकि आपके खाते से पैसे कट चुके हैं, मैं बैंक सत्यापन के लिए वित्त टीम को यह मामला भेज रहा हूँ।",
                "kannada": "ನಿಮ್ಮ ಖಾತೆಯಿಂದ ಹಣ ಕಡಿತಗೊಂಡಿದ್ದರೆ, ಪರಿಶೀಲನೆಗಾಗಿ ನಾನು ಇದನ್ನು ನಮ್ಮ ಹಣಕಾಸು ತಂಡಕ್ಕೆ ಕಳುಹಿಸುತ್ತೇನೆ.",
                "tamil": "உங்கள் கணக்கிலிருந்து பணம் பிடித்தம் செய்யப்பட்டிருந்தால், சரிபார்க்க நிதிக்குழுவிற்கு மாற்றுகிறேன்.",
                "telugu": "మీ ఖాతా నుండి డబ్బులు కట్ అయితే, ధృవీకరణ కోసం మా ఫైనాన్స్ టీమ్‌కు బదిలీ చేస్తున్నాను.",
                "marathi": "आपल्या खात्यातून पैसे वजा झाले असल्यास, मी तपासणीसाठी वित्त विभागाकडे पाठवत आहे.",
                "bengali": "যেহেতু আপনার টাকা কেটে নেওয়া হয়েছে, আমি এটি তদন্তের জন্য অর্থ বিভাগের কাছে পাঠাচ্ছি।",
            }

        if intent == VoiceIntent.PAYMENT_DISPUTE:
            return {
                "english": "Your dispute has been recorded. I am pausing all retry attempts and opening a dispute review ticket.",
                "hinglish": "Aapka dispute note kar liya gaya hai. Main sabhi retry pause kar raha hoon aur review initiate kar raha hoon.",
                "hindi": "आपका विवाद दर्ज कर लिया गया है। मैं सभी पुन: प्रयास रोक रहा हूँ।",
                "kannada": "ನಿಮ್ಮ ಆಕ್ಷೇಪಣೆಯನ್ನು ದಾಖಲಿಸಲಾಗಿದೆ. ಎಲ್ಲಾ ಮರುಪ್ರಯತ್ನಗಳನ್ನು ತಡೆಹಿಡಿಯಲಾಗಿದೆ.",
                "tamil": "உங்கள் புகார் பதிவு செய்யப்பட்டது. அனைத்து மறுமுயற்சிகளும் தற்காலிகமாக நிறுத்தப்படுகின்றன.",
                "telugu": "మీ ఫిర్యాదు నమోదు చేయబడింది. అన్ని ప్రయత్నాలు నిలిపివేయబడ్డాయి.",
                "marathi": "आपली तक्रार नोंदवली आहे. सर्व पुढील प्रयत्न तात्पुरते थांबवले आहेत.",
                "bengali": "আপনার অভিযোগ নথিভুক্ত হয়েছে। সমস্ত পুনর্চেষ্টা স্থগিত করা হয়েছে।",
            }

        if intent == VoiceIntent.WRONG_CUSTOMER:
            return {
                "english": "I apologize for the inconvenience. I have marked this number as a wrong contact and removed it from this account.",
                "hinglish": "Maafi chahta hoon. Maine is number ko galat contact ke roop me update karke remove kar diya hai.",
                "hindi": "असुविधा के लिए क्षमा करें। मैंने इस नंबर को हटा दिया है।",
                "kannada": "ಕ್ಷಮಿಸಿ, ಈ ಸಂಖ್ಯೆಯನ್ನು ತಪ್ಪಾದ ಸಂಪರ್ಕ ಎಂದು ಗುರುತಿಸಿ ತೆಗೆದುಹಾಕಲಾಗಿದೆ.",
                "tamil": "மன்னிக்கவும், இந்த எண் தவறான தொடர்பு என குறிக்கப்பட்டு நீக்கப்பட்டது.",
                "telugu": "క్షమించండి, ఈ నంబర్‌ను తొలగించడం జరిగింది.",
                "marathi": "क्षमस्व, हा नंबर चुकीचा संपर्क म्हणून काढून टाकला आहे.",
                "bengali": "দুঃখিত, এই নম্বরটি ভুল যোগাযোগ হিসেবে মুছে ফেলা হয়েছে।",
            }

        if intent == VoiceIntent.SEND_PAYMENT_LINK:
            return {
                "english": f"Certainly! I am preparing a secure Razorpay payment link for {amt_str} to your WhatsApp and SMS. Shall I send it now?",
                "hinglish": f"Ji zaroor! Main {amt_str} ka secure Razorpay payment link aapke WhatsApp aur SMS pe bhej raha hoon. Kya main link dispatch kar doon?",
                "hindi": f"जी बिल्कुल! मैं {amt_str} का सुरक्षित रेज़रपे लिंक व्हाट्सएप और एसएमएस पर भेज रहा हूँ। क्या मैं भेज दूँ?",
                "kannada": f"ಖಂಡಿತ! ನಾನು {amt_str} ಮೊತ್ತದ ರೇಜರ್‌ಪೇ ಲಿಂಕ್ ಅನ್ನು ವಾಟ್ಸಾಪ್‌ಗೆ ಕಳುಹಿಸುತ್ತಿದ್ದೇನೆ. ಕಳುಹಿಸಲೇ?",
                "tamil": f"நிச்சயமாக! {amt_str} தொகைக்கான ரேசர் பே லிங்க் வாட்ஸ்அப் மூலம் அனுப்புகிறேன். அனுப்பவா?",
                "telugu": f"తప్పకుండా! {amt_str} మొత్తానికి రేజర్ పే లింక్ వాట్సాప్‌కు పంపుతున్నాను. పంపమంటారా?",
                "marathi": f"हो नक्कीच! मी {amt_str} चा रेझरपे लिंक व्हॉट्सॲपवर पाठवत आहे. पाठवू का?",
                "bengali": f"অবশ্যই! আমি {amt_str} টাকার রেজ়র পে লিংক পাঠাচ্ছি। পাঠাব কি?",
            }

        if intent == VoiceIntent.PROMISE_TO_PAY:
            return {
                "english": f"Understood! I have scheduled your promise to pay for {date_str}. Automatic retries will remain paused. Shall I confirm this?",
                "hinglish": f"Samajh gaya! Maine aapka payment date {date_str} ke liye note kar liya hai. Tab tak retries pause rahenge. Kya confirm kar doon?",
                "hindi": f"समझ गया! मैंने {date_str} के लिए भुगतान तिथि दर्ज कर ली है। क्या मैं इसे सुरक्षित कर दूँ?",
                "kannada": f"ತಿಳಿಯಿತು! {date_str} ದಿನಾಂಕದ ಪಾವತಿ ಭರವಸೆಯನ್ನು ದಾಖಲಿಸಲಾಗಿದೆ. ಇದನ್ನು ಖಚಿತಪಡಿಸಲೇ?",
                "tamil": f"புரிந்தது! {date_str} அன்று செலுத்த ஒப்புக்கொண்டதை பதிவு செய்துள்ளேன். உறுதி செய்யவா?",
                "telugu": f"అర్థమైంది! {date_str} చెల్లింపు వాగ్దానాన్ని నమోదు చేశాను. నిర్ధారించమంటారా?",
                "marathi": f"समजले! मी {date_str} साठी वचनबद्ध तारीख नोंदवली आहे. पुष्टी करू का?",
                "bengali": f"বুঝেছি! আমি {date_str} তারিখের পেমেন্ট প্রতিশ্রুতি নথিভুক্ত করেছি। নিশ্চিত করব কি?",
            }

        if intent == VoiceIntent.REQUEST_HUMAN:
            return {
                "english": "Certainly, I am connecting you to one of our customer support representatives right away.",
                "hinglish": "Ji bilkul, main aapki call hamare customer care specialist ko transfer kar raha hoon.",
                "hindi": "जी बिल्कुल, मैं आपकी कॉल हमारे ग्राहक सेवा अधिकारी को स्थानांतरित कर रहा हूँ।",
                "kannada": "ಖಂಡಿತ, ನಾನು ನಿಮ್ಮ ಕರೆಯನ್ನು ನಮ್ಮ ಗ್ರಾಹಕ ಸೇವಾ ಪ್ರತಿನಿಧಿಗೆ ವರ್ಗಾಯಿಸುತ್ತಿದ್ದೇನೆ.",
                "tamil": "நிச்சயமாக, உங்கள் அழைப்பை எங்கள் வாடிக்கையாளர் சேவை அதிகாரிக்கு மாற்றுகிறேன்.",
                "telugu": "తప్పకుండా, మీ కాల్‌ను మా కస్టమర్ కేర్ ప్రతినిధికి బదిలీ చేస్తున్నాను.",
                "marathi": "होय, मी आपला कॉल आमच्या प्रतिनिधीकडे हस्तांतरित करत आहे.",
                "bengali": "অবশ্যই, আমি আপনার কলটি আমাদের প্রতিনিধির কাছে স্থানান্তর করছি।",
            }

        if intent == VoiceIntent.REPEAT_REQUEST:
            return {
                "english": f"I was explaining that your subscription renewal of {amt_str} failed. Would you like me to send a payment link or retry later?",
                "hinglish": f"Main bata raha tha ki aapka {amt_str} ka subscription renewal fail hua tha. Kya aap payment link chahte hain?",
                "hindi": f"मैं बता रहा था कि {amt_str} का नवीनीकरण असफल हुआ। क्या आप लिंक चाहते हैं?",
                "kannada": f"ನಿಮ್ಮ {amt_str} ಚಂದಾದಾರಿಕೆ ನವೀಕರಣ ವಿಫಲವಾಗಿದೆ ಎಂದು ತಿಳಿಸುತ್ತಿದ್ದೆ. ಲಿಂಕ್ ಕಳುಹಿಸಲೇ?",
                "tamil": f"உங்கள் {amt_str} சந்தா புதுப்பித்தல் தோல்வியடைந்தது. லிங்க் அனுப்பவா?",
                "telugu": f"మీ {amt_str} సబ్‌స్క్రిప్షన్ ఫెయిల్ అయిందని చెప్పాను. లింక్ పంపమంటారా?",
                "marathi": f"मी सांगत होतो की आपले {amt_str} चे नूतनीकरण अयशस्वी झाले. लिंक पाठवू का?",
                "bengali": f"আমি জানাচ্ছিলাম যে আপনার {amt_str} টাকার সাবস্ক্রিপশন ব্যর্থ হয়েছে। লিংক পাঠাব?",
            }

        if intent == VoiceIntent.CONFIRM_YES:
            return {
                "english": "Thank you! I have confirmed and executed your request successfully.",
                "hinglish": "Dhanyawaad! Maine action successfully confirm kar diya hai.",
                "hindi": "धन्यवाद! मैंने आपकी कार्रवाई सफलतापूर्वक निष्पादित कर दी है।",
                "kannada": "ಧನ್ಯವಾದಗಳು! ವಿನಂತಿಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಪೂರ್ಣಗೊಳಿಸಲಾಗಿದೆ.",
                "tamil": "நன்றி! உங்கள் கோரிக்கை வெற்றிகரமாக நிறைவேற்றப்பட்டது.",
                "telugu": "ధన్యవాదాలు! మీ అభ్యర్థన విజయవంతంగా పూర్తయింది.",
                "marathi": "धन्यवाद! आपली विनंती यशस्वीरित्या पूर्ण झाली आहे.",
                "bengali": "ধন্যবাদ! আপনার অনুরোধ সফলভাবে সম্পন্ন হয়েছে।",
            }

        if intent == VoiceIntent.CONFIRM_NO:
            return {
                "english": "No problem at all, the action has been cancelled. Is there anything else I can help you with?",
                "hinglish": "Koi baat nahi, action cancel kar diya gaya hai. Kya aapko kisi aur cheez me help chahiye?",
                "hindi": "कोई बात नहीं, कार्रवाई रद्द कर दी गई है। क्या मैं अन्य किसी सहायता कर सकता हूँ?",
                "kannada": "ಯಾವುದೇ ತೊಂದರೆಯಿಲ್ಲ, ಕ್ರಿಯೆಯನ್ನು ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ. ಬೇರೆ ಯಾವುದೇ ಸಹಾಯ ಬೇಕೇ?",
                "tamil": "பரவாயில்லை, செயல்முறை ரத்து செய்யப்பட்டது. வேறு ஏதேனும் உதவி தேவையா?",
                "telugu": "ఏం పర్వాలేదు, చర్య రద్దు చేయబడింది. మరేదైనా సహాయం కావాలా?",
                "marathi": "काही हरकत नाही, कारवाई रद्द केली आहे. इतर काही मदत हवी आहे का?",
                "bengali": "কোনো समस्या নেই, বাতিল করা হয়েছে। অন্য কোনো সাহায্য লাগবে?",
            }

        return {
            "english": f"Your current subscription balance is {amt_str}. Would you prefer a payment link or a scheduled retry?",
            "hinglish": f"Aapka subscription balance {amt_str} hai. Kya aap WhatsApp link chahte hain ya kal pay karna prefer karenge?",
            "hindi": f"आपका बकाया {amt_str} है। क्या आप लिंक चाहते हैं या कल भुगतान करेंगे?",
            "kannada": f"ನಿಮ್ಮ ಬಾಕಿ ಮೊತ್ತ {amt_str}. ನೀವು ಲಿಂಕ್ ಬಯಸುತ್ತೀರಾ ಅಥವಾ ನಾಳೆ ಪಾವತಿಸುತ್ತೀರಾ?",
            "tamil": f"உங்கள் நிலுவைத் தொகை {amt_str}. லிங்க் அனுப்பவா அல்லது பின்னர் செலுத்தவா?",
            "telugu": f"మీ బకాయి {amt_str}. పేమెంట్ లింక్ పంపమంటారా లేదా రేపు చెల్లిస్తారా?",
            "marathi": f"आपली थकबाकी {amt_str} आहे. लिंक हवी आहे की नंतर भरणार?",
            "bengali": f"আপনার বকেয়া {amt_str} টাকা। লিংক চান নাকি পরে দেবেন?",
        }

    async def analyze_utterance(
        self,
        utterance: str,
        conversation_history: Optional[List[Any]] = None,
        case_or_amount: Any = 2999.0,
        amount: Optional[float] = None,
        case_id: str = "",
        language_hint: Optional[LanguageDetected] = None,
        transcription_confidence: Optional[float] = 1.0,
        **kwargs: Any,
    ) -> VoiceAgentAnalysis:
        """
        Comprehensive Multilingual Intent Classification, Entity Extraction,
        Safety Guardrails, and Structured Output Generation.
        """
        history = conversation_history or []
        effective_amount = 2999.0
        if amount is not None:
            effective_amount = float(amount)
        elif hasattr(case_or_amount, "context") and hasattr(case_or_amount.context, "amount_inr"):
            effective_amount = float(case_or_amount.context.amount_inr)
        elif isinstance(case_or_amount, (int, float)):
            effective_amount = float(case_or_amount)

        sanitized_text, safety_flags = VoiceGuardrails.inspect_and_sanitize_input(utterance)
        effective_transcription_confidence = (
            1.0 if transcription_confidence is None else float(transcription_confidence)
        )
        transcript_meta = MultilingualNormalizer.build_transcript_metadata(
            sanitized_text,
            previous_language_hint=language_hint.value if language_hint else None,
            transcription_confidence=effective_transcription_confidence,
        )
        detected_lang = LanguageDetected(transcript_meta.detected_language)
        lower = transcript_meta.normalized_transcript.lower()

        extracted_entities = MultilingualNormalizer.extract_entities(transcript_meta.normalized_transcript)
        if "promised_date" in extracted_entities and "promise_date" not in extracted_entities:
            extracted_entities["promise_date"] = extracted_entities.pop("promised_date")
        is_safe = "SENSITIVE_CREDENTIAL_DETECTED" not in safety_flags
        safety_reason = None
        if not is_safe:
            safety_reason = "Sensitive financial credentials (OTP / PIN / CVV) detected and scrubbed."

        recommended_action: Optional[str] = None
        requires_confirmation = False
        requires_human_escalation = False
        sentiment = "neutral"
        clarification_q: Optional[str] = None
        confidence = 0.95

        # -------------------------------------------------------------
        # QUALITY & LOW-CONFIDENCE GATING
        # -------------------------------------------------------------
        if effective_transcription_confidence < 0.60:
            intent = VoiceIntent.UNCLEAR
            confidence = effective_transcription_confidence
            recommended_action = "clarify"
            requires_confirmation = False
            transcript_meta.needs_clarification = True
            clarification_q = "Could you please repeat? I did not hear clearly."
            reasoning = "Low transcription confidence. Initiating clarification turn."

        # -------------------------------------------------------------
        # PROMPT INJECTION & ATTACK GATING
        # -------------------------------------------------------------
        elif any(w in lower for w in [
            "ignore all previous", "system prompt override", "delete database", "waive off my entire",
            "open assistant", "zero dollars"
        ]):
            intent = VoiceIntent.UNCLEAR
            confidence = 0.30
            recommended_action = "clarify"
            requires_confirmation = False
            reasoning = "Prompt injection attempt detected and suppressed."

        elif not is_safe:
            intent = VoiceIntent.UNCLEAR
            confidence = 0.20
            recommended_action = "clarify"
            requires_confirmation = False
            reasoning = "Sensitive financial credential detected and blocked by anti-OTP guardrail."

        # -------------------------------------------------------------
        # HYBRID INTENT ENGINE: High-Recall Multi-Language Classifiers
        # -------------------------------------------------------------

        # 1. STOP CONTACT / DND (Critical Intent - High Recall)
        elif any(w in lower for w in [
            "dnd", "stop calling", "remove my number", "call mat karo", "don't call", "block",
            "phone madbedi", "call madbedi", "phone mad bedi", "ಮಾಡಬೇಡಿ", "ತೆಗೆದುಹಾಕಿ",
            "call pannathinga", "phone pannathenga", "call pannadeenga", "பண்ணாதீங்க", "போடுங்க",
            "call cheyyavaddhu", "phone cheyyodhu", "call cheyodu", "చేయవద్దు", "పెట్టండి",
            "call karu naka", "phone karu naka", "punha phone karu naka", "करू नका", "टाका",
            "phone korben na", "call korben na", "ar phone korben na", "করবেন না",
            "baar baar phone mat karo", "harass"
        ]):
            intent = VoiceIntent.STOP_CONTACT
            sentiment = "frustrated"
            recommended_action = "dnd_opt_out"
            reasoning = f"Customer explicitly requested DND in {detected_lang.value}. Immediate contact suppression applied."

        # 2. ALREADY PAID (Critical Intent - High Recall)
        elif any(w in lower for w in [
            "already paid", "paise kat gaye", "debit ho chuka", "debit ho gaya", "paid already", "kat gaya",
            "kat aagide", "kat aayithu", "debit aayithu", "duddu kat", "ಕಡಿತಗೊಂಡಿದೆ", "ಕಟ್ ಆಗಿದೆ",
            "cut aachu", "debit aachu", "panam cut", "பிடித்தம் செய்யப்பட்டது", "கட் ஆயிடுச்சு",
            "cut aindi", "debit aindi", "dabbu cut", "కట్ అయ్యాయి",
            "cut jhale", "debit jhale", "वजा झाले",
            "kete geche", "debit hoyeche", "কেটে নেওয়া হয়েছে",
            "account se deduct", "receipt", "already deducted"
        ]):
            intent = VoiceIntent.ALREADY_PAID
            sentiment = "frustrated"
            requires_human_escalation = True
            recommended_action = "escalate_to_human"
            reasoning = "Customer asserts payment was already debited. Escalating to finance queue for reconciliation."

        # 3. PAYMENT DISPUTE / FRAUD (Critical Intent)
        elif any(w in lower for w in [
            "dispute", "fraud", "scam", "unauthorized", "cancel subscription", "band karo", "refund",
            "galat charge", "cheating", "thappu charge", "tappu charge", "churi",
            "ಅಕ್ರಮ ಶುಲ್ಕ", "தவறான கட்டணம்", "మోసం", "चुकीचे शुल्क", "জালিয়াতি"
        ]):
            intent = VoiceIntent.PAYMENT_DISPUTE
            sentiment = "frustrated"
            requires_human_escalation = True
            recommended_action = "dispute_investigation"
            reasoning = "Customer disputes validity of charge or alleges fraud. Pausing recovery."

        # 4. WRONG CUSTOMER / PERSON (Critical Intent)
        elif any(w in lower for w in [
            "wrong number", "wrong customer", "wrong person", "galat number", "not me", "i am not",
            "thappu number", "tappu number", "ತಪ್ಪು ಸಂಖ್ಯೆ", "தவறான எண்", "తప్పు నంబర్", "चुकीचा नंबर", "ভুল নম্বর",
            "naan illa", "nenu kaadu", "ami noi", "mi nahi"
        ]):
            intent = VoiceIntent.WRONG_CUSTOMER
            sentiment = "neutral"
            recommended_action = "mark_wrong_contact"
            reasoning = "Caller states they are not the intended account holder."

        # 5. REQUEST HUMAN SUPERVISOR (Critical Intent)
        elif any(w in lower for w in [
            "human", "agent se baat", "manager", "support person", "representative", "real person",
            "executive", "adhikari", "officer", "supervisor", "insaan se baat", "live person",
            "ಅಧಿಕಾರಿ", "மேலாளர்", "కస్టమర్ కేర్", "अधिकाऱ्याशी", "ম্যানেজার"
        ]):
            intent = VoiceIntent.REQUEST_HUMAN
            requires_human_escalation = True
            recommended_action = "escalate_to_human"
            reasoning = "Customer requested human representative."

        # 6. SEND PAYMENT LINK
        elif any(w in lower for w in [
            "whatsapp", "bhej do link", "send link", "link bhejo", "payment link", "upi se pay",
            "link bhej do", "link kalsi", "link anupunga", "link anuppunga", "link pampandi",
            "link pampinchandi", "link pathva", "link pathan", "qr code", "email pe link",
            "ಲಿಂಕ್ ಕಳುಹಿಸಿ", "ಲಿಂಕ್", "ಕಳುಹಿಸಿ", "லிங்க் அனுப்புங்கள்", "லிங்க்", "அனுப்புங்க", "அனுப்புங்கள்",
            "లింక్ పంపండి", "లింక్", "పంపండి", "लिंक पाठवा", "पाठवा", "লিংক পাঠান", "লিংক", "পাঠান", "भेजें", "भेजिए"
        ]):
            intent = VoiceIntent.SEND_PAYMENT_LINK
            sentiment = "cooperative"
            requires_confirmation = True
            recommended_action = "send_payment_link"
            reasoning = "Customer requested instant Razorpay payment link."

        # 7. PROMISE TO PAY
        elif any(w in lower for w in [
            "kal", "tomorrow", "salary", "shaam", "parso", "pay later", "baad me",
            "naale", "naadiddu", "ನಾಳೆ", "ಪಾವತಿಸುತ್ತೇನೆ", "ಮಾಡುತ್ತೇನೆ",
            "naalaiki", "naalaikku", "நாளைக்கு", "கட்டுகிறேன்", "செலுத்துகிறேன்",
            "repu", "ellundi", "రేపు", "చెల్లిస్తాను",
            "udya", "parva", "उद्या", "भरतो",
            "aagami kaal", "kaal", "আগামীকাল", "করব",
            "somvaar", "next week", "next monday"
        ]) and not any(w in lower for w in ["retry", "dubara try"]):
            intent = VoiceIntent.PROMISE_TO_PAY
            sentiment = "cooperative"
            requires_confirmation = True
            recommended_action = "record_promise_to_pay"
            if "promised_date" not in extracted_entities:
                extracted_entities["promised_date"] = "tomorrow"
            extracted_entities["promised_amount"] = effective_amount
            reasoning = f"Customer committed to pay ({extracted_entities['promised_date']}). 24h pause scheduled."

        # 8. RETRY LATER
        elif any(w in lower for w in ["retry later", "baad me retry", "retry karna", "try later", "phir se try karo", "munde try madi"]):
            intent = VoiceIntent.RETRY_LATER
            sentiment = "cooperative"
            recommended_action = "schedule_retry"
            reasoning = "Customer requested an automated retry after a delay."

        # 9. PAY NOW
        elif any(w in lower for w in ["pay now", "abhi pay", "proceed now", "turant pay", "aata pay karto", "ebhoni pay korbo"]):
            intent = VoiceIntent.PAY_NOW
            sentiment = "cooperative"
            requires_confirmation = True
            recommended_action = "execute_pay_now"
            reasoning = "Customer wants to immediately authorize payment capture."

        # 10. REPEAT REQUEST
        elif any(w in lower for w in [
            "repeat", "dubara bolo", "phir se bolo", "munde heli", "marupadi sollunga",
            "malli cheppandi", "puna sanga", "aarekbar bolun", "pardon", "what did you say", "samajh nahi aaya"
        ]):
            intent = VoiceIntent.REPEAT_REQUEST
            reasoning = "Customer asked to repeat the context."

        # 11. LANGUAGE CHANGE REQUEST
        elif "requested_language" in extracted_entities:
            intent = VoiceIntent.LANGUAGE_CHANGE
            reasoning = f"Customer requested language switch to {extracted_entities['requested_language']}."

        # 12. CONFIRM YES
        elif any(w in lower for w in ["haan", "yes", "theek hai", "kardo", "confirm", "bhejo", "sari", "aam", "hou", "thik achhe", "proceed"]):
            intent = VoiceIntent.CONFIRM_YES
            sentiment = "cooperative"
            recommended_action = "confirm_action"
            reasoning = "Customer provided explicit verbal consent/confirmation."

        # 13. CONFIRM NO
        elif any(w in lower for w in ["nahi", "no", "cancel", "mat karo", "beda", "vendam", "vaddu", "nako", "na"]):
            intent = VoiceIntent.CONFIRM_NO
            recommended_action = "cancel_action"
            reasoning = "Customer explicitly declined pending action."

        # 14. UNCLEAR / UNKNOWN (Low confidence -> conversation repair)
        else:
            intent = VoiceIntent.UNCLEAR
            confidence = 0.45
            recommended_action = "clarify"
            transcript_meta.needs_clarification = True
            clarification_q = "Could you please repeat? Would you prefer a payment link or a scheduled retry for tomorrow?"
            reasoning = "Utterance did not match deterministic intent grammar. Initiating clarification turn."

        # Structured Intent Result Contract
        structured_entities = IntentEntities(
            promised_date=extracted_entities.get("promise_date"),
            promised_time=extracted_entities.get("promised_time"),
            amount=extracted_entities.get("amount", effective_amount),
            requested_language=extracted_entities.get("requested_language"),
        )
        structured_res = StructuredIntentResult(
            intent=intent.value,
            confidence=confidence,
            entities=structured_entities,
            requires_confirmation=requires_confirmation,
            requires_human=requires_human_escalation,
            clarification_question=clarification_q,
            safety_reason=safety_reason,
        )

        # Generate localized multi-language speech copies
        localized_copies = self._generate_localized_responses(
            intent=intent,
            amount=effective_amount,
            entities=extracted_entities,
            clarification_q=clarification_q,
        )

        effective_response_lang = language_hint or detected_lang
        if detected_lang in [LanguageDetected.HINDI, LanguageDetected.MARATHI]:
            if language_hint == LanguageDetected.MARATHI or any(w in lower for w in ["मला", "पाठवा", "उद्या", "करतो", "आहे"]):
                effective_response_lang = LanguageDetected.MARATHI

        resp_english = localized_copies["english"]
        resp_hinglish = localized_copies["hinglish"]
        active_resp = localized_copies.get(effective_response_lang.value, resp_english)

        return VoiceAgentAnalysis(
            detected_intent=intent,
            confidence=confidence,
            detected_language=detected_lang,
            customer_sentiment=sentiment,
            extracted_entities=extracted_entities,
            reasoning=reasoning,
            is_safe=is_safe,
            safety_flags=safety_flags,
            recommended_action=recommended_action,
            response_language=effective_response_lang,
            agent_response=active_resp,
            agent_response_hinglish=resp_hinglish,
            agent_response_english=resp_english,
            localized_responses=localized_copies,
            requires_confirmation=requires_confirmation,
            requires_human_escalation=requires_human_escalation,
            structured_intent=structured_res,
            transcript_meta=transcript_meta,
        )
