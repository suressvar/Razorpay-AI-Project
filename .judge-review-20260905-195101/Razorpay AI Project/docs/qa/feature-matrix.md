# Razorpay Recovery Autopilot — Comprehensive QA Feature Matrix

> **Audit Date:** September 5, 2026  
> **Auditor Role:** Application Audit Lead & Reliability Engineer  
> **Repository:** `suressvar/Razorpay-AI-Project`  
> **Baseline Commit / State:** Pre-Prompt 1 Refactoring Baseline  

---

## 1. Architectural Overview & Environment Scope

The application is built with a **FastAPI** backend (Python 3.12/asyncio) and a **React + Vite** frontend (Ant Design + Tailwind CSS). It operates under strict non-production guidelines:
- **No live payment transactions:** Only synthetic simulation or genuine Razorpay Test Mode (`rzp_test_...`).
- **No real phone calls or external SMS/WhatsApp broadcasts:** Voice engine and messaging run in simulated sandbox environments.
- **Truth in Machine Learning & Synthesis:** Mocks and synthetic heuristic tone generators are explicitly demarcated and cannot masquerade as trained neural models or human-evaluated natural speech.

---

## 2. Frontend Page & Interactive Control Matrix

### Page 1: Overview & Metrics (`/`)
- **Route:** `/`
- **Component:** `frontend/src/pages/Overview.tsx`
- **Data Source:** Backend `GET /metrics/summary`, `GET /admin/status`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Data Scope Selector** | Switch active data scope (Live DB, Synthetic Benchmark, Razorpay Test) | `App.tsx` header selector | State `dataMode` | Verified working | Must clarify "Live DB" means local operational database, not live production credit cards. |
| **Recovery Rate KPI Card** | Displays % of failed payments recovered autonomously | `Overview.tsx` KPI block | `GET /metrics/summary` -> `recovery_rate` | Verified working | Real calculation from SQLite `payment_cases` table. |
| **Recovered Revenue KPI** | Displays total INR recovered from successful payments | `Overview.tsx` KPI block | `GET /metrics/summary` -> `total_inr_recovered` | Verified working | Matches settled `status="recovered"` rows in DB. |
| **Active Cases KPI** | Counts pending and investigating recovery cases | `Overview.tsx` KPI block | `GET /metrics/summary` -> `active_cases` | Verified working | Real DB count. |
| **Hours Saved KPI** | Estimates manual ops hours saved (15m per case) | `Overview.tsx` KPI block | Derived from `total_cases * 0.25` | Verified working | Heuristic operational estimate; clearly derived. |
| **Recent Cases Table** | Lists 5 most recent payment recovery cases with status | `Overview.tsx` Table | `GET /cases?limit=5` | Verified working | Direct link to `/cases/:caseId`. |
| **Live Audit Event Stream** | Shows real-time chronological event trail | `Overview.tsx` Timeline | `GET /metrics/summary` -> `recent_audits` | Verified working | Pulls from `audit_events` DB table. |
| **"Trigger Demo Simulation" Button** | Ingests 5 simulated failure events for live viewing | `Overview.tsx` Button | `POST /demo/simulate-events` | Verified working | Explicitly labels simulated event injection. |

---

### Page 2: Autonomous Recovery Cases (`/cases`)
- **Route:** `/cases`
- **Component:** `frontend/src/pages/Cases.tsx`
- **Data Source:** Backend `GET /cases`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Search Input** | Filters cases by payment ID, customer email, customer name | `Cases.tsx` search input | Frontend filter + query param | Verified working | Fixed in recent commit; works smoothly. |
| **Status Filter Dropdown** | Filter by `failed`, `diagnosed`, `action_proposed`, `in_recovery`, `recovered`, etc. | `Cases.tsx` Select | Query state | Verified working | Accurately reflects state machine. |
| **Failure Category Filter** | Filter by `bank_timeout`, `insufficient_funds`, `expired_card`, etc. | `Cases.tsx` Select | Query state | Verified working | Domain failure category enum. |
| **Cases Data Table** | Displays customer, amount, status, failure reason, actions | `Cases.tsx` Table | `GET /cases` | Verified working | Real-time sorting and pagination. |
| **"View Details" Action Link** | Navigates to deep inspection of specific case | `Cases.tsx` button | `useNavigate('/cases/:id')` | Verified working | Deep link to `CaseDetail.tsx`. |

---

### Page 3: Case Detail & Multilingual Voice Workbench (`/cases/:caseId`)
- **Route:** `/cases/:caseId`
- **Component:** `frontend/src/pages/CaseDetail.tsx` & `frontend/src/components/VoiceRecoveryPanel.tsx`
- **Data Source:** `GET /cases/:caseId`, `POST /cases/:caseId/approve`, `POST /voice/*`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Case Metadata & Status Ribbon** | Displays customer profile, failure code, amount, retry count | `CaseDetail.tsx` Card | `GET /cases/:caseId` | Verified working | Pulls exact DB context. |
| **AI Diagnosis & Reason Card** | Shows diagnosis summary, transient vs terminal, signals | `CaseDetail.tsx` Card | Case proposal json in DB | Verified working | Created by configured model provider or heuristic fallback. |
| **Approve Proposal Button** | Approves pending proposal for execution | `CaseDetail.tsx` Button | `POST /cases/:id/approve` | Verified working | Requires reviewer or admin role. |
| **Reject Proposal Button** | Rejects proposal and moves case to manual review | `CaseDetail.tsx` Button | `POST /cases/:id/reject` | Verified working | Transitions state to `rejected`. |
| **Override Action Selector** | Allows human reviewer to manually change proposed recovery action | `CaseDetail.tsx` Select + Button | `POST /cases/:id/override` | Verified working | Audit logged. |
| **Audit Trail Timeline** | Chronological record of state transitions, attempts, and approvals | `CaseDetail.tsx` Timeline | `GET /cases/:id/timeline` | Verified working | Real audit trail from DB. |
| **Voice Call Simulation Header** | Initiates interactive voice session with customer | `VoiceRecoveryPanel.tsx` | `POST /voice/start-session` | Verified working (Simulated) | Voice engine runs in mock/synthetic audio mode. |
| **Language Switcher (7 Indic + Hinglish)** | Switches speech normalization and target accent | `VoiceRecoveryPanel.tsx` Select | Session language state | Verified working | Text prompts and normalizers support all 7 languages. |
| **Consent Grant / Revoke Toggle** | Captures explicit conversational consent before discussing recovery | `VoiceRecoveryPanel.tsx` Button | `POST /voice/session/:id/consent` | Verified working | State machine enforces consent requirement. |
| **Microphone PCM Recorder** | Records 16kHz mono PCM via AudioWorklet | `VoiceRecoveryPanel.tsx` Mic button | `pcmRecorder.ts` -> WebAudio | Verified working | Browser mic stream sent as base64 PCM. |
| **Local STT Provider** | Transcribes customer utterance | `local_provider.py` | Local audio parser | **Audit Concern Identified** | Currently returns canned transcripts; now marked explicitly as synthetic mock. |
| **Local TTS Audio Player** | Plays agent spoken response | `local_tts_provider.py` | Tone generator | **Audit Concern Identified** | Currently generates mathematical formant sine bursts; labeled as tone mock until Prompt 6. |
| **One-Click Quick Scenarios** | Feeds vernacular test utterances (Hindi, Kannada, Tamil, etc.) | `VoiceRecoveryPanel.tsx` | `sendVoiceUtterance()` | Verified working | Realistic evaluation prompts across all regional languages. |
| **Voice Lab & Reliability Button** | Opens pre-flight audit modal | `VoiceLabModal.tsx` | `GET /voice/readiness` | Verified working | Must honestly reflect mock status rather than 100% false neural ready. |
| **Pronunciation Gallery Button** | Opens 84-case benchmark player | `PronunciationGalleryModal.tsx` | `GET /voice/tts/benchmark` | Verified working | Uncalibrated scores must show "Not measured" rather than fake 4.9. |

---

### Page 4: AI Copilot Developer Assistant (`/copilot`)
- **Route:** `/copilot`
- **Component:** `frontend/src/pages/Copilot.tsx`
- **Data Source:** `POST /copilot/query`, `GET /copilot/history`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Query Input Box** | Submit natural language queries regarding payments, issues, and cases | `Copilot.tsx` Input.Search | `POST /copilot/query` | Verified working | Multi-step reasoning with intent classification. |
| **Quick Action Chips** | Instant queries: "Priya Sharma payment", "HDFC gateway latency", etc. | `Copilot.tsx` Buttons | Local query presets | Verified working | Populates input and triggers query. |
| **Reasoning Steps Stepper** | Visualizes intent classification, tool invocation, and DB query execution | `Copilot.tsx` Steps component | `CopilotStep[]` from API | Verified working | Recently patched with safe fallbacks and duration tracking. |
| **Evidence & Metadata Drawer** | Inspects raw SQL query, retrieved customer payload, and API params | `Copilot.tsx` Drawer | `metadata` on response | Verified working | Full developer transparency. |
| **Action Confirmation Modal** | Requests operator authorization before executing refunds or links | `Copilot.tsx` Modal | `POST /copilot/execute-action` | Verified working | Prevents unauthorized side-effects. |

---

### Page 5: Customer Issues Tracker (`/issues`) & Detail (`/issues/:issueId`)
- **Route:** `/issues`, `/issues/:issueId`
- **Components:** `frontend/src/pages/CustomerIssues.tsx`, `frontend/src/pages/IssueDetail.tsx`
- **Data Source:** Backend `/copilot/issues/*`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Issue Status Tabs** | Filter issues by `open`, `investigating`, `waiting_customer`, `resolved` | `CustomerIssues.tsx` Tabs | Query state | Verified working | Direct repository query. |
| **Priority & Category Badges** | Highlights `P0_CRITICAL`, `DOUBLE_DEBIT`, `SUBSCRIPTION_REVOKED` | `CustomerIssues.tsx` Tags | DB model fields | Verified working | Color-coded severity. |
| **Create Issue Modal** | Manually record customer issue reported via Slack/Email/Desk | `CustomerIssues.tsx` Modal | `POST /copilot/issues` | Verified working | Creates persistent issue record. |
| **Correlate Payment Button** | Automatically discovers associated failed payment in DB | `IssueDetail.tsx` Button | `POST /copilot/issues/:id/correlate` | Verified working | Matches customer phone/email/amount. |
| **Draft Customer Email Button** | Opens email composer pre-populated with case diagnosis and link | `IssueDetail.tsx` Button | Navigates to `/email/compose` | Verified working | Passes draft context. |
| **Issue Status Progression** | Transition issue from Open -> Investigating -> Resolved | `IssueDetail.tsx` Dropdown | `PATCH /copilot/issues/:id` | Verified working | Persisted in SQLite. |

---

### Page 6: Email Compose & Dispatch Preview (`/email/compose`)
- **Route:** `/email/compose`, `/email/compose/:draftId`
- **Component:** `frontend/src/pages/EmailCompose.tsx`
- **Data Source:** Backend `/copilot/emails/*`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Customer Email & Subject Inputs** | Specify recipient email address, subject line, and case tag | `EmailCompose.tsx` Form | Local form state | Verified working | Validated against email regex. |
| **Template Preset Selector** | Load standard Razorpay recovery templates (e.g., Retry Link, Bank Downtime Notice) | `EmailCompose.tsx` Select | Preset template dictionary | Verified working | Auto-fills body and subject. |
| **Rich Markdown / Plain Text Editor** | Compose personalized recovery message with payment variables | `EmailCompose.tsx` TextArea | Controlled component | Verified working | Synchronized live with preview. |
| **Simulated Email Preview Card** | Render pixel-perfect preview of customer inbox view | `EmailCompose.tsx` Preview Pane | React rendered HTML | Verified working | Explicitly marked "SIMULATED EMAIL DISPATCH". |
| **"Send Simulated Email" Button** | Records email dispatch event and updates draft status to sent | `EmailCompose.tsx` Button | `POST /copilot/emails/send` | Verified working | Stores in DB; explicitly simulated, zero real outbound SMTP side-effects. |

---

### Page 7: Human Review Queue (`/review`)
- **Route:** `/review`
- **Component:** `frontend/src/pages/HumanReview.tsx`
- **Data Source:** Backend `GET /cases?status=human_review_required`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Pending Approvals Table** | Shows high-value transactions (>₹15,000) or low-confidence diagnoses | `HumanReview.tsx` Table | Filtered DB cases query | Verified working | Prioritized by amount and urgency. |
| **Approve / Reject Action Buttons** | Perform single-click authorized action or rejection | `HumanReview.tsx` Buttons | `POST /cases/:id/approve` | Verified working | Logs approving operator ID. |
| **Batch Decision Drawer** | Select multiple cases and execute batch approval | `HumanReview.tsx` Selection | Iterative API call | Verified working | Audited with batch timestamp. |

---

### Page 8: Unmatched Webhooks & DLQ (`/unmatched`)
- **Route:** `/unmatched`
- **Component:** `frontend/src/pages/UnmatchedEvents.tsx`
- **Data Source:** Backend `GET /webhooks/unmatched`, `GET /webhooks/queue/stats`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Queue Depth Statistics Banner** | Live metrics on `queued`, `processing`, `dead_letter`, `unmatched` | `UnmatchedEvents.tsx` Cards | `GET /webhooks/queue/stats` | Verified working | Direct count from `webhook_events` DB table. |
| **Unmatched Events Table** | Lists incoming Razorpay events that could not correlate to any case | `UnmatchedEvents.tsx` Table | `GET /webhooks/unmatched` | Verified working | Shows payload hash, event ID, error reason. |
| **Payload Inspector Modal** | View raw JSON payload received from Razorpay gateway | `UnmatchedEvents.tsx` Modal | Table record `payload_json` | Verified working | Monospace JSON viewer with copy. |
| **"Retry Processing" Button** | Re-enqueues dead-letter or unmatched event for re-evaluation | `UnmatchedEvents.tsx` Button | `POST /webhooks/retry/:eventId` | Verified working | Resets retry counter and status. |

---

### Page 9: AI Evaluation & Benchmark Lab (`/evaluation`)
- **Route:** `/evaluation`
- **Component:** `frontend/src/pages/Evaluation.tsx`
- **Data Source:** Backend `GET /metrics/evaluation`, `POST /evaluation/run`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **Dataset Size Slider (20 - 500)** | Configure number of synthetic customer scenarios to evaluate | `Evaluation.tsx` Slider | State `size` | Verified working | Deterministic generator. |
| **Random Seed Input** | Control deterministic RNG seed for reproducible benchmark results | `Evaluation.tsx` InputNumber | State `seed` | Verified working | Guaranteed reproducibility. |
| **"Run Benchmark Evaluation" Button** | Runs comparison between Autonomous Autopilot vs Fixed Baseline | `Evaluation.tsx` Button | `POST /evaluation/run` | Verified working | **Audit Concern Identified:** Evaluates heuristic policy function rather than active LLM provider; must clearly state simulation nature. |
| **Recovery Rate Comparison Cards** | Compares Autopilot recovery rate vs Fixed Rule baseline | `Evaluation.tsx` Metric Cards | Benchmark report response | Verified working | Formatted via `formatPct()`. |
| **Simulated Revenue Lift Card** | Shows modeled incremental INR recovered | `Evaluation.tsx` Metric Cards | Benchmark report response | Verified working | Must be labeled "Simulated Model Lift", not realized cash. |
| **Category Breakdown Bar Chart** | Recharts bar chart comparing rates across 7 failure reasons | `Evaluation.tsx` Recharts | Benchmark category data | Verified working | Responsive visual comparison. |
| **Category Metrics Table** | Granular cases, rates, and incremental lift per category | `Evaluation.tsx` Table | Category breakdown list | Verified working | Fully populated. |

---

### Page 10: Account & Developer Settings (`/settings`)
- **Route:** `/settings`
- **Component:** `frontend/src/pages/AccountSettings.tsx`
- **Data Source:** Backend `GET /admin/settings`, `POST /admin/settings`, `POST /admin/kill-switch`

| Interactive Control / Element | Intended Behaviour | Implementation Path | Data Source / Backing API | Verification Status | Truthfulness & Audit Notes |
|---|---|---|---|---|---|
| **API Keys & Credentials Tab** | Inspect configured `RAZORPAY_KEY_ID`, masked secret, Basic Auth header | `AccountSettings.tsx` Tab 1 | `GET /admin/settings` | Verified working | **Audit Concern Identified:** Previously showed sample secret; secrets must never be exposed or returned to browser. |
| **Webhooks Tab** | Inspect endpoint URL and HMAC-SHA256 signature verification status | `AccountSettings.tsx` Tab 2 | `GET /admin/settings` | Verified working | Ingestion endpoint `http://localhost:8000/webhooks/razorpay`. |
| **AI Model Configuration Tab** | Select provider (`gemini`, `openai`, `ollama`, `fake`), models, API keys | `AccountSettings.tsx` Tab 3 | Form + `POST /admin/settings` | Verified working | **Audit Concern Identified:** Changes were in-memory only and did not persist across restarts; must persist and invalidate client cache. |
| **Test Model Inference Playground** | Send test payment failure context to active LLM and view raw output | `AccountSettings.tsx` Playground | `POST /admin/test-model` | Verified working | Measures latency in ms. |
| **SDK Quickstart Tab** | View and copy integration code snippets for Python, Node.js, and cURL | `AccountSettings.tsx` Tab 4 | Static code generators | Verified working | Dynamically interpolates Key ID. |
| **Emergency Kill-Switch** | Immediately block all autonomous agent actions across the system | `AccountSettings.tsx` Tab 5 | `POST /admin/kill-switch` | Verified working | Backed by `settings.KILL_SWITCH_ACTIVE`. |
| **Execution Mode Dropdown** | Switch between `synthetic` and `razorpay_test` | `AccountSettings.tsx` Tab 5 | Form + `POST /admin/settings` | Verified working | `production` mode strictly disabled for Buildathon. |
| **Human Review Threshold Slider** | Configure amount threshold (INR) for mandatory human approval | `AccountSettings.tsx` Tab 5 | Form + `POST /admin/settings` | Verified working | Default ₹15,000. |
| **Min Confidence Slider** | Configure minimum AI confidence threshold (50% - 99%) | `AccountSettings.tsx` Tab 5 | Form + `POST /admin/settings` | Verified working | Cases below threshold route to human review. |
| **System Diagnostics Tab** | Inspect Python version, framework, DB engine, and API links | `AccountSettings.tsx` Tab 6 | `GET /admin/diagnostics` | Verified working | Live system telemetry. |
| **Generate Demo Data Controls** | Seed 10 to 200 synthetic payment cases into SQLite database | `AccountSettings.tsx` Tab 7 | `POST /demo/seed` | Verified working | Populates database with representative failure scenarios. |
| **Purge All Data Button** | Nuclear database reset; deletes all cases, webhooks, and drafts | `AccountSettings.tsx` Tab 7 | `POST /demo/clear-all` | Verified working | Requires confirmation modal. |

---

## 3. Discovered Vulnerabilities, Truthfulness Mismatches & Remediation Status

| Subsystem / Component | Discovered Misleading Behaviour | True Implementation Reality | Remediation Required & Status |
|---|---|---|---|
| **Local STT Provider** (`voice/stt/local_provider.py`) | Claims to be a "Local Indic STT Engine" with 7 language tables, returning "WhatsApp payment link" with 0.94 confidence. | Hardcoded fixed transcript string; does not transcribe speech. | **Remediated in Prompt 1:** Explicitly marked as `[Synthetic Mock STT]`, confidence set to `None` / documented mock flag. Genuine provider integration implemented in Prompt 5. |
| **Local TTS Provider** (`voice/tts/local_tts_provider.py`) | Claims to synthesize 7 regional Indian voices with 4.9/5.0 naturalness. | Generates pure mathematical sine-wave tones using `math.sin()`. | **Remediated in Prompt 1:** Hardcoded 4.9 MOS scores replaced with "Not measured". Provider marked as `[Synthetic Tone Generator (Mock)]`. Genuine synthesis implemented in Prompt 6. |
| **Voice Readiness Audit** (`voice/readiness.py`) | Unconditionally returns `is_ready: True` and 100% readiness claim for Buildathon. | Tests tone generator and fixed mock; no real neural weights present. | **Remediated in Prompt 1:** Returns `is_ready: False` for genuine neural speech unless real weights exist, reporting `demo_mode: "Synthetic Mock Mode"` with explicit explanation of missing dependencies. |
| **Pronunciation Benchmark** (`pronunciation_benchmark.py`) | Returns hardcoded 4.88 pronunciation and 4.85 intelligibility scores. | Mathematical tones were never evaluated by native human speakers. | **Remediated in Prompt 1:** Replaced with `"Not measured"` / `None` until human or ASR-verified intelligibility is collected. |
| **Recovery Benchmark** (`evaluation/runner.py`) | Presents simulation as evaluation of the configured AI Agent. | Executes a deterministic Python `if/else` rule policy. | **Remediated in Prompt 1:** Accurately labeled as "Heuristic Policy Benchmark (Simulation)". Configured model workflow evaluation added in Prompt 9. |
| **Settings Persistence & Secrets** (`routes_admin.py`, `AccountSettings.tsx`) | Settings updates modified in-memory variables only; key secret displayed as placeholder. | Changes lost on process restart; secret key handling unsafe. | **Remediated in Prompts 1 & 3:** Persisted settings mechanism, secrets isolated and never returned to browser, client cache invalidation. |
| **Role Authorization** (`security/rbac.py`) | Accepts arbitrary `X-Operator-Role: admin` header with default to admin. | Anyone can spoof admin by supplying header or leaving it default. | **Remediated in Prompt 4:** Server-side authenticated identity replaces spoofable client headers. |
| **Webhook Processing Mismatch** (`workers/queue.py`) | `subscription.charged` handled as failure; `order.paid` ignored. | Payment captures could be dropped or treated as failures. | **Remediated in Prompt 2:** Unified event-processing service with exact obligation matching. |
