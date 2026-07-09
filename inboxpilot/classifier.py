"""
classifier.py — Hybrid email classification engine.

Two tiers, always available:
1. Rule-based engine (heuristic keyword/pattern scoring) — works instantly,
   no API key, no network required. This is the default and what CI tests run against.
2. LLM engine (Anthropic Claude) — used automatically when ANTHROPIC_API_KEY is set,
   for higher-accuracy classification and nuanced priority scoring.

Both return the same TriageResult shape so the rest of the app doesn't care which
engine produced it.
"""

from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass, asdict
from typing import Optional

CATEGORIES = ["urgent_support", "sales_lead", "spam", "newsletter", "general"]

URGENT_KEYWORDS = [
    "urgent", "asap", "immediately", "down", "outage", "not working",
    "broken", "critical", "emergency", "issue", "problem", "error",
    "can't access", "cannot access", "blocked", "failing"
]

SALES_KEYWORDS = [
    "pricing", "quote", "demo", "purchase", "buy", "interested in",
    "partnership", "trial", "subscription", "upgrade", "proposal", "budget"
]

SPAM_KEYWORDS = [
    "winner", "click here", "free money", "viagra", "lottery", "act now",
    "100% free", "risk-free", "congratulations you", "wire transfer",
    "crypto investment", "double your"
]

NEWSLETTER_SIGNS = [
    "unsubscribe", "newsletter", "digest", "weekly update", "no-reply",
    "noreply", "notifications@"
]


@dataclass
class TriageResult:
    category: str
    priority: int          # 1 (low) – 5 (critical)
    confidence: float       # 0.0 – 1.0
    reasoning: str
    suggested_reply: str
    engine: str              # "rules" or "llm"

    def to_dict(self):
        return asdict(self)


NEGATION_PATTERNS = [
    r"\bnot urgent\b", r"\bnot urgently\b", r"\bno rush\b", r"\bno urgency\b",
    r"\bnothing urgent\b", r"\bnot a problem\b", r"\bno issue\b", r"\bno problem\b",
]


def _strip_negations(text: str) -> str:
    """Removes negated keyword phrases (e.g. 'not urgent') before scoring, so
    they don't get counted as positive urgency/problem signals."""
    for pattern in NEGATION_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def _score_keywords(text: str, keywords: list[str]) -> int:
    text = _strip_negations(text.lower())
    return sum(1 for kw in keywords if kw in text)


def _rule_based_classify(subject: str, body: str, sender: str) -> TriageResult:
    full_text = f"{subject}\n{body}"
    sender_l = sender.lower()

    spam_score = _score_keywords(full_text, SPAM_KEYWORDS)
    urgent_score = _score_keywords(full_text, URGENT_KEYWORDS)
    sales_score = _score_keywords(full_text, SALES_KEYWORDS)
    newsletter_score = _score_keywords(full_text, NEWSLETTER_SIGNS) + _score_keywords(sender_l, NEWSLETTER_SIGNS)

    # excessive punctuation / caps is a spam signal
    exclaim_count = full_text.count("!")
    caps_ratio = sum(1 for c in subject if c.isupper()) / max(len(subject), 1)
    if exclaim_count >= 3 or caps_ratio > 0.6:
        spam_score += 2

    scores = {
        "spam": spam_score,
        "urgent_support": urgent_score,
        "sales_lead": sales_score,
        "newsletter": newsletter_score,
    }
    top_category = max(scores, key=scores.get)
    top_score = scores[top_category]

    if top_score == 0:
        category = "general"
        confidence = 0.55
    else:
        category = top_category
        confidence = min(0.6 + 0.1 * top_score, 0.97)

    # priority: urgent_support scales with urgency signal count; sales/general lower;
    # spam/newsletter are always low priority regardless of keyword count
    if category == "urgent_support":
        priority = min(3 + urgent_score, 5)
    elif category == "sales_lead":
        priority = 3
    elif category == "general":
        priority = 2
    else:  # spam, newsletter
        priority = 1

    reasoning = (
        f"Rule engine matched {top_score} '{category}' signal(s) "
        f"(scores: {scores})."
    )

    suggested_reply = _template_reply(category, subject, sender)

    return TriageResult(
        category=category,
        priority=priority,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        suggested_reply=suggested_reply,
        engine="rules",
    )


def _template_reply(category: str, subject: str, sender: str) -> str:
    name = sender.split("@")[0].replace(".", " ").title()
    templates = {
        "urgent_support": (
            f"Hi {name},\n\nThanks for flagging this — I understand it's urgent. "
            f"I'm looking into \"{subject}\" right now and will follow up with an update "
            f"as soon as possible. If this is impacting a live system, please let me know "
            f"the severity so I can prioritize accordingly.\n\nBest,\nSupport Team"
        ),
        "sales_lead": (
            f"Hi {name},\n\nThanks for your interest! I'd love to learn more about what "
            f"you're looking for regarding \"{subject}\" and share pricing/next steps. "
            f"Do you have 15 minutes this week for a quick call?\n\nBest,\nSales Team"
        ),
        "spam": "(No reply — flagged as likely spam.)",
        "newsletter": "(No reply needed — informational/newsletter email.)",
        "general": (
            f"Hi {name},\n\nThanks for reaching out about \"{subject}\". "
            f"I'll take a look and get back to you shortly with more details.\n\nBest,\nTeam"
        ),
    }
    return templates.get(category, templates["general"])


def _llm_classify(subject: str, body: str, sender: str) -> Optional[TriageResult]:
    """Uses the Anthropic API for classification if ANTHROPIC_API_KEY is set.
    Returns None on any failure so callers can fall back to the rule engine.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic  # imported lazily so the package is optional
    except ImportError:
        return None

    prompt = f"""You are an email triage assistant. Classify this email and draft a short reply.

Sender: {sender}
Subject: {subject}
Body: {body}

Respond ONLY with JSON in this exact shape, no other text:
{{
  "category": one of {CATEGORIES},
  "priority": integer 1-5,
  "confidence": float 0-1,
  "reasoning": "one sentence",
  "suggested_reply": "a short draft reply, or '(No reply needed)' for spam/newsletter"
}}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        return TriageResult(
            category=data["category"],
            priority=int(data["priority"]),
            confidence=float(data["confidence"]),
            reasoning=data["reasoning"],
            suggested_reply=data["suggested_reply"],
            engine="llm",
        )
    except Exception:
        return None


def classify_email(subject: str, body: str, sender: str) -> TriageResult:
    """Main entry point. Tries the LLM engine first (if configured), falls back
    to the always-available rule engine.
    """
    llm_result = _llm_classify(subject, body, sender)
    if llm_result is not None:
        return llm_result
    return _rule_based_classify(subject, body, sender)
