"""Research tools: real web search when available, cached demo sources otherwise.

NEVER fabricate statistics. Every evidence item carries provenance. Demo-mode
sources are clearly labeled demo_cache.
"""
from __future__ import annotations

import logging
import uuid

from ..config.settings import get_settings
from ..models.evidence import Evidence

log = logging.getLogger(__name__)

# Controlled public-reference sources used ONLY in demo mode. These are real,
# well-known public references — not invented statistics.
DEMO_SOURCES = [
    {"title": "U.S. Bureau of Labor Statistics — Employment Projections",
     "url": "https://www.bls.gov/emp/",
     "text": "Official government employment and occupation projections; useful for labor-market sizing.",
     "source_type": "report"},
    {"title": "Crunchbase", "url": "https://www.crunchbase.com",
     "text": "Company funding data; use for competitor funding signals.",
     "source_type": "web"},
    {"title": "G2 Crowd", "url": "https://www.g2.com",
     "text": "Verified user reviews of software competitors; source of customer pain/complaint evidence.",
     "source_type": "web"},
    {"title": "Product Hunt", "url": "https://www.producthunt.com",
     "text": "New product launches; competitor launch monitoring.",
     "source_type": "web"},
    {"title": "Statista", "url": "https://www.statista.com",
     "text": "Market statistics aggregator; specific figures require a license — treat as directional only.",
     "source_type": "report"},
]


def _evidence(startup_id: str, claim: str, src: dict, confidence: float, relevance: float) -> Evidence:
    return Evidence(
        evidence_id=uuid.uuid4().hex[:12],
        startup_id=startup_id,
        claim=claim,
        source_url=src["url"],
        source_title=src["title"],
        source_type=src["source_type"],
        evidence_text=src["text"],
        confidence=confidence,
        relevance=relevance,
    )


def search_web(query: str) -> list[dict]:
    """Real web search via Google Custom Search API if configured.

    Returns [] when no API key is configured — callers fall back to demo cache.
    """
    settings = get_settings()
    api_key = settings.google_search_api_key if hasattr(settings, "google_search_api_key") else None
    cx = settings.google_search_cx if hasattr(settings, "google_search_cx") else None
    if not api_key or not cx:
        return []
    try:
        import requests

        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": api_key, "cx": cx, "q": query, "num": 5},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [{"title": i.get("title"), "url": i.get("link"),
                 "snippet": i.get("snippet", ""), "source_type": "web"} for i in items]
    except Exception as exc:
        log.warning("Web search failed (%s) — returning empty.", exc)
        return []


def gather_research_evidence(startup_id: str, idea_summary: str, research_areas: list[str]) -> dict[str, list[Evidence]]:
    """Collect evidence per research area. Real search first, demo cache fallback."""
    result: dict[str, list[Evidence]] = {}
    for area in research_areas:
        found: list[Evidence] = []
        hits = search_web(f"{idea_summary} {area}")
        if hits:
            for h in hits[:4]:
                found.append(_evidence(startup_id, f"[{area}] {h['snippet']}", h, 0.6, 0.7))
        else:
            # Demo mode: attach controlled reference sources, labeled honestly.
            for src in DEMO_SOURCES[:3]:
                ev = _evidence(startup_id,
                               f"[{area}] Reference source identified for {area} validation "
                               "(demo mode — no live search configured).",
                               src, 0.3, 0.5)
                ev.source_type = "demo_cache"
                found.append(ev)
        result[area] = found
    return result


RESEARCH_AREAS = ["market_size", "competitors", "customer_pain", "pricing", "trends", "funding"]
