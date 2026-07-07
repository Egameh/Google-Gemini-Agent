# Gemini Agentic Assistant

A production-deployed, multi-agent AI assistant that manages Gmail and Google Calendar through natural language. Built with a tool-dispatch architecture, served via FastAPI, and hosted on AWS EC2.

---

## What It Does

Send a plain-English request — the agent classifies your intent, selects the right tool, calls the appropriate Google API, and returns a result. No UI needed; the interface is the API.

**Supported actions:**
- View recent inbox emails
- Search emails by sender, keyword, or label
- Send emails (AI-drafted from a brief)
- Reply to emails
- View upcoming calendar events
- Create calendar events from natural language descriptions

**Example request:**
```json
POST /query
{
  "query": "Can you check if I have any emails from Irene and create a calendar reminder for tomorrow at 1pm called Review Notes?"
}
```

---

## Architecture

```
User Request (HTTP POST)
        │
        ▼
   FastAPI Endpoint
        │
        ▼
   Agent 1 (Gemini 2.5 Pro)
   ├── Intent classification
   ├── Tool selection & dispatch
   ├── Multi-turn reasoning loop
   └── Tool results:
       ├── view_emails
       ├── search_email
       ├── send_email
       ├── create_event
       └── view_calendar
        │
        ▼ (if reply needed)
   Agent 2 (Gemini 2.5 Pro)
   └── reply_email
```

**Key design decisions:**
- **Tool dispatch pattern**: tools registered in a dictionary (`TOOLS` dict), not hardcoded if/elif chains — adding a new capability requires one function, one dict entry, one prompt line
- **Multi-turn reasoning loop**: Agent 1 can chain tools sequentially, feeding results from one tool as context for the next
- **Structured JSON output**: all LLM responses use `response_mime_type: application/json` for reliable parsing
- **Two-agent handoff**: email reply is delegated to a specialised Agent 2, keeping routing logic clean

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 2.5 Pro (Google AI Studio) |
| API Framework | FastAPI + Uvicorn |
| Email (send) | SMTP over SSL (smtplib) |
| Email (read/search/reply) | Gmail API v1 |
| Calendar | Google Calendar API v3 |
| Auth | OAuth 2.0 (google-auth, InstalledAppFlow) |
| Deployment | AWS EC2 (Amazon Linux 2023) |
| Process management | GNU Screen |
| Config | python-dotenv (.env) |

---

## Project Structure

```
├── gmail_agent.py      # All agent logic, tools, and API functions
├── main.py             # FastAPI app and endpoint definition
├── .env                # Environment variables (not committed)
├── credentials.json    # Google OAuth client secrets (not committed)
├── token.pickle        # OAuth token (not committed)
└── .gitignore
```

---

## Running Locally

**Prerequisites:** Python 3.10+, a Google Cloud project with Gmail and Calendar APIs enabled, and a Google AI Studio API key.

```bash
# Clone the repo
git clone https://github.com/Egameh/Google-Gemini-Agent.git
cd Google-Gemini-Agent

# Install dependencies
pip install fastapi uvicorn google-api-python-client google-auth-oauthlib google-genai python-dotenv

# Create .env file
echo "GOOGLE_API_KEY=your_key" > .env
echo "GMAIL_APP_PASSWORD=your_app_password" >> .env
echo "SENDER_EMAIL=your_email@gmail.com" >> .env

# Add your credentials.json from Google Cloud Console

# Start the server
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for the interactive API UI.

---

## Deployment (AWS EC2)

The API is deployed on an AWS EC2 t2.micro instance (Amazon Linux 2023) and runs persistently using GNU Screen.

```bash
# SSH into server
ssh -i "your-key.pem" ec2-user@your-ec2-address

# Start persistent session
screen -S agent
cd ~/Google-Gemini-Agent
uvicorn main:app --host 0.0.0.0 --port 8000

# Detach (Ctrl+A, D) — server keeps running after terminal closes
```

---

## What This Demonstrates

- **Agentic system design** — multi-agent architecture with intent routing, tool dispatch, and multi-turn reasoning loops
- **Production deployment** — live REST API on AWS EC2, accessible via HTTP from anywhere
- **Real API integration** — OAuth2 authentication, Gmail API, Google Calendar API, SMTP
- **LLM prompt engineering** — structured JSON output, tool-use prompting, multi-turn conversation management
- **Software engineering practices** — environment variable management, `.gitignore`, modular function design, error handling

---

## Author

**Egameh Omokagbo** — Data Scientist | Process Engineer  
[LinkedIn](https://www.linkedin.com/in/egameh) | [GitHub](https://github.com/Egameh)
