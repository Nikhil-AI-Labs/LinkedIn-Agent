# LinkedIn AI Agent

A production-grade autonomous LinkedIn presence management platform built with LangGraph, FastAPI, Next.js, and PostgreSQL.

## Overview

The LinkedIn AI Agent helps you manage your LinkedIn presence through:

- **Content Creation**: AI-powered post drafting with human-in-the-loop approval
- **Engagement Monitoring**: Automated monitoring of posts and watchlist profiles
- **Voice Interface**: Text and voice chat in English, Hindi, and Hinglish
- **OAuth Integration**: Secure LinkedIn authentication (recommended for production)
- **Browser Fallback**: Experimental Playwright automation (unofficial, use with caution)

## Architecture

- **Backend**: FastAPI + LangGraph + PostgreSQL
- **Frontend**: Next.js + React + TailwindCSS
- **LLMs**: Sarvam-M (reasoning) + Groq llama-3.3-70b-versatile (speed)
- **Voice**: Sarvam Saarika (STT) + Sarvam Bulbul v3 (TTS)

## Project Structure

```
linkedin-agent/
├── backend/              # FastAPI application
│   ├── alembic/         # Database migrations
│   ├── app/             # Application code
│   │   ├── api/         # REST endpoints
│   │   ├── core/        # Core utilities
│   │   ├── db/          # Database models
│   │   ├── graphs/      # LangGraph workflows
│   │   ├── services/    # Service layer
│   │   └── main.py      # FastAPI entry point
│   ├── tests/           # Backend tests
│   └── requirements.txt # Python dependencies
├── frontend/            # Next.js application
│   ├── src/
│   │   ├── app/         # App router pages
│   │   ├── components/  # React components
│   │   └── lib/         # Utilities
│   └── package.json     # Node dependencies
├── infra/               # Infrastructure configs
│   ├── docker/          # Docker files
│   └── k8s/             # Kubernetes manifests
└── .kiro/               # Kiro spec files
    └── specs/
        └── linkedin-ai-agent/
            ├── requirements.md
            ├── design.md
            └── tasks.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Sarvam AI API key ([Get one here](https://dashboard.sarvam.ai))
- Groq API key ([Get one here](https://console.groq.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd linkedin-agent
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

3. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Run database migrations
   alembic upgrade head
   
   # Start backend
   uvicorn app.main:app --reload
   ```

4. **Frontend setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

## Development

### Running Tests

**Backend**:
```bash
cd backend
pytest
```

**Frontend**:
```bash
cd frontend
npm run test
```

### Code Quality

**Backend**:
```bash
# Linting
ruff check .

# Formatting
black .

# Type checking
mypy .
```

**Frontend**:
```bash
# Linting
npm run lint

# Formatting
npm run format
```

## Authentication Modes

### Browser Mode with Kimi WebBridge (Recommended for Personal Use)

Uses Kimi WebBridge to control your existing browser session. No LinkedIn credentials needed - reuses your active login.

**Pros**:
- Uses your actual browser session
- No credential storage needed
- Human-like behavior (it's literally your browser)
- Local execution - all data stays on your machine

**Cons**:
- Requires Kimi running locally
- Manual session required

Set `AUTH_MODE=browser` and `BROWSER_PROVIDER=kimi_webbridge` in `.env`.

### Browser Mode with Playwright (Fallback)

Uses Playwright browser automation with unofficial methods.

**⚠️ WARNING**: This mode uses unofficial methods and may break without notice. LinkedIn actively detects automation.

**Pros**:
- Fully automated
- No manual session needed

**Cons**:
- High detection risk
- Account restriction risk
- Requires credentials storage

Set `AUTH_MODE=browser` and `BROWSER_PROVIDER=playwright` in `.env`.

### OAuth Mode (Future - Requires LinkedIn App Approval)

Uses official LinkedIn OAuth 2.0 API. **Currently not available** without approved LinkedIn Developer app.

**Requirements**:
- LinkedIn Developer app with "Sign In with LinkedIn using OpenID Connect" product
- "Share on LinkedIn" product approval
- `w_member_social` scope (rarely approved for personal projects)
- Redirect URI: `http://localhost:8000/api/v1/auth/linkedin/callback`

**Pros**:
- Official and supported by LinkedIn
- Stable and compliant
- Lower risk of account restrictions

**Cons**:
- Requires lengthy app approval process (weeks to months)
- Personal projects rarely get posting permissions
- Scoped permissions limit functionality

Set `AUTH_MODE=oauth` in `.env` (when you have approved app credentials).

## Deployment

See [deployment guide](./docs/deployment.md) for production deployment instructions.

## License

[MIT License](./LICENSE)

## Support

For issues and feature requests, please use GitHub Issues.
