"""
app.py — LinkedIn Post Agent
Streamlit web app for reviewing articles, generating posts, and publishing.
"""

import json
import os
import sys
from pathlib import Path

import requests
import streamlit as st

# ── Password Gate ─────────────────────────────────────────────────────────────

def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
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
from generate_post import generate_posts, generate_summary
from fetch_articles import fetch_and_save_article
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

# ── State Management ──────────────────────────────────────────────────────────

def load_state_from_github():
    url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/state.json"
    try:
        resp = requests.get(url, params={"t": os.urandom(4).hex()}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

def load_state_local():
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
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or not GITHUB_OWNER or not GITHUB_REPO:
        return False
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/state.json"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(url, headers=headers)
    sha = resp.json().get("sha", "")
    import base64
    content = base64.b64encode(json.dumps(state, indent=2).encode()).decode()
    requests.put(url, headers=headers, json={
        "message": "Update article state [skip ci]",
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
        margin-bottom: 16px;
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
    .summary-box {
        background: #eef4fb;
        border-radius: 6px;
        padding: 14px 18px;
        margin-bottom: 20px;
        font-size: 14px;
        line-height: 1.7;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# ── Session State Init ────────────────────────────────────────────────────────

for key, default in [
    ("linkedin_draft", ""),
    ("facebook_draft", ""),
    ("generated", False),
    ("posted", False),
    ("ai_summary", ""),
    ("summary_loaded", False),
    ("state", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def reset_article_state():
    st.session_state.summary_loaded = False
    st.session_state.ai_summary = ""
    st.session_state.generated = False
    st.session_state.posted = False
    st.session_state.linkedin_draft = ""
    st.session_state.facebook_draft = ""

# ── Main UI ───────────────────────────────────────────────────────────────────

st.title("✍️ Post Agent")

if st.session_state.state is None:
    st.session_state.state = get_state()

state = st.session_state.state

if not state or not state.get("current"):
    st.info("No article queued yet. Fetching one now...")
    with st.spinner("Finding the best article for you..."):
        article = fetch_and_save_article()
        if article:
            update_state_on_github({"current": article, "history": []})
            st.session_state.state = {"current": article, "history": []}
            reset_article_state()
            st.rerun()
        else:
            st.error("No qualifying articles found right now. Try again later.")
            st.stop()

article = state["current"]

# ── Article Card ──────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="article-card">
  <div class="source-tag">{article.get('source', 'Unknown Source')}</div>
  <strong style="font-size: 17px; line-height: 1.4;">{article.get('title', '')}</strong>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    st.link_button("📄 Read Full Article", article.get("url", "#"))
with col2:
    if st.button("⏭️ Next Article"):
        with st.spinner("Finding next article..."):
            current_url = article.get("url", "")
            # Add current to history so it won't repeat
            history = state.get("history", [])
            if current_url not in history:
                history.append(current_url)
            new_article = fetch_and_save_article(skip_url=current_url)
            if new_article:
                new_state = {"current": new_article, "history": history}
                update_state_on_github(new_state)
                st.session_state.state = new_state
                reset_article_state()
                st.rerun()
            else:
                st.warning("No more qualifying articles available right now.")

st.divider()

# ── AI Summary ────────────────────────────────────────────────────────────────

st.markdown('<div class="step-label">What This Article Is About</div>', unsafe_allow_html=True)

if not st.session_state.summary_loaded:
    with st.spinner("Summarizing..."):
        try:
            st.session_state.ai_summary = generate_summary(article)
        except Exception:
            st.session_state.ai_summary = article.get("summary", "")[:400]
        st.session_state.summary_loaded = True

st.markdown(f'<div class="summary-box">{st.session_state.ai_summary}</div>', unsafe_allow_html=True)

st.divider()

# ── Step 1: Opinion ───────────────────────────────────────────────────────────

st.markdown('<div class="step-label">Step 1 — Your Take</div>', unsafe_allow_html=True)
st.caption("Bullet points or prose — either works. Just write what you actually think.")

opinion = st.text_area(
    label="Your opinion",
    placeholder="- AI adoption is outpacing org readiness\n- Most teams don't have clean enough data\n- The real bottleneck is decision-making culture, not the tech",
    height=140,
    label_visibility="collapsed",
)

generate_clicked = st.button("Generate Posts →", type="primary", disabled=not opinion.strip())

# ── Step 2: Draft ─────────────────────────────────────────────────────────────

if generate_clicked and opinion.strip():
    with st.spinner("Writing your posts..."):
        try:
            posts = generate_posts(article, opinion)
            st.session_state.linkedin_draft = posts.get("linkedin", "")
            st.session_state.facebook_draft = posts.get("facebook", "")
            st.session_state.generated = True
            st.session_state.posted = False
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
        word_count = len(st.session_state.linkedin_draft.split())
        char_count = len(st.session_state.linkedin_draft)
        st.caption(f"{word_count} words · {char_count} chars")

    with tab_fb:
        st.session_state.facebook_draft = st.text_area(
            "Facebook Post",
            value=st.session_state.facebook_draft,
            height=300,
            label_visibility="collapsed",
        )
        word_count_fb = len(st.session_state.facebook_draft.split())
        char_count_fb = len(st.session_state.facebook_draft)
        st.caption(f"{word_count_fb} words · {char_count_fb} chars")

    st.divider()

    # ── Step 3: Copy & Post ───────────────────────────────────────────────────

    st.markdown('<div class="step-label">Step 3 — Copy & Post</div>', unsafe_allow_html=True)
    st.caption("Select all text in either tab above, copy, and paste into LinkedIn or Facebook.")

    col_li, col_fb = st.columns(2)
    with col_li:
        st.link_button("🔵 Open LinkedIn", "https://www.linkedin.com/feed/")
    with col_fb:
        st.link_button("🔷 Open Facebook", "https://www.facebook.com/")
