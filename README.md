# JanVaani: Call the Internet. Hear the Answer.

![JanVaani Architecture](https://via.placeholder.com/800x400.png?text=JanVaani+Architecture)

**JanVaani** is a production-quality, multilingual, voice-first AI phone agent built for the Sarvam AI Hackathon. 

It allows anyone to dial a phone number, ask a question in their natural Indian language (including code-mixed speech), and hear a concise answer researched from multiple web sources. No app, no typing, and no digital literacy required.

## 🚀 Features

- **Voice First, Multilingual**: Built natively for phone lines (8kHz mu-law audio). Auto-detects English, Hindi, Odia, Kannada, Tamil, and other Indian languages.
- **Truth Grounding**: Cross-checks claims across multiple web sources (Tavily, Serper, Sarvam Wiki). Never guesses if unsure.
- **Zero Transcoding Latency**: Uses raw 8kHz audio end-to-end for ultra-low latency streaming.
- **Risk Router**: Instantly routes Emergency (112) or Self-Harm queries to safe paths without executing a web search.
- **Privacy by Default**: Compliant with the DPDP Act. Explicit spoken consent is required to proceed.
- **Dynamic Tool Calling**: The agent can invoke backend APIs mid-conversation (e.g., look up schemes, weather, or transfer to a human).
- **Intelligent Barge-in & Silence Handling**: Gracefully handles interruptions and prompts users when they are silent.

---

## 🛠️ Tech Stack

- **Telephony:** Exotel / Twilio Media Streams (Voice streaming over WebSockets)
- **Voice Gateway:** FastAPI + Uvicorn + WebSockets
- **AI Models (Sarvam AI Suite):**
  - **STT:** `saaras:v4` / `saaras:v3-realtime` (Real-time Speech-to-Text)
  - **LLM:** `sarvam-105b-conversations` / `sarvam-105b` (Chat Completions & Orchestration)
  - **TTS:** `bulbul:v3` (Streaming Text-to-Speech in 11 languages)
- **Search Broker:** Tavily + Serper for web evidence retrieval.
- **Data & Caching:** PostgreSQL & Redis.

---

## 🏗️ Architecture & Data Flow

1. **Ingestion:** Twilio/Exotel forwards the WebSocket media payload (8kHz mu-law) to the FastAPI Gateway.
2. **Transcription:** Audio is queued and streamed to Sarvam Saaras STT. Language auto-detection identifies the spoken language.
3. **Orchestration & Research:** The Agent intercepts the transcript, checks for intent/risk, and queries the Search Broker (Tavily/Serper).
4. **Synthesis:** Sarvam-105B writes a grounded answer using *only* the retrieved evidence.
5. **Speech Generation:** Text is chunked (sentence by sentence) and streamed to Sarvam Bulbul TTS.
6. **Playback:** TTS returns mu-law audio chunks relayed directly back to the caller.

---

## 💻 Local Setup & Installation

### Prerequisites

- Python 3.9+
- A [Sarvam AI](https://sarvam.ai) API Key
- A Twilio / Exotel account and phone number
- `ngrok` (for tunneling local WebSockets to the public internet)

### 1. Clone the repository
```bash
git clone https://github.com/your-username/sarvam-voice-agent.git
cd sarvam-voice-agent
```

### 2. Set up the virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```ini
SARVAM_API_KEY="your-sarvam-api-key"
TWILIO_ACCOUNT_SID="your-twilio-sid"
TWILIO_AUTH_TOKEN="your-twilio-token"
PORT=8000
```

### 4. Run the Application
Start the FastAPI server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Expose with ngrok
To allow Twilio to reach your local server, expose port 8000:
```bash
ngrok http 8000
```
*Note the `wss://` URL provided by ngrok.*

### 6. Configure Twilio
In your Twilio Console, configure your active phone number's incoming call webhook to point to your ngrok URL or use TwiML:
```xml
<Response>
    <Connect>
        <Stream url="wss://<your-ngrok-id>.ngrok-free.app/media" />
    </Connect>
</Response>
```

---

## 🛡️ Trust & Safety (No Loopholes)

- **Strict Grounding:** The model is evaluated on its ability to say "I don't know" when sources disagree.
- **SSRF Protection:** The page extractor runs in a sandbox and blocks internal/private IP requests.
- **DPDP Act Compliance:** No raw audio is recorded. Call logs are anonymized and retained only based on the configured policy.

---

## 🔮 Future Roadmap

- **Multi-turn Memory:** Remembering previous conversational turns across a session.
- **Vector Database Integration:** Replacing basic search with Milvus/Pinecone for large-scale enterprise RAG.
- **Follow-up Actions:** Sending the verified source links directly to the caller via SMS or WhatsApp after the call.

---
*Built with ❤️ for the Sarvam AI Hackathon.*
