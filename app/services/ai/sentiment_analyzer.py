"""
Review Sentiment Analyzer
--------------------------
Classifies review text as positive / neutral / negative and produces
a normalized sentiment score in [-1, 1].

Uses VADER (vaderSentiment) — lightweight, no GPU, no model download.
Falls back to simple keyword scoring if VADER is unavailable.
"""
from __future__ import annotations
from typing import Dict, Any, Optional

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _analyzer = SentimentIntensityAnalyzer()
    _VADER_AVAILABLE = True
except ImportError:
    _analyzer = None
    _VADER_AVAILABLE = False

TOXIC_KEYWORDS = {
    "fraud", "scam", "fake", "liar", "terrible", "awful", "horrible",
    "worst", "cheat", "steal", "theft", "danger", "unsafe", "violent",
}

POSITIVE_KEYWORDS = {
    "excellent", "great", "amazing", "wonderful", "fantastic", "perfect",
    "professional", "reliable", "skilled", "efficient", "recommend",
}


def _keyword_fallback(text: str) -> float:
    words = set(text.lower().split())
    pos = len(words & POSITIVE_KEYWORDS)
    neg = len(words & TOXIC_KEYWORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 4)


def analyze_sentiment(text: Optional[str]) -> Dict[str, Any]:
    """
    Returns:
        sentiment_score : float in [-1, 1]  (negative → positive)
        label           : "positive" | "neutral" | "negative"
        is_toxic        : bool — true if toxic keywords detected
        compound        : raw VADER compound score (or None)
    """
    if not text or not text.strip():
        return {"sentiment_score": 0.0, "label": "neutral", "is_toxic": False, "compound": None}

    words = set(text.lower().split())
    is_toxic = bool(words & TOXIC_KEYWORDS)

    if _VADER_AVAILABLE:
        scores = _analyzer.polarity_scores(text)
        compound = scores["compound"]
    else:
        compound = _keyword_fallback(text)

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "sentiment_score": round(compound, 4),
        "label": label,
        "is_toxic": is_toxic,
        "compound": compound,
    }
