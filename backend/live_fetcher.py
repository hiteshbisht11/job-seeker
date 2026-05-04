"""Fetch live job postings from public ATS APIs (no keys, no auth).

Sources
-------
* Greenhouse Boards API   — https://boards-api.greenhouse.io/v1/boards/{token}/jobs
* Lever Postings API      — https://api.lever.co/v0/postings/{company}?mode=json
* Remotive (aggregator)   — https://remotive.com/api/remote-jobs?category=software-dev
* RemoteOK (aggregator)   — https://remoteok.com/api

All sources are public and require no API keys. Each fetcher gracefully returns
[] on network failure so one dead board doesn't take down the whole pipeline.

Results are cached in-memory for 30 minutes.
"""

from __future__ import annotations

import asyncio
import html
import re
import time
from typing import Any

import httpx

# ---- Confirmed-working seed lists (probed at build time) -------------------

GREENHOUSE_BOARDS: list[str] = [
    # Indian / India-presence companies known to use Greenhouse
    "phonepe",
    # Global product companies (many hire remote-India)
    "anthropic", "cloudflare", "datadog", "vercel", "togetherai",
    "discord", "airtable", "coinbase", "databricks", "monzo",
    "figma", "robinhood", "instacart", "samsara", "gitlab",
    "stripe", "brex", "mercury", "chime", "affirm", "sumup",
    "nubank", "gusto", "toast", "postman", "newrelic",
    "elastic", "mongodb", "cockroachlabs", "thoughtworks",
]

LEVER_BOARDS: list[str] = [
    "spotify",
]

# ---- Cache -----------------------------------------------------------------

CACHE_TTL_SEC = 30 * 60
_cache: dict[str, tuple[float, list[dict]]] = {}

# Cap concurrent upstream fetches so we don't starve the event loop on
# tiny shared CPUs (Render free tier ≈ 0.1 CPU). With 34 sources running
# unbounded, health checks time out and Render kills the container.
_FETCH_CONCURRENCY = 4

# ---- Helpers ---------------------------------------------------------------

INDIAN_CITY_TOKENS = [
    "india", "bangalore", "bengaluru", "hyderabad", "mumbai",
    "delhi", "gurgaon", "gurugram", "noida", "pune", "chennai",
    "kolkata", "ahmedabad", "jaipur",
]
REMOTE_TOKENS = ["remote", "anywhere", "worldwide", "global", "distributed"]


def _strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _classify_scope(location: str) -> str | None:
    """Return 'India', 'Worldwide Remote', or None (drop the job)."""
    l = (location or "").lower()
    if any(c in l for c in INDIAN_CITY_TOKENS):
        return "India"
    if any(c in l for c in REMOTE_TOKENS):
        return "Worldwide Remote"
    return None


_EXP_RE = re.compile(r"(\d+)\s*(?:[-–]\s*(\d+))?\s*\+?\s*(?:yrs?|years?)", re.IGNORECASE)


def _extract_experience(text: str) -> str:
    if not text:
        return ""
    m = _EXP_RE.search(text)
    if not m:
        return ""
    lo, hi = m.group(1), m.group(2)
    return f"{lo}-{hi} yrs" if hi else f"{lo}+ yrs"


# ---- Source fetchers -------------------------------------------------------

async def _fetch_greenhouse_one(client: httpx.AsyncClient, token: str) -> list[dict]:
    try:
        r = await client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
            params={"content": "true"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []

    out: list[dict] = []
    for j in data.get("jobs", []):
        loc = j.get("location") or {}
        loc_name = loc.get("name") if isinstance(loc, dict) else str(loc)
        scope = _classify_scope(loc_name or "")
        if not scope:
            continue
        desc = _strip_html(j.get("content", ""))
        out.append(_normalized(
            company=token.replace("-", " ").title(),
            role=j.get("title", "") or "",
            location=loc_name or "",
            scope=scope,
            description=desc,
            url=j.get("absolute_url", ""),
            source="Greenhouse",
        ))
    return out


async def _fetch_lever_one(client: httpx.AsyncClient, company: str) -> list[dict]:
    try:
        r = await client.get(
            f"https://api.lever.co/v0/postings/{company}",
            params={"mode": "json"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []

    out: list[dict] = []
    if not isinstance(data, list):
        return []
    for j in data:
        cats = j.get("categories", {}) or {}
        loc_name = cats.get("location") or ""
        scope = _classify_scope(loc_name)
        if not scope:
            continue
        desc = _strip_html(j.get("descriptionPlain") or j.get("description", ""))
        out.append(_normalized(
            company=company.replace("-", " ").title(),
            role=j.get("text", "") or "",
            location=loc_name,
            scope=scope,
            description=desc,
            url=j.get("hostedUrl", "") or j.get("applyUrl", ""),
            source="Lever",
        ))
    return out


async def _fetch_remotive(client: httpx.AsyncClient) -> list[dict]:
    out: list[dict] = []
    for cat in ("software-dev", "data", "devops"):
        try:
            r = await client.get(
                "https://remotive.com/api/remote-jobs",
                params={"category": cat, "limit": 50},
                timeout=12,
            )
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception:
            continue
        for j in data.get("jobs", []):
            loc_name = j.get("candidate_required_location", "") or "Remote"
            scope = _classify_scope(loc_name)
            if not scope:
                # Default Remotive jobs to Worldwide Remote since they're a remote board
                scope = "Worldwide Remote"
            desc = _strip_html(j.get("description", ""))
            out.append(_normalized(
                company=j.get("company_name", "") or "Unknown",
                role=j.get("title", "") or "",
                location=loc_name,
                scope=scope,
                description=desc,
                url=j.get("url", ""),
                source="Remotive",
                comp_hint=j.get("salary"),
            ))
    return out


async def _fetch_remoteok(client: httpx.AsyncClient) -> list[dict]:
    try:
        r = await client.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Mozilla/5.0 (compatible; job-seeker/1.0)"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []

    if not isinstance(data, list) or len(data) < 2:
        return []
    out: list[dict] = []
    for j in data[1:]:
        if not isinstance(j, dict):
            continue
        loc = j.get("location") or "Remote"
        scope = _classify_scope(loc) or "Worldwide Remote"
        desc = _strip_html(j.get("description", ""))
        tags = " ".join(j.get("tags", []) or []) if isinstance(j.get("tags"), list) else ""
        out.append(_normalized(
            company=j.get("company", "") or "Unknown",
            role=j.get("position", "") or "",
            location=str(loc),
            scope=scope,
            description=f"{tags}\n{desc}",
            url=j.get("url") or j.get("apply_url") or "",
            source="RemoteOK",
        ))
    return out


# ---- Normalizer ------------------------------------------------------------

def _normalized(
    *,
    company: str,
    role: str,
    location: str,
    scope: str,
    description: str,
    url: str,
    source: str,
    comp_hint: Any = None,
) -> dict:
    """Return a dict matching the shape the matcher + frontend expect."""
    snippet = description[:600] + ("…" if len(description) > 600 else "")
    return {
        "company": company.strip() or "Unknown",
        "role": role.strip() or "Untitled role",
        "category": source,
        "location": location.strip() or "Not specified",
        "experience": _extract_experience(description) or "Not specified",
        "key_requirements": snippet,
        "why_fit": "",  # populated by matcher post-scoring
        "primary_link": url,
        "search_link": url,
        "scope": scope,
        "comp_band_inr": str(comp_hint) if comp_hint else None,
        "_raw_text": description,  # full text used for skill detection; stripped before client
    }


# ---- Top-level coordinator -------------------------------------------------

async def fetch_all(force: bool = False) -> list[dict]:
    """Hit every source in parallel and return the union, India/remote-filtered.
    Cached for CACHE_TTL_SEC seconds."""
    now = time.time()
    if not force and "all" in _cache and now - _cache["all"][0] < CACHE_TTL_SEC:
        return _cache["all"][1]

    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)

    async def _bounded(coro):
        async with sem:
            return await coro

    async with httpx.AsyncClient(headers={"User-Agent": "job-seeker/1.0"}) as client:
        tasks: list[asyncio.Future] = []
        for token in GREENHOUSE_BOARDS:
            tasks.append(_bounded(_fetch_greenhouse_one(client, token)))
        for company in LEVER_BOARDS:
            tasks.append(_bounded(_fetch_lever_one(client, company)))
        tasks.append(_bounded(_fetch_remotive(client)))
        tasks.append(_bounded(_fetch_remoteok(client)))
        results = await asyncio.gather(*tasks, return_exceptions=True)

    jobs: list[dict] = []
    for r in results:
        if isinstance(r, list):
            jobs.extend(r)

    # De-dupe on (company, role, location)
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for j in jobs:
        key = (j["company"].lower(), j["role"].lower(), j["location"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)

    _cache["all"] = (now, deduped)
    return deduped


def cache_stats() -> dict:
    if "all" not in _cache:
        return {"cached": False}
    ts, jobs = _cache["all"]
    return {
        "cached": True,
        "age_seconds": int(time.time() - ts),
        "ttl_seconds": CACHE_TTL_SEC,
        "job_count": len(jobs),
        "by_scope": {
            "India":            sum(1 for j in jobs if j["scope"] == "India"),
            "Worldwide Remote": sum(1 for j in jobs if j["scope"] == "Worldwide Remote"),
        },
        "by_source": {
            src: sum(1 for j in jobs if j["category"] == src)
            for src in ("Greenhouse", "Lever", "Remotive", "RemoteOK")
        },
    }
