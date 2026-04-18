# Post Agent — Setup Guide

A personal daily agent that surfaces relevant B2B SaaS/AI articles, captures your opinion, generates LinkedIn and Facebook posts in your voice, and publishes them on approval.

---

## How It Works

1. **GitHub Actions** runs at 8am weekdays, fetches the best article from your RSS feeds, commits it to `state.json`, and emails you a link
2. **You click the link** → Streamlit app opens with the article
3. **You type your raw opinion** → agent generates LinkedIn + Facebook posts in your voice
4. **You edit if needed** → click Approve & Post → live

---

## One-Time Setup

### 1. Fork / Clone This Repo

Push to your own GitHub account. Keep it private.

### 2. Create a Streamlit Account

Go to [share.streamlit.io](https://share.streamlit.io) → Connect GitHub → Deploy `app.py` from your repo.

### 3. Get Your API Keys

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn Developer App (see below) |
| `FACEBOOK_PAGE_ID` + `FACEBOOK_PAGE_ACCESS_TOKEN` | Meta Developer App (see below) |
| `GITHUB_TOKEN` | GitHub Settings → Developer Settings → Personal Access Tokens (repo scope) |

### 4. Set GitHub Secrets

In your repo → **Settings → Secrets and variables → Actions → New secret**:

```
ANTHROPIC_API_KEY         your Anthropic API key
STREAMLIT_APP_URL         https://yourapp.streamlit.app (your deployed URL)
EMAIL_FROM                your sending email address
EMAIL_TO                  where you want notifications sent
SMTP_HOST                 smtp.gmail.com  (or your provider)
SMTP_PORT                 587
SMTP_USER                 your Gmail address
SMTP_PASS                 Gmail App Password (not your login password)
```

### 5. Set Streamlit Secrets

In Streamlit Cloud → your app → **Settings → Secrets**:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
LINKEDIN_ACCESS_TOKEN = "..."
FACEBOOK_PAGE_ID = "..."
FACEBOOK_PAGE_ACCESS_TOKEN = "..."
GITHUB_OWNER = "your-github-username"
GITHUB_REPO = "linkedin-agent"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = "ghp_..."
```

---

## LinkedIn Setup

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Create an App → add your profile as admin
3. Request access to **Share on LinkedIn** product
4. Under Auth → OAuth 2.0 scopes: `w_member_social`, `r_liteprofile`
5. Generate an access token via OAuth flow (tokens expire in 60 days — you'll need to refresh)

**Token refresh tip:** Use [LinkedIn's token generator tool](https://www.linkedin.com/developers/tools/oauth) in the developer portal.

---

## Facebook Setup

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create an App → type: Business
3. Add **Pages API** product
4. Generate a Page Access Token for your Page (not your personal profile)
5. Extend the token to a long-lived token (60 days) via Graph API Explorer

**Note:** Facebook personal profiles cannot be posted to via API. You need a Facebook Page.

---

## Gmail App Password (for email notifications)

1. Google Account → Security → 2-Step Verification (must be on)
2. Search "App passwords" → Generate for "Mail"
3. Use that 16-character password as `SMTP_PASS`

---

## Customizing Your Sources

Edit `config/sources.json`:

- Add/remove RSS feeds in the `feeds` array
- Add keywords to `high_value` to boost topic relevance
- Add terms to `exclude` to filter out off-topic articles
- Adjust `scoring.min_score_threshold` (higher = more selective)

---

## Adjusting the Schedule

Edit `.github/workflows/daily_article.yml`:

```yaml
- cron: "0 15 * * 1-5"   # 8am PT, Mon-Fri
```

Cron uses UTC. Converter: [crontab.guru](https://crontab.guru)

---

## Adjusting Your Voice

Edit `voice_profile.md` — this is what the AI reads when generating posts. Update it when your focus areas, tone, or typical post structure evolves.

---

## File Structure

```
linkedin-agent/
├── .github/workflows/
│   └── daily_article.yml     # Runs daily, fetches article, sends email
├── agent/
│   ├── fetch_articles.py     # RSS fetcher + scorer + email sender
│   ├── generate_post.py      # Claude-powered post generator
│   └── post_to_social.py     # LinkedIn + Facebook API calls
├── config/
│   └── sources.json          # RSS feeds, keywords, scoring config
├── app.py                    # Streamlit web UI
├── state.json                # Current article + URL history
├── voice_profile.md          # Your writing voice (edit this)
└── requirements.txt
```

---

## Troubleshooting

**No email received:** Check GitHub Actions logs under the Actions tab. Verify SMTP secrets are set correctly.

**"No article queued" in app:** The previous article is still marked `pending_opinion`, or no articles scored above threshold. Trigger the workflow manually from the Actions tab.

**LinkedIn post fails:** Access tokens expire every 60 days. Regenerate via the LinkedIn developer portal.

**State doesn't update:** Verify `GITHUB_TOKEN` has `repo` scope in Streamlit secrets.
