"""Score a list of jobs against a parsed resume profile.

Source-agnostic: takes any list[dict] of jobs (live-fetched, static, etc.)
and returns them annotated with fit_score / priority / matched_skills.

Scoring breakdown (0-100):
  - Skill recall      (50)  — fraction of job-required skills the candidate has
  - Skill breadth     (15)  — bonus for many overlapping skills
  - Experience fit    (20)  — within job's stated yr range = full points
  - Title alignment   (15)  — resume titles overlap with role keywords
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .parser import ResumeProfile
from .skills import SKILLS, TITLE_HINTS


# ---- Skill / title detection in arbitrary text -----------------------------

def _detect(taxonomy: dict[str, list[str]], text: str) -> set[str]:
    out: set[str] = set()
    lower = text.lower()
    for canonical, aliases in taxonomy.items():
        for alias in aliases:
            pattern = alias if any(c in alias for c in r"\b()+*?") else rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lower):
                out.add(canonical)
                break
    return out


def skills_in_text(text: str) -> set[str]:
    return _detect(SKILLS, text)


def titles_in_text(text: str) -> set[str]:
    return _detect(TITLE_HINTS, text)


# ---- Experience parsing ----------------------------------------------------

_EXP_RANGE_RE = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*(?:yrs?|years?)", re.IGNORECASE)
_EXP_PLUS_RE  = re.compile(r"(\d+)\s*\+\s*(?:yrs?|years?)", re.IGNORECASE)


def parse_experience(s: str) -> tuple[float, float]:
    if m := _EXP_RANGE_RE.search(s):
        return float(m.group(1)), float(m.group(2))
    if m := _EXP_PLUS_RE.search(s):
        return float(m.group(1)), float(m.group(1)) + 5
    return 0.0, 10.0


# ---- Scoring ---------------------------------------------------------------

@dataclass
class ScoredJob:
    job: dict
    fit_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    breakdown: dict


def _job_text(job: dict) -> str:
    """Concatenate all the searchable fields. Use the full description if the
    job came from a live source; fall back to key_requirements for static data."""
    return " ".join([
        job.get("role", "") or "",
        job.get("_raw_text", "") or job.get("key_requirements", "") or "",
        job.get("category", "") or "",
    ])


def score_job(profile: ResumeProfile, job: dict) -> ScoredJob:
    text = _job_text(job)
    job_skills = skills_in_text(text)
    resume_skills = set(profile.skills)

    matched = sorted(job_skills & resume_skills)
    missing = sorted(job_skills - resume_skills)

    # Use a min-denominator so JDs with very few tech keywords (e.g. sales, ops)
    # can't earn full recall just because the 1-2 keywords they do mention happen
    # to be in the resume. Real engineering JDs typically detect 5-15 skills.
    denom = max(5, len(job_skills))
    skill_recall  = (len(matched) / denom * 50) if job_skills else 0
    breadth_bonus = min(15, len(matched) * 2)

    lo, hi = parse_experience(job.get("experience", "") or text)
    yrs = profile.years_experience
    if lo <= yrs <= hi:
        exp_score = 20.0
    else:
        gap = min(abs(yrs - lo), abs(yrs - hi))
        exp_score = max(0.0, 20.0 - gap * 5)

    job_titles = titles_in_text(text)
    resume_titles = set(profile.titles)
    title_overlap = job_titles & resume_titles
    title_score = 15.0 if title_overlap else (8.0 if resume_titles else 0.0)

    total = max(0, min(100, round(skill_recall + breadth_bonus + exp_score + title_score)))

    return ScoredJob(
        job=job,
        fit_score=total,
        matched_skills=matched,
        missing_skills=missing,
        breakdown={
            "skill_recall":  round(skill_recall, 1),
            "skill_breadth": round(breadth_bonus, 1),
            "experience":    round(exp_score, 1),
            "title":         round(title_score, 1),
        },
    )


def priority_for(score: int) -> str:
    if score >= 75: return "High"
    if score >= 55: return "Medium"
    return "Stretch"


def _why_fit(matched: list[str]) -> str:
    if not matched:
        return "Adjacent role; few direct skill overlaps."
    if len(matched) >= 5:
        return f"Strong stack overlap — matches {len(matched)} of your skills including {', '.join(matched[:3])}."
    return f"Partial fit — overlaps on {', '.join(matched)}."


# Cap response size so the JSON payload + serialization don't blow 512 MB
# instances. Dashboard never shows more than this anyway.
MAX_RESULTS = 200


def score_all(profile: ResumeProfile, jobs: list[dict]) -> list[dict]:
    """Score every job, drop heavy fields, sort, return top MAX_RESULTS."""
    scored = [score_job(profile, j) for j in jobs]
    scored.sort(key=lambda s: s.fit_score, reverse=True)
    out: list[dict] = []
    for s in scored[:MAX_RESULTS]:
        clean = {k: v for k, v in s.job.items() if k != "_raw_text"}
        out.append({
            **clean,
            "fit_score": s.fit_score,
            "priority":  priority_for(s.fit_score),
            "matched_skills": s.matched_skills,
            "missing_skills": s.missing_skills[:15],  # cap modal payload
            "breakdown": s.breakdown,
            "why_fit": clean.get("why_fit") or _why_fit(s.matched_skills),
        })
    return out
