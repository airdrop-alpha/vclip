# 🎬 VClip

**Automatic VTuber clip & highlight editor — powered by AI**

VClip watches VTuber streams and VODs, detects the best moments using AI-powered speech analysis, and automatically generates ready-to-upload highlight clips. No manual editing required.

---

![VClip Screenshot](docs/screenshot.png)
*↑ Screenshot placeholder — replace with actual UI screenshot*

## ✨ Features

- 🎙️ **AI Speech Analysis** — Whisper-powered transcription detects hype moments, funny quotes, and emotional peaks
- 📺 **YouTube / Twitch Support** — Paste a VOD URL and let VClip do the rest
- ✂️ **Smart Clip Extraction** — Automatically trims clips with context-aware boundaries
- 🔥 **Highlight Scoring** — Ranks moments by energy, chat activity, and speech patterns
- 📊 **Real-time Dashboard** — Monitor processing jobs, preview clips, and manage your library
- 🎨 **Clip Editor** — Fine-tune start/end points, add subtitles, adjust timing
- 📤 **Export Ready** — Download clips in multiple formats optimized for YouTube Shorts, TikTok, Twitter
- 🐳 **One-Command Setup** — Docker Compose gets you running in minutes
- 🔄 **Background Processing** — Queue multiple VODs and process them concurrently
- 🌐 **REST API** — Fully documented API for integration with bots and automation

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/your-username/vclip.git
cd vclip

# Configure environment
cp .env.example .env

# Start all services
docker compose up -d

# Open the dashboard
open http://localhost:3000
```

### Manual Setup

```bash
# Run the setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Start the backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# In another terminal, start the frontend
cd frontend
npm run dev
```

## 📡 API Documentation

Base URL: `http://localhost:8000`

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Create a new clip extraction job |
| `GET` | `/api/jobs` | List all jobs (with pagination) |
| `GET` | `/api/jobs/{job_id}` | Get job status and details |
| `DELETE` | `/api/jobs/{job_id}` | Cancel / delete a job |

### Clips

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/clips` | List all generated clips |
| `GET` | `/api/clips/{clip_id}` | Get clip metadata |
| `GET` | `/api/clips/{clip_id}/download` | Download clip file |
| `PUT` | `/api/clips/{clip_id}` | Update clip metadata (title, tags) |
| `DELETE` | `/api/clips/{clip_id}` | Delete a clip |

### Transcription

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/jobs/{job_id}/transcript` | Get full transcript with timestamps |
| `GET` | `/api/jobs/{job_id}/highlights` | Get detected highlight moments |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Get current configuration |

Interactive docs available at `http://localhost:8000/docs` (Swagger UI).

## ⚙️ Configuration

Copy `.env.example` to `.env` and customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `large-v3` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`) |
| `WHISPER_DEVICE` | `auto` | Device for inference (`auto`, `cpu`, `cuda`, `mps`) |
| `MAX_CONCURRENT_JOBS` | `2` | Maximum parallel processing jobs |
| `CLIPS_DIR` | `./clips` | Directory for processed clip files |
| `DATABASE_URL` | `sqlite:///./vclip.db` | Database connection string |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL for the frontend |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection for job queue |

### Whisper Model Selection

| Model | VRAM | Speed | Accuracy | Recommended For |
|-------|------|-------|----------|-----------------|
| `tiny` | ~1 GB | ⚡⚡⚡⚡ | ⭐ | Testing / low-resource |
| `base` | ~1 GB | ⚡⚡⚡ | ⭐⭐ | Quick previews |
| `small` | ~2 GB | ⚡⚡ | ⭐⭐⭐ | Balanced |
| `medium` | ~5 GB | ⚡ | ⭐⭐⭐⭐ | Good accuracy |
| `large-v3` | ~10 GB | 🐢 | ⭐⭐⭐⭐⭐ | Best accuracy (default) |

## 🏗️ Tech Stack

**Backend:**
- Python 3.12 + FastAPI
- OpenAI Whisper (speech-to-text)
- FFmpeg (video processing)
- yt-dlp (video download)
- SQLite / SQLAlchemy (database)
- Redis + Celery (job queue)

**Frontend:**
- Next.js 15 (React 19)
- TypeScript
- Tailwind CSS
- Shadcn/ui components

**Infrastructure:**
- Docker + Docker Compose
- Redis 7

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser :3000                       │
│                    Next.js Frontend                       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  FastAPI Backend :8000                    │
│                                                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────────┐  │
│  │ REST API │  │ Job Queue │  │  Processing Pipeline │  │
│  │          │  │  (Redis)  │──│                      │  │
│  │ /api/*   │  │           │  │  yt-dlp → Whisper    │  │
│  │          │  │           │  │    → Analysis         │  │
│  │          │  │           │  │      → FFmpeg clip    │  │
│  └──────────┘  └───────────┘  └──────────────────────┘  │
│        │                              │                  │
│        ▼                              ▼                  │
│  ┌──────────┐                ┌────────────────┐         │
│  │ SQLite   │                │ /clips (volume) │         │
│  │ Database │                │ Processed files │         │
│  └──────────┘                └────────────────┘         │
└──────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  Redis :6379     │
│  Job Queue       │
│  Result Cache    │
└──────────────────┘
```

## 🧑‍💻 Development

```bash
# Use the Makefile for convenience
make dev        # Start backend + frontend in dev mode
make backend    # Start backend only
make frontend   # Start frontend only
make docker     # Start with Docker Compose
make test       # Run all tests
make clean      # Clean temp files and caches
```

### Project Structure

```
vclip/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry
│   │   ├── api/             # Route handlers
│   │   ├── core/            # Config, dependencies
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   │       ├── downloader.py    # yt-dlp wrapper
│   │       ├── transcriber.py   # Whisper integration
│   │       ├── analyzer.py      # Highlight detection
│   │       └── clipper.py       # FFmpeg clip extraction
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js app router
│   │   ├── components/      # React components
│   │   └── lib/             # Utilities, API client
│   ├── package.json
│   └── Dockerfile
├── scripts/
│   └── setup.sh             # Local dev setup
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feat/my-feature`
3. **Commit** your changes: `git commit -m 'feat: add my feature'`
4. **Push** to the branch: `git push origin feat/my-feature`
5. **Open** a Pull Request

### Guidelines

- Follow the existing code style
- Add tests for new features
- Update documentation as needed
- Use [Conventional Commits](https://www.conventionalcommits.org/)

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ⚡ by the VClip team
</p>
