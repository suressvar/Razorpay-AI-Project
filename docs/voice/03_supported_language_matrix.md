# Supported Language & Dialect Matrix

## 1. Primary Supported Indian Languages

| Language | Native Script Name | Locale Code | Voice Profile | Pronunciation Lexicon | Lakh/Crore Currency Conversion |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Indian English** | English | `en-IN` | `en-IN-priya` (Female), `en-IN-aarav` (Male) | Full | Yes ("one lakh twenty-five thousand rupees") |
| **Hindi** | हिन्दी | `hi-IN` | `hi-IN-swara` (Female), `hi-IN-madhav` (Male) | Full | Yes ("एक लाख पच्चीस हज़ार रुपये") |
| **Kannada** | ಕನ್ನಡ | `kn-IN` | `kn-IN-sapna` (Female) | Full | Yes ("ಒಂದು ಲಕ್ಷದ ಇಪ್ಪತ್ತೈದು ಸಾವಿರ ರೂಪಾಯಿಗಳು") |
| **Tamil** | தமிழ் | `ta-IN` | `ta-IN-ananya` (Female) | Full | Yes ("ஒரு லட்சத்து இருபத்தைந்தாயிரம் ரூபாய்") |
| **Telugu** | తెలుగు | `te-IN` | `te-IN-kavita` (Female) | Full | Yes ("ఒక లక్ష ఇరవై ఐదు వేల రూపాయలు") |
| **Marathi** | मराठी | `mr-IN` | `mr-IN-radhika` (Female) | Full | Yes ("एक लाख पंचवीस हजार रुपये") |
| **Bengali** | বাংলা | `bn-IN` | `bn-IN-shreya` (Female) | Full | Yes ("এক লক্ষ পঁচিশ হাজার টাকা") |

---

## 2. Code-Switched Dialects & Script Fallbacks

| Dialect | Description | Sample Utterance | Recognized Intent |
| :--- | :--- | :--- | :--- |
| **Hinglish** | Hindi mixed with English | *"Mera salary kal aayega, main kal shaam ko pakka pay kar dunga"* | `promise_to_pay` |
| **Kanglish** | Kannada mixed with English | *"Enaku WhatsApp-nalli payment link kalsi, immediate-agi pay madtini"* | `send_payment_link` |
| **Tanglish** | Tamil mixed with English | *"Enaku WhatsApp-la payment link anupunga, immediate-ah pay panren"* | `send_payment_link` |
| **Tenglish** | Telugu mixed with English | *"Naaku WhatsApp-lo payment link pampandi, UPI tho pay chesthanu"* | `send_payment_link` |
| **Marathi-English** | Marathi mixed with English | *"Mala WhatsApp var payment link pathva, pay karto"* | `send_payment_link` |
| **Bengali-English** | Bengali mixed with English | *"Amake WhatsApp-e payment link pathan, pay korchi"* | `send_payment_link` |

---

## 3. Strict Locale Protection Gating

To prevent the common defect where missing regional voices silently degrade into reading Kannada or Tamil text using an English synth voice, the engine enforces:
1. Native acoustic synthesis via local backend provider (`LocalMultilingualTTSProvider`).
2. Strict browser locale match: If the client OS lacks native regional Indic voice packages, browser synthesis falls back cleanly with user notification rather than executing cross-language voice distortion.
