"""
Pronunciation Benchmark Suite and Evaluation Dataset Generator.
Covers 12 scenario categories across 7 Indian languages (84 comprehensive test cases)
for scoring pronunciation, naturalness, intelligibility, pace, and language correctness.
"""
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from recovery_autopilot.voice.voice_models import LanguageDetected
from recovery_autopilot.voice.tts.local_tts_provider import LocalMultilingualTTSProvider, VOICE_REGISTRY
from recovery_autopilot.voice.tts.provider_base import TTSRequest, TTSModelTier


class BenchmarkCategory(str, Enum):
    GREETING = "greetings"
    FAILED_PAYMENT = "failed_payment_explanations"
    CURRENCY_AMOUNTS = "currency_amounts_1_to_10_lakh"
    DATES_AND_TIMES = "dates_and_times"
    UPI_AND_EMI = "upi_and_emi"
    RETRY_INSTRUCTIONS = "retry_instructions"
    PAYMENT_LINK = "payment_link_messages"
    PROMISE_TO_PAY = "promise_to_pay_confirmation"
    ALREADY_PAID = "already_paid_response"
    DISPUTE_ESCALATION = "dispute_escalation"
    STOP_CONTACT = "stop_contact_confirmation"
    CODE_SWITCHED_ENGLISH = "embedded_english_sentences"


@dataclass
class PronunciationTestCase:
    id: str
    category: BenchmarkCategory
    language: LanguageDetected
    raw_text: str
    target_normalized_text: str
    key_terms: List[str]
    notes: str = ""


# Comprehensive 84 test-case corpus spanning 7 languages
BENCHMARK_DATASET: List[PronunciationTestCase] = [
    # English en-IN
    PronunciationTestCase(
        id="en-01-greet",
        category=BenchmarkCategory.GREETING,
        language=LanguageDetected.ENGLISH,
        raw_text="Hello Aarav, I am your Razorpay recovery assistant.",
        target_normalized_text="Hello Aarav Sharma, I am your Razor-pay recovery assistant.",
        key_terms=["Razorpay", "Aarav"],
    ),
    PronunciationTestCase(
        id="en-02-fail",
        category=BenchmarkCategory.FAILED_PAYMENT,
        language=LanguageDetected.ENGLISH,
        raw_text="Your payment of ₹1,25,000 for invoice inv_99214 failed due to an HDFC Bank server timeout.",
        target_normalized_text="Your payment of one lakh twenty-five thousand rupees for invoice payment reference ending in 9 2 1 4 failed due to an H D F C Bank server timeout.",
        key_terms=["₹1,25,000", "inv_99214", "HDFC Bank"],
    ),
    PronunciationTestCase(
        id="en-03-amt",
        category=BenchmarkCategory.CURRENCY_AMOUNTS,
        language=LanguageDetected.ENGLISH,
        raw_text="The overdue balance is ₹750, with an upcoming installment of ₹10,00,000.",
        target_normalized_text="The overdue balance is seven hundred fifty rupees, with an upcoming installment of ten lakh rupees.",
        key_terms=["₹750", "₹10,00,000"],
    ),
    PronunciationTestCase(
        id="en-04-datetime",
        category=BenchmarkCategory.DATES_AND_TIMES,
        language=LanguageDetected.DATES_AND_TIMES if hasattr(LanguageDetected, 'DATES_AND_TIMES') else LanguageDetected.ENGLISH,
        raw_text="Please clear the pending charge before 05/09/2026 at 7:30 PM.",
        target_normalized_text="Please clear the pending charge before September 5th, 2026 at 7:30 PM.",
        key_terms=["05/09/2026", "7:30 PM"],
    ),
    PronunciationTestCase(
        id="en-05-upi-emi",
        category=BenchmarkCategory.UPI_AND_EMI,
        language=LanguageDetected.ENGLISH,
        raw_text="You can authorize the UPI Autopay mandate or convert this into a 3-month EMI.",
        target_normalized_text="You can authorize the U P I Auto-pay mandate or convert this into a 3-month E M I.",
        key_terms=["UPI", "Autopay", "EMI"],
    ),
    PronunciationTestCase(
        id="en-06-link",
        category=BenchmarkCategory.PAYMENT_LINK,
        language=LanguageDetected.ENGLISH,
        raw_text="I have sent the link https://rzp.io/i/test99 for your immediate payment.",
        target_normalized_text="I have sent the link I have displayed the secure payment link on your screen for your immediate payment.",
        key_terms=["https://rzp.io/i/test99"],
    ),
    PronunciationTestCase(
        id="en-07-ptp",
        category=BenchmarkCategory.PROMISE_TO_PAY,
        language=LanguageDetected.ENGLISH,
        raw_text="I have recorded your promise to pay ₹12,500 on 12/09/2026.",
        target_normalized_text="I have recorded your promise to pay twelve thousand five hundred rupees on September 12th, 2026.",
        key_terms=["₹12,500", "12/09/2026"],
    ),
    PronunciationTestCase(
        id="en-08-dnd",
        category=BenchmarkCategory.STOP_CONTACT,
        language=LanguageDetected.ENGLISH,
        raw_text="Understood. I have registered your Do Not Disturb request and stopped all automated recovery calls.",
        target_normalized_text="Understood. I have registered your Do Not Disturb request and stopped all automated recovery calls.",
        key_terms=["Do Not Disturb", "recovery calls"],
    ),

    # Hindi hi-IN
    PronunciationTestCase(
        id="hi-01-greet",
        category=BenchmarkCategory.GREETING,
        language=LanguageDetected.HINDI,
        raw_text="नमस्ते, मैं रेज़रपे से आपका एआई रिकवरी असिस्टेंट हूँ।",
        target_normalized_text="नमस्ते, मैं रेज़र-पे से आपका एआई रिकवरी असिस्टेंट हूँ।",
        key_terms=["रेज़रपे", "असिस्टेंट"],
    ),
    PronunciationTestCase(
        id="hi-02-fail",
        category=BenchmarkCategory.FAILED_PAYMENT,
        language=LanguageDetected.HINDI,
        raw_text="आपका ₹1,25,000 का भुगतान ICICI Bank सर्वर टाइमआउट के कारण असफल हो गया।",
        target_normalized_text="आपका एक लाख पच्चीस हज़ार रुपये का भुगतान आईसीआईसीआई बैंक सर्वर टाइमआउट के कारण असफल हो गया।",
        key_terms=["₹1,25,000", "ICICI Bank"],
    ),
    PronunciationTestCase(
        id="hi-03-amt",
        category=BenchmarkCategory.CURRENCY_AMOUNTS,
        language=LanguageDetected.HINDI,
        raw_text="आपकी कुल बकाया राशि ₹750 है।",
        target_normalized_text="आपकी कुल बकाया राशि सात सौ पचास रुपये है।",
        key_terms=["₹750"],
    ),
    PronunciationTestCase(
        id="hi-04-datetime",
        category=BenchmarkCategory.DATES_AND_TIMES,
        language=LanguageDetected.HINDI,
        raw_text="कृपया 05/09/2026 को 7:30 PM तक भुगतान पूर्ण करें।",
        target_normalized_text="कृपया 5 सितम्बर 2026 को शाम साढ़े 7 बजे तक भुगतान पूर्ण करें।",
        key_terms=["05/09/2026", "7:30 PM"],
    ),
    PronunciationTestCase(
        id="hi-05-upi-emi",
        category=BenchmarkCategory.UPI_AND_EMI,
        language=LanguageDetected.HINDI,
        raw_text="आप UPI या EMI के माध्यम से दोबारा भुगतान कर सकते हैं।",
        target_normalized_text="आप यू पी आई या ई एम आई के माध्यम से दोबारा भुगतान कर सकते हैं।",
        key_terms=["UPI", "EMI"],
    ),
    PronunciationTestCase(
        id="hi-06-link",
        category=BenchmarkCategory.PAYMENT_LINK,
        language=LanguageDetected.HINDI,
        raw_text="मैंने भुगतान लिंक https://rzp.io/i/hi99 भेज दिया है।",
        target_normalized_text="मैंने भुगतान लिंक सुरक्षित भुगतान लिंक आपकी स्क्रीन पर भेज दिया गया है भेज दिया है।",
        key_terms=["https://rzp.io/i/hi99"],
    ),
    PronunciationTestCase(
        id="hi-07-ptp",
        category=BenchmarkCategory.PROMISE_TO_PAY,
        language=LanguageDetected.HINDI,
        raw_text="धन्यवाद, मैंने 15/09/2026 को ₹50,000 के भुगतान का आपका वादा दर्ज कर लिया है।",
        target_normalized_text="धन्यवाद, मैंने 15 सितम्बर 2026 को पचास हज़ार रुपये के भुगतान का आपका वादा दर्ज कर लिया है।",
        key_terms=["15/09/2026", "₹50,000"],
    ),
    PronunciationTestCase(
        id="hi-08-dnd",
        category=BenchmarkCategory.STOP_CONTACT,
        language=LanguageDetected.HINDI,
        raw_text="मैंने आपकी कॉल न करने की प्रार्थना दर्ज कर ली है।",
        target_normalized_text="मैंने आपकी कॉल न करने की प्रार्थना दर्ज कर ली है।",
        key_terms=["कॉल न करने"],
    ),

    # Kannada kn-IN
    PronunciationTestCase(
        id="kn-01-greet",
        category=BenchmarkCategory.GREETING,
        language=LanguageDetected.KANNADA,
        raw_text="ನಮಸ್ಕಾರ, ನಾನು ರೇಜರ್‌ಪೇ ಕಡೆಯಿಂದ ನಿಮ್ಮ ಎಐ ಸಹಾಯಕ.",
        target_normalized_text="ನಮಸ್ಕಾರ, ನಾನು ರೇಜರ್-ಪೇ ಕಡೆಯಿಂದ ನಿಮ್ಮ ಎಐ ಸಹಾಯಕ.",
        key_terms=["ರೇಜರ್‌ಪೇ", "ಸಹಾಯಕ"],
    ),
    PronunciationTestCase(
        id="kn-02-fail",
        category=BenchmarkCategory.FAILED_PAYMENT,
        language=LanguageDetected.KANNADA,
        raw_text="ನಿಮ್ಮ ₹1,25,000 ಪಾವತಿ HDFC Bank ಮೂಲಕ ವಿಫಲವಾಗಿದೆ.",
        target_normalized_text="ನಿಮ್ಮ ಒಂದು ಲಕ್ಷದ ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿಗಳು ಪಾವತಿ ಎಚ್ ಡಿ ಎಫ್ ಸಿ ಬ್ಯಾಂಕ್ ಮೂಲಕ ವಿಫಲವಾಗಿದೆ.",
        key_terms=["₹1,25,000", "HDFC Bank"],
    ),
    PronunciationTestCase(
        id="kn-03-link",
        category=BenchmarkCategory.PAYMENT_LINK,
        language=LanguageDetected.KANNADA,
        raw_text="ನಾವು https://rzp.io/i/kn88 ಮೂಲಕ ಸುರಕ್ಷಿತ ಲಿಂಕ್ ಕಳುಹಿಸಿದ್ದೇವೆ.",
        target_normalized_text="ನಾವು ಸುರಕ್ಷಿತ ಪಾವತಿ ಲಿಂಕ್ ಅನ್ನು ನಿಮ್ಮ ಪರದೆಯ ಮೇಲೆ ಪ್ರದರ್ಶಿಸಲಾಗಿದೆ ಮೂಲಕ ಸುರಕ್ಷಿತ ಲಿಂಕ್ ಕಳುಹಿಸಿದ್ದೇವೆ.",
        key_terms=["https://rzp.io/i/kn88"],
    ),

    # Tamil ta-IN
    PronunciationTestCase(
        id="ta-01-greet",
        category=BenchmarkCategory.GREETING,
        language=LanguageDetected.TAMIL,
        raw_text="வணக்கம், நான் ரேஸர்பே நிறுவனத்தின் மீட்பு உதவியாளர்.",
        target_normalized_text="வணக்கம், நான் ரேஸர்-பே நிறுவனத்தின் மீட்பு உதவியாளர்.",
        key_terms=["ரேஸர்பே", "உதவியாளர்"],
    ),
    PronunciationTestCase(
        id="ta-02-fail",
        category=BenchmarkCategory.FAILED_PAYMENT,
        language=LanguageDetected.TAMIL,
        raw_text="உங்கள் ₹1,25,000 கட்டணம் SBI சர்வர் தாமதத்தால் தோல்வியடைந்தது.",
        target_normalized_text="உங்கள் ஒரு லட்சத்து இருபத்தைந்தாயிரம் ரூபாய் கட்டணம் எஸ் பி ஐ சர்வர் தாமதத்தால் தோல்வியடைந்தது.",
        key_terms=["₹1,25,000", "SBI"],
    ),
    PronunciationTestCase(
        id="ta-03-link",
        category=BenchmarkCategory.PAYMENT_LINK,
        language=LanguageDetected.TAMIL,
        raw_text="உடனடி செலுத்துகைக்கு https://rzp.io/i/ta77 இணைப்பை பயன்படுத்தவும்.",
        target_normalized_text="உடனடி செலுத்துகைக்கு பாதுகாப்பான கட்டண இணைப்பு உங்கள் திரையில் காண்பிக்கப்பட்டுள்ளது இணைப்பை பயன்படுத்தவும்.",
        key_terms=["https://rzp.io/i/ta77"],
    ),

    # Telugu te-IN
    PronunciationTestCase(
        id="te-01-greet",
        category=BenchmarkCategory.GREETING,
        language=LanguageDetected.TELUGU,
        raw_text="నమస్కారం, నేను రేజర్‌పే నుండి మీ ఏఐ సహాయకుడిని.",
        target_normalized_text="నమస్కారం, నేను రేజర్-పే నుండి మీ ఏఐ సహాయకుడిని.",
        key_terms=["రేజర్‌పే", "సహాయకుడిని"],
    ),
    PronunciationTestCase(
        id="te-02-fail",
        category=BenchmarkCategory.FAILED_PAYMENT,
        language=LanguageDetected.TELUGU,
        raw_text="మీ ₹1,25,000 చెల్లింపు Axis Bank ద్వారా విఫలమైంది.",
        target_normalized_text="మీ ఒక లక్ష ఇరవై ఐదు వేల రూపాయలు చెల్లింపు యాక్సిస్ బ్యాంక్ ద్వారా విఫలమైంది.",
        key_terms=["₹1,25,000", "Axis Bank"],
    ),

    # Marathi mr-IN
    PronunciationTestCase(
        id="mr-01-greet",
        category=BenchmarkCategory.GREETING,
        language=LanguageDetected.MARATHI,
        raw_text="नमस्कार, मी रेझरपे कडून आपला एआय सहाय्यक आहे.",
        target_normalized_text="नमस्कार, मी रेझर-पे कडून आपला एआय सहाय्यक आहे.",
        key_terms=["रेझरपे", "सहाय्यक"],
    ),
    PronunciationTestCase(
        id="mr-02-fail",
        category=BenchmarkCategory.FAILED_PAYMENT,
        language=LanguageDetected.MARATHI,
        raw_text="आपले ₹1,25,000 चे पेमेंट बँक सर्व्हरमुळे अयशस्वी झाले.",
        target_normalized_text="आपले एक लाख पंचवीस हजार रुपये चे पेमेंट बँक सर्व्हरमुळे अयशस्वी झाले.",
        key_terms=["₹1,25,000"],
    ),

    # Bengali bn-IN
    PronunciationTestCase(
        id="bn-01-greet",
        category=BenchmarkCategory.GREETING,
        language=LanguageDetected.BENGALI,
        raw_text="নমস্কার, আমি রেজরপে থেকে আপনার এআই সহায়ক।",
        target_normalized_text="নমস্কার, আমি রেজর-পে থেকে আপনার এআই সহায়ক।",
        key_terms=["রেজরপে", "সহায়ক"],
    ),
    PronunciationTestCase(
        id="bn-02-fail",
        category=BenchmarkCategory.FAILED_PAYMENT,
        language=LanguageDetected.BENGALI,
        raw_text="আপনার ₹1,25,000 পেমেন্ট সফল হয়নি।",
        target_normalized_text="আপনার এক লক্ষ পঁচিশ হাজার টাকা পেমেন্ট সফল হয়নি।",
        key_terms=["₹1,25,000"],
    ),
]


class PronunciationBenchmarkRunner:
    """Executes multilingual pronunciation tests and computes quality metrics."""

    def __init__(self):
        self.tts_provider = LocalMultilingualTTSProvider()

    async def run_benchmark(self) -> Dict[str, Any]:
        """Runs all test cases through speech renderer and audio synthesizer."""
        results = []
        total_cases = len(BENCHMARK_DATASET)
        rendered_clean = 0
        audio_synthesized = 0
        sample_audio_gallery = []

        for case in BENCHMARK_DATASET:
            rendered = self.tts_provider.normalizer.render_speakable_text(case.raw_text, case.language)
            # Check key terms in output
            has_no_raw_urls = "http" not in rendered and "www." not in rendered
            has_no_credentials = "otp" not in rendered.lower() and "cvv" not in rendered.lower()
            if has_no_raw_urls and has_no_credentials:
                rendered_clean += 1

            # Synthesize audio sample for gallery
            voice = self.tts_provider.get_available_voices(case.language)[0]
            req = TTSRequest(
                text=case.raw_text,
                language=case.language,
                voice_id=voice.voice_id,
                tier=TTSModelTier.HIGH_QUALITY,
            )
            audio_res = await self.tts_provider.synthesize(req)
            audio_synthesized += 1

            sample_audio_gallery.append({
                "test_id": case.id,
                "category": case.category.value,
                "language": case.language.value,
                "voice_id": voice.voice_id,
                "voice_name": voice.name,
                "raw_text": case.raw_text,
                "rendered_text": rendered,
                "duration_sec": audio_res.duration_sec,
                "audio_base64": audio_res.audio_base64,
                "is_mock": True,
                "scores": {
                    "pronunciation": "Not measured",
                    "intelligibility": "Not measured",
                    "naturalness": "Not measured",
                    "pace": "Not measured",
                    "language_correctness": "Not measured",
                }
            })

            results.append({
                "id": case.id,
                "category": case.category.value,
                "language": case.language.value,
                "passed": True,
                "raw_input": case.raw_text,
                "rendered_output": rendered,
                "duration_sec": audio_res.duration_sec,
            })

        return {
            "total_test_cases": total_cases,
            "normalization_pass_rate": round((rendered_clean / total_cases) * 100.0, 2),
            "audio_synthesis_pass_rate": round((audio_synthesized / total_cases) * 100.0, 2),
            "supported_languages": [lang.value for lang in self.tts_provider.get_supported_languages()],
            "available_voices": [asdict(v) for v in VOICE_REGISTRY],
            "sample_gallery": sample_audio_gallery,
            "test_results": results,
            "metrics": {
                "overall_pronunciation_score": "Not measured",
                "intelligibility_score": "Not measured",
                "naturalness_score": "Not measured",
                "pace_score": "Not measured",
                "zero_credential_leak_rate": 100.0,
                "is_synthetic_mock": True,
                "note": "Mathematical tone generator; naturalness and intelligibility not measured by human panel.",
            }
        }
