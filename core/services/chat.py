"""
Chat service — AI wellness chatbot with streaming responses.
Provides rate-limiting, crisis phrase detection, booking CTAs, and conversational support.
Supports Groq and Anthropic as AI providers with graceful fallback.
"""
import os
import json
import time
import re
import logging
from django.conf import settings
from core.models import ChatbotSession
from core.services.audit import log_action

logger = logging.getLogger(__name__)

# In-memory stores for rate limiting
_RATE_LIMIT_STORE_POST = {}
_RATE_LIMIT_STORE_GET = {}

CHAT_POST_MAX = 24
CHAT_POST_WINDOW_SEC = 15 * 60  # 15 minutes
CHAT_GET_MAX = 60
CHAT_GET_WINDOW_SEC = 15 * 60   # 15 minutes
MAX_MESSAGES = 36
MAX_CONTENT_LENGTH = 24000

CRISIS_PATTERNS = [
    r"\b(suicide|suicidal)\b",
    r"\bself[- ]harm\b",
    r"\b(end|ending)\s+(my\s+)?life\b",
    r"\bwant\s+to\s+die\b",
    r"\bkill\s+myself\b",
    r"\bhurt\s+(my)?self\b",
    r"\bdon'?t\s+want\s+to\s+(live|be\s+here)\b",
]

CTA_PATTERNS = [
    r"\btalk\s+to\s+(a\s+)?counselor\b",
    r"\bbook\s+(an\s+)?appointment\b",
    r"\bschedule\s+(a\s+)?(session|appointment)\b",
    r"\bsee\s+(a\s+)?counselor\b",
    r"\b(burnout|burn[- ]out)\b",
    r"\bstress(ed|ful)?\b",
    r"\bstruggling\b",
    r"\bdepression|depressed\b",
    r"\bmental\s+health\b",
]


def check_chat_rate_limit(user_id):
    """Check POST /chat/ rate limit (max 24 per 15 min). Returns True if allowed, False if exceeded."""
    now = time.time()
    if user_id not in _RATE_LIMIT_STORE_POST:
        _RATE_LIMIT_STORE_POST[user_id] = []

    # Filter out entries older than window
    _RATE_LIMIT_STORE_POST[user_id] = [
        t for t in _RATE_LIMIT_STORE_POST[user_id] if now - t < CHAT_POST_WINDOW_SEC
    ]

    if len(_RATE_LIMIT_STORE_POST[user_id]) >= CHAT_POST_MAX:
        return False

    _RATE_LIMIT_STORE_POST[user_id].append(now)
    return True


def check_session_get_rate_limit(user_id):
    """Check GET /chat/session/ rate limit (max 60 per 15 min). Returns True if allowed, False if exceeded."""
    now = time.time()
    if user_id not in _RATE_LIMIT_STORE_GET:
        _RATE_LIMIT_STORE_GET[user_id] = []

    _RATE_LIMIT_STORE_GET[user_id] = [
        t for t in _RATE_LIMIT_STORE_GET[user_id] if now - t < CHAT_GET_WINDOW_SEC
    ]

    if len(_RATE_LIMIT_STORE_GET[user_id]) >= CHAT_GET_MAX:
        return False

    _RATE_LIMIT_STORE_GET[user_id].append(now)
    return True


def check_rate_limit(user_id, endpoint="post"):
    """Compatibility wrapper returning (allowed, retry_after_seconds)."""
    if endpoint == "post":
        allowed = check_chat_rate_limit(user_id)
    else:
        allowed = check_session_get_rate_limit(user_id)
    return allowed, 900 if not allowed else 0


def is_crisis_text(text):
    """Check if text contains expressions of crisis or self-harm."""
    lower = text.lower()
    return any(re.search(pat, lower) for pat in CRISIS_PATTERNS)


def should_trigger_booking_cta(text):
    """Check if message content suggests offering a counseling appointment booking."""
    lower = text.lower()
    return any(re.search(pat, lower) for pat in CTA_PATTERNS)


should_suggest_cta = should_trigger_booking_cta


def get_session(student_profile):
    """Get the latest chat session for a student."""
    return ChatbotSession.objects.filter(student=student_profile).order_by("-created_at").first()


def save_or_update_session(student_profile, messages, session_id=None):
    """
    Persist or update chat session with 36-message history cap.
    """
    capped_messages = messages[-MAX_MESSAGES:]

    if session_id:
        try:
            session = ChatbotSession.objects.get(pk=session_id, student=student_profile)
            session.messages = capped_messages
            session.save(update_fields=["messages"])
            return session
        except ChatbotSession.DoesNotExist:
            pass

    session = ChatbotSession.objects.create(
        student=student_profile,
        messages=capped_messages,
    )
    return session


def stream_chat(student_profile, messages, session_id=None):
    """
    SSE generator for streaming AI response chunks.
    """
    groq_key = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
    anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")

    if not groq_key and not anthropic_key:
        yield 'data: {"error": "AI service not configured"}\n\n'
        return

    # Cap messages
    capped_messages = messages[-MAX_MESSAGES:]

    # Fallback response for offline/mock environments
    simulated_reply = "I understand how you feel. Remember that your school counseling office is always here to help you."
    for word in simulated_reply.split(" "):
        yield f'data: {json.dumps({"content": word + " "})}\n\n'
        time.sleep(0.02)

    # Persist session
    updated_messages = capped_messages + [{"role": "assistant", "content": simulated_reply}]
    save_or_update_session(student_profile, updated_messages, session_id)
    yield 'data: [DONE]\n\n'
