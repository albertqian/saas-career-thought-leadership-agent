"""
fetch_articles.py
Fetches the best article from configured RSS feeds.
Can be run as a GitHub Actions job (main) or imported by the Streamlit app
for on-demand article refresh.
"""

import feedparser
import json
import os
import re
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.json"
STATE_PATH = ROOT / "state.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"current": None, "history": []}

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def article_id(url):
    return hashlib.md5(url.encode()).hexdigest()[:12]

def score_article(title, summary, config):
    text = (title + " " + summary).lower()
    score = 0
    keywords = config["keywords"]
    weights = config["scoring"]

    for kw in keywords["exclude"]:
        if kw.lower() in text:
            score += weights["exclude_penalty"]

    for kw in keywords["high_value"]:
        if kw.lower() in text:
            score += weights["high_value_weight"]

    for kw in keywords["medium_value"]:
        if kw.lower() in text:
            score += weights["medium_value_weight"]

    return score

# ── Core ──────────────────────────────────────────────────────────────────────

def fetch_best_article(config, seen_urls):
    """
    Fetches and scores articles from all configured feeds.
    Returns the single highest-scoring unseen article, or None.
    """
    candidates = []
    min_score = config["scoring"]["min_score_threshold"]

    for feed_info in config["feeds"]:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:15]:
                url = entry.get("link", "")
                if not url or url in seen_urls:
                    continue

                title = entry.get("title", "")
                summary = strip_html(entry.get("summary", ""))[:600]
                score = score_article(title, summary, config)
                score *= feed_info.get("weight", 1.0)

                if score >= min_score:
                    candidates.append({
                        "id": article_id(url),
                        "title": title,
                        "url": url,
                        "summary": summary,
                        "source": feed_info["name"],
                        "score": score,
                        "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "stage": "pending_opinion",
                    })
        except Exception as e:
            print(f"[WARN] Failed to parse {feed_info['name']}: {e}")

    if not candidates:
        return None

    return sorted(candidates, key=lambda x: x["score"], reverse=True)[0]


def fetch_and_save_article(skip_url=None):
    """
    Callable from both GitHub Actions and the Streamlit app.
    Fetches a new article, updates state, returns the article dict or None.
    skip_url: optionally skip a specific URL (the one currently shown)
    """
    config = load_config()
    state = load_state()

    seen_urls = set(state.get("history", []))
    if skip_url:
        seen_urls.add(skip_url)

    article = fetch_best_article(config, seen_urls)

    if not article:
        return None

    state["current"] = article
    save_state(state)
    return article

# ── GitHub Actions entrypoint ─────────────────────────────────────────────────

def main():
    config = load_config()
    state = load_state()
    seen_urls = set(state.get("history", []))

    if state.get("current") and state["current"].get("stage") == "pending_opinion":
        print("[SKIP] Previous article still pending opinion.")
        sys.exit(0)

    article = fetch_best_article(config, seen_urls)

    if not article:
        print("[SKIP] No qualifying articles found today.")
        sys.exit(0)

    print(f"[OK] Selected: {article['title']} ({article['source']}, score={article['score']:.1f})")
    state["current"] = article
    save_state(state)
    print("[DONE] State updated.")

if __name__ == "__main__":
    main()
