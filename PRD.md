# VClip — VTuber Automatic Clip/Highlight Editor
## Product Requirements Document (PRD)

**Version:** 1.0  
**Date:** 2026-03-22  
**Author:** Alpha (AI Agent)  
**Status:** Research & Planning Complete — Ready for Development

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Market Research](#2-market-research)
3. [User Persona Research](#3-user-persona-research)
4. [Technical Research](#4-technical-research)
5. [Feature Specification](#5-feature-specification)
6. [Technical Architecture](#6-technical-architecture)
7. [Business Model](#7-business-model)
8. [Go-to-Market Strategy](#8-go-to-market-strategy)
9. [Development Roadmap](#9-development-roadmap)
10. [Risks & Mitigations](#10-risks--mitigations)

---

## 1. Executive Summary

### Problem
VTuber streams run 2–8 hours. Clippers (切片師) manually watch entire VODs, identify highlight moments, clip them, add subtitles/effects, and re-upload — a process taking **3–6 hours per stream**. With 60,000+ active VTubers streaming daily, there's massive unclipped content that never reaches short-form audiences.

### Solution
**VClip** is an AI-powered clipping platform purpose-built for VTuber content. It automatically detects highlight moments from livestream VODs using multimodal analysis (speech, chat/danmaku, audio energy, visual cues), extracts clips, generates multi-language subtitles, and exports in platform-optimized formats (YouTube Shorts, TikTok, Bilibili).

### Key Differentiators vs. Generic Clip Tools
| Feature | OpusClip / Vizard | VClip |
|---------|-------------------|-------|
| VTuber avatar-aware tracking | ❌ Face-based | ✅ Live2D/3D model tracking |
| Chat/danmaku spike analysis | ❌ | ✅ Core signal |
| CJK subtitle generation | Basic | ✅ Native JP/CN/EN with speaker labels |
| Bilibili support | ❌ | ✅ Native |
| Stream length support | 1–3 hr max | ✅ Up to 8 hours |
| VTuber-specific templates | ❌ | ✅ Anime-style, vertical for TikTok |
| Clipper workflow integration | ❌ Generic | ✅ Batch, approval queue, channel management |

### Why Now
- **VStream shut down (April 2024)** — validated market demand but also a cautionary tale about unit economics
- **AI tooling matured**: Whisper turbo (8x faster), faster-whisper (4x faster than Whisper), pyannote speaker diarization, Chapter-Llama (CVPR 2025)
- **Existing tools don't serve this niche**: OpusClip (16M+ users) focuses on podcasts/talking-head; Eklipse focuses on gaming/Twitch with no VTuber-specific features
- **VTuber market growing**: $1.5B+ market by 2028 (projected), 60,000+ active VTubers

---

## 2. Market Research

### 2.1 VTuber Ecosystem Overview

| Metric | Estimate | Source |
|--------|----------|--------|
| Active VTubers globally | 60,000+ | UserLocal JP DB tracks top 20,000+; many indie untracked |
| VTubers with >100K subs | ~1,500 | UserLocal rankings |
| Top VTuber subscribers | 4.32M (Gawr Gura) | UserLocal JP (March 2026) |
| Major agencies | Hololive, Nijisanji, VShojo, WACTOR, Neo-Porte, Brave Group | — |
| Primary platforms | YouTube, Twitch, Bilibili, Niconico | — |
| Avg. stream duration | 2–6 hours (some up to 12hr endurance streams) | Community observation |
| Avg. clips per popular stream | 5–20 highlight moments | Clipper community estimates |
| Clipper channels (EN) | 2,000+ listed on community spreadsheet | r/VirtualYoutubers wiki |
| Clipper channels (JP/CN) | 10,000+ (Bilibili alone has thousands) | Bilibili ecosystem |
| VTuber market size (2024) | ~$800M | Industry reports extrapolation |
| Projected market (2028) | $1.5B–$2B | CAGR ~15–20% |

### 2.2 Competitive Landscape

#### Tier 1: General AI Clip Tools (No VTuber Focus)

| Tool | Users | Price | Strengths | Weaknesses for VTubers |
|------|-------|-------|-----------|----------------------|
| **OpusClip** | 16M+ | Free / $15 / $29 / Custom | ClipAnything model works on any genre; auto reframe; brand templates; virality scoring; team workspace; Zapier integration | No chat analysis; no CJK subtitle quality; no Bilibili; max video 10–30GB; designed for podcasts & talking head |
| **Eklipse** | ~1M | Free (720p, 15 clips) / Premium | Gaming-focused; supports 1000+ games; Twitch/Kick native | No VTuber-specific detection; no Bilibili; limited language support; 8hr max on premium |
| **Vizard.ai** | ~500K | Subscription | AI editing and clipping | Generic; no streaming platform integration |
| **Kapwing** | ~10M | Freemium | Full editor + AI clip creator | Too generic; no highlight detection from streams |
| **Munch** | Shut down | — | Was AI repurposing tool | Domain for sale — another failed competitor |

#### Tier 2: Stream-Specific / Open Source

| Tool | Type | Strengths | Weaknesses |
|------|------|-----------|------------|
| **AutoClipper** (GitHub) | Open source | FastAPI + Celery; YouTube audience retention + Twitch chat spikes; Whisper subtitles; auto YouTube upload | No VTuber features; no CJK; no Bilibili; early stage |
| **Twitch Highlight Detection** (GitHub, 黃允竹) | Academic OSS | Multi-modal (ASR + chat + visual); LLM-based (Chapter-Llama); supports 6–8hr streams; Llama 3.2 fine-tuned; F1=0.86 | Research project, not productized; no export pipeline; no subtitle overlay |
| **VStream** | Shut down (Apr 2024) | VTuber-native streaming platform | Ran out of money; couldn't raise funds — cautionary on VTuber platform economics |

#### Tier 3: Manual / Semi-Auto Workflows

| Tool | Usage | Notes |
|------|-------|-------|
| **DaVinci Resolve / Premiere Pro** | Professional clippers | Full control but 3–6 hours per stream |
| **yt-dlp + ffmpeg** | Technical clippers | Download + manual clip extraction |
| **Whisper CLI + auto-subtitle** | DIY subtitles | Open source, works but no integration |
| **Bilibili 自動字幕** | CN clippers | Built-in but basic |

### 2.3 Market Gaps Identified

1. **No VTuber-specific AI clipper exists** — all tools are generic
2. **Chat/danmaku analysis is underutilized** — the #1 signal for VTuber highlights
3. **CJK language support is afterthought** in Western tools
4. **Bilibili is completely ignored** by all English-market tools
5. **Long-form stream handling (>3hr) is poorly supported** by most tools
6. **Clipper team collaboration** doesn't exist — clippers work solo with primitive tooling
7. **Vertical (Shorts/TikTok) reformatting** for anime avatars is unsolved — face tracking fails on Live2D

---

## 3. User Persona Research

### 3.1 Primary Personas

#### Persona A: The Dedicated Clipper (切片師)
- **Who:** Fan-clippers who translate/subtitle VTuber content
- **Count:** ~12,000+ active globally (JP/EN/CN)
- **Motivation:** Community recognition, YouTube ad revenue, love for the VTuber
- **Current workflow:**
  1. Watch full 3–6 hour stream → 3–6 hours
  2. Identify 5–15 highlight moments → notes with timestamps
  3. Download VOD with yt-dlp → 15–30 min
  4. Clip segments in Premiere/DaVinci → 1–2 hours
  5. Translate & add subtitles → 1–3 hours (the biggest bottleneck)
  6. Add effects/thumbnails → 30 min–1 hr
  7. Upload to YouTube/Bilibili → 15 min
  - **Total: 6–12 hours per stream clip set**
- **Pain points:**
  - Watching entire streams is exhausting
  - Subtitle timing is tedious manual work
  - Translation quality needs human touch but AI can draft
  - Uploading to multiple platforms is repetitive
  - No way to know which moments will go viral
- **Willingness to pay:** $10–30/month (many are hobby clippers, some earn $200–2000/month from clips)

#### Persona B: The VTuber Creator
- **Who:** Independent VTubers who want to clip their own streams
- **Count:** ~60,000+ active
- **Motivation:** Growing channel, repurposing content for Shorts/TikTok/Reels
- **Current workflow:** Either don't clip at all, or spend 1–2 hours manually
- **Pain points:**
  - No time to clip after long streams
  - Don't have editing skills
  - Want clips same day for algorithm boost
  - Need vertical format but avatar tracking is hard
- **Willingness to pay:** $5–15/month (indie) to $30–100/month (agency-managed)

#### Persona C: VTuber Agency Manager
- **Who:** Staff at Hololive, Nijisanji, VShojo, etc. who manage content pipeline
- **Count:** ~50–100 agencies, 5–20 staff each
- **Motivation:** Maximize content output, grow talent channels, monetize clips
- **Current workflow:** Hire clippers / in-house team; manual process
- **Pain points:**
  - Can't scale — each talent streams daily
  - Quality control across clip channels
  - Multi-language distribution (JP→EN→CN→KR)
  - Analytics on what clips perform well
- **Willingness to pay:** $100–500/month per seat, enterprise

### 3.2 Platform Distribution

| Platform | Primary Users | Content Type | Priority |
|----------|--------------|--------------|----------|
| YouTube | EN/JP VTubers + Clippers | Horizontal + Shorts | P0 (MVP) |
| Bilibili | CN VTubers + Clippers | Horizontal + Danmaku | P1 (V1) |
| Twitch | EN VTubers (gaming) | VODs | P1 (V1) |
| TikTok | All regions, clips | Vertical shorts | P0 (Export format) |
| Niconico | JP VTubers | JP-specific | P2 (V2) |

### 3.3 Language Priority

| Language | Importance | Reason |
|----------|-----------|--------|
| Japanese | ⭐⭐⭐⭐⭐ | Largest VTuber market; Hololive/Nijisanji are JP |
| English | ⭐⭐⭐⭐⭐ | Second largest; HoloEN, VShojo, translation market |
| Chinese (Mandarin) | ⭐⭐⭐⭐ | Bilibili ecosystem; huge clipper community |
| Korean | ⭐⭐⭐ | Growing VTuber scene |
| Indonesian | ⭐⭐⭐ | HoloID is very popular |
| Spanish | ⭐⭐ | Growing EN-ES translation demand |

---

## 4. Technical Research

### 4.1 AI Pipeline Components

#### Speech-to-Text (STT)

| Model | Speed | Accuracy | JP/CN | VRAM | License | Recommendation |
|-------|-------|----------|-------|------|---------|---------------|
| **Whisper large-v3** | 1x baseline | Best | ✅ Excellent | 10GB | MIT | Production (cloud) |
| **Whisper turbo** | 8x | Very good (EN) | ⚠️ No translate | 6GB | MIT | EN-only fast path |
| **faster-whisper** (CTranslate2) | 4x whisper, batch=8 → 17s/13min | Same as whisper | ✅ Same | 4.5–6GB (fp16) | MIT | **Primary choice** |
| **faster-whisper int8** | Similar, less VRAM | Slight loss | ✅ | 2.9GB | MIT | Budget/CPU fallback |
| **Whisper.cpp** | 2x whisper | Same | ✅ | 4GB | MIT | Edge/desktop option |

**Recommendation:** **faster-whisper** with large-v3 model as primary engine. Batch processing mode for throughput. Int8 quantization for cost optimization.

#### Speaker Diarization

| Model | DER | Speed | License | Cost |
|-------|-----|-------|---------|------|
| **pyannote community-1** | 11.7–46.8% (dataset-dependent) | 31s/hr audio (H100) | Open (HuggingFace) | Free |
| **pyannote precision-2** | 7.4–39.0% | 14s/hr audio (H100) | Premium API | $0.10+/hr |
| **NeMo MSDD** | Competitive | Fast | Apache 2.0 | Free |

**Recommendation:** **pyannote community-1** for MVP (free, good enough). Upgrade to precision-2 for enterprise tier.

#### Highlight Detection

| Approach | Description | Accuracy | Complexity |
|----------|-------------|----------|------------|
| **Chat/Danmaku spike detection** | Sliding window over chat message rate; z-score for anomalies | High for VTuber content | Low |
| **Audio energy peaks** | RMS/dB spikes = laughter, shouting, excitement | Medium-High | Low |
| **LLM-based (Chapter-Llama)** | Feed ASR + chat to LLM, ask for highlights | F1=0.86 (fine-tuned) | High |
| **Keyword triggers** | Detect specific words/phrases (e.g., "草", "wwww", "kusa", clip-worthy exclamations) | Medium | Low |
| **Audience retention data** | YouTube's retention graph as signal | High | Medium (API access) |
| **Composite scoring** | Weighted combination of all above | Highest | Medium |

**Recommendation:** MVP uses **chat spike + audio energy + keyword triggers** (low complexity, high accuracy for VTuber content). V1 adds LLM-based scoring for refined selection.

#### VTuber-Specific Visual Processing

| Challenge | Solution | Tool |
|-----------|----------|------|
| Live2D avatar reframing | Track avatar bounding box; not face detection | Custom CV model or template-based |
| 3D model tracking | Track model center of mass | MediaPipe pose estimation (limited) |
| Screen layout detection | Detect game screen vs. avatar vs. overlay | YOLO-based layout classifier |
| Reaction frames | Detect when avatar has exaggerated expression | Live2D parameter analysis (if accessible) |

**Key insight:** Traditional face tracking (OpusClip's approach) **fails on anime avatars**. VClip needs a custom avatar detection model or region-of-interest approach.

### 4.2 Open Source Foundation

| Component | Repository | Stars | Maturity | We Use For |
|-----------|-----------|-------|----------|-----------|
| faster-whisper | SYSTRAN/faster-whisper | 13K+ | Production | Core STT engine |
| Whisper | openai/whisper | 74K+ | Production | Reference model |
| pyannote-audio | pyannote/pyannote-audio | 6K+ | Production | Speaker diarization |
| auto-subtitle | m1guelpf/auto-subtitle | 4K+ | Stable | Subtitle overlay reference |
| Chapter-Llama | lucas-ventura/chapter-llama | New (CVPR 2025) | Research | Highlight detection backbone |
| autoclipper | VadlapatiKarthik/autoclipper | New | Early | Reference architecture (FastAPI + Celery) |
| Twitch-Highlight-Detection | YunZhuHuang327 | New | Research | Multi-modal fusion reference |
| FFmpeg | ffmpeg.org | — | Mature | Video processing core |
| yt-dlp | yt-dlp/yt-dlp | 90K+ | Production | Video downloading |

### 4.3 VTuber-Specific Technical Challenges

| Challenge | Impact | Proposed Solution |
|-----------|--------|-------------------|
| **Anime avatar ≠ real face** | Face tracking fails; reframing broken | Custom avatar region detector; template zones |
| **Multi-language streams** | JP VTuber speaks JP + some EN → mixed transcription | Whisper language detection per segment; multi-lang output |
| **4–8 hour VODs** | GPU memory; processing time; cost | Sliding window processing (like Chapter-Llama); chunked pipeline |
| **Chat spam vs. real spikes** | Bot messages, repeated emotes inflate chat rate | Chat quality filter: unique users/window, weighted by subscriber status |
| **Bilibili danmaku format** | Different from Twitch/YouTube chat | Custom parser for Bilibili's protobuf-based danmaku API |
| **Copyright music in streams** | Auto-detected and blocked on YouTube | Audio segment classification; auto-mute or skip copyrighted segments |
| **Stream overlays/alerts** | Donation alerts, subscriber notifications on screen | Overlay detection model; either include or crop around |

---

## 5. Feature Specification

### 5.1 MVP (4-Week Sprint)

**Goal:** Process a YouTube VOD → detect highlights → export clips with subtitles

| Feature | Description | Priority |
|---------|-------------|----------|
| **YouTube VOD import** | Paste URL → yt-dlp download + audio extraction | P0 |
| **STT engine** | faster-whisper large-v3 → timestamped transcript (JP/EN/CN) | P0 |
| **Chat data ingestion** | YouTube live chat replay parsing → timestamped messages | P0 |
| **Highlight detection v1** | Chat spike detection + audio energy peaks + keyword triggers → scored highlight list | P0 |
| **Clip extraction** | FFmpeg-based clip cutting at detected timestamps with ±buffer | P0 |
| **Auto-subtitles** | Burn subtitles onto clips (word-level timing from Whisper) | P0 |
| **Basic web UI** | Upload/paste → see detected highlights → select & export | P0 |
| **Aspect ratio conversion** | Export as 16:9 (YouTube) or 9:16 (Shorts/TikTok) with center crop | P0 |
| **Batch export** | Export all selected clips at once as zip | P0 |

**Non-goals for MVP:**
- No Twitch/Bilibili support
- No real-time processing
- No user accounts / payment
- No advanced editing (templates, effects)

### 5.2 V1 (Weeks 5–10)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Multi-platform input** | Twitch VODs + Bilibili videos | P1 |
| **Bilibili danmaku parser** | Parse Bilibili's danmaku for highlight detection | P1 |
| **Advanced highlight scoring** | LLM-based scoring (GPT-4o-mini or local Llama) combining all signals | P1 |
| **Speaker diarization** | Label who's speaking (pyannote) for multi-person collabs | P1 |
| **Template engine** | Pre-designed VTuber clip templates: anime subtitle style, colored speaker labels, progress bar | P1 |
| **Smart avatar reframe** | Detect avatar region → intelligent crop for vertical format | P1 |
| **Multi-language subtitles** | Generate JP→EN, JP→CN, EN→JP subtitle tracks | P1 |
| **User accounts** | Auth, project management, clip history | P1 |
| **Freemium model** | Free tier (3 clips/day, watermark) + paid tiers | P1 |
| **Direct upload** | Publish clips directly to YouTube / TikTok | P2 |
| **Thumbnail generator** | Auto-generate thumbnails from highlight frames + text overlay | P2 |
| **Virality prediction** | Score clips by predicted performance based on content features | P2 |

### 5.3 V2 (Weeks 11–20)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Real-time stream monitoring** | Connect to live stream → detect highlights in near-real-time → queue clips | P1 |
| **Clipper team workspace** | Multiple clippers collaborate on same VTuber's content; assignment, review, approval | P1 |
| **Agency dashboard** | Manage multiple VTuber channels; analytics across all talents | P1 |
| **Analytics engine** | Track clip performance across platforms; learn what works | P2 |
| **Custom keyword dictionaries** | User-defined trigger words/phrases per VTuber | P2 |
| **Clip scheduling** | Schedule clip uploads for optimal posting times | P2 |
| **Watermark/branding** | Custom watermarks, intros, outros per channel | P2 |
| **API access** | REST API for programmatic clip generation (x402 monetizable) | P2 |
| **Mobile app** | iOS/Android for quick clip review and approval | P3 |
| **Plugin system** | Custom post-processing plugins (effects, filters, memes) | P3 |

---

## 6. Technical Architecture

### 6.1 System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        Frontend                          │
│              Next.js 14+ / React / Tailwind              │
│         (Web App — responsive, no desktop app MVP)       │
└─────────────┬──────────────────────────────┬─────────────┘
              │ REST/WebSocket                │
              ▼                               ▼
┌─────────────────────────┐    ┌──────────────────────────┐
│      API Gateway         │    │   WebSocket Server        │
│      (FastAPI)           │    │   (Progress/Status)       │
└─────────────┬────────────┘    └──────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│                   Task Queue (Redis + Celery/BullMQ)     │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Download  │ │   STT    │ │ Highlight│ │  Export   │   │
│  │ Worker    │ │ Worker   │ │ Scorer   │ │ Worker    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│                  AI Processing Pipeline                   │
│                                                          │
│  Stage 1: Download & Ingest                              │
│  ├── yt-dlp (YouTube/Twitch/Bilibili VOD download)       │
│  ├── Audio extraction (ffmpeg → WAV 16kHz)               │
│  └── Chat/danmaku data fetch                             │
│                                                          │
│  Stage 2: Analysis                                       │
│  ├── faster-whisper → timestamped transcript             │
│  ├── pyannote → speaker diarization                      │
│  ├── Audio energy analysis (librosa RMS/spectral)        │
│  ├── Chat spike detector (sliding window z-score)        │
│  └── Keyword trigger scanner                             │
│                                                          │
│  Stage 3: Highlight Scoring                              │
│  ├── Multi-signal fusion → composite score per segment   │
│  ├── (V1) LLM re-ranking of top candidates              │
│  └── Cluster & merge overlapping highlights              │
│                                                          │
│  Stage 4: Clip Generation                                │
│  ├── FFmpeg segment extraction                           │
│  ├── Subtitle rendering (ASS/SRT → burned-in)           │
│  ├── Aspect ratio conversion + avatar-aware crop         │
│  └── Template overlay (intro/outro, branding)            │
│                                                          │
│  Stage 5: Export & Delivery                              │
│  ├── MP4 encoding (H.264/H.265, optimized per platform) │
│  ├── Thumbnail generation                                │
│  └── Upload to platforms (YouTube API, etc.)             │
└─────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│                     Storage                              │
│                                                          │
│  ├── Object Storage (S3/R2) — VODs, clips, thumbnails   │
│  ├── PostgreSQL — users, projects, metadata              │
│  ├── Redis — task queue, cache, real-time state          │
│  └── (V2) ClickHouse — analytics data                   │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | Next.js 14+ (App Router), React 18, Tailwind CSS, shadcn/ui | SSR for SEO; great DX; familiar to most developers |
| **Backend API** | FastAPI (Python) | Python ecosystem for ML; async; great for AI pipelines |
| **Task Queue** | Celery + Redis (or BullMQ if Node.js preferred) | Proven for long-running tasks; distributed workers |
| **STT** | faster-whisper (CTranslate2) | 4x faster than Whisper, same accuracy, less VRAM |
| **Diarization** | pyannote-audio community-1 | Free, state-of-the-art, well-maintained |
| **Video Processing** | FFmpeg (via ffmpeg-python) | Industry standard; handles everything |
| **Download** | yt-dlp | Best multi-platform downloader |
| **LLM (V1)** | GPT-4o-mini API or Groq (Llama 3.2) | Fast, cheap, good for highlight scoring |
| **Database** | PostgreSQL 16 | Reliable, JSON support, full-text search |
| **Cache/Queue** | Redis 7 | Queue backend + session cache + real-time |
| **Object Storage** | Cloudflare R2 or AWS S3 | R2 is cheaper (no egress fees) |
| **Hosting** | Railway / Fly.io (API) + Vercel (frontend) | Easy deployment; scale as needed |
| **GPU Workers** | Modal.com or RunPod | Serverless GPU for STT/diarization; pay-per-use |
| **Monitoring** | Sentry + Posthog | Error tracking + product analytics |

### 6.3 GPU Processing Cost Estimation

| Operation | Model | Time (per 1hr audio) | GPU Required | Cost (cloud) |
|-----------|-------|---------------------|--------------|-------------|
| STT | faster-whisper large-v3 (batch) | ~2 min | A10G / T4 | $0.02–0.04 |
| Diarization | pyannote community-1 | ~30 sec | T4 | $0.01 |
| Audio analysis | librosa | ~10 sec | CPU | $0.001 |
| LLM scoring (V1) | GPT-4o-mini | ~30 sec | API | $0.01–0.03 |
| FFmpeg clip export | — | ~1 min per clip | CPU | $0.005/clip |
| Subtitle burn-in | FFmpeg ASS | ~30 sec per clip | CPU | $0.003/clip |

**Total cost per 1-hour stream processed: ~$0.05–0.10**  
**Total cost per 4-hour stream: ~$0.20–0.40**  
**Cost per exported clip (avg 60 sec): ~$0.01–0.02**

### 6.4 API Design (x402 Monetizable)

```yaml
# Core Endpoints

POST /api/v1/jobs
  # Submit a new clipping job
  body:
    url: string          # YouTube/Twitch/Bilibili URL
    options:
      languages: ["ja", "en"]
      max_clips: 10
      min_score: 0.7
      aspect_ratios: ["16:9", "9:16"]
      subtitle_style: "anime" | "modern" | "minimal"
  response:
    job_id: string
    estimated_time: number  # seconds

GET /api/v1/jobs/{job_id}
  # Get job status + results
  response:
    status: "processing" | "analyzing" | "generating" | "complete"
    progress: number  # 0-100
    highlights: [
      {
        id: string
        start_time: number
        end_time: number
        score: number
        type: "funny" | "exciting" | "emotional" | "skill"
        description: string
        transcript_snippet: string
        chat_intensity: number
      }
    ]
    clips: [
      {
        id: string
        highlight_id: string
        aspect_ratio: "16:9" | "9:16"
        download_url: string
        thumbnail_url: string
        duration: number
        subtitles: { "ja": string, "en": string }
      }
    ]

POST /api/v1/jobs/{job_id}/clips/{clip_id}/regenerate
  # Re-generate a clip with different settings

GET /api/v1/jobs/{job_id}/transcript
  # Full timestamped transcript

# x402 Payment Headers
x-402-price: 0.05        # $0.05 per clip via x402
x-402-payment-methods: ["base-usdc"]
```

---

## 7. Business Model

### 7.1 Pricing Tiers

| Tier | Price | Included | Target |
|------|-------|----------|--------|
| **Free** | $0 | 3 clips/day, 720p, watermark, 1hr max VOD | Trial users, hobby clippers |
| **Clipper** | $12/mo ($9/mo annual) | 50 clips/day, 1080p, no watermark, 8hr VODs, 3 languages, batch export | Active clippers |
| **Pro** | $29/mo ($22/mo annual) | Unlimited clips, 4K, all languages, direct upload, team of 3, templates, priority processing | Serious clippers, indie VTubers |
| **Agency** | $99/mo per seat ($79/mo annual) | Everything in Pro + agency dashboard, 10+ VTuber channels, analytics, API access, custom branding, SLA | VTuber agencies |
| **API / x402** | $0.05/clip | Pay-per-clip via API or x402 micropayments | Developers, automation |

### 7.2 Pricing Comparison

| Tool | Free Tier | Starter | Pro | Enterprise |
|------|-----------|---------|-----|-----------|
| **OpusClip** | $0 (watermark, 3-day storage) | $15/mo | $29/mo | Custom |
| **Eklipse** | $0 (720p, 15 clips/stream) | ~$10/mo | ~$25/mo | — |
| **Vizard** | Limited | $19/mo | $49/mo | Custom |
| **VClip (Ours)** | $0 (3 clips/day) | $12/mo | $29/mo | $99/mo/seat |

**Positioning:** Slightly cheaper than OpusClip at entry, similar Pro pricing, but **uniquely valuable** for VTuber content where competitors fail.

### 7.3 Revenue Projections

**Assumptions:**
- Launch in JP/EN VTuber communities
- 6-month ramp to steady state
- Average 15% free→paid conversion (niche community, higher than average)

| Scenario | Month 6 Users | Paid Users | MRR | ARR |
|----------|--------------|------------|-----|-----|
| **Conservative** | 2,000 | 300 | $5,400 | $64,800 |
| **Moderate** | 8,000 | 1,200 | $21,600 | $259,200 |
| **Optimistic** | 20,000 | 3,000 | $54,000 | $648,000 |

**Unit economics:**
- Average revenue per paid user: ~$18/mo (blended)
- Cost per paid user: ~$3/mo (compute, storage, bandwidth)
- Gross margin: **~83%**
- CAC target: < $20 (organic community growth)
- LTV (12-month): ~$216
- LTV/CAC ratio target: > 10x

### 7.4 x402 Micropayment Integration

VClip's API can be monetized via x402 protocol:

```
Request: POST /api/v1/clips/generate
Header: x-402-price: 0.05 USDC
```

- Each API clip generation costs $0.05 USDC
- Agent-to-agent payments: other AI agents can use VClip as a service
- Revenue stream independent of subscription model
- Deployed on Base network (low gas, fast settlement)
- Aligns with Ted's existing x402 infrastructure (x402-token-scan, x402-wallet-risk workers)

---

## 8. Go-to-Market Strategy

### 8.1 Launch Phases

#### Phase 0: Closed Alpha (Week 5)
- **Who:** 10–20 hand-picked clippers from Hololive/Nijisanji fan communities
- **Where:** Direct outreach on Discord, Twitter
- **Goal:** Validate core pipeline works; collect feedback on highlight accuracy

#### Phase 1: Open Beta (Week 8)
- **Who:** r/VirtualYoutubers, VTuber Discord servers, #VTuber Twitter
- **Channels:**
  - Reddit post on r/VirtualYoutubers (600K+ members)
  - Twitter/X threads with demo clips (tag VTuber community accounts)
  - Bilibili 专栏 article (Chinese VTuber community)
  - VTuber fan Discord servers (Hololive, Nijisanji, VShojo)
- **Offer:** Free Pro tier for 30 days for all beta users
- **Goal:** 1,000 signups in first week

#### Phase 2: Public Launch (Week 12)
- **Product Hunt launch**
- **Hacker News "Show HN"**
- **YouTube demo video** — show side-by-side: manual clipping (6 hours) vs. VClip (10 minutes)
- **Activate freemium model**

### 8.2 Community-First Growth

| Channel | Strategy | Expected Impact |
|---------|----------|----------------|
| **Twitter/X #VTuber** | Daily clip showcase; VTuber fan accounts; tag clippers | High (core community lives here) |
| **Reddit r/VirtualYoutubers** | Useful posts, not spam; clipper AMA; "VTuber of the week" clips | High (600K+ members) |
| **Discord** | Bot integration that auto-clips streams | Very High (where clippers coordinate) |
| **Bilibili 专栏** | Chinese-language content; 切片教程 | High (CN clipper market) |
| **YouTube** | Tutorial content; "How to clip faster with AI" | Medium-High |
| **NicoNico** | JP community outreach | Medium |

### 8.3 Partnership Opportunities

| Partner Type | Examples | Value Proposition |
|-------------|---------|-------------------|
| **VTuber agencies** | Hololive, Nijisanji, VShojo, Brave Group | "We help your talent's clips reach more platforms faster" |
| **Clipper translation groups** | HoloTranslations, MukiROSE, Vtube Tengoku | "Cut your translation workflow from 6hr to 1hr" |
| **Streaming platforms** | YouTube, Twitch, Bilibili | API integration; "recommended clipping tool" |
| **VTuber tool creators** | Live2D, VTube Studio, VRoid | Cross-promotion; "complete VTuber toolkit" |
| **AI infra providers** | Modal.com, Replicate | Discounted GPU access in exchange for case study |

### 8.4 Content Marketing

1. **"State of VTuber Clipping" annual report** — data on clip trends, popular formats, growth metrics
2. **Clipper spotlight series** — interview top clippers, feature their workflow improvements
3. **Technical blog** — "How we detect VTuber highlights with AI" (SEO + developer credibility)
4. **VTuber clip compilation** — showcase tool-generated clips to prove quality
5. **Localized content** — JP blog (はてなブログ), CN blog (知乎/B站), EN blog (Medium/own blog)

---

## 9. Development Roadmap

### 9.1 Week-by-Week MVP Timeline

#### Week 1: Foundation
- [ ] Project scaffolding: FastAPI backend, Next.js frontend, Redis, PostgreSQL
- [ ] yt-dlp integration: YouTube URL → download VOD + audio extraction
- [ ] YouTube live chat replay parser (pytchat or custom)
- [ ] Basic web UI: paste URL, show progress

#### Week 2: AI Pipeline Core
- [ ] faster-whisper integration: audio → timestamped transcript
- [ ] Chat spike detector: sliding window (60s window, 10s step) → z-score anomaly detection
- [ ] Audio energy analyzer: librosa RMS → peak detection
- [ ] Keyword trigger system: configurable word list (草, wwww, lol, etc.)
- [ ] Highlight scorer: weighted combination of all signals

#### Week 3: Clip Generation
- [ ] FFmpeg clip extraction: highlight timestamp → video segment with buffer
- [ ] Subtitle rendering: Whisper word-level timing → ASS format → burn-in
- [ ] Aspect ratio conversion: 16:9 → 9:16 center crop
- [ ] Batch export: zip multiple clips
- [ ] Basic subtitle styling (anime-style karaoke look)

#### Week 4: Polish & Deploy
- [ ] Web UI: highlight list with scores, preview player, select/deselect clips
- [ ] Progress tracking via WebSocket
- [ ] Error handling and retry logic
- [ ] Deploy: Vercel (frontend) + Railway (backend) + Modal (GPU workers)
- [ ] Basic monitoring: Sentry + logging
- [ ] Documentation + demo video

### 9.2 V1 Sprint Plan (Weeks 5–10)

| Week | Focus | Deliverables |
|------|-------|-------------|
| 5–6 | Multi-platform + Auth | Twitch VOD support; Bilibili video support; user auth (Clerk/Auth.js); project management |
| 7 | Advanced scoring | LLM-based highlight re-ranking; speaker diarization; improved subtitle quality |
| 8 | Templates + Reframe | VTuber clip templates (3–5 designs); smart avatar reframe for vertical; multi-language subtitle generation |
| 9 | Billing + Upload | Stripe integration; freemium tiers; direct YouTube upload; TikTok export |
| 10 | Beta launch prep | Load testing; documentation; community outreach; feedback collection |

### 9.3 V2 Sprint Plan (Weeks 11–20)

| Week | Focus | Deliverables |
|------|-------|-------------|
| 11–13 | Real-time + Collaboration | Live stream monitoring; near-real-time highlight detection; team workspace |
| 14–16 | Analytics + Agency | Performance tracking; agency dashboard; multi-channel management |
| 17–18 | API + x402 | Public REST API; x402 payment integration; API documentation |
| 19–20 | Mobile + Plugins | Mobile web app (PWA); plugin system for custom effects; community template marketplace |

### 9.4 Team & Resource Requirements

| Phase | Team Size | Roles | Monthly Cost |
|-------|-----------|-------|-------------|
| **MVP (Weeks 1–4)** | 1–2 devs | Full-stack + ML eng (can be same person with AI assist) | $0 (solo) – $8K (contractor) |
| **V1 (Weeks 5–10)** | 2–3 devs | Full-stack, ML eng, frontend | $8K–$15K |
| **V2 (Weeks 11–20)** | 3–5 devs | + DevOps, designer | $15K–$30K |

**Infrastructure costs (MVP):**
| Item | Monthly Cost |
|------|-------------|
| Railway (API server) | $20–50 |
| Vercel (frontend) | $0–20 |
| Modal.com (GPU workers) | $50–200 (depends on usage) |
| Cloudflare R2 (storage) | $10–50 |
| Redis (Upstash) | $10 |
| PostgreSQL (Neon/Supabase) | $0–25 |
| Domain + misc | $10 |
| **Total MVP infra** | **$100–365/mo** |

---

## 10. Risks & Mitigations

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|-----------|
| **VTuber copyright claims on clips** | High | Medium | Respect agency guidelines (Hololive has clip guidelines); build compliance features; allow VTubers to claim/manage clip channels |
| **Highlight detection inaccuracy** | High | Medium | Start with chat-spike (most reliable signal); add human approval step; learn from user corrections |
| **GPU costs exceed revenue** | High | Low | Aggressive quantization (int8); batch processing; serverless GPU (pay per use); cache repeat VODs |
| **VStream-style cash burn** | High | Low | Lean infrastructure; freemium model (not free platform); focus on unit economics from day 1 |
| **Platform API changes** | Medium | Medium | Abstract platform layer; yt-dlp community maintains adapters; fallback to direct download |
| **Low conversion rate** | Medium | Medium | Niche community = higher conversion; free tier generous enough to prove value; agency tier anchors revenue |
| **Competition from OpusClip adding VTuber features** | Medium | Low | First-mover advantage in niche; deep CJK + Bilibili + VTuber expertise; community loyalty |
| **Bilibili access restrictions** | Medium | Medium | Self-host in Asia for Bilibili access; use official Bilibili API where possible |
| **Translation quality for JP/CN** | Medium | High | Use best available models (Whisper large-v3); offer human-in-the-loop editing; don't claim "perfect" translation |
| **Solo developer burnout** | High | High | Use AI coding assistants aggressively (Codex/Claude Code); limit scope to MVP; community contributors |

---

## Appendix A: Highlight Detection Algorithm (MVP)

```python
def detect_highlights(transcript, chat_messages, audio_rms, config):
    """
    Multi-signal highlight detection for VTuber streams.
    
    Signals:
    1. Chat spike: z-score of message rate per window
    2. Audio energy: z-score of RMS energy per window  
    3. Keyword triggers: match against VTuber-specific word list
    
    Returns scored, time-ordered list of highlight segments.
    """
    WINDOW_SIZE = 60  # seconds
    STEP_SIZE = 10    # seconds
    MIN_SCORE = 0.6
    
    # Signal 1: Chat spike detection
    chat_rates = sliding_window_count(chat_messages, WINDOW_SIZE, STEP_SIZE)
    chat_z_scores = z_score_normalize(chat_rates)
    
    # Signal 2: Audio energy peaks
    energy_windows = sliding_window_rms(audio_rms, WINDOW_SIZE, STEP_SIZE)
    energy_z_scores = z_score_normalize(energy_windows)
    
    # Signal 3: Keyword triggers
    keyword_hits = scan_transcript_keywords(
        transcript, 
        keywords=["草", "wwww", "kusa", "lol", "omg", "やばい", "すごい",
                   "えぇ", "うわぁ", "haha", "LETS GO", "no way"],
        window_size=WINDOW_SIZE,
        step_size=STEP_SIZE
    )
    keyword_scores = normalize_0_1(keyword_hits)
    
    # Composite scoring (weighted fusion)
    weights = {
        'chat': 0.45,    # Chat is the strongest signal for VTuber content
        'audio': 0.30,   # Audio energy captures excitement
        'keyword': 0.25  # Keywords catch specific reactions
    }
    
    composite_scores = (
        weights['chat'] * chat_z_scores +
        weights['audio'] * energy_z_scores +
        weights['keyword'] * keyword_scores
    )
    
    # Find peaks above threshold
    highlights = find_peaks(composite_scores, min_score=MIN_SCORE)
    
    # Merge overlapping segments
    highlights = merge_overlapping(highlights, max_gap=30)
    
    # Expand to natural boundaries (sentence boundaries from transcript)
    highlights = snap_to_sentences(highlights, transcript)
    
    return sorted(highlights, key=lambda h: h.score, reverse=True)
```

## Appendix B: VTuber Keyword Dictionary (Seed)

```yaml
# Japanese reactions
ja_keywords:
  excitement: ["草", "くさ", "wwww", "ワロタ", "やばい", "すごい", "まじ", "うそ", "えぇぇ"]
  emotion: ["泣ける", "感動", "かわいい", "尊い", "てぇてぇ"]
  action: ["神プレイ", "ナイス", "うまい", "天才", "さすが"]
  surprise: ["!?", "えぇ", "うわぁ", "なにぃ", "はぁ!?"]

# English reactions  
en_keywords:
  excitement: ["LETS GO", "POG", "no way", "omg", "lol", "lmao", "bruh"]
  emotion: ["crying", "wholesome", "cute", "precious"]
  action: ["clutch", "insane", "cracked", "goated"]
  surprise: ["WHAT", "HOW", "wait what", "no shot"]

# Chinese reactions
zh_keywords:
  excitement: ["草", "哈哈哈", "笑死", "666", "牛逼", "太强了"]
  emotion: ["好可爱", "泪目", "感动", "贴贴"]
  action: ["神操作", "厉害", "太猛了", "秀"]
  surprise: ["卧槽", "我靠", "什么鬼", "不会吧"]

# Universal emotes (Twitch/YouTube)
emotes:
  positive: ["PogChamp", "KEKW", "Pog", "catJAM", "HYPERS", "PepeHands"]
  negative: ["Sadge", "BibleThump", "NotLikeThis"]
  spam_filter: ["7777", "!command"]  # ignore these
```

## Appendix C: Competitive Feature Matrix

| Feature | VClip | OpusClip | Eklipse | Manual (Premiere) |
|---------|-------|----------|---------|-------------------|
| VTuber avatar tracking | ✅ | ❌ | ❌ | Manual |
| Chat/danmaku analysis | ✅ | ❌ | ❌ | N/A |
| YouTube support | ✅ | ✅ | ✅ | N/A |
| Twitch support | ✅ (V1) | ❌ | ✅ | N/A |
| Bilibili support | ✅ (V1) | ❌ | ❌ | N/A |
| Japanese STT | ✅ Native | ⚠️ Basic | ❌ | Manual |
| Chinese STT | ✅ Native | ⚠️ Basic | ❌ | Manual |
| 8hr+ stream support | ✅ | ❌ (3hr max) | ✅ (Premium) | ✅ |
| Speaker diarization | ✅ (V1) | ❌ | ❌ | Manual |
| Vertical reframe | ✅ | ✅ | ✅ | Manual |
| Multi-language subs | ✅ | ⚠️ | ❌ | Manual |
| Team collaboration | ✅ (V2) | ✅ (Business) | ❌ | ❌ |
| API / x402 | ✅ (V2) | ✅ (Business) | ❌ | ❌ |
| Free tier | ✅ | ✅ | ✅ | N/A |
| Anime-style templates | ✅ | ❌ | ❌ | Manual |
| Processing time (4hr stream) | ~15 min | N/A | ~30 min | 6–12 hr |
| Price (Pro) | $29/mo | $29/mo | ~$25/mo | $0 + time |

---

## Summary: Why VClip Will Win

1. **No one is building for VTubers specifically** — every existing tool treats VTuber content as an afterthought
2. **Chat/danmaku is the killer signal** — it's the single most reliable indicator of highlight moments in VTuber streams, and no competitor uses it
3. **CJK-first** — Japanese and Chinese are first-class citizens, not translations of an English product
4. **Bilibili is a blue ocean** — zero competition for automated clipping on the world's largest VTuber platform outside YouTube
5. **The tech is ready** — faster-whisper, pyannote, Chapter-Llama, and LLMs make this possible now at reasonable cost
6. **Unit economics are strong** — $0.05–0.10 to process a full stream, charge $12–99/mo
7. **Community-driven growth** — VTuber fans are passionate, organized, and share tools virally
8. **x402 monetization** — unique agent-to-agent payment model for API access

**Next step:** Start building the MVP. Week 1, Day 1.
