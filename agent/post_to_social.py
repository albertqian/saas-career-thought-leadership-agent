"""
post_to_social.py
Posts content to LinkedIn and/or Facebook.
Returns a dict of results with post URLs where available.
"""

import os
import json
import requests

# ── LinkedIn ──────────────────────────────────────────────────────────────────

def post_to_linkedin(text: str, article_url: str) -> dict:
    """
    Posts to LinkedIn using the UGC Posts API.
    Requires LINKEDIN_ACCESS_TOKEN with w_member_social scope.
    """
    token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Get the authenticated user's URN
    profile_resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers=headers,
        timeout=10,
    )
    profile_resp.raise_for_status()
    person_urn = f"urn:li:person:{profile_resp.json()['sub']}"

    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text
                },
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "originalUrl": article_url,
                    }
                ],
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()

    post_id = resp.headers.get("x-restli-id", "")
    post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else None

    return {
        "platform": "linkedin",
        "success": True,
        "post_id": post_id,
        "url": post_url,
    }


# ── Facebook ──────────────────────────────────────────────────────────────────

def post_to_facebook(text: str, article_url: str) -> dict:
    """
    Posts to a Facebook Page.
    Requires FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN.
    Note: Facebook personal profiles cannot be posted to via API.
    This requires a Facebook Page.
    """
    page_id = os.environ["FACEBOOK_PAGE_ID"]
    page_token = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]

    full_text = f"{text}\n\n{article_url}"

    resp = requests.post(
        f"https://graph.facebook.com/v19.0/{page_id}/feed",
        data={
            "message": full_text,
            "access_token": page_token,
        },
        timeout=15,
    )
    resp.raise_for_status()
    post_id = resp.json().get("id", "")
    post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}" if post_id else None

    return {
        "platform": "facebook",
        "success": True,
        "post_id": post_id,
        "url": post_url,
    }


# ── Dispatcher ────────────────────────────────────────────────────────────────

def post_to_socials(
    linkedin_text: str,
    facebook_text: str,
    article_url: str,
    post_linkedin: bool = True,
    post_facebook: bool = True,
) -> list[dict]:
    """
    Posts to configured platforms and returns list of result dicts.
    Errors are caught per-platform so one failure doesn't block the other.
    """
    results = []

    if post_linkedin:
        try:
            result = post_to_linkedin(linkedin_text, article_url)
            results.append(result)
        except Exception as e:
            results.append({"platform": "linkedin", "success": False, "error": str(e)})

    if post_facebook:
        try:
            result = post_to_facebook(facebook_text, article_url)
            results.append(result)
        except Exception as e:
            results.append({"platform": "facebook", "success": False, "error": str(e)})

    return results
