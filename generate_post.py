"""
generate_post.py
Given an article and a raw opinion, generates LinkedIn and Facebook posts
in the user's voice using Claude. Returns both drafts as a dict.
"""

import os
import anthropic
from pathlib import Path

ROOT = Path(__file__).parent.parent
VOICE_PROFILE_PATH = ROOT / "voice_profile.md"

def load_voice_profile():
    with open(VOICE_PROFILE_PATH) as f:
        return f.read()

def generate_posts(article: dict, opinion: str) -> dict:
    """
    article: dict with keys: title, url, summary, source
    opinion: raw opinion text from the user
    Returns: {"linkedin": str, "facebook": str}
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    voice_profile = load_voice_profile()

    system_prompt = f"""You are a ghostwriter producing LinkedIn and Facebook posts for a B2B SaaS and AI marketer.

Your job is to translate their raw opinion into a polished post that sounds exactly like them — not like a content marketer, not like an AI assistant, and not like a press release.

Here is their complete voice profile. Follow it precisely:

{voice_profile}

CRITICAL RULES:
- Never start a post with "I" — it's a weak opener on LinkedIn
- No phrases like "Great read", "Fascinating article", "This is a must-read"
- No fake enthusiasm. No hollow affirmations.
- Do not summarize the article — the post is about THEIR take, not the article
- The article is context. The opinion is the content.
- Do not make up facts or statistics not provided
- Preserve the user's specific argument — sharpen it, don't replace it
- LinkedIn post: 150-250 words, no markdown, line breaks between thoughts, 3 hashtags max at the end
- Facebook post: same length, warmer tone, no hashtags needed
- Return ONLY valid JSON — no preamble, no explanation, no markdown fences
"""

    user_prompt = f"""Article:
Title: {article['title']}
Source: {article['source']}
URL: {article['url']}
Summary: {article['summary']}

My raw opinion:
{opinion}

Generate both posts. Return ONLY this JSON structure:
{{
  "linkedin": "the full linkedin post text here",
  "facebook": "the full facebook post text here"
}}"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )

    import json
    raw = message.content[0].text.strip()
    # Strip markdown fences if model includes them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    return result


def stream_linkedin_post(article: dict, opinion: str):
    """
    Generator that streams the LinkedIn post token by token.
    Used by Streamlit for real-time display.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    voice_profile = load_voice_profile()

    system_prompt = f"""You are a ghostwriter producing a LinkedIn post for a B2B SaaS and AI marketer.

Voice profile:
{voice_profile}

Write ONLY the LinkedIn post — no preamble, no explanation, no labels.
150-250 words. No markdown. Line breaks between thoughts. End with 3 hashtags max."""

    user_prompt = f"""Article: {article['title']} ({article['source']})
Summary: {article['summary'][:300]}

My opinion: {opinion}

Write the LinkedIn post now."""

    with client.messages.stream(
        model="claude-opus-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    ) as stream:
        for text in stream.text_stream:
            yield text
