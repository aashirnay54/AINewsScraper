# AI Markets Briefing

A daily email newsletter that combines AI/ML news with market trends. Runs automatically on GitHub Actions, uses Gemini Flash for intelligent curation, yfinance for market data, and Gmail SMTP for delivery.

## What It Produces

Every day you receive an email with:

- **Top Story**: The most important AI/ML news with a curated summary
- **Categorized AI News**: Stories grouped into "Models & releases", "Research", "Tools & infra", and "Industry"
- **Market Overview**: Indices by region (US/Europe/Asia), your watchlist with prices and daily changes, best/worst performing sectors
- **On the Radar**: A one-sentence AI-generated summary blending market sentiment with AI news themes
- **Market News**: Top financial headlines

## Stack

- **Python 3.11+** with type hints
- **Gemini Flash** (via google-genai) for content curation
- **yfinance** for market data
- **feedparser** for RSS parsing
- **GitHub Actions** for scheduling (free tier)
- **Gmail SMTP** for email delivery

## Setup

### 1. Create Repository

Fork or clone this repository to your GitHub account.

### 2. Get a Gemini API Key

1. Go to [Google AI Studio](https://ai.google.dev/)
2. Click "Get API Key"
3. Create a new API key or use an existing one
4. Copy the key for the next step

### 3. Set Up Gmail App Password

1. Enable 2-Factor Authentication on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Select "Mail" and your device
4. Generate and copy the 16-character app password

### 4. Add GitHub Secrets

Go to your repository's Settings > Secrets and variables > Actions, and add:

| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `RECIPIENT_EMAIL` | Email address to receive the briefing |
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASS` | Your Gmail app password |

### 5. Adjust Schedule (Optional)

Edit `.github/workflows/daily.yml` to change the cron schedule:

```yaml
schedule:
  - cron: '0 14 * * *'  # 14:00 UTC = 7:00 AM PT / 10:00 AM ET
```

Use [crontab.guru](https://crontab.guru/) to find your preferred time.

### 6. Test Run

1. Go to Actions tab in your repository
2. Select "Daily Briefing" workflow
3. Click "Run workflow"

## Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-markets-briefing.git
cd ai-markets-briefing

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the pipeline
python -m briefing.main
```

Without SMTP credentials, the email will be saved to `data/last.html` for preview.

## Customization

Edit `config.yaml` to customize:

### News Sources

```yaml
ai_sources:
  rss:
    - name: Your Blog
      url: https://example.com/feed.xml
  hn_keywords:
    - your-keyword
  reddit:
    - YourSubreddit
```

### Watchlist

```yaml
watchlist:
  tickers:
    - symbol: AAPL
      name: Apple
  indices:
    US:
      - symbol: ^GSPC
        name: S&P 500
```

### Settings

```yaml
settings:
  max_ai_items: 12      # AI articles in email
  max_market_items: 4   # Market news in email
  max_age_hours: 30     # Article freshness
  llm_model: gemini-2.5-flash-lite
```

## File Structure

```
ai-markets-briefing/
├── .github/workflows/
│   └── daily.yml       # GitHub Actions workflow
├── briefing/
│   ├── __init__.py
│   ├── main.py         # Pipeline orchestrator
│   ├── sources.py      # RSS, arXiv, HN, Reddit fetchers
│   ├── markets.py      # yfinance wrapper
│   ├── llm.py          # Gemini curation
│   ├── template.py     # HTML email assembly
│   ├── mailer.py       # SMTP delivery
│   └── state.py        # Seen article tracking
├── data/
│   └── seen.json       # Tracks sent articles (auto-updated)
├── config.yaml         # Sources and settings
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Free Tier Notes

This project is designed to run within free tiers:

| Service | Free Allowance | This Project Uses |
|---------|----------------|-------------------|
| GitHub Actions | 2,000 min/month | ~2 min/day (~60 min/month) |
| Gemini API | 15 RPM / 1M tokens/month | ~3 requests/day |
| Gmail SMTP | 500 emails/day | 1 email/day |

**Caveats:**
- Free tier limits may change; monitor your usage
- yfinance occasionally has rate limits or data gaps
- Some RSS feeds may change URLs or go offline

## Troubleshooting

### No email received
- Check GitHub Actions logs for errors
- Verify all secrets are set correctly
- Check spam folder

### Market data missing
- yfinance may have temporary outages
- Some international indices may not resolve
- The pipeline continues even if some symbols fail

### LLM errors
- Check your Gemini API key is valid
- The pipeline falls back to raw articles if LLM fails

## License

MIT
