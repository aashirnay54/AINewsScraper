"""Gemini LLM wrapper for content curation."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def get_client() -> genai.Client:
    """Create a Gemini client with API key from environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)


def curate_ai_news(
    articles: list[dict[str, Any]],
    model: str,
    max_items: int = 12,
) -> list[dict[str, Any]]:
    """
    Use Gemini to curate and summarize AI news articles.

    Args:
        articles: List of article dicts with title, url, source, summary
        model: Gemini model name
        max_items: Maximum items to return

    Returns:
        List of curated articles with summaries and groups
    """
    if not articles:
        return []

    # Prepare input for LLM
    articles_text = "\n".join(
        f"- [{i}] {a.get('title', '')} (source: {a.get('source', '')}) "
        f"[summary: {a.get('summary', '')[:200]}]"
        for i, a in enumerate(articles[:50])  # Limit input size
    )

    prompt = f"""You are curating an AI/ML news briefing. Analyze these articles and select the {max_items} most important ones.

For each selected article:
1. Rank by importance (breaking news, major releases, significant research > routine updates)
2. Write a 1-2 sentence plain-English summary explaining why it matters
3. Assign to ONE group: "Models & releases", "Research", "Tools & infra", or "Industry"

Articles:
{articles_text}

Return JSON array with objects having these fields:
- index: original article index (integer)
- summary: your 1-2 sentence summary (string)
- group: one of the four groups above (string)
- importance: 1-10 score (integer)

Sort by importance descending. Return exactly {max_items} items or fewer if not enough quality articles."""

    try:
        client = get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        result_text = response.text.strip()
        curated = json.loads(result_text)

        if not isinstance(curated, list):
            raise ValueError("Expected JSON array")

        # Map back to original articles
        output = []
        for item in curated[:max_items]:
            idx = item.get("index", 0)
            if 0 <= idx < len(articles):
                article = articles[idx].copy()
                article["llm_summary"] = item.get("summary", "")
                article["group"] = item.get("group", "Industry")
                article["importance"] = item.get("importance", 5)
                output.append(article)

        logger.info(f"LLM curated {len(output)} AI articles")
        return output

    except Exception as e:
        logger.warning(f"LLM curation failed, using fallback: {e}")
        return _fallback_curate(articles, max_items)


def curate_market_news(
    articles: list[dict[str, Any]],
    model: str,
    max_items: int = 4,
) -> list[dict[str, Any]]:
    """
    Use Gemini to curate market news articles.

    Args:
        articles: List of article dicts
        model: Gemini model name
        max_items: Maximum items to return

    Returns:
        List of curated articles with summaries
    """
    if not articles:
        return []

    articles_text = "\n".join(
        f"- [{i}] {a.get('title', '')} (source: {a.get('source', '')})"
        for i, a in enumerate(articles[:30])
    )

    prompt = f"""You are curating market news for a daily briefing. Select the {max_items} most important market/finance stories.

Articles:
{articles_text}

Return JSON array with objects having:
- index: original article index (integer)
- summary: 1 sentence summary of why it matters (string)
- importance: 1-10 score (integer)

Prioritize: market-moving news, major economic data, significant corporate news.
Sort by importance descending."""

    try:
        client = get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        result_text = response.text.strip()
        curated = json.loads(result_text)

        if not isinstance(curated, list):
            raise ValueError("Expected JSON array")

        output = []
        for item in curated[:max_items]:
            idx = item.get("index", 0)
            if 0 <= idx < len(articles):
                article = articles[idx].copy()
                article["llm_summary"] = item.get("summary", "")
                article["group"] = "Markets"
                output.append(article)

        logger.info(f"LLM curated {len(output)} market articles")
        return output

    except Exception as e:
        logger.warning(f"Market news curation failed, using fallback: {e}")
        return _fallback_curate(articles, max_items, group="Markets")


def generate_radar_line(
    market_data: dict[str, Any],
    ai_headlines: list[str],
    model: str,
) -> str:
    """
    Generate a one-sentence "on the radar today" summary.

    Args:
        market_data: Dict with indices, watchlist, sectors data
        ai_headlines: Top AI news headlines
        model: Gemini model name

    Returns:
        One-sentence radar summary
    """
    # Build market context
    market_context = []

    # Index changes
    for region, indices in market_data.get("indices", {}).items():
        for idx in indices[:2]:
            name = idx.get("name", idx.get("symbol", ""))
            change = idx.get("change_pct", 0)
            direction = "up" if change > 0 else "down"
            market_context.append(f"{name} {direction} {abs(change):.1f}%")

    # Best/worst sectors
    sectors = market_data.get("sectors", [])
    if sectors:
        sorted_sectors = sorted(sectors, key=lambda x: x.get("change_pct", 0), reverse=True)
        if sorted_sectors:
            best = sorted_sectors[0]
            worst = sorted_sectors[-1]
            market_context.append(f"{best.get('name', '')} leading ({best.get('change_pct', 0):+.1f}%)")
            market_context.append(f"{worst.get('name', '')} lagging ({worst.get('change_pct', 0):+.1f}%)")

    headlines_str = "; ".join(ai_headlines[:3])
    market_str = "; ".join(market_context[:4])

    prompt = f"""Write ONE sentence (max 30 words) summarizing what's on the radar today for an AI/tech investor.

Market moves: {market_str}
AI headlines: {headlines_str}

The sentence should blend market sentiment with AI news themes. Be concise and insightful."""

    try:
        client = get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
            ),
        )

        radar = response.text.strip().strip('"')
        # Ensure it's one sentence
        radar = radar.split(".")[0] + "."
        logger.info("Generated radar line")
        return radar

    except Exception as e:
        logger.warning(f"Radar generation failed: {e}")
        return "Markets and AI developments continue to evolve."


def _fallback_curate(
    articles: list[dict[str, Any]],
    max_items: int,
    group: str = "Industry",
) -> list[dict[str, Any]]:
    """
    Fallback curation when LLM fails: return first N items.
    """
    output = []
    for article in articles[:max_items]:
        article = article.copy()
        article["llm_summary"] = article.get("summary", "")[:200]
        article["group"] = group
        output.append(article)
    return output
