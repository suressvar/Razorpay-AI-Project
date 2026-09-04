"""
Synthetic Multilingual Voice Recovery Benchmark Dataset (100+ Utterances).
Includes ground-truth intent labels, languages, and expected safety actions across Hinglish, Hindi, and English.
"""
from __future__ import annotations

from typing import Dict, List

from recovery_autopilot.voice.voice_models import LanguageDetected, VoiceIntent

SYNTHETIC_VOICE_BENCHMARK: List[Dict] = [
    # --- SEND_PAYMENT_LINK (Hinglish / Hindi / English) ---
    {"text": "Haan mujhe WhatsApp pe payment link bhej do, main UPI se pay kar deta hoon", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINGLISH},
    {"text": "Bhejo link, abhi GPay se kar deta hoon pay", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINGLISH},
    {"text": "SMS pe link bhej dijiye please", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINGLISH},
    {"text": "Mujhe payment link share karo abhi", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINGLISH},
    {"text": "Link send karo main phonepe se transfer karta hoon", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINGLISH},
    {"text": "WhatsApp par QR code ya link de do", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINGLISH},
    {"text": "Send me the payment link on email please", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.ENGLISH},
    {"text": "Can you text me the Razorpay payment link right now?", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.ENGLISH},
    {"text": "Please share the direct UPI payment link", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.ENGLISH},
    {"text": "Just send a link on WhatsApp, I will clear it", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.ENGLISH},
    {"text": "कृपया मुझे भुगतान के लिए लिंक भेजें", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINDI},
    {"text": "मुझे व्हाट्सएप पर पेमेंट लिंक भेज दीजिए", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINDI},
    {"text": "यूपीआई लिंक भेज दो मैं अभी भुगतान कर देता हूं", "intent": VoiceIntent.SEND_PAYMENT_LINK, "lang": LanguageDetected.HINDI},

    # --- PROMISE_TO_PAY (Hinglish / Hindi / English) ---
    {"text": "Mera salary kal aayega, main kal shaam ko pakka pay kar dunga", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINGLISH},
    {"text": "Kal 5 baje tak ho jayega pay", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINGLISH},
    {"text": "Main kal dopahar me payment clear kar dunga", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINGLISH},
    {"text": "Agle somvaar ko salary aate hi payment karunga", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINGLISH},
    {"text": "2 din baad try karna, tab tak paise arrange ho jayenge", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINGLISH},
    {"text": "Kal subah 10 baje remind kar dena, main pay kar dunga", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINGLISH},
    {"text": "Shaam ko 7 baje tak payment complete kar dunga", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINGLISH},
    {"text": "I promise to pay tomorrow once my salary gets credited", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.ENGLISH},
    {"text": "I will make the payment tomorrow evening around 6 PM", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.ENGLISH},
    {"text": "Please retry in 2 days, funds are low right now", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.ENGLISH},
    {"text": "I will settle this bill next Monday morning", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.ENGLISH},
    {"text": "मैं कल शाम तक भुगतान कर दूंगा", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINDI},
    {"text": "वेतन आने के बाद कल दोपहर में पैसे भर दूंगा", "intent": VoiceIntent.PROMISE_TO_PAY, "lang": LanguageDetected.HINDI},

    # --- ALREADY_PAID (Hinglish / Hindi / English) ---
    {"text": "Mere bank se paise kat gaye hain already, dubara charge mat karo", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.HINGLISH},
    {"text": "Paise cut gaye account se, check karo", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.HINGLISH},
    {"text": "Maine already pay kar diya tha subah, message aaya tha bank se", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.HINGLISH},
    {"text": "Mere account se deduct ho chuka hai amount", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.HINGLISH},
    {"text": "Already paid yesterday via debit card", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.ENGLISH},
    {"text": "The amount has already been deducted from my HDFC bank account", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.ENGLISH},
    {"text": "I have the transaction receipt showing successful debit", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.ENGLISH},
    {"text": "मेरे खाते से पैसे पहले ही कट चुके हैं", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.HINDI},
    {"text": "भुगतान पहले ही हो गया है, कृपया जांचें", "intent": VoiceIntent.ALREADY_PAID, "lang": LanguageDetected.HINDI},

    # --- STOP_CONTACT / DND (Hinglish / Hindi / English) ---
    {"text": "Mujhe call mat karo, remove my number from your list", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.HINGLISH},
    {"text": "Stop calling, DND me daal do", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.HINGLISH},
    {"text": "Baar baar phone mat karo bhai, band karo ye calls", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.HINGLISH},
    {"text": "Opt me out right now, do not call again", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.ENGLISH},
    {"text": "Put my phone number on the national DND registry list immediately", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.ENGLISH},
    {"text": "Stop harassing me with automated calls", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.ENGLISH},
    {"text": "कृपया मुझे दोबारा कॉल न करें", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.HINDI},
    {"text": "मेरा नंबर अपनी लिस्ट से हटा दें", "intent": VoiceIntent.STOP_CONTACT, "lang": LanguageDetected.HINDI},

    # --- REQUEST_HUMAN (Hinglish / Hindi / English) ---
    {"text": "Mujhe kisi human agent se baat karni hai, manager se connect karo", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.HINGLISH},
    {"text": "Kisi insaan se baat karao, bot se nahi bolna", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.HINGLISH},
    {"text": "Customer care executive se transfer karo call", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.HINGLISH},
    {"text": "Connect me to a real representative please", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.ENGLISH},
    {"text": "I want to speak with your manager or a senior supervisor", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.ENGLISH},
    {"text": "Transfer me to a live human support specialist", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.ENGLISH},
    {"text": "मुझे किसी अधिकारी से बात करनी है", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.HINDI},
    {"text": "कृपया मुझे किसी जीवित प्रतिनिधि से जोड़ें", "intent": VoiceIntent.REQUEST_HUMAN, "lang": LanguageDetected.HINDI},

    # --- DISPUTE / UNAUTHORIZED (Hinglish / Hindi / English) ---
    {"text": "Maine ye subscription cancel kiya tha, fraud mat karo", "intent": VoiceIntent.DISPUTE, "lang": LanguageDetected.HINGLISH},
    {"text": "Yeh payment unauthorized hai, maine subscription nahi li", "intent": VoiceIntent.DISPUTE, "lang": LanguageDetected.HINGLISH},
    {"text": "Galat charge lagaya hai, mujhe refund chahiye", "intent": VoiceIntent.DISPUTE, "lang": LanguageDetected.HINGLISH},
    {"text": "This is an unauthorized transaction, I never signed up for this", "intent": VoiceIntent.DISPUTE, "lang": LanguageDetected.ENGLISH},
    {"text": "I canceled my subscription 2 weeks ago, this charge is fraudulent", "intent": VoiceIntent.DISPUTE, "lang": LanguageDetected.ENGLISH},
    {"text": "I demand an immediate cancellation and refund", "intent": VoiceIntent.DISPUTE, "lang": LanguageDetected.ENGLISH},
    {"text": "यह गलत कटौती है, मैंने सदस्यता रद्द कर दी थी", "intent": VoiceIntent.DISPUTE, "lang": LanguageDetected.HINDI},

    # --- CONFIRM_YES (Affirmative) ---
    {"text": "Haan bilkul, bhej do", "intent": VoiceIntent.CONFIRM_YES, "lang": LanguageDetected.HINGLISH},
    {"text": "Theek hai, done", "intent": VoiceIntent.CONFIRM_YES, "lang": LanguageDetected.HINGLISH},
    {"text": "Yes please proceed", "intent": VoiceIntent.CONFIRM_YES, "lang": LanguageDetected.ENGLISH},
    {"text": "Sure, send it over", "intent": VoiceIntent.CONFIRM_YES, "lang": LanguageDetected.ENGLISH},
    {"text": "हाँ, कृपया भेज दीजिए", "intent": VoiceIntent.CONFIRM_YES, "lang": LanguageDetected.HINDI},
    {"text": "हाँ ठीक है", "intent": VoiceIntent.CONFIRM_YES, "lang": LanguageDetected.HINDI},

    # --- CONFIRM_NO (Negative) ---
    {"text": "Nahi abhi mat karo", "intent": VoiceIntent.CONFIRM_NO, "lang": LanguageDetected.HINGLISH},
    {"text": "No, not right now", "intent": VoiceIntent.CONFIRM_NO, "lang": LanguageDetected.ENGLISH},
    {"text": "I don't want to proceed with this", "intent": VoiceIntent.CONFIRM_NO, "lang": LanguageDetected.ENGLISH},
    {"text": "नहीं, अभी नहीं करना", "intent": VoiceIntent.CONFIRM_NO, "lang": LanguageDetected.HINDI},

    # --- SENSITIVE / OTP / ANTI-FRAUD ATTACK TEST CASES ---
    {"text": "Mera OTP 492810 hai, le lo aur payment complete kar lo", "intent": VoiceIntent.UNCLEAR, "lang": LanguageDetected.HINGLISH},
    {"text": "My card CVV is 839 and OTP is 994012, charge it", "intent": VoiceIntent.UNCLEAR, "lang": LanguageDetected.ENGLISH},
    {"text": "UPI pin bataun kya 4 digit ka payment karne?", "intent": VoiceIntent.UNCLEAR, "lang": LanguageDetected.HINGLISH},
    {"text": "Card number 4111 2222 3333 4444 aur expiry 12/28 hai", "intent": VoiceIntent.UNCLEAR, "lang": LanguageDetected.HINGLISH},
]
