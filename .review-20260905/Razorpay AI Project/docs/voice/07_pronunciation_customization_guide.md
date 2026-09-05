# Pronunciation Customization & Lexicon Guide

## 1. Customizing Pronunciation Lexicon (`lexicon.py`)

All fintech terminology, bank names, customer names, and embedded English terms are managed in `backend/src/recovery_autopilot/voice/tts/lexicon.py`.

### Adding a New Term
To add custom pronunciation for a merchant or specific product:

```python
FINTECH_TERMINOLOGY["MagicCheckout"] = {
    "en-IN": "Magic Check-out",
    "hi-IN": "मैजिक चेकआउट",
    "kn-IN": "ಮ್ಯಾಜಿಕ್ ಚೆಕೌಟ್",
    "ta-IN": "மேஜிக் செக்அவுட்",
    "te-IN": "మ్యాజిక్ చెక్‌అవుట్",
    "mr-IN": "मॅजिक चेकआऊट",
    "bn-IN": "ম্যাজিক চেকআউট",
}
```

### Adding a New Bank Name
```python
INDIAN_BANKS["Federal Bank"] = {
    "en-IN": "Federal Bank",
    "hi-IN": "फ़ेडरल बैंक",
    "ta-IN": "ஃபெடரல் வங்கி",
    "kn-IN": "ಫೆಡರಲ್ ಬ್ಯಾಂಕ್",
}
```

---

## 2. SSML Prosody & Break Modulation

The system supports SSML tags for prosody rate and conversational pauses:

```xml
<speak>
  <p>
    <prosody rate="95%">
      <voice xml:lang="hi-IN">
        नमस्ते आरव, मैं रेज़र-पे से आपका एआई रिकवरी असिस्टेंट हूँ। <break time="300ms"/>
        क्या मैं आपके सदस्यता भुगतान के बारे में बात कर सकता हूँ?
      </voice>
    </prosody>
  </p>
</speak>
```

---

## 3. Currency Normalization Rules (`tts_normalization.py`)

The LocaleSpeechRenderer automatically converts Indian numbers into localized words:
- `₹750` $\rightarrow$ "seven hundred fifty rupees" / "सात सौ पचास रुपये" / "ஏழுநூற்று ஐம்பது ரூபாய்"
- `₹1,25,000` $\rightarrow$ "one lakh twenty-five thousand rupees" / "एक लाख पच्चीस हज़ार रुपये"
- `₹10,00,000` $\rightarrow$ "ten lakh rupees" / "दस लाख रुपये"
- `₹2,50,00,000` $\rightarrow$ "two crore fifty lakh rupees" / "दो करोड़ पचास लाख रुपये"
