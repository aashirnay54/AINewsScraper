"""Fetchers for RSS feeds, arXiv, Hacker News, and Reddit."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

import feedparser
import requests

logger = logging.getLogger(__name__)

USER_AGENT = "BriefingBot/1.0"
REQUEST_TIMEOUT = 30


def strip_html(text: str) -> str:
    """Remove HTML tags using pure stdlib regex."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(entry: dict[str, Any]) -> datetime | None:
    """Parse date from feedparser entry."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def fetch_rss(feeds: list[dict[str, str]], max_age_hours: int) -> list[dict[str, Any]]:
    """
    Fetch articles from RSS feeds.

    Args:
        feeds: List of feed dicts with 'name' and 'url' keys
        max_age_hours: Maximum article age in hours

    Returns:
        List of article dicts with title, url, source, published, summary
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    articles = []

    for feed_info in feeds:
        name = feed_info.get("name", "Unknown")
        url = feed_info.get("url", "")
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                logger.warning(f"RSS feed {name} failed to parse: {feed.bozo_exception}")
                continue

            for entry in feed.entries:
                pub_date = parse_date(entry)
                if pub_date and pub_date < cutoff:
                    continue

                articles.append({
                    "title": strip_html(entry.get("title", "")),
                    "url": entry.get("link", ""),
                    "source": name,
                    "published": pub_date.isoformat() if pub_date else None,
                    "summary": strip_html(entry.get("summary", ""))[:500],
                    "type": "rss",
                })

            logger.info(f"Fetched {len(feed.entries)} entries from {name}")

        except Exception as e:
            logger.warning(f"Failed to fetch RSS feed {name}: {e}")
            continue

    return articles


def fetch_arxiv(categories: list[str], max_age_hours: int, max_results: int = 15) -> list[dict[str, Any]]:
    """
    Fetch recent papers from arXiv categories.

    Args:
        categories: List of arXiv categories (e.g., cs.CL, cs.AI)
        max_age_hours: Maximum paper age in hours
        max_results: Maximum results per category

    Returns:
        List of paper dicts
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    articles = []

    for category in categories:
        try:
            # arXiv API query
            query = f"cat:{category}"
            url = (
                f"http://export.arxiv.org/api/query?"
                f"search_query={quote_plus(query)}&"
                f"sortBy=submittedDate&sortOrder=descending&"
                f"max_results={max_results}"
            )

            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            feed = feedparser.parse(response.text)

            for entry in feed.entries:
                pub_date = parse_date(entry)
                if pub_date and pub_date < cutoff:
                    continue

                # Extract arXiv ID from URL
                arxiv_id = entry.get("id", "").split("/abs/")[-1]

                articles.append({
                    "title": strip_html(entry.get("title", "")).replace("\n", " "),
                    "url": entry.get("link", ""),
                    "source": f"arXiv {category}",
                    "published": pub_date.isoformat() if pub_date else None,
                    "summary": strip_html(entry.get("summary", ""))[:500].replace("\n", " "),
                    "arxiv_id": arxiv_id,
                    "authors": [a.get("name", "") for a in entry.get("authors", [])[:3]],
                    "type": "arxiv",
                })

            logger.info(f"Fetched {len(feed.entries)} papers from arXiv {category}")
            time.sleep(0.5)  # Be nice to arXiv API

        except Exception as e:
            logger.warning(f"Failed to fetch arXiv {category}: {e}")
            continue

    return articles


def fetch_hackernews(
    keywords: list[str], max_age_hours: int, min_points: int = 30, hits_per_page: int = 20
) -> list[dict[str, Any]]:
    """
    Fetch Hacker News stories matching keywords using Algolia API.

    Args:
        keywords: List of search keywords
        max_age_hours: Maximum story age in hours
        min_points: Minimum points threshold
        hits_per_page: Results per keyword search

    Returns:
        List of story dicts
    """
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).timestamp())
    articles = []
    seen_urls = set()

    for keyword in keywords:
        try:
            url = (
                f"https://hn.algolia.com/api/v1/search?"
                f"query={quote_plus(keyword)}&"
                f"tags=story&"
                f"numericFilters=created_at_i>{cutoff_ts},points>{min_points}&"
                f"hitsPerPage={hits_per_page}"
            )

            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            for hit in data.get("hits", []):
                story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"

                # Dedupe by URL
                if story_url in seen_urls:
                    continue
                seen_urls.add(story_url)

                created_at = hit.get("created_at_i", 0)
                pub_date = datetime.fromtimestamp(created_at, tz=timezone.utc) if created_at else None

                articles.append({
                    "title": hit.get("title", ""),
                    "url": story_url,
                    "source": "Hacker News",
                    "published": pub_date.isoformat() if pub_date else None,
                    "summary": "",
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "hn_id": hit.get("objectID"),
                    "type": "hn",
                })

            logger.info(f"Fetched {len(data.get('hits', []))} HN stories for '{keyword}'")
            time.sleep(0.2)  # Rate limiting

        except Exception as e:
            logger.warning(f"Failed to fetch HN for keyword '{keyword}': {e}")
            continue

    return articles


def fetch_reddit(
    subreddits: list[str], max_age_hours: int, limit: int = 25
) -> list[dict[str, Any]]:
    """
    Fetch hot posts from subreddits using Reddit's JSON API.

    Args:
        subreddits: List of subreddit names
        max_age_hours: Maximum post age in hours
        limit: Maximum posts per subreddit

    Returns:
        List of post dicts
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    articles = []

    for subreddit in subreddits:
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})

                # Skip stickied posts
                if post_data.get("stickied"):
                    continue

                created_utc = post_data.get("created_utc", 0)
                pub_date = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None

                if pub_date and pub_date < cutoff:
                    continue

                # Get the actual link (external URL or reddit post)
                post_url = post_data.get("url", "")
                if post_url.startswith("/r/"):
                    post_url = f"https://www.reddit.com{post_url}"

                articles.append({
                    "title": post_data.get("title", ""),
                    "url": post_url,
                    "source": f"r/{subreddit}",
                    "published": pub_date.isoformat() if pub_date else None,
                    "summary": strip_html(post_data.get("selftext", ""))[:500],
                    "score": post_data.get("score", 0),
                    "comments": post_data.get("num_comments", 0),
                    "type": "reddit",
                })

            logger.info(f"Fetched {len(data.get('data', {}).get('children', []))} posts from r/{subreddit}")
            time.sleep(1)  # Reddit rate limiting

        except Exception as e:
            logger.warning(f"Failed to fetch Reddit r/{subreddit}: {e}")
            continue

    return articles


def fetch_all_ai_news(config: dict[str, Any], max_age_hours: int) -> list[dict[str, Any]]:
    """Fetch all AI news from configured sources."""
    ai_sources = config.get("ai_sources", {})
    all_articles = []

    # RSS feeds
    rss_feeds = ai_sources.get("rss", [])
    if rss_feeds:
        all_articles.extend(fetch_rss(rss_feeds, max_age_hours))

    # arXiv
    arxiv_cats = ai_sources.get("arxiv_categories", [])
    if arxiv_cats:
        all_articles.extend(fetch_arxiv(arxiv_cats, max_age_hours))

    # Hacker News
    hn_keywords = ai_sources.get("hn_keywords", [])
    if hn_keywords:
        all_articles.extend(fetch_hackernews(hn_keywords, max_age_hours))

    # Reddit
    subreddits = ai_sources.get("reddit", [])
    if subreddits:
        all_articles.extend(fetch_reddit(subreddits, max_age_hours))

    logger.info(f"Total AI news articles fetched: {len(all_articles)}")
    return all_articles


def fetch_all_market_news(config: dict[str, Any], max_age_hours: int) -> list[dict[str, Any]]:
    """Fetch all market news from configured RSS sources."""
    market_sources = config.get("market_sources", {})
    rss_feeds = market_sources.get("rss", [])

    if not rss_feeds:
        return []

    articles = fetch_rss(rss_feeds, max_age_hours)
    logger.info(f"Total market news articles fetched: {len(articles)}")
    return articles
