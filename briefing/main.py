"""Main orchestrator for the AI Markets Briefing pipeline."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from . import llm, mailer, markets, sources, state, techcompanies, template

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict:
    """Load configuration from config.yaml."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run() -> None:
    """Run the complete briefing pipeline."""
    logger.info("Starting AI Markets Briefing pipeline")

    # Step 1: Load config
    config = load_config()
    settings = config.get("settings", {})
    max_age_hours = settings.get("max_age_hours", 30)
    max_ai_items = settings.get("max_ai_items", 12)
    max_market_items = settings.get("max_market_items", 4)
    max_tech_companies = settings.get("max_tech_companies", 8)
    llm_model = settings.get("llm_model", "gemini-2.5-flash-lite")

    logger.info(
        f"Config loaded: max_age={max_age_hours}h, max_ai={max_ai_items}, "
        f"max_market={max_market_items}, max_tech={max_tech_companies}"
    )

    # Step 2: Fetch AI news
    logger.info("Fetching AI news...")
    ai_articles = sources.fetch_all_ai_news(config, max_age_hours)
    logger.info(f"Fetched {len(ai_articles)} AI articles")

    # Step 3: Fetch market news
    logger.info("Fetching market news...")
    market_articles = sources.fetch_all_market_news(config, max_age_hours)
    logger.info(f"Fetched {len(market_articles)} market articles")

    # Step 4: Fetch market data
    logger.info("Fetching market data...")
    market_data = markets.fetch_market_data(config)

    # Step 4b: Fetch tech company news
    logger.info("Fetching tech company news...")
    tech_companies_cfg = config.get("tech_companies", [])
    company_news = techcompanies.fetch_company_news(tech_companies_cfg, max_age_hours)

    # Step 5: Filter unseen articles
    logger.info("Filtering unseen articles...")
    seen = state.load_seen()

    ai_unseen = state.filter_unseen(ai_articles, seen)
    market_unseen = state.filter_unseen(market_articles, seen)

    logger.info(f"After filtering: {len(ai_unseen)} unseen AI, {len(market_unseen)} unseen market")

    # Track stats for footer
    total_feeds = (
        len(config.get("ai_sources", {}).get("rss", []))
        + len(config.get("ai_sources", {}).get("arxiv_categories", []))
        + len(config.get("ai_sources", {}).get("hn_keywords", []))
        + len(config.get("ai_sources", {}).get("reddit", []))
        + len(config.get("market_sources", {}).get("rss", []))
    )
    stats = {
        "feeds_scanned": total_feeds,
        "articles_processed": len(ai_articles) + len(market_articles),
    }

    # Step 6: Curate with LLM
    logger.info("Curating AI news with LLM...")
    curated_ai = llm.curate_ai_news(ai_unseen, llm_model, max_ai_items)

    logger.info("Curating market news with LLM...")
    curated_market = llm.curate_market_news(market_unseen, llm_model, max_market_items)

    # Step 6b: Filter and curate tech company news
    logger.info("Filtering unseen tech company news...")
    # Flatten company news into single list for filtering
    all_company_articles = []
    for company_articles in company_news.values():
        all_company_articles.extend(company_articles)

    company_unseen_articles = state.filter_unseen(all_company_articles, seen)

    # Rebuild company_news dict with only unseen articles
    company_news_unseen: dict[str, list] = {}
    for company_name in company_news.keys():
        company_news_unseen[company_name] = [
            a for a in company_unseen_articles
            if a.get("source", "").startswith(company_name) or a.get("company") == company_name
        ]

    logger.info("Curating tech company summaries with LLM...")
    tech_summaries = llm.curate_tech_companies(company_news_unseen, llm_model, max_tech_companies)

    # Step 7: Generate radar line
    logger.info("Generating radar line...")
    ai_headlines = [a.get("title", "") for a in curated_ai[:5]]
    radar_line = llm.generate_radar_line(market_data, ai_headlines, llm_model)

    # Step 8: Render email
    logger.info("Rendering email...")
    html_content, plain_content = template.render_email(
        ai_articles=curated_ai,
        market_articles=curated_market,
        market_data=market_data,
        radar_line=radar_line,
        stats=stats,
        tech_companies=tech_summaries,
    )

    # Step 9: Send email (or save to file if no SMTP creds)
    logger.info("Sending email...")
    success = mailer.send_email(html_content, plain_content)

    if success:
        logger.info("Email sent/saved successfully")
    else:
        logger.error("Failed to send/save email")

    # Step 10: Update seen.json
    logger.info("Updating seen.json...")
    today_iso = datetime.now().date().isoformat()

    # Combine all curated items for marking as seen
    all_used = curated_ai + curated_market + company_unseen_articles
    updated_seen = state.mark_seen(all_used, seen, today_iso)
    state.save_seen(updated_seen)

    logger.info(f"Marked {len(all_used)} items as seen, {len(updated_seen)} total in seen.json")
    logger.info("Pipeline completed successfully")


def main() -> None:
    """Entry point with error handling."""
    try:
        run()
    except Exception as e:
        logger.exception(f"Pipeline failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
