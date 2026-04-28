"""Tech company news aggregation and analysis."""
from __future__ import annotations

import logging
from typing import Any

from . import sources

logger = logging.getLogger(__name__)


def fetch_company_news(
    companies: list[dict[str, Any]],
    max_age_hours: int,
) -> dict[str, list[dict[str, Any]]]:
    """
    Fetch news for each tech company from multiple sources.

    Args:
        companies: List of company dicts with name, keywords, newsroom
        max_age_hours: Maximum article age in hours

    Returns:
        Dict mapping company name to list of articles
    """
    company_news: dict[str, list[dict[str, Any]]] = {}

    for company in companies:
        name = company.get("name", "Unknown")
        logger.info(f"Fetching news for {name}")

        articles = []

        # Fetch from company newsroom RSS if available
        newsroom = company.get("newsroom")
        if newsroom:
            try:
                rss_articles = sources.fetch_rss([{"name": name, "url": newsroom}], max_age_hours)
                articles.extend(rss_articles)
                logger.info(f"  - Fetched {len(rss_articles)} articles from {name} newsroom")
            except Exception as e:
                logger.warning(f"  - Failed to fetch {name} newsroom: {e}")

        # Search HN for company-specific keywords
        keywords = company.get("keywords", [])
        if keywords:
            try:
                # Use first 3 most specific keywords for HN search
                primary_keywords = keywords[:3]
                hn_articles = sources.fetch_hackernews(
                    primary_keywords,
                    max_age_hours,
                    min_points=20,  # Lower threshold for company news
                    hits_per_page=10,
                )
                # Tag articles with company name
                for article in hn_articles:
                    article["company"] = name
                articles.extend(hn_articles)
                logger.info(f"  - Fetched {len(hn_articles)} HN articles for {name}")
            except Exception as e:
                logger.warning(f"  - Failed to fetch HN for {name}: {e}")

        # Search Reddit for company mentions
        try:
            # Search r/technology and r/business
            reddit_articles = sources.fetch_reddit(
                ["technology", "business"],
                max_age_hours,
                limit=15,
            )
            # Filter for company-specific content
            company_reddit = []
            for article in reddit_articles:
                title_lower = article.get("title", "").lower()
                if any(kw.lower() in title_lower for kw in keywords):
                    article["company"] = name
                    company_reddit.append(article)
            articles.extend(company_reddit)
            logger.info(f"  - Fetched {len(company_reddit)} Reddit articles for {name}")
        except Exception as e:
            logger.warning(f"  - Failed to fetch Reddit for {name}: {e}")

        company_news[name] = articles
        logger.info(f"Total articles for {name}: {len(articles)}")

    return company_news


def aggregate_layoff_news(
    all_articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Extract articles specifically about layoffs, hiring freezes, or workforce changes.

    Args:
        all_articles: Combined list of all tech company articles

    Returns:
        List of layoff-related articles
    """
    layoff_keywords = [
        "layoff",
        "layoffs",
        "job cuts",
        "workforce reduction",
        "hiring freeze",
        "restructuring",
        "downsize",
        "downsizing",
        "job losses",
        "staff reduction",
    ]

    layoff_articles = []
    for article in all_articles:
        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()
        text = f"{title} {summary}"

        if any(keyword in text for keyword in layoff_keywords):
            layoff_articles.append(article)

    logger.info(f"Found {len(layoff_articles)} layoff-related articles")
    return layoff_articles
