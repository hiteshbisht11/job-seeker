---
title: Job Seeker
emoji: 🔍
colorFrom: indigo
colorTo: violet
sdk: docker
app_port: 7860
pinned: false
short_description: Upload your resume, get personalized live job matches.
---

# Job Seeker

Upload your resume PDF; get back a ranked list of currently-open roles
scored against your skills. Live data, no sign-up, nothing stored.

## Sources

Real-time fetch from public ATS APIs (no keys required):
- **Greenhouse** boards — 31 companies (PhonePe, Stripe, GitLab, Anthropic, Cloudflare, Datadog, Databricks, Mongo, …)
- **Lever** — Spotify
- **Remotive** + **RemoteOK** — remote-job aggregators

Roughly 1,800 currently-open jobs per fetch, filtered to India + worldwide remote.

## Stack

- **Backend**: FastAPI + httpx (async parallel fetch with bounded concurrency)
- **Frontend**: vanilla JS + Tailwind CDN
- **PDF parsing**: pdfminer.six (fallback to pypdf for stylized PDFs)
- **Matching**: regex skill taxonomy → fit score (skill recall, breadth, experience, title)
- **Cache**: 30-min in-memory; pre-warmed at startup as a background task

## Run locally

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8765
```

Open http://localhost:8765.
