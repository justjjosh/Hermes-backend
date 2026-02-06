# Hermes 🪽 - AI-Powered Brand Pitch Automation

> Named after the Greek god of communication and commerce

**Hermes** is a backend API that automates brand outreach for content creators. It generates personalized pitches using AI (Google Gemini), sends them via email (Mailgun), and tracks engagement (opens, clicks, replies).

## Features

- **Manual Mode**: Select brands, review AI-generated pitches, send when ready
- **Auto-Pilot Mode**: AI discovers brands, generates pitches, and sends them automatically
- **AI Pitch Generation**: Personalized pitches using Google Gemini API
- **Email Tracking**: Tracking pixels and Mailgun webhooks for open/click detection
- **Analytics**: Open rates, reply rates, brand engagement history
- **Smart Volume Control**: Warm-up schedule, auto-scaling, spam protection

## Tech Stack

| Component | Technology        |
| --------- | ----------------- |
| Backend   | FastAPI (Python)  |
| Database  | PostgreSQL        |
| AI        | Google Gemini API |
| Email     | Mailgun API       |
| Hosting   | Heroku            |
| Scheduler | Heroku Scheduler  |

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/hermes.git
cd hermes
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Start PostgreSQL with Docker

```bash
docker-compose up -d
```

### 4. Create virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 5. Initialize the database

```bash
python init_db.py
```

### 6. Run the server

```bash
uvicorn app.main:app --reload
```

### 7. Open API docs

Visit: [http://localhost:8000/docs](http://localhost:8000/docs)

## API Endpoints

### Brands

- `POST /brands` - Create brand
- `GET /brands` - List brands (filter by status, category)
- `GET /brands/{id}` - Get brand
- `PUT /brands/{id}` - Update brand
- `DELETE /brands/{id}` - Delete brand

### Creator Profile

- `POST /profile` - Create profile
- `GET /profile` - Get profile
- `PUT /profile` - Update profile

### Pitches

- `POST /pitches/generate` - Generate AI pitch
- `POST /pitches/{id}/send` - Send pitch
- `GET /pitches` - List pitches
- `GET /pitches/{id}` - Get pitch
- `PUT /pitches/{id}` - Update pitch
- `DELETE /pitches/{id}` - Delete pitch

### Tracking

- `GET /track/pixel/{id}.png` - Tracking pixel
- `POST /webhooks/mailgun` - Mailgun webhook

### Analytics

- `GET /analytics/overview` - Overall stats
- `GET /analytics/brands/{id}` - Brand history

### Auto-Pilot

- `POST /autopilot/configure` - Configure auto-pilot
- `GET /autopilot/status` - Get status
- `POST /autopilot/pause` - Pause
- `POST /autopilot/resume` - Resume
- `GET /autopilot/history` - Send history
- `POST /autopilot/blacklist` - Blacklist brand

## Project Structure

```
Hermes/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # CRUD operations
│   ├── config.py            # Settings
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic & integrations
│   └── tasks/               # Scheduled tasks
├── tests/                   # Unit tests
├── docker-compose.yml       # Local PostgreSQL
├── requirements.txt         # Dependencies
└── Procfile                 # Heroku config
```

## Environment Variables

See `.env.example` for all required variables.

## License

MIT

## Author

Josh - Skincare & Self-Care Content Creator
