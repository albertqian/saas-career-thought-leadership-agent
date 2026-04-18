"""
app.py — LinkedIn Post Agent
Streamlit web app for reviewing articles, generating posts, and publishing.
Deploy to Streamlit Community Cloud connected to this GitHub repo.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
import streamlit as st

PASSWORD = st.secrets.get("APP_PASSWORD", "AtGUBerF6?")

def check_password():
    def password_entered():
        if st.session_state["password"] == PASSWORD:AtGUBerF6?
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.text_input("Password", type="password", 
                      on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["authenticated"]:
        st.text_input("Password", type="password", 
                      on_change=password_entered, key="password")
        st.error("Incorrect password")
        st.stop()

check_password()

# Add agent dir to path
sys.path.insert(0, str(Path(__file__).parent / "agent"))
from generate_post import generate_posts, stream_linkedin_post
from post_to_social import post_to_socials

# ── Config ────────────────────────────────────────────────────────────────────

GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

st.set_page_config(
    page_title="Post Agent",
    page_icon="✍️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Load State ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_state_from_github():
    """Fetch state.json directly from GitHub raw content — no redeploy needed."""
    url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/state.json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None

def load_state_local():
    """Fallback: read from local filesystem (works in dev)."""
    state_path = Path(__file__).parent / "state.json"
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return None

def get_state():
    if GITHUB_OWNER and GITHUB_REPO:
        state = load_state_from_github()
        if state:
            return state
    return load_state_local()

def update_state_on_github(state: dict):
    """Commit updated state.json to GitHub via API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or not GITHUB_OWNER or not GITHUB_REPO:
        return False

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/state.json"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Get current SHA
    resp = requests.get(url, headers=headers)
    sha = resp.json().get("sha", "")

    import base64
    content = base64.b64encode(json.dumps(state, indent=2).encode()).decode()

    requests.put(url, headers=headers, json={
        "message": f"Mark article as posted [skip ci]",
        "content": content,
        "sha": sha,
        "branch": GITHUB_BRANCH,
    })
    return True

# ── Styles ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { max-width: 720px; margin: 0 auto; }
    .article-card {
        background: #f8f9fa;
        border-left: 4px solid #0a66c2;
        padding: 16px 20px;
        border-radius: 4px;
        margin-bottom: 24px;
    }
    .source-tag {
        font-size: 12px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .step-label {
        font-size: 11px;
        font-weight: 700;
        color: #0a66c2;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .success-box {
        background: #e8f5e9;
        border: 1px solid #4caf50;
        border-radius: 6px;
        padding: 16px;
        margin-top: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ── Main UI ───────────────────────────────────────────────────────────────────

st.title("✍️ Post Agent")

state = get_state()

if not state or not state.get("current"):
    st.info("No article queued. The agent runs daily — check back after your scheduled time.")
    st.stop()

article = state["current"]
stage = article.get("stage", "pending_opinion")

# ── Article Card ──────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="article-card">
  <div class="source-tag">{article.get('source', 'Unknown Source')}</div>
  <strong style="font-size: 17px; line-height: 1.4;">{article.get('title', '')}</strong>
  <p style="margin-top: 10px; color: #444; font-size: 14px; line-height: 1.6;">
    {article.get('summary', '')[:400]}...
  </p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.link_button("📄 Read Full Article", article.get("url", "#"))
with col2:
    if st.button("🔄 Refresh Article"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ── Step 1: Opinion ───────────────────────────────────────────────────────────

st.markdown('<div class="step-label">Step 1 — Your Take</div>', unsafe_allow_html=True)
st.caption("Don't polish it. Write what you actually think — the agent does the rest.")

opinion = st.text_area(
    label="Your opinion",
    placeholder="E.g. This confirms what I've been seeing in enterprise AI deployments — companies are buying tools but not changing their decision-making processes. The tech is ready. The org design isn't.",
    height=120,
    label_visibility="collapsed",
)

generate_clicked = st.button("Generate Posts →", type="primary", disabled=not opinion.strip())

# ── Step 2: Draft ─────────────────────────────────────────────────────────────

if "linkedin_draft" not in st.session_state:
    st.session_state.linkedin_draft = ""
if "facebook_draft" not in st.session_state:
    st.session_state.facebook_draft = ""
if "generated" not in st.session_state:
    st.session_state.generated = False

if generate_clicked and opinion.strip():
    st.divider()
    st.markdown('<div class="step-label">Step 2 — Review & Edit</div>', unsafe_allow_html=True)

    with st.spinner("Writing your posts..."):
        try:
            posts = generate_posts(article, opinion)
            st.session_state.linkedin_draft = posts.get("linkedin", "")
            st.session_state.facebook_draft = posts.get("facebook", "")
            st.session_state.generated = True
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.stop()

if st.session_state.generated:
    st.divider()
    st.markdown('<div class="step-label">Step 2 — Review & Edit</div>', unsafe_allow_html=True)

    tab_li, tab_fb = st.tabs(["🔵 LinkedIn", "🔷 Facebook"])

    with tab_li:
        st.session_state.linkedin_draft = st.text_area(
            "LinkedIn Post",
            value=st.session_state.linkedin_draft,
            height=300,
            label_visibility="collapsed",
        )
        char_count = len(st.session_state.linkedin_draft)
        word_count = len(st.session_state.linkedin_draft.split())
        st.caption(f"{word_count} words · {char_count} chars")

    with tab_fb:
        st.session_state.facebook_draft = st.text_area(
            "Facebook Post",
            value=st.session_state.facebook_draft,
            height=300,
            label_visibility="collapsed",
        )
        char_count_fb = len(st.session_state.facebook_draft)
        word_count_fb = len(st.session_state.facebook_draft.split())
        st.caption(f"{word_count_fb} words · {char_count_fb} chars")

    st.divider()

    # ── Step 3: Approve & Post ────────────────────────────────────────────────

    st.markdown('<div class="step-label">Step 3 — Approve & Post</div>', unsafe_allow_html=True)

    col_li, col_fb = st.columns(2)
    with col_li:
        post_linkedin = st.checkbox("Post to LinkedIn", value=True)
    with col_fb:
        post_facebook = st.checkbox("Post to Facebook", value=True)

    if "posted" not in st.session_state:
        st.session_state.posted = False

    if not st.session_state.posted:
        if st.button("🚀 Approve & Post Now", type="primary"):
            with st.spinner("Posting..."):
                try:
                    results = post_to_socials(
                        linkedin_text=st.session_state.linkedin_draft,
                        facebook_text=st.session_state.facebook_draft,
                        article_url=article.get("url", ""),
                        post_linkedin=post_linkedin,
                        post_facebook=post_facebook,
                    )

                    # Mark as posted in state
                    state["current"]["stage"] = "posted"
                    posted_url = article.get("url", "")
                    if posted_url not in state.get("history", []):
                        state.setdefault("history", []).append(posted_url)

                    update_state_on_github(state)
                    st.session_state.posted = True

                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.success("✅ Posted successfully!")

                    for r in results:
                        platform = r["platform"].capitalize()
                        if r["success"]:
                            url = r.get("url")
                            if url:
                                st.markdown(f"**{platform}:** [View post]({url})")
                            else:
                                st.markdown(f"**{platform}:** Posted ✓")
                        else:
                            st.error(f"**{platform} failed:** {r.get('error')}")

                    st.markdown('</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Posting failed: {e}")
    else:
        st.success("✅ Already posted this session.")
