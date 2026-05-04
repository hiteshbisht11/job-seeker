"""Parse a resume PDF into a structured profile.

No LLM, no API calls. Pure text extraction + regex against a curated taxonomy.
Accuracy is ~70% on well-formatted resumes; good enough to drive job matching.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field, asdict
from datetime import date

from pypdf import PdfReader
from pdfminer.high_level import extract_text as pdfminer_extract

from .skills import SKILLS, TITLE_HINTS


@dataclass
class ResumeProfile:
    raw_text: str = ""
    skills: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    years_experience: float = 0.0
    locations: list[str] = field(default_factory=list)
    name_hint: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw_text", None)  # don't ship the full text to client
        return d


# ---- PDF -> text -----------------------------------------------------------

def _normalize(text: str) -> str:
    """Collapse runs of spaces; leave casing/word-boundaries intact so that
    well-formed brand names like 'PostgreSQL' or 'FastAPI' aren't fragmented."""
    return re.sub(r"[ \t]+", " ", text)


def _pypdf_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(parts)
    except Exception:
        return ""


def _pdfminer_text(pdf_bytes: bytes) -> str:
    try:
        return pdfminer_extract(io.BytesIO(pdf_bytes)) or ""
    except Exception:
        return ""


def extract_text(pdf_bytes: bytes) -> tuple[str, str]:
    """Return (combined_text, primary_text).
    `combined_text` = union of pdfminer + pypdf output, used for skill detection
    (each library loses different glyphs on stylized PDFs).
    `primary_text`  = best single source (pdfminer if non-empty), used for
    years-of-experience and date parsing — concatenation would double-count dates.
    """
    miner = _pdfminer_text(pdf_bytes)
    py    = _pypdf_text(pdf_bytes)
    if not (miner.strip() or py.strip()):
        raise RuntimeError("Could not extract any text from this PDF (likely a scanned image).")
    primary = miner.strip() and miner or py
    combined = miner + "\n" + py
    return _normalize(combined), _normalize(primary)


# ---- Skills ----------------------------------------------------------------

def detect_skills(text: str) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for canonical, aliases in SKILLS.items():
        for alias in aliases:
            pattern = alias if any(c in alias for c in r"\b()+*?") else rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lower):
                found.append(canonical)
                break
    return found


def detect_titles(text: str) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for canonical, aliases in TITLE_HINTS.items():
        for alias in aliases:
            pattern = alias if any(c in alias for c in r"\b()+*?") else rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lower):
                found.append(canonical)
                break
    return found


# ---- Years of experience ---------------------------------------------------

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_DATE_RANGE_RE = re.compile(
    r"([A-Za-z]{3,4})\.?\s+(\d{4})\s*[-–—to]+\s*(present|current|now|([A-Za-z]{3,4})\.?\s+(\d{4}))",
    re.IGNORECASE,
)
_EXPLICIT_YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", re.IGNORECASE)


def estimate_years(text: str) -> float:
    """Combine explicit '2+ years' phrasing with summed date ranges."""
    explicit = 0.0
    m = _EXPLICIT_YEARS_RE.search(text)
    if m:
        try:
            explicit = float(m.group(1))
        except ValueError:
            pass

    today = date.today()
    summed_months = 0
    for match in _DATE_RANGE_RE.finditer(text):
        start_mo = _MONTHS.get(match.group(1).lower()[:3])
        start_yr = int(match.group(2))
        if not start_mo:
            continue
        end_token = match.group(3).lower()
        if end_token in ("present", "current", "now"):
            end_mo, end_yr = today.month, today.year
        else:
            end_mo = _MONTHS.get(match.group(4).lower()[:3]) if match.group(4) else None
            end_yr = int(match.group(5)) if match.group(5) else None
            if not end_mo or not end_yr:
                continue
        months = (end_yr - start_yr) * 12 + (end_mo - start_mo)
        if 0 < months < 240:
            summed_months += months
    summed_years = round(summed_months / 12.0, 1)

    return max(explicit, summed_years)


# ---- Location hints --------------------------------------------------------

INDIA_CITIES = [
    "Bangalore", "Bengaluru", "Hyderabad", "Mumbai", "Delhi", "Gurgaon",
    "Gurugram", "Noida", "Pune", "Chennai", "Kolkata", "Ahmedabad",
    "Bhimtal", "Dehradun", "Jaipur",
]


def detect_locations(text: str) -> list[str]:
    found = []
    for city in INDIA_CITIES:
        if re.search(rf"\b{city}\b", text, re.IGNORECASE):
            found.append(city)
    if re.search(r"\bremote\b", text, re.IGNORECASE):
        found.append("Remote")
    return found


# ---- Name hint -------------------------------------------------------------

def detect_name(text: str) -> str:
    """Heuristic: first non-empty line that's a couple of capitalized words."""
    for raw in text.splitlines()[:10]:
        line = raw.strip()
        if 4 <= len(line) <= 60 and re.match(r"^[A-Z][a-zA-Z]+(\s+[A-Z][a-zA-Z]+){1,3}$", line):
            return line
    return ""


# ---- Top-level -------------------------------------------------------------

def parse_resume(pdf_bytes: bytes) -> ResumeProfile:
    combined, primary = extract_text(pdf_bytes)
    return ResumeProfile(
        raw_text=primary,
        skills=detect_skills(combined),       # union catches more glyphs
        titles=detect_titles(combined),
        years_experience=estimate_years(primary),  # single source; no double-count
        locations=detect_locations(primary),
        name_hint=detect_name(primary),
    )
