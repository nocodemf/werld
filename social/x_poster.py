"""
X (Twitter) Auto-Poster — turns story chapters into tweet threads.

Each story chapter is:
  1. Sent to Gemini LLM to be rewritten as a tweet thread
  2. Posted as: 1 hook tweet + up to 6 follow-up replies
  3. Tracked in the database to avoid duplicate posts

Commentates as if observing a tiny digital civilisation from the outside —
warm, curious, and slightly awed, like a nature documentary narrator.

Character limits (standard X account):
  - 280 characters per tweet
  - URLs count as 23 characters (t.co wrapping)
  - Threads are created by replying to the previous tweet

Requires:
  pip install tweepy google-genai python-dotenv
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from persistence.db import get_connection

# ── Environment ──────────────────────────────────────────────────────────────

def _load_env() -> None:
    """Load .env file from project root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(env_path)
    except ImportError:
        pass  # User must set env vars manually


_load_env()

X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY", "")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3000")

# ── Constants ────────────────────────────────────────────────────────────────

MAX_TWEET_CHARS = 280
MAX_THREAD_TWEETS = 7  # 1 hook + up to 6 follow-ups
TWEET_SAFE_CHARS = 270  # Leave margin for edge cases

# Minimum hours between tweet posts (X free tier = 500 posts/month)
# At 2 threads/day × 7 tweets = 14/day × 30 = 420/month — safely under limit
MIN_HOURS_BETWEEN_POSTS = 12


# ── Database: track posted chapters ──────────────────────────────────────────

def _ensure_table() -> None:
    """Create the posted_tweets table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posted_tweets (
            chapter     INTEGER PRIMARY KEY,
            tweet_ids   TEXT,
            posted_at   TEXT
        )
    """)
    conn.commit()


def _already_posted(chapter: int) -> bool:
    """Check if a chapter has already been posted to X."""
    _ensure_table()
    conn = get_connection()
    row = conn.execute(
        "SELECT chapter FROM posted_tweets WHERE chapter = ?", (chapter,)
    ).fetchone()
    return row is not None


def _record_posted(chapter: int, tweet_ids: List[str]) -> None:
    """Record that a chapter was posted."""
    _ensure_table()
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO posted_tweets (chapter, tweet_ids, posted_at) VALUES (?, ?, ?)",
        (chapter, json.dumps(tweet_ids), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


# ── Gemini: generate tweet thread from chapter ───────────────────────────────

SYSTEM_PROMPT = """You narrate updates from a long-running artificial life experiment. Tiny autonomous agents live in a simulated world — they're born, they struggle to survive, they evolve, they reproduce, and they die. Nobody controls them. We just watch.

You post updates to X after each epoch, narrating what happened like a nature documentary. Your audience is general — no tech jargon, no scientific terminology. Anyone should be able to read this and find it interesting.

VOICE:
- Warm and observant. You're narrating life unfolding in a small world. Think nature documentary, not lab report.
- Plain language. Say "their brains got more complex" not "neural architecture evolved rapidly." Say "a few are left" not "population declined to 14."
- Don't react to things. Don't say "wow", "incredible", "I didn't expect this." Just describe what happened and let it speak for itself.
- Use contrast to create natural tension: "more were born than ever before, but more died too."
- Numbers are good when they make it concrete — "just 4 remain" or "28 were born and 26 didn't make it." Don't list stats.
- "we" = the people running the experiment. "they" = the agents/creatures.
- Light anthropomorphism is natural — "they started talking to each other", "they figured out how to chain actions together." Just don't get sentimental.
- Go into detail in the thread. Don't just skim the surface — explain what's happening with their brains, their communication, their species. Make each tweet say something substantive. But say it plainly.

STRUCTURE:
- Tweet 1 (HOOK): Set the scene. One or two sentences that draw someone in. End with 🧵
- Tweets 2-6: Tell the story of this epoch in order. What happened to the population, how they're evolving, what new behaviours appeared, how they're communicating. Each tweet should carry real content.
- FINAL tweet: End with the live dashboard link: {dashboard_url}
  Something natural like "You can watch them live here: {dashboard_url}" (URLs = 23 chars on X)

HARD RULES:
- Every tweet MUST be under 275 characters.
- 5-7 tweets total. Use the space — don't cut it short.
- Return ONLY a JSON array of strings. No markdown, no explanation.
- NO hashtags. NO numbering. One 🧵 on the hook, no other emoji."""


def _generate_thread(title: str, content: str, chapter_num: int) -> Optional[List[str]]:
    """Use Gemini to turn a story chapter into a tweet thread."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "REPLACE_ME":
        print("  [X-POSTER] Gemini API key not configured — skipping tweet generation")
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("  [X-POSTER] google-genai not installed — pip install google-genai")
        return None

    prompt = f"""Chapter {chapter_num + 1}: "{title}"

{content}

Turn this into an X thread (JSON array of tweet strings). Remember: each tweet under 275 chars, 3-7 tweets total, last tweet includes {DASHBOARD_URL}"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT.format(dashboard_url=DASHBOARD_URL),
                temperature=0.8,
                max_output_tokens=2000,
                response_mime_type="application/json",
            ),
        )

        # Parse the JSON response
        text = response.text.strip()
        # Handle potential markdown code block wrapping
        if text.startswith("```"):
            text = text.split("\n", 1)[1]  # Remove first line
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        tweets: List[str] = json.loads(text)

        # Validate
        if not isinstance(tweets, list) or len(tweets) < 2:
            print(f"  [X-POSTER] Gemini returned invalid format: {text[:100]}")
            return None

        # Enforce character limits
        valid_tweets = []
        for tweet in tweets[:MAX_THREAD_TWEETS]:
            if len(tweet) > MAX_TWEET_CHARS:
                # Truncate gracefully at word boundary
                tweet = tweet[:MAX_TWEET_CHARS - 3]
                last_space = tweet.rfind(" ")
                if last_space > MAX_TWEET_CHARS - 50:
                    tweet = tweet[:last_space]
                tweet += "..."
            valid_tweets.append(tweet)

        return valid_tweets

    except Exception as e:
        print(f"  [X-POSTER] Gemini error: {e}")
        return None


# ── X (Twitter): post thread ─────────────────────────────────────────────────

def _post_thread(tweets: List[str]) -> Optional[List[str]]:
    """Post a thread to X. Returns list of tweet IDs, or None on failure."""
    if not all([X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        print("  [X-POSTER] X API credentials not fully configured — skipping post")
        return None

    if X_CONSUMER_SECRET == "REPLACE_ME":
        print("  [X-POSTER] X Consumer Secret not set — skipping post")
        return None

    try:
        import tweepy
    except ImportError:
        print("  [X-POSTER] tweepy not installed — pip install tweepy")
        return None

    try:
        client = tweepy.Client(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
        )

        tweet_ids: List[str] = []

        # Post hook tweet
        response = client.create_tweet(text=tweets[0])
        hook_id = response.data["id"]
        tweet_ids.append(str(hook_id))
        print(f"  [X-POSTER] Hook tweet posted: {hook_id}")

        # Post thread replies
        prev_id = hook_id
        for i, tweet_text in enumerate(tweets[1:], 1):
            # Small delay to avoid rate limits
            time.sleep(1)
            response = client.create_tweet(
                text=tweet_text,
                in_reply_to_tweet_id=prev_id,
            )
            tid = response.data["id"]
            tweet_ids.append(str(tid))
            prev_id = tid
            print(f"  [X-POSTER] Thread {i}/{len(tweets)-1} posted: {tid}")

        return tweet_ids

    except Exception as e:
        print(f"  [X-POSTER] Failed to post to X: {e}")
        return None


# ── Public API ───────────────────────────────────────────────────────────────

def post_chapter_to_x(chapter_num: int, title: str, content: str) -> bool:
    """
    Generate a tweet thread from a story chapter and post it to X.

    Returns True if the thread was posted successfully, False otherwise.
    Called from the simulation loop after a new story chapter is generated.
    """
    # Check if already posted
    if _already_posted(chapter_num):
        return False

    print(f"  [X-POSTER] Generating thread for Chapter {chapter_num + 1}: {title}")

    # Generate tweet thread via Gemini
    tweets = _generate_thread(title, content, chapter_num)
    if not tweets:
        return False

    # Log the generated tweets (for debugging)
    for i, t in enumerate(tweets):
        print(f"  [X-POSTER]   Tweet {i+1} ({len(t)} chars): {t[:80]}{'...' if len(t) > 80 else ''}")

    # Post to X
    tweet_ids = _post_thread(tweets)
    if not tweet_ids:
        return False

    # Record in DB
    _record_posted(chapter_num, tweet_ids)
    print(f"  [X-POSTER] Chapter {chapter_num + 1} thread posted successfully ({len(tweet_ids)} tweets)")
    return True


def _hours_since_last_post() -> float:
    """Return hours since the last tweet was posted, or infinity if never posted."""
    _ensure_table()
    conn = get_connection()
    row = conn.execute(
        "SELECT posted_at FROM posted_tweets ORDER BY chapter DESC LIMIT 1"
    ).fetchone()
    if not row or not row["posted_at"]:
        return float("inf")
    last = datetime.fromisoformat(row["posted_at"])
    now = datetime.now(timezone.utc)
    return (now - last).total_seconds() / 3600


def post_latest_unposted_chapter() -> bool:
    """
    Find the latest story chapter that hasn't been posted to X yet, and post it.
    Respects MIN_HOURS_BETWEEN_POSTS to stay within X API rate limits.
    Returns True if a chapter was posted.
    """
    # Rate limit: don't post too frequently (X free tier = 500 posts/month)
    hours = _hours_since_last_post()
    if hours < MIN_HOURS_BETWEEN_POSTS:
        remaining = MIN_HOURS_BETWEEN_POSTS - hours
        print(f"  [X-POSTER] Rate limit: next post in {remaining:.1f}h")
        return False

    _ensure_table()
    conn = get_connection()

    # Find the LATEST unposted chapter (skip intermediate ones — post the most recent)
    row = conn.execute("""
        SELECT sc.chapter, sc.title, sc.content
        FROM story_chapters sc
        LEFT JOIN posted_tweets pt ON sc.chapter = pt.chapter
        WHERE pt.chapter IS NULL
        ORDER BY sc.chapter DESC
        LIMIT 1
    """).fetchone()

    if not row:
        return False

    return post_chapter_to_x(row["chapter"], row["title"], row["content"])

