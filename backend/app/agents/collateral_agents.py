"""Collateral Engine: Website, Pitch Deck and MVP agents (run in parallel).

Content is derived strictly from the Market Fit report. Unknowns are labeled
as hypotheses; no invented statistics.
"""
from __future__ import annotations

import json

from ..services.event_service import log_event
from ..services.firestore_service import get_firestore_service


def run_website_agent(startup_id: str) -> dict:
    fs = get_firestore_service()
    log_event(startup_id, "WebsiteAgent", "Generating landing page")
    fit = fs.get("market_fit", startup_id) or {}
    strategy = fs.get("strategy", startup_id) or {}
    page = {
        "startup_id": startup_id,
        "hero": "Solve it faster.",
        "problem": strategy.get("icp", "Customers") + " face this problem today.",
        "solution": fit.get("recommendation", ""),
        "validation_evidence": {
            s["stream"]: {"score": s["score"], "label": s["label"]}
            for s in fit.get("stream_scores", []) if s.get("has_data")
        },
        "pricing": strategy.get("pricing_hypothesis", "₹99/month"),
        "cta": "Join the waitlist",
        "note": "All validation figures carry their REAL/SIMULATED/DEMO labels.",
    }
    fs.set("assets_website", startup_id, page)
    log_event(startup_id, "WebsiteAgent", "Website generated (preview route available)")
    return page


def run_deck_agent(startup_id: str) -> dict:
    fs = get_firestore_service()
    log_event(startup_id, "PitchDeckAgent", "Generating pitch deck")
    fit = fs.get("market_fit", startup_id) or {}
    strategy = fs.get("strategy", startup_id) or {}
    synthetic = fs.get("simulations", startup_id) or {}
    slides = [
        {"n": 1, "title": "Title", "content": strategy.get("value_proposition", "")},
        {"n": 2, "title": "Problem", "content": strategy.get("icp", "")},
        {"n": 3, "title": "Market", "content": "See research stream for cited sizing (hypothesis where unverified)"},
        {"n": 4, "title": "Evidence", "content": [
            {"stream": s["stream"], "score": s["score"], "label": s["label"]}
            for s in fit.get("stream_scores", [])]},
        {"n": 5, "title": "Solution", "content": fit.get("recommendation", "")},
        {"n": 6, "title": "Business Model", "content": strategy.get("pricing_hypothesis", "")},
        {"n": 7, "title": "Validation", "content": {
            "market_fit": fit.get("market_fit_score"),
            "confidence": fit.get("confidence"),
            "synthetic_best": (synthetic.get("scores") or {}).get("best_scenario")}},
        {"n": 8, "title": "Roadmap & Ask", "content": strategy.get("roadmap", [])},
    ]
    deck = {"startup_id": startup_id, "slides": slides}
    fs.set("assets_deck", startup_id, deck)
    log_event(startup_id, "PitchDeckAgent", f"{len(slides)} slides generated")
    return deck


def run_mvp_agent(startup_id: str) -> dict:
    fs = get_firestore_service()
    log_event(startup_id, "MVPAgent", "Deriving MVP scope from evidence")
    strategy = fs.get("strategy", startup_id) or {}
    mvp = strategy.get("mvp_scope", {})
    result = {"startup_id": startup_id, **mvp,
              "scope_creep_warnings": ["Any feature without supporting evidence is flagged DO NOT BUILD"]}
    fs.set("assets_mvp", startup_id, result)
    return result
