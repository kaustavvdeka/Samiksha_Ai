# Samiksha — Personal AI Voice Computer Agent

> **"Hey Samiksha, open YouTube and search for Swin Transformer."**

Samiksha is a modular, extensible personal AI voice assistant that listens to your voice, understands natural language, controls your computer, and speaks results back to you.

---

## Architecture

```
Microphone
    ↓
Sarvam AI Speech-to-Text (voice/sarvam_stt.py)
    ↓
User Text
    ↓
SamikshaAgent (agent/agent.py)
    ↓
    ├─ Planner → LLM (llm/provider.py)
    │       ↓
    │   Intent + Tool Selection
    │       ↓
    ├─ PermissionChecker (security/permissions.py)
    │       ↓
    └─ Executor → Tool (tools/*.py)
            ↓
        Computer Action
            ↓
        Tool Result
            ↓
        LLM → Final Response
    ↓
Local TTS (voice/tts.py → Text_To_speech_api)
    ↓
Speaker
```

---

## Features

| Feature | Milestone | Status |
|---|---|---|
| Microphone capture | Milestone 1 | ✅ |
| Sarvam AI Speech-to-Text (`voice/sarvam_stt.py`) | Milestone 1 | ✅ |
| Local TTS abstraction layer (`voice/tts.py` → `Text_To_speech_api`) | Milestone 1 | ✅ |
| Native macOS `afplay` & cross-platform audio playback (`voice/audio.py`) | Milestone 1 | ✅ |
| Replaceable LLM agent (`llm/provider.py`: OpenAI / Local Ollama) | Milestone 2 | ✅ |
| Safe tool registry (`tools/registry.py`) | Milestone 3 | ✅ |
| Multi-platform application control (`tools/applications.py`) | Milestone 3 | ✅ |
| Web & browser automation (`tools/browser.py`) | Milestone 4 | ✅ |
| Multi-step planner & executor (`agent/planner.py`, `agent/executor.py`) | Milestone 5 | ✅ |
| Persistent SQLite memory (`memory/database.py`, `tools/memory_tools.py`) | Milestone 6 | ✅ |
| Custom workflows execution (`execute_custom_workflow`) | Milestone 7 | ✅ |
| Screen vision analysis (`tools/screenshot.py`: `analyze_screen`) | Milestone 8 | ✅ |
| Security permission model (`security/permissions.py`) | All | ✅ |
| Structured JSON logging (`logger.py`) | All | ✅ |
| Unit + integration test suite (50 automated tests) | All | ✅ |

---

## Requirements

- **Python 3.11+**
- **macOS** (primary), **Linux**, or **Windows**
- **Sarvam AI API key** (free tier available at [sarvam.ai](https://sarvam.ai))
- **OpenAI API key** (or a local model via Ollama / LM Studio)
- Your **Text_To_speech_api** server running locally

---

## Installation

### 1. Clone and enter the project

```bash
cd samiksha-ai-agent
```

### 2. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. macOS audio (if needed)

```bash
brew install portaudio   # Required by sounddevice
```

### 5. Copy and configure `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
SARVAM_API_KEY=your_sarvam_key_here
LLM_API_KEY=your_openai_key_here
LLM_MODEL=gpt-4o
TTS_API_URL=http://localhost:8000
```

---

## Starting the TTS Server

Before running Samiksha, start your local TTS server (separate terminal):

```bash
cd ../Text_To_speech_api
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Verify it works:
```bash
curl http://localhost:8000/health
# → {"status":"healthy"}
```

---

## How to Run

### Full voice mode (microphone + STT + agent + TTS)

```bash
python main.py
```

### Text mode (type commands, no microphone required)

```bash
python main.py --text
```

### Milestone 1 echo test (mic → Sarvam STT → TTS, no LLM)

```bash
python main.py --milestone1
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SARVAM_API_KEY` | ✅ | — | Your Sarvam AI API key |
| `SARVAM_STT_ENDPOINT` | ❌ | `https://api.sarvam.ai/speech-to-text` | Sarvam STT endpoint |
| `LLM_PROVIDER` | ❌ | `openai` | `openai` or `local` |
| `LLM_API_KEY` | ✅ | — | OpenAI or compatible API key |
| `LLM_MODEL` | ❌ | `gpt-4o` | Model name |
| `LLM_BASE_URL` | ❌ | — | Set for local models (e.g. Ollama) |
| `TTS_API_URL` | ❌ | `http://localhost:8000` | Your TTS server URL |
| `TTS_VOICE` | ❌ | `nova` | TTS voice name |
| `MIC_SAMPLE_RATE` | ❌ | `16000` | Microphone sample rate (Hz) |
| `MIC_MAX_DURATION` | ❌ | `10` | Max recording length (seconds) |
| `MEMORY_DB_PATH` | ❌ | `./data/samiksha.db` | SQLite database path |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |

---

## Configuring Sarvam AI (STT)

1. Sign up at [sarvam.ai](https://www.sarvam.ai)
2. Get your API key from the dashboard
3. Set `SARVAM_API_KEY` in `.env`

The STT model used is `saarika:v2` with auto language detection.

---

## Configuring Local TTS

Your TTS repo (`Text_To_speech_api`) exposes:
```
POST /tts  →  {"text": "...", "voice": "nova"}  →  MP3 bytes
```

Samiksha connects to it via `TTS_API_URL` in `.env`.

To use a different TTS backend, edit only `voice/tts.py`.

---

## Configuring the LLM

### OpenAI (default)
```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o
```

### Local model (Ollama)
```bash
ollama serve
ollama pull llama3
```
```env
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
LLM_API_KEY=not-needed
```

---

## Available Commands (Examples)

```
"Open YouTube"
"Open WhatsApp"
"Open Brave"
"Open VS Code"
"Search Google for Swin Transformer"
"Search YouTube for machine learning tutorials"
"Take a screenshot"
"What time is it?"
"Open my project"
"Search my computer for main.py"
"My main project is at ~/projects/cropguard"   ← stores in memory
"Start coding"                                  ← runs custom workflow
```

---

## Adding a New Tool

1. Create or open a file in `tools/`
2. Apply the `@register_tool` decorator:

```python
from tools.registry import register_tool

@register_tool(description="Send an email to a contact.")
def send_email(recipient: str, subject: str, body: str) -> str:
    """..."""
    ...
```

3. Import the module in `tools/__init__.py`:

```python
import tools.email
```

That's it — the tool is now available to the agent.

---

## Adding a Custom Workflow

You can define multi-step workflows via the agent:

**Voice:**
> "Remember that 'start coding' should open VS Code, then open terminal, then open my project."

**Or programmatically:**
```python
from memory.memory import Memory
mem = Memory()
mem.save_workflow(
    name="start coding",
    description="My dev setup",
    steps=[
        {"tool": "open_application", "arguments": {"application": "VS Code"}},
        {"tool": "open_application", "arguments": {"application": "Terminal"}},
        {"tool": "open_file", "arguments": {"path": "~/projects/my-project"}},
    ]
)
```

Then say: **"Start coding"**

---

## Security Model

| Level | Tools | Behaviour |
|---|---|---|
| **SAFE** | open apps, search web, screenshot, time | Execute immediately |
| **CONFIRMATION REQUIRED** | delete file, shutdown, send email | Ask before executing |
| **BLOCKED** | arbitrary shell, format disk | Refuse always |

The LLM **never** executes raw shell commands. Every action goes through `security/permissions.py`.

---

## Running Tests

```bash
pytest -v
```

Tests mock all external services (LLM, STT, TTS) — no API keys needed for testing.

---

## Project Structure

```
samiksha-ai-agent/
├── main.py              ← Entry point
├── logger.py            ← Structured logging
├── requirements.txt
├── .env.example
│
├── config/
│   └── settings.py      ← All configuration from .env
│
├── agent/
│   ├── agent.py         ← Main coordinator
│   ├── planner.py       ← LLM query + tool selection
│   ├── executor.py      ← Tool execution + permission check
│   ├── state.py         ← Conversation history
│   └── prompts.py       ← System prompt + personality
│
├── llm/
│   ├── base.py          ← Abstract interface
│   └── provider.py      ← OpenAI + local implementations
│
├── voice/
│   ├── microphone.py    ← Audio capture (sounddevice)
│   ├── sarvam_stt.py    ← Sarvam AI STT
│   ├── tts.py           ← Local TTS (your repo)
│   └── audio.py         ← Audio playback helpers
│
├── tools/
│   ├── registry.py      ← @register_tool decorator + executor
│   ├── applications.py  ← open/close apps
│   ├── browser.py       ← search Google/YouTube, open URLs
│   ├── keyboard.py      ← type_text, press_key
│   ├── mouse.py         ← click, move_mouse
│   ├── screenshot.py    ← take_screenshot, analyze_screen (vision)
│   ├── system.py        ← time, system info
│   ├── files.py         ← search/create/read/open files
│   └── memory_tools.py  ← long-term memory & custom workflows
│
├── memory/
│   ├── database.py      ← SQLite queries
│   └── memory.py        ← High-level memory API
│
├── security/
│   └── permissions.py   ← SAFE / CONFIRM / BLOCK classification
│
└── tests/
    ├── conftest.py
    ├── test_tools.py
    ├── test_voice.py
    ├── test_agent.py
    ├── test_memory.py
    ├── test_planner.py
    └── test_integration.py
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `EnvironmentError: SARVAM_API_KEY not set` | Copy `.env.example` → `.env` and add your key |
| `TTS server not reachable` | Start TTS: `cd ../Text_To_speech_api && uvicorn app:app --port 8000` |
| `PortAudioError` on macOS | `brew install portaudio && pip install sounddevice` |
| LLM not responding | Check `LLM_API_KEY` and internet connection |
| App won't open | Check it's installed; edit `_APP_MAP_MACOS` in `tools/applications.py` |
| Audio playback on macOS | Built-in `/usr/bin/afplay` is used automatically (zero dependencies) |
| Audio playback on Linux/Windows | Install `ffmpeg` (`sudo apt install ffmpeg`) or `ffplay` |

---

## Future Improvements (Milestones 5–8)

- [ ] Multi-step Playwright browser automation
- [ ] Wake word detection ("Hey Samiksha")
- [ ] Screen understanding (vision: GPT-4V / LLaVA)
- [ ] Fine-tuned local model for faster inference
- [ ] Voice confirmation for CONFIRMATION_REQUIRED actions
- [ ] Streaming TTS for low-latency responses
- [ ] Plugin system for third-party tool packs
