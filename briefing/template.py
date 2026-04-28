"""HTML email template assembly with inline styles."""
from __future__ import annotations

from datetime import datetime
from typing import Any

# Colors
GREEN = "#1d9e75"
RED = "#c04848"
GRAY = "#666666"
LIGHT_GRAY = "#f5f5f5"
DARK = "#1a1a1a"


def render_email(
    ai_articles: list[dict[str, Any]],
    market_articles: list[dict[str, Any]],
    market_data: dict[str, Any],
    radar_line: str,
    stats: dict[str, int],
    tech_companies: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """
    Render the complete email as HTML and plain text.

    Args:
        ai_articles: Curated AI news articles
        market_articles: Curated market news articles
        market_data: Market data with indices, watchlist, sectors
        radar_line: One-sentence radar summary
        stats: Dict with feeds_scanned, articles_processed counts
        tech_companies: Optional list of tech company summaries

    Returns:
        Tuple of (html_content, plain_text_content)
    """
    today = datetime.now().strftime("%B %d, %Y")

    # Build HTML
    html_parts = [_html_header(today)]

    # Top story (first AI article gets special treatment)
    if ai_articles:
        html_parts.append(_render_top_story(ai_articles[0]))

    # Grouped AI sections
    html_parts.append(_render_ai_sections(ai_articles[1:] if ai_articles else []))

    # Big Tech section (NEW)
    if tech_companies:
        html_parts.append(_render_tech_companies(tech_companies))

    # Markets section
    html_parts.append(_render_markets_section(market_data, radar_line))

    # Market news
    if market_articles:
        html_parts.append(_render_market_news(market_articles))

    # Footer
    html_parts.append(_html_footer(stats))

    html = "\n".join(html_parts)

    # Build plain text version
    plain = _render_plain_text(ai_articles, market_articles, market_data, radar_line, stats, today, tech_companies)

    return html, plain


def _html_header(date: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: {LIGHT_GRAY}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        <tr>
            <td style="padding: 24px; border-bottom: 3px solid {DARK};">
                <h1 style="margin: 0; font-size: 24px; color: {DARK};">AI Markets Briefing</h1>
                <p style="margin: 8px 0 0 0; color: {GRAY}; font-size: 14px;">{date}</p>
            </td>
        </tr>"""


def _render_top_story(article: dict[str, Any]) -> str:
    title = article.get("title", "")
    url = article.get("url", "#")
    source = article.get("source", "")
    summary = article.get("llm_summary", article.get("summary", ""))

    return f"""
        <tr>
            <td style="padding: 24px;">
                <p style="margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase; color: {GREEN}; font-weight: 600;">Top Story</p>
                <h2 style="margin: 0 0 12px 0; font-size: 20px; line-height: 1.3;">
                    <a href="{url}" style="color: {DARK}; text-decoration: none;">{title}</a>
                </h2>
                <p style="margin: 0 0 8px 0; color: {DARK}; font-size: 15px; line-height: 1.5;">{summary}</p>
                <p style="margin: 0; font-size: 12px; color: {GRAY};">{source}</p>
            </td>
        </tr>
        <tr><td style="padding: 0 24px;"><hr style="border: none; border-top: 1px solid #e0e0e0; margin: 0;"></td></tr>"""


def _render_ai_sections(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return ""

    # Group articles
    groups: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        group = article.get("group", "Industry")
        if group not in groups:
            groups[group] = []
        groups[group].append(article)

    html_parts = []

    # Define group order
    group_order = ["Models & releases", "Research", "Tools & infra", "Industry"]

    for group_name in group_order:
        if group_name not in groups:
            continue

        html_parts.append(f"""
        <tr>
            <td style="padding: 20px 24px 8px 24px;">
                <h3 style="margin: 0; font-size: 14px; text-transform: uppercase; color: {GRAY}; letter-spacing: 0.5px;">{group_name}</h3>
            </td>
        </tr>""")

        for article in groups[group_name]:
            title = article.get("title", "")
            url = article.get("url", "#")
            source = article.get("source", "")
            summary = article.get("llm_summary", "")

            html_parts.append(f"""
        <tr>
            <td style="padding: 8px 24px;">
                <p style="margin: 0 0 4px 0; font-size: 15px;">
                    <a href="{url}" style="color: {DARK}; text-decoration: none;">{title}</a>
                </p>
                {f'<p style="margin: 0 0 4px 0; font-size: 13px; color: {GRAY}; line-height: 1.4;">{summary}</p>' if summary else ''}
                <p style="margin: 0; font-size: 11px; color: {GRAY};">{source}</p>
            </td>
        </tr>""")

    return "\n".join(html_parts)


def _render_tech_companies(companies: list[dict[str, Any]]) -> str:
    """Render Big Tech company summaries."""
    if not companies:
        return ""

    html_parts = [f"""
        <tr><td style="padding: 0 24px;"><hr style="border: none; border-top: 1px solid #e0e0e0; margin: 16px 0;"></td></tr>
        <tr>
            <td style="padding: 16px 24px;">
                <h3 style="margin: 0 0 16px 0; font-size: 18px; color: {DARK};">Big Tech Watch</h3>
            </td>
        </tr>"""]

    for company in companies:
        name = company.get("name", "")
        summary = company.get("summary", "")
        highlights = company.get("highlights", [])
        sentiment = company.get("sentiment", "neutral")
        layoffs = company.get("layoffs", False)
        article_count = company.get("article_count", 0)

        # Sentiment colors
        sentiment_colors = {
            "positive": GREEN,
            "negative": RED,
            "neutral": GRAY,
            "mixed": "#ff9800",
        }
        sentiment_color = sentiment_colors.get(sentiment, GRAY)

        # Layoff badge
        layoff_badge = ""
        if layoffs:
            layoff_badge = f'<span style="display: inline-block; background-color: {RED}; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; margin-left: 8px; text-transform: uppercase; font-weight: 600;">Layoffs</span>'

        # Build highlights list
        highlights_html = ""
        if highlights:
            highlight_items = "".join(
                f'<li style="margin: 4px 0; font-size: 13px; color: {DARK};">{h}</li>'
                for h in highlights[:4]
            )
            highlights_html = f'<ul style="margin: 8px 0 0 0; padding-left: 20px;">{highlight_items}</ul>'

        html_parts.append(f"""
        <tr>
            <td style="padding: 8px 24px;">
                <div style="background-color: {LIGHT_GRAY}; padding: 16px; border-radius: 4px; border-left: 4px solid {sentiment_color};">
                    <p style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600; color: {DARK};">
                        {name}
                        {layoff_badge}
                        <span style="font-size: 11px; color: {GRAY}; font-weight: 400; margin-left: 8px;">({article_count} articles)</span>
                    </p>
                    <p style="margin: 0; font-size: 14px; color: {DARK}; line-height: 1.5;">{summary}</p>
                    {highlights_html}
                </div>
            </td>
        </tr>""")

    return "\n".join(html_parts)


def _render_markets_section(market_data: dict[str, Any], radar_line: str) -> str:
    html_parts = [f"""
        <tr><td style="padding: 0 24px;"><hr style="border: none; border-top: 1px solid #e0e0e0; margin: 16px 0;"></td></tr>
        <tr>
            <td style="padding: 16px 24px;">
                <h3 style="margin: 0 0 16px 0; font-size: 18px; color: {DARK};">Markets</h3>
                <p style="margin: 0 0 20px 0; font-size: 14px; color: {DARK}; font-style: italic; background-color: {LIGHT_GRAY}; padding: 12px; border-radius: 4px;">📡 {radar_line}</p>
            </td>
        </tr>"""]

    # Indices by region
    indices = market_data.get("indices", {})
    if indices:
        html_parts.append(_render_indices(indices))

    # Watchlist table
    watchlist = market_data.get("watchlist", [])
    if watchlist:
        html_parts.append(_render_watchlist_table(watchlist))

    # Best/worst sectors
    sectors = market_data.get("sectors", [])
    if sectors:
        html_parts.append(_render_sector_cards(sectors))

    return "\n".join(html_parts)


def _render_indices(indices: dict[str, list[dict[str, Any]]]) -> str:
    html_parts = ['<tr><td style="padding: 0 24px 16px 24px;">']

    region_order = ["US", "Europe", "Asia"]
    for region in region_order:
        if region not in indices:
            continue

        html_parts.append(f'<p style="margin: 8px 0 4px 0; font-size: 12px; text-transform: uppercase; color: {GRAY}; font-weight: 600;">{region}</p>')
        html_parts.append('<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>')

        for idx in indices[region]:
            name = idx.get("name", idx.get("symbol", ""))
            change = idx.get("change_pct", 0)
            color = GREEN if change >= 0 else RED
            sign = "+" if change >= 0 else ""

            html_parts.append(f"""
                <td style="padding: 4px 8px 4px 0;">
                    <span style="font-size: 13px; color: {DARK};">{name}</span>
                    <span style="font-size: 13px; color: {color}; font-weight: 600;"> {sign}{change:.2f}%</span>
                </td>""")

        html_parts.append('</tr></table>')

    html_parts.append('</td></tr>')
    return "\n".join(html_parts)


def _render_watchlist_table(watchlist: list[dict[str, Any]]) -> str:
    rows = []
    for item in watchlist:
        symbol = item.get("symbol", "")
        name = item.get("name", "")
        price = item.get("price", 0)
        change = item.get("change_pct", 0)
        color = GREEN if change >= 0 else RED
        sign = "+" if change >= 0 else ""

        rows.append(f"""
            <tr>
                <td style="padding: 6px 8px; font-size: 13px; font-weight: 600;">{symbol}</td>
                <td style="padding: 6px 8px; font-size: 13px; color: {GRAY};">{name}</td>
                <td style="padding: 6px 8px; font-size: 13px; text-align: right;">${price:,.2f}</td>
                <td style="padding: 6px 8px; font-size: 13px; text-align: right; color: {color}; font-weight: 600;">{sign}{change:.2f}%</td>
            </tr>""")

    return f"""
        <tr>
            <td style="padding: 0 24px 16px 24px;">
                <p style="margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase; color: {GRAY}; font-weight: 600;">Watchlist</p>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: {LIGHT_GRAY}; border-radius: 4px;">
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <th style="padding: 8px; font-size: 11px; text-align: left; color: {GRAY}; font-weight: 600;">Ticker</th>
                        <th style="padding: 8px; font-size: 11px; text-align: left; color: {GRAY}; font-weight: 600;">Name</th>
                        <th style="padding: 8px; font-size: 11px; text-align: right; color: {GRAY}; font-weight: 600;">Price</th>
                        <th style="padding: 8px; font-size: 11px; text-align: right; color: {GRAY}; font-weight: 600;">Change</th>
                    </tr>
                    {"".join(rows)}
                </table>
            </td>
        </tr>"""


def _render_sector_cards(sectors: list[dict[str, Any]]) -> str:
    if len(sectors) < 2:
        return ""

    sorted_sectors = sorted(sectors, key=lambda x: x.get("change_pct", 0), reverse=True)
    best = sorted_sectors[0]
    worst = sorted_sectors[-1]

    def card(sector: dict[str, Any], label: str) -> str:
        name = sector.get("name", "")
        change = sector.get("change_pct", 0)
        color = GREEN if change >= 0 else RED
        sign = "+" if change >= 0 else ""
        bg = "#e8f5e9" if change >= 0 else "#ffebee"

        return f"""
            <td style="width: 50%; padding: 8px;">
                <div style="background-color: {bg}; padding: 12px; border-radius: 4px;">
                    <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; color: {GRAY};">{label}</p>
                    <p style="margin: 0; font-size: 14px; font-weight: 600; color: {DARK};">{name}</p>
                    <p style="margin: 4px 0 0 0; font-size: 16px; font-weight: 600; color: {color};">{sign}{change:.2f}%</p>
                </div>
            </td>"""

    return f"""
        <tr>
            <td style="padding: 0 24px 16px 24px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        {card(best, "Best Sector")}
                        {card(worst, "Worst Sector")}
                    </tr>
                </table>
            </td>
        </tr>"""


def _render_market_news(articles: list[dict[str, Any]]) -> str:
    html_parts = [f"""
        <tr>
            <td style="padding: 16px 24px 8px 24px;">
                <h3 style="margin: 0; font-size: 14px; text-transform: uppercase; color: {GRAY}; letter-spacing: 0.5px;">Market News</h3>
            </td>
        </tr>"""]

    for article in articles:
        title = article.get("title", "")
        url = article.get("url", "#")
        source = article.get("source", "")
        summary = article.get("llm_summary", "")

        html_parts.append(f"""
        <tr>
            <td style="padding: 8px 24px;">
                <p style="margin: 0 0 4px 0; font-size: 15px;">
                    <a href="{url}" style="color: {DARK}; text-decoration: none;">{title}</a>
                </p>
                {f'<p style="margin: 0 0 4px 0; font-size: 13px; color: {GRAY}; line-height: 1.4;">{summary}</p>' if summary else ''}
                <p style="margin: 0; font-size: 11px; color: {GRAY};">{source}</p>
            </td>
        </tr>""")

    return "\n".join(html_parts)


def _html_footer(stats: dict[str, int]) -> str:
    feeds = stats.get("feeds_scanned", 0)
    articles = stats.get("articles_processed", 0)

    return f"""
        <tr>
            <td style="padding: 24px; background-color: {LIGHT_GRAY}; border-top: 1px solid #e0e0e0;">
                <p style="margin: 0; font-size: 12px; color: {GRAY}; text-align: center;">
                    Scanned {feeds} feeds • {articles} articles • Curated with Gemini
                </p>
            </td>
        </tr>
    </table>
</body>
</html>"""


def _render_plain_text(
    ai_articles: list[dict[str, Any]],
    market_articles: list[dict[str, Any]],
    market_data: dict[str, Any],
    radar_line: str,
    stats: dict[str, int],
    date: str,
    tech_companies: list[dict[str, Any]] | None = None,
) -> str:
    """Render plain text version of the email."""
    lines = [
        f"AI MARKETS BRIEFING - {date}",
        "=" * 40,
        "",
    ]

    # Top story
    if ai_articles:
        top = ai_articles[0]
        lines.extend([
            "TOP STORY",
            "-" * 20,
            top.get("title", ""),
            top.get("llm_summary", top.get("summary", "")),
            f"Source: {top.get('source', '')}",
            top.get("url", ""),
            "",
        ])

    # Other AI articles
    for article in ai_articles[1:]:
        lines.extend([
            f"[{article.get('group', 'News')}] {article.get('title', '')}",
            article.get("llm_summary", ""),
            article.get("url", ""),
            "",
        ])

    # Big Tech section
    if tech_companies:
        lines.extend([
            "",
            "BIG TECH WATCH",
            "-" * 20,
        ])
        for company in tech_companies:
            name = company.get("name", "")
            summary = company.get("summary", "")
            highlights = company.get("highlights", [])
            layoffs = company.get("layoffs", False)
            layoff_text = " [LAYOFFS]" if layoffs else ""

            lines.extend([
                f"{name}{layoff_text}:",
                f"  {summary}",
            ])
            if highlights:
                for h in highlights[:4]:
                    lines.append(f"  • {h}")
            lines.append("")

    # Markets
    lines.extend([
        "",
        "MARKETS",
        "-" * 20,
        f"On the radar: {radar_line}",
        "",
    ])

    # Indices
    for region, indices in market_data.get("indices", {}).items():
        region_str = f"{region}: "
        idx_strs = []
        for idx in indices:
            change = idx.get("change_pct", 0)
            sign = "+" if change >= 0 else ""
            idx_strs.append(f"{idx.get('name', '')} {sign}{change:.2f}%")
        lines.append(region_str + " | ".join(idx_strs))

    lines.append("")

    # Watchlist
    lines.append("Watchlist:")
    for item in market_data.get("watchlist", []):
        change = item.get("change_pct", 0)
        sign = "+" if change >= 0 else ""
        lines.append(f"  {item.get('symbol', '')} ({item.get('name', '')}): ${item.get('price', 0):,.2f} {sign}{change:.2f}%")

    lines.append("")

    # Market news
    if market_articles:
        lines.append("Market News:")
        for article in market_articles:
            lines.extend([
                f"  - {article.get('title', '')}",
                f"    {article.get('url', '')}",
            ])

    lines.extend([
        "",
        "-" * 40,
        f"Scanned {stats.get('feeds_scanned', 0)} feeds • {stats.get('articles_processed', 0)} articles • Curated with Gemini",
    ])

    return "\n".join(lines)
